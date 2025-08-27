from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.db.models import Q, Sum, F, ExpressionWrapper, FloatField
from django.db import transaction
from django.core.paginator import Paginator
from apps.inventory.models import Transfer, TransferItems, Inventory, ActivityLog, Holdtransfer, Accessory, DefectiveItem, WriteOff, InventoryShrinkage
from apps.core.company.models import Branch
from loguru import logger
import json
import datetime
from collections import defaultdict
from ..forms import DefectiveForm, addTransferForm

class ProcessTransferCartView(View):
    """Handle product transfers between branches."""

    def post(self, request, *args, **kwargs) -> JsonResponse:
        """
        Process a transfer request or create a held transfer.
        Returns JSON response indicating success or failure.
        """
        try:
            data = json.loads(request.body)
            action = data['action']

            logger.info(f'data: {data}')

            if action == 'process':
                with transaction.atomic():
                    user = request.user
                    user_branch = user.branch

                    branches_data = data['branches_to']
                    transfer_id = data.get('transfer_id', '')
                    cart = data['cart']

                    # Get branch objects
                    branch_objects = []
                    for branch in branches_data:
                        if branch.get('value'):
                            branch_obj = Branch.objects.get(id=branch['value'])
                        else:
                            branch_obj = Branch.objects.get(name=branch['name'])
                        branch_objects.append(branch_obj)

                    # Get products
                    products = Inventory.objects.filter(branch=user_branch).select_related('branch')
                    products_dict = {product.id: product for product in products}

                    # Validate quantities
                    product_quantities = defaultdict(int)
                    for item in cart:
                        product_quantities[item['product_id']] += item['quantity']

                    for product_id, total_quantity in product_quantities.items():
                        product = products_dict.get(int(product_id))
                        if total_quantity > product.quantity:
                            raise ValueError(f'Insufficient stock for product: {product.name}')

                    # Create or get transfer
                    branch_names = [branch['name'] for branch in branches_data]
                    if not transfer_id:
                        transfer = Transfer.objects.create(
                            branch=user_branch,
                            user=user,
                            transfer_ref=Transfer.generate_transfer_ref(user_branch.name, branch_names),
                            description='transfer'
                        )
                    else:
                        transfer = Transfer.objects.get(id=transfer_id)

                    transfer.transfer_to.set(branch_objects)

                    # Process transfer items
                    track_quantity = 0
                    transfer_items = []

                    for branch_obj in branch_objects:
                        for item in cart:
                            if item['branch_name'] == branch_obj.name:
                                product = products_dict.get(int(item['product_id']))
                                transfer_item = TransferItems(
                                    transfer=transfer,
                                    product=product,
                                    cost=item['cost'],
                                    price=item['price'],
                                    dealer_price=item['dealer_price'],
                                    quantity=item['quantity'],
                                    from_branch=user_branch,
                                    to_branch=branch_obj,
                                    description=f'from {user_branch} to {branch_obj}'
                                )
                                transfer_items.append(transfer_item)
                                track_quantity += item['quantity']

                    created_items = TransferItems.objects.bulk_create(transfer_items)

                    # Update inventory and create activity logs
                    for transfer_item in created_items:
                        inventory = Inventory.objects.select_for_update().get(
                            id=transfer_item.product.id,
                            branch__name=transfer_item.from_branch
                        )
                        inventory.quantity -= int(transfer_item.quantity)
                        inventory.save()

                        ActivityLog.objects.create(
                            invoice=None,
                            product_transfer=transfer_item,
                            branch=user_branch,
                            user=user,
                            action='transfer out',
                            dealer_price=transfer_item.dealer_price,
                            selling_price=transfer_item.price,
                            inventory=inventory,
                            system_quantity=inventory.quantity,
                            quantity=-transfer_item.quantity,
                            total_quantity=inventory.quantity,
                            description=f'to {transfer_item.to_branch}'
                        )

                        transfer.quantity += transfer_item.quantity

                    transfer.total_quantity_track = track_quantity
                    transfer.hold = False
                    transfer.date = datetime.datetime.now()
                    transfer.save()

                    return JsonResponse({'success': True, 'message': 'Transfer processed successfully'})

            else:
                return JsonResponse({'success': True, 'message': 'Held transfer saved'})

        except Exception as e:
            logger.error(f"Error processing transfer: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

@login_required
def delete_transfer(request, transfer_id):
    try:
        transfer = get_object_or_404(Transfer, id=transfer_id)

        if transfer.receive_status:
            return JsonResponse({'success':False, 'message':f'Cancel failed the transfer is already received.'})

        transfer_items = TransferItems.objects.filter(transfer=transfer)

        with transaction.atomic():
            inventory_updates = []
            activity_logs = []
            quantity_updates = {}

            for item in transfer_items:
                product = Inventory.objects.get(branch=item.from_branch, id=item.product.id)

                if product.id not in quantity_updates:
                    quantity_updates[product.id] = {'product': product, 'increment': 0}

                quantity_updates[product.id]['increment'] += item.quantity

            for update in quantity_updates.values():
                product = update['product']
                product.quantity += update['increment']
                inventory_updates.append(product)

                activity_logs.append(ActivityLog(
                    invoice=None,
                    product_transfer=None,
                    branch=request.user.branch,
                    user=request.user,
                    action='transfer cancel',
                    inventory=product,
                    selling_price=None,
                    dealer_price=None,
                    quantity=update['increment'],
                    total_quantity=product.quantity,
                    description='Transfer cancelled'
                ))

            Inventory.objects.bulk_update(inventory_updates, ['quantity'])
            ActivityLog.objects.bulk_create(activity_logs)

            transfer.delete = True
            transfer.save()

        return JsonResponse({'success':True})
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'})


@login_required
def transfer_details(request, transfer_id):
    transfer = TransferItems.objects.filter(id=transfer_id).values(
        'product__name',
        'transfer__transfer_ref',
        'quantity',
        'price',
        'from_branch__name',
        'to_branch__name'
    ).select_related(
        'transfer',
        'transfer_to',
        'transfer_from'
    )
    return JsonResponse(list(transfer), safe=False)

@login_required
def inventory_transfer_index(request):
    q = request.GET.get('q', '')
    branch_id = request.GET.get('branch', '')
    page_number = request.GET.get('page', 1)

    transfers = Transfer.objects.filter(
        Q(branch=request.user.branch) | Q(transfer_to=request.user.branch),
        delete=False
    ).annotate(
        total_quantity=Sum('transferitems__quantity'),
        total_received_qnt=Sum('transferitems__received_quantity'),
        total_r_difference=(F('transferitems__quantity')) - Sum(F('transferitems__received_quantity')),
        total_received_amount=Sum(F('transferitems__received_quantity') * F('transferitems__cost')),
        total_amount=ExpressionWrapper(
            Sum(F('transferitems__quantity') * F('transferitems__cost')),
            output_field=FloatField()
        ),
        check_all_received=Sum(F('transferitems__quantity') - F('transferitems__received_quantity')),
    ).order_by('-time')

    if q:
        transfers = transfers.filter(Q(transfer_ref__icontains=q) | Q(date__icontains=q))
    if branch_id:
        transfers = transfers.filter(transfer_to__id=branch_id)

    transfers_list = list(transfers)
    unique_transfers = list({t.id: t for t in transfers_list}.values())
    unique_transfers.sort(key=lambda x: x.time, reverse=True)

    paginator = Paginator(unique_transfers, 20)
    paginated_transfers = paginator.get_page(page_number)

    if paginated_transfers:
        transfers_data = [
            {
                'id': transfer.id,
                'transfer_ref': transfer.transfer_ref,
                'branch': transfer.branch.name,
                'transfer_to': [branch.id for branch in transfer.transfer_to.all()],
                'total_quantity': transfer.total_quantity,
                'total_received_qnt': transfer.total_received_qnt,
                'total_r_difference': transfer.total_r_difference,
                'total_received_amount': transfer.total_received_amount,
                'total_amount': transfer.total_amount,
                'check_all_received': transfer.check_all_received,
                'time': transfer.time.strftime('%Y-%m-%d %H:%M:%S'),
                'username': transfer.user.username,
                'description': transfer.description
            }
            for transfer in paginated_transfers
        ]
    else:
        transfers_data = []

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'transfers': transfers_data,
            'has_next': paginated_transfers.has_next(),
        })

    return render(request, 'transfers.html', {
        'transfers': paginated_transfers,
        'search_query': q,
    })

@login_required
def inventory_transfer_item_data(request, id):
    """
    Transfer items of the parent transfer
    """
    transfer_items = TransferItems.objects.filter(
        Q(to_branch=request.user.branch) | Q(from_branch=request.user.branch),
        transfer__id=id,
        transfer__delete=False,
    ).select_related(
        'product', 'from_branch', 'to_branch', 'action_by', 'received_by', 'transfer'
    ).annotate(
        total_amount=F('quantity') * F('product__cost')
    ).values(
        'id',
        'quantity',
        'over_less_quantity',
        'price',
        'dealer_price',
        'received',
        'declined',
        'over_less',
        'quantity_track',
        'description',
        'over_less_description',
        'received_quantity',
        'cost',
        'date',
        'date_received',
        'transfer__id',
        'from_branch__name',
        'product__name',
        'to_branch__name',
        'action_by__username',
        'received_by__username',
        'received_back_quantity'
    )

    return JsonResponse(list(transfer_items), safe=False)

@login_required
def add_transfer_item(request, transfer_id):
    if request.method == 'GET':
        try:
            transfer = Transfer.objects.get(id=transfer_id)
            return render(request, 'add_transfer_item.html', {
                'transfer': transfer,
            })
        except Transfer.DoesNotExist:
            messages.warning(request, f'Transfer with ID {transfer_id} does not exist.')
            return redirect('inventory:transfers')

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('items', [])
            branches_data = data['branches_to']
            transfer_id = data.get('transfer_id', '')

            products = ProcessTransferCartView._get_products(request.user.branch)
            branch_obj_list = ProcessTransferCartView._get_branch_objects(branches_data)

            transfer = Transfer.objects.get(id=transfer_id)

            ProcessTransferCartView._process_transfer(data['cart'], products, branch_obj_list, transfer, request)

            return JsonResponse({'success': True, 'message': 'Items added to transfer successfully'}, status=200)

        except Transfer.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transfer not found'}, status=404)
        except Exception as e:
            logger.error(f"Error adding items to transfer: {e}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def held_transfer_json(request, transfer_id):
    transfer_items = Holdtransfer.objects.filter(transfer__id=transfer_id).values(
        'product__name',
        'from_branch__name',
        'to_branch__name',
        'quantity',
        'price',
        'cost',
        'dealer_price'
    )
    return JsonResponse(list(transfer_items), safe=False)

@login_required
def held_transfers(request):
    transfers = Transfer.objects.filter(
        Q(branch=request.user.branch),
        delete=False,
        hold=True
    )
    return render(request, 'held_transfers.html',{
        'transfers':transfers
    })

@login_required
def process_held_transfer(request, transfer_id):
    try:
        transfer = Transfer.objects.get(
            id=transfer_id,
            branch=request.user.branch,
            delete=False,
            hold=True
        )
        return render(request, 'process_held_transfers.html',{
            'transfer':transfer
        })
    except:
        messages.warning(request, f'Transfer with id {transfer_id} not found.')
        return redirect('inventory:transfers')

@login_required
def print_transfer(request, transfer_id):
    if request.method == 'GET':
        try:
            transfer = Transfer.objects.get(id=transfer_id)
            transfer_items = TransferItems.objects.filter(transfer=transfer)

            return render(request, 'components/ibt.html', {
                'date':datetime.datetime.now(),
                'transfer':transfer,
                'transfer_items':transfer_items
            })
        except:
            messages.warning(request, 'Transfer doesnt exists')
            return redirect('inventory:transfers')

    if request.method == 'POST':
        try:
            transfer = Transfer.objects.get(id=transfer_id)
            transfer_items = TransferItems.objects.filter(transfer=transfer).values(
                'product__name',
                'product__price',
                'quantity',
                'to_branch__name',
                'product__cost'
            )

            return JsonResponse({'success':True, 'data':list(transfer_items)})
        except Exception as e:
            return JsonResponse({'success':False, 'meesage':f'{e}'})

@login_required
@transaction.atomic
def receive_inventory(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            transfer_id = data.get('item_id')
            quantity_received = int(data.get('received_quantity'))
            serial_numbers = data.get('serial_numbers', [])
            received = True

            branch_transfer = get_object_or_404(TransferItems, id=transfer_id)
            transfer_obj = get_object_or_404(Transfer, id=branch_transfer.transfer.id)

            if received:
                if quantity_received != branch_transfer.quantity:
                    branch_transfer.over_less_quantity = branch_transfer.quantity - quantity_received
                    branch_transfer.over_less = True
                    branch_transfer.save()

                with transaction.atomic():
                    product, created = Inventory.objects.get_or_create(
                        name=branch_transfer.product.name,
                        branch=request.user.branch,
                        defaults={
                            'cost': branch_transfer.cost,
                            'price': branch_transfer.price,
                            'quantity': quantity_received,
                            'dealer_price': branch_transfer.dealer_price,
                            'description': branch_transfer.product.description or '',
                            'category': branch_transfer.product.category,
                            'tax_type': branch_transfer.product.tax_type,
                            'stock_level_threshold': branch_transfer.product.stock_level_threshold,
                        }
                    )

                    if not created:
                        product.quantity += quantity_received
                        product.price = branch_transfer.price
                        product.cost = branch_transfer.cost
                        product.dealer_price = branch_transfer.dealer_price
                        product.save()

                    ActivityLog.objects.create(
                        branch=request.user.branch,
                        user=request.user,
                        action='stock in',
                        inventory=product,
                        dealer_price=product.dealer_price,
                        selling_price=product.price,
                        system_quantity=product.quantity,
                        quantity=quantity_received,
                        total_quantity=product.quantity,
                        product_transfer=branch_transfer,
                        description=f'From {branch_transfer.from_branch}, received: {branch_transfer.received_quantity} x {branch_transfer.quantity}'
                    )

                    product.batch += f'{branch_transfer.product.batch}, '
                    product.save()

            branch_transfer.quantity_track = branch_transfer.quantity - quantity_received
            branch_transfer.received_quantity += quantity_received
            branch_transfer.received_by = request.user
            branch_transfer.received = True
            branch_transfer.description = f'received {quantity_received} out of {branch_transfer.quantity}'
            branch_transfer.save()

            transfer_obj.total_quantity_track -= quantity_received
            transfer_obj.save()

            if not transfer_obj.receive_status:
                transfer_obj.receive_status = True
                transfer_obj.save()

            return JsonResponse({'success': True, 'message': 'Product received successfully'}, status=200)
        except TransferItems.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid transfer ID'}, status=400)
        except Transfer.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Transfer object not found'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def edit_transfer_item(request, transfer_item_id):
    try:
        transfer_item = TransferItems.objects.get(id=transfer_item_id)
    except TransferItems.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Transfer item not found'}, status=404)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_quantity = int(data.get('edit_quantity'))

            if transfer_item.received:
                return JsonResponse({'success':False, 'message':f'{transfer_item.product.name}, is already received.'})

            if new_quantity is None:
                return JsonResponse({'success': False, 'message': 'Quantity is required'}, status=400)

            with transaction.atomic():
                old_quantity = transfer_item.quantity
                transfer_item.quantity = new_quantity
                transfer_item.save()

                inventory = Inventory.objects.select_for_update().get(
                    id=transfer_item.product.id,
                    branch__name=transfer_item.from_branch
                )

                if inventory.quantity < new_quantity:
                    return JsonResponse({'success': False, 'message': 'Insufficient stock to update transfer item quantity'}, status=400)

                inventory.quantity += old_quantity - new_quantity
                inventory.save()

                ActivityLog.objects.create(
                    branch=request.user.branch,
                    user=request.user,
                    action='edit transfer item',
                    inventory=inventory,
                    quantity=inventory.quantity,
                    total_quantity=inventory.quantity,
                    description=f'Edited transfer item quantity from {old_quantity} to {new_quantity}'
                )

            return JsonResponse({'success': True, 'message': 'Transfer item updated successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@login_required
def receive_inventory_json(request):
    transfers =  TransferItems.objects.filter(to_branch=request.user.branch).order_by('-date')
    if request.method ==  'GET':
        transfers = transfers.values(
            'id',
            'date',
            'quantity',
            'received',
            'description',
            'date_received',
            'product__name',
            'from_branch__name',
            'received_by__username'
        )
        return JsonResponse(list(transfers), safe=False)

@login_required
def over_less_list_stock(request):
    form = DefectiveForm()
    search_query = request.GET.get('search_query', '')

    transfers =  TransferItems.objects.filter(to_branch=request.user.branch).prefetch_related('product', 'transfer').order_by('-date')

    if search_query:
        transfers = transfers.filter(
            Q(transfer__product__name__icontains=search_query)|
            Q(transfer__transfer_ref__icontains=search_query)|
            Q(date__icontains=search_query)
        )

    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            action = data.get('action')
            transfer_id = data.get('transfer_id')
            quantity = int(data.get('quantity', 0))
            branch = data.get('branch')
            reason = data.get('reason', '')
            action_taken = data.get('action_taken')

            branch_transfer = TransferItems.objects.filter(id=transfer_id).select_related('transfer').first()
            transfer = branch_transfer.transfer

            with transaction.atomic():
                if int(branch_transfer.received_quantity) != int(branch_transfer.quantity):

                    if action == 's_receive':
                        if quantity > branch_transfer.quantity:
                            return JsonResponse({'success': False, 'message': 'Quantity cannot be more than the transfer quantity'}, status=400)

                        product = Inventory.objects.get(name=branch_transfer.product.name, branch=request.user.branch)

                        product.quantity += quantity
                        product.save()

                        branch_transfer.description = f'Received {branch_transfer.received_quantity} from {branch_transfer.from_branch}'
                        branch_transfer.received_quantity += quantity
                        branch_transfer.save()

                        ActivityLog.objects.create(
                            branch=request.user.branch,
                            user=request.user,
                            action='stock in',
                            inventory=product,
                            quantity=quantity,
                            total_quantity=product.quantity,
                            product_transfer=branch_transfer,
                            description=f'Received {quantity} from {branch_transfer.from_branch}'
                        )

                        return JsonResponse({'success': True, 'message': 'Quantity successfully transferred to another branch'}, status=200)

                    if action == 'send_to':
                        if quantity > branch_transfer.quantity:
                            return JsonResponse({'success': False, 'message': 'Quantity cannot be more than the transfer quantity'}, status=400)

                        new_branch = Branch.objects.get(id=branch)

                        try:
                            product = Inventory.objects.get(name=branch_transfer.product.name, branch=new_branch)
                        except Exception as e:
                            product = Inventory.objects.create(
                                name=branch_transfer.product.name,
                                branch=new_branch,
                                cost=branch_transfer.cost,
                                price=branch_transfer.price,
                                quantity=quantity,
                                dealer_price=branch_transfer.dealer_price,
                                description=branch_transfer.product.description or '',
                                category=branch_transfer.product.category,
                                tax_type=branch_transfer.product.tax_type,
                                stock_level_threshold=branch_transfer.product.stock_level_threshold,
                            )

                        product.quantity += quantity
                        product.save()

                        ActivityLog.objects.create(
                            branch=request.user.branch,
                            user=request.user,
                            action='stock in',
                            inventory=product,
                            quantity=quantity,
                            total_quantity=product.quantity,
                            product_transfer=branch_transfer,
                            description=f'Received {quantity} from {branch_transfer.from_branch}'
                        )

                        branch_transfer.quantity -= quantity
                        branch_transfer.save()

                        branch_transfer.transfer.transfer_to.add(new_branch.id)

                        try:
                            send_to_branch_transfer_item = TransferItems.objects.get(transfer__id=transfer.id, product__name=product.name, to_branch=new_branch)
                        except Exception as e:
                            send_to_branch_transfer_item = TransferItems.objects.create(
                                transfer=branch_transfer.transfer,
                                product=product,
                                cost=branch_transfer.cost,
                                price=branch_transfer.price,
                                dealer_price=branch_transfer.dealer_price,
                                quantity=quantity,
                                from_branch=branch_transfer.from_branch,
                                to_branch=new_branch,
                                description=f'Transferred {quantity} to {new_branch} from {branch_transfer.from_branch}'
                            )

                        send_to_branch_transfer_item.quantity += quantity
                        send_to_branch_transfer_item.save()

                        product.quantity -= quantity
                        product.save()

                        ActivityLog.objects.create(
                            branch=request.user.branch,
                            user=request.user,
                            action='transfer out',
                            inventory=product,
                            quantity=-quantity,
                            total_quantity=product.quantity,
                            product_transfer=branch_transfer,
                            description=f'Transferred {quantity} to {new_branch}'
                        )

                        return JsonResponse({'success': True, 'message': 'Quantity successfully transferred to another branch'}, status=200)

                    if action in ['write-off', 'defective', 'shrinkage']:

                        if request.user.branch == branch_transfer.to_branch:
                            return JsonResponse({'success': False, 'message': 'Sorry, action not available'}, status=400)

                        product = Inventory.objects.get(
                            id=branch_transfer.product.id,
                            branch=request.user.branch
                        )

                        if quantity > branch_transfer.quantity:
                            return JsonResponse({'success': False, 'message': 'Quantity cannot be more than the transfer quantity'}, status=400)

                        if action == 'write-off':
                            WriteOff.objects.create(
                                inventory_item=product,
                                quantity=quantity,
                                reason=f'{reason} (transfer number: {branch_transfer.transfer.transfer_ref})',
                                created_by=request.user
                            )
                        elif action == 'defective':
                            DefectiveItem.objects.create(
                                inventory_item=product,
                                quantity=quantity,
                                defect_description=f'{reason} (transfer number: {branch_transfer.transfer.transfer_ref})',
                                action_taken=action_taken,
                                created_by=request.user
                            )
                        elif action == 'shrinkage':
                            InventoryShrinkage.objects.create(
                                inventory_item=product,
                                quantity=quantity,
                                reason=action_taken,
                                created_by=request.user
                            )

                        product.quantity += quantity
                        product.save()

                        ActivityLog.objects.create(
                            branch = request.user.branch,
                            user=request.user,
                            action= 'stock in',
                            inventory=product,
                            quantity=quantity,
                            total_quantity=product.quantity,
                            product_transfer=branch_transfer,
                            description=f'Received from {transfer.transfer_ref}'
                        )

                        product.quantity -= quantity
                        product.save()

                        branch_transfer.defect_quantity =+ quantity
                        description = f'{branch_transfer.defect_quantity} item(s) transferred to {action} account.'
                        branch_transfer.quantity -= int(quantity)
                        branch_transfer.description = description
                        branch_transfer.over_less_description = description
                        branch_transfer.action_by = request.user
                        branch_transfer.over_less = False
                        branch_transfer.save()

                        transfer.defective_status = True
                        transfer.save()

                        ActivityLog.objects.create(
                            branch=request.user.branch,
                            user=request.user,
                            action=action,
                            inventory=product,
                            quantity=-quantity,
                            total_quantity=product.quantity,
                            product_transfer=branch_transfer,
                            description=description
                        )

                        return JsonResponse({'success': True}, status=200)

                    if action == 'receive':
                        """
                            receiving the transfer on the current branch
                        """

                        if request.user.branch != branch_transfer.from_branch:
                            return JsonResponse({'success': False, 'message': 'Sorry, action not available'}, status=400)

                        product = Inventory.objects.get(
                            Q(name__icontains = branch_transfer.product.name),
                            branch=request.user.branch
                        )

                        if (branch_transfer.quantity - branch_transfer.received_quantity) < int(quantity):
                            return JsonResponse({'success':False, 'message':f'Cant receive more quantity'})

                        product.quantity += int(quantity)
                        product.save()

                        branch_transfer.received_back_quantity += quantity
                        branch_transfer.quantity -= quantity
                        branch_transfer.description = f'Received {branch_transfer.received_quantity} x {branch_transfer.quantity}'
                        branch_transfer.over_less = False
                        branch_transfer.over_less_description = 'received'
                        branch_transfer.save()

                        ActivityLog.objects.create(
                            branch = request.user.branch,
                            user=request.user,
                            action= 'stock in',
                            inventory=product,
                            quantity=quantity,
                            total_quantity=product.quantity,
                            product_transfer=branch_transfer,
                            description=f'Received from {transfer.transfer_ref}'
                        )

                        return JsonResponse({'success':True}, status=200)

                    if action == 'send_back':

                        """
                            creation of a new transfer to the source branch with a product returned and
                            deduction of a the quantity transfered on the current transfer
                        """

                        branch_transfer.quantity -= int(quantity)
                        branch_transfer.description = f'Received {branch_transfer.quantity} and returned back {quantity}'
                        branch_transfer.received = True

                        receive_poduct = Inventory.objects.get(id=branch_transfer.product.id, branch=request.user.branch)

                        receive_poduct.quantity += int(quantity)

                        receive_poduct.save()
                        branch_transfer.save()

                        data = [
                            {
                                'transfer_id':branch_transfer.id,
                                'description':branch_transfer.description,
                                'status':branch_transfer.received
                            }
                        ]

                        return JsonResponse({'success':True, 'data':data}, status=200)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

    return render(request, 'over_less_transfers.html', {'over_less_transfers':transfers, 'form':form})

@login_required
def add_inventory_transfer(request):
    form = addTransferForm()
    inventory = Inventory.objects.filter(branch=request.user.branch).order_by('-quantity')
    return render(request, 'add_transfer.html', {'fornm':form, 'inventory':inventory})

@login_required
def accessory_view(request, product_id):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            accessory_data = data.get('accessories', [])

            product = Inventory.objects.get(id=product_id)
            current_accessories = Accessory.objects.filter(main_product=product).values('accessory_product', 'quantity')
            current_ids = set(current_accessories.values_list('accessory_product', flat=True))

            input_data = {acc['id']: acc['quantity'] for acc in accessory_data}
            input_ids = set(input_data.keys())

            accessories_to_add = input_ids - current_ids
            accessories_to_remove = current_ids - input_ids

            if Accessory.objects.filter(main_product=product).exists():
                acc = Accessory.objects.get(main_product=product)
            else:
                acc = Accessory.objects.create(main_product=product, quantity=0)

            if accessories_to_add:
                accessories_to_add_objs = Inventory.objects.filter(id__in=accessories_to_add)

                for accessory in accessories_to_add_objs:
                    quantity = input_data[f'{accessory.id}']
                    acc.accessory_product.add(int(accessory.id))
                    acc.quantity = quantity
                    acc.save()

            if accessories_to_remove:
                accessories_to_remove_objs = Inventory.objects.filter(id__in=accessories_to_remove)

                for accessory in accessories_to_remove_objs:
                    acc.accessory_product.remove(accessory)
                    acc.save()

            for accessory_id in input_ids.intersection(current_ids):
                quantity = input_data[accessory_id]
                acc_instance = Accessory.objects.filter(main_product=product, accessory_product_id=accessory_id).first()
                if acc_instance:
                    acc_instance.quantity = quantity
                    acc_instance.save()

            updated_accessories = Accessory.objects.filter(main_product=product).values(
                'id', 'main_product__name', 'accessory_product__name', 'quantity'
            )

            return JsonResponse({'success': True, 'data': list(updated_accessories)}, status=200)

        except Inventory.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
def get_accessory(request, product_id):
    """
    Get accessory data including related product information for a given main product.
    """
    if product_id:
        accessory = Accessory.objects.filter(
            main_product__id=product_id
        ).prefetch_related(
            'accessory_product'
        ).values(
            'id',
            'main_product__name',
            'quantity',
            'accessory_product__id',
            'accessory_product__name',
            'accessory_product__price',
        )

        return JsonResponse({
            'success': True,
            'data': list(accessory)
        })

    return JsonResponse({
        'success': False,
        'message': 'Product ID is required'
    }, status=400)
