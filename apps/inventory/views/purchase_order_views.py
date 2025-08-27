from django.utils import timezone
import json, datetime, openpyxl
from os import system
import csv, base64
from django.core.files.base import ContentFile
from django.http import HttpResponse
from datetime import timedelta
from openpyxl.styles import Alignment, Font, PatternFill
from ..models import *
import apps.inventory.tasks as tasks
from decimal import Decimal
from django.views import View
from django.db.models import Q, Sum, F, FloatField, ExpressionWrapper, Count
from django.db import transaction
from django.contrib import messages
from utils.utils import generate_pdf
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from apps.finance.models import (
    StockTransaction,
    PurchaseOrderAccount,
    PurchasesAccount,
    Expense,
    Currency,
    VATTransaction,
    VATRate,
    Account,
    Cashbook,
    ExpenseCategory,
    AccountBalance,
    AccountTransaction
)
from ..utils import (
    calculate_inventory_totals,
    average_inventory_cost,
    generete_delivery_note
)
from ..forms import (
    BatchForm,
    AddProductForm,
    addCategoryForm,
    addTransferForm,
    DefectiveForm,
    RestockForm,
    AddDefectiveForm,
    ServiceForm,
    AddSupplierForm,
    CreateOrderForm,
    noteStatusForm,
    PurchaseOrderStatusForm,
    ReorderSettingsForm,
    EditSupplierForm,
    StockTakeForm,
    AddShrinkageForm,
    AddWriteOffForm
)
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from channels.generic.websocket import  AsyncJsonWebsocketConsumer
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from permissions.permissions import (
    admin_required,
    # sales_required,
    # accountant_required
)
from utils.account_name_identifier import account_identifier
from loguru import logger
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.core.files.uploadedfile import InMemoryUploadedFile
from apps.inventory.utils import best_price
from collections import defaultdict
from django.core.cache import cache
from django.core.paginator import Paginator
from typing import List, Dict, Any
from apps.finance.models import UserAccount
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO

@login_required
def temporary_purchase_order(request):
    logger.info('done')
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data.get('name')
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        price = data.get('price')
        supplier_id = data.get('supplier')

        temp_purchase_order = None

        with transaction.atomic():

            temp_purchase_order, created = TemporaryPurchaseOrder.objects.get_or_create(
            name=name,
                defaults={
                    'name': name,
                    'order_number': temp_purchase_order.generate_order_number(),
                    'branch': request.user.branch,
                    'user': request.user
                }
            )
            if created:
                temp_purchase_order.save()

            TemporaryPurchaseOrderItem.objects.create(
                temporary_purchase_order=temp_purchase_order,
                product_id=product_id,
                quantity=quantity,
                price=price,
                supplier_id=supplier_id,
                unit_cost=price
            )

        return JsonResponse({'success':True, 'message':'Temporary purchase order created successfully'})

@login_required
def get_temporary_purchase_order_items(request, temp_po_id):
    if request.method == 'GET':
        temp_purchase_order_items = TemporaryPurchaseOrderItem.objects.filter(temporary_purchase_order=temp_po_id)
        return JsonResponse({'success':True, 'message':'Temporary purchase order items fetched successfully', 'temp_purchase_order_items':list(temp_purchase_order_items)})

@login_required
def confirm_purchase_order_items(request, po_id):
    try:
        order_items = PurchaseOrderItem.objects.filter(purchase_order__id=po_id).select_related('product')

        logs = []
        inventory_updates = []

        with transaction.atomic():
            for item in order_items:
                print(item.received_quantity)
                print(item.product)
                inventory_updates.append(
                    Inventory(
                        id=item.product.id,
                        quantity=item.product.quantity + item.received_quantity,
                        price=item.price,
                        dealer_price=item.wholesale_price,
                        cost=item.actual_unit_cost,
                        status=True,
                        disable=False,
                    )
                )

                existing_quantity = item.product.quantity
                new_quantity = item.received_quantity + item.product.quantity

                quantity_change = abs(new_quantity -  existing_quantity)

                print(f' bvbproduct quantity {item.product.quantity}')
                print(f'update product quantity {item.product.quantity + item.received_quantity}')

                logs.append(
                    ActivityLog(
                        purchase_order=item.purchase_order,
                        branch=request.user.branch,
                        user=request.user,
                        action='stock in',
                        dealer_price=item.wholesale_price,
                        selling_price=item.price,
                        inventory=item.product,
                        quantity=quantity_change,
                        system_quantity=item.received_quantity,
                        description=f'Stock in from batch {item.purchase_order.batch}',
                        total_quantity=item.product.quantity + item.received_quantity,
                    )
                )

            Inventory.objects.bulk_update(
                inventory_updates, ['quantity', 'price', 'dealer_price', 'cost']
            )

            ActivityLog.objects.bulk_create(logs)

        return JsonResponse({'success': True, 'message': 'All purchase order items processed'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def if_purchase_order_is_received(request, purchase_order, tax_amount, payment_method):
    try:
        currency = Currency.objects.get(default=True)
        rate = VATRate.objects.get(status=True)

        # get account
        account_details = account_identifier(request, currency, payment_method)
        account_name = account_details['account_name']
        account_type = account_details['account_type']

        account, _ = Account.objects.get_or_create(
            name=account_name,
            type=account_type
        )

        account_balance, _ = AccountBalance.objects.get_or_create(
            account=account,

            defaults={
                'branch':request.user.branch,
                'currency':currency,
                'balance':0
            }
        )

        account_balance.balance -= purchase_order.total_cost

        account_balance.save()

        # get or create purchase order category
        category, _ = ExpenseCategory.objects.get_or_create(name='Purchase orders')
        logger.info(category)

        # create an expense and exclude the vat amount
        expense = Expense.objects.create(
            amount = purchase_order.total_cost - purchase_order.tax_amount,
            payment_method = payment_method,
            currency = currency,
            category = category,
            user = request.user,
            branch = request.user.branch,
            status = False,
            purchase_order = purchase_order,
            description = f'Purchase order: {purchase_order.order_number}',
        )

        # create a cashbook entry
        Cashbook.objects.create(
            expense = expense,
            description = f'Purchase order: {purchase_order.order_number}',
            credit = True,
            amount = purchase_order.total_cost,
            currency = currency,
            branch = request.user.branch
        )

        # create account transaction log
        AccountTransaction.objects.create(
            account = account,
            expense = expense
        )

        # revisit
        # PurchaseOrderAccount.objects.create(
        #     purchase_order = purchase_order,
        #     amount = purchase_order.total_cost - purchase_order.tax_amount,
        #     balance = 0,
        #     expensed = False
        # )

        # create a vat entry
        VATTransaction.objects.create(
            purchase_order = purchase_order,
            vat_type='Input',
            vat_rate = rate.rate,
            tax_amount = tax_amount
        )

    except Exception as e:
        logger.info(e)
        return JsonResponse({'success':False, 'message':f'currency doesnt exists'})
    except VATRate.DoesNotExist:
        return JsonResponse({'success':False, 'message':f'Make sure you have a stipulated vat rate in the system'})

@login_required
def delete_purchase_order(request, purchase_order_id):
    try:
        # Retrieve the purchase order
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)

        if purchase_order.received:
            return JsonResponse({'success': False, 'message': 'Cannot delete a received purchase order'}, status=400)

        with transaction.atomic():

            # Reverse related account transactions
            currency = Currency.objects.get(default=True)

            account_transaction = AccountTransaction.objects.filter(expense__purchase_order=purchase_order).first()
            if account_transaction:
                account_balance = AccountBalance.objects.get(account=account_transaction.account)

                # Reverse account balance adjustments
                account_balance.balance += purchase_order.total_cost
                account_balance.save()

                # Delete account transaction log
                account_transaction.delete()

            # Reverse Cashbook entry
            cashbook_entry = Cashbook.objects.filter(expense__purchase_order=purchase_order).first()
            if cashbook_entry:
                cashbook_entry.delete()

            # Reverse the VAT transaction
            vat_transaction = VATTransaction.objects.filter(purchase_order=purchase_order).first()
            if vat_transaction:
                vat_transaction.delete()

            # Reverse the Expense record
            expense = Expense.objects.filter(purchase_order=purchase_order).first()
            if expense:
                expense.delete()

            # Reverse other expenses related to the purchase order
            other_expenses = otherExpenses.objects.filter(purchase_order=purchase_order)
            if other_expenses.exists():
                other_expenses.delete()


            items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
            products = Inventory.objects.all()

            for item in items:
                for prod in products:
                    if item.product == prod.product:
                        prod.quantity -= item.received_quantity

                        # eliminate negative stock
                        if prod.quantity < 0:
                            prod.quantity = 0

                        prod.save()

                        ActivityLog.objects.create(
                            branch = request.user.branch,
                            user= request.user,
                            action= 'delete',
                            inventory=prod,
                            quantity=item.received_quantity,
                            total_quantity=prod.quantity
                        )

            # Remove PurchaseOrderItems
            PurchaseOrderItem.objects.filter(purchase_order=purchase_order).delete()

            # Finally, delete the purchase order itself
            purchase_order.delete()

        return JsonResponse({'success': True, 'message': 'Purchase order deleted successfully'})
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Purchase order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def download_delivery_note(request, po_id):
    delivery_note = get_object_or_404(DeliveryNote, purchase_order_id=po_id)

    if delivery_note.pdf:
        response = HttpResponse(delivery_note.pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Delivery_Note_{po_id}.pdf"'
        return response
    else:
        return HttpResponse("No PDF found for this delivery note.", status=404)

@login_required
@transaction.atomic
def change_purchase_order_status(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'error': f'Purchase order with ID: {order_id} does not exist'}, status=404)

    try:
        data = json.loads(request.body)
        status = data['status']

        if status:
            purchase_order.status=status

            with transaction.atomic():
                if purchase_order.status == 'received':
                    purchase_order.save()

                    tax_amount = purchase_order.tax_amount
                    payment_method = purchase_order.payment_method

                    if_purchase_order_is_received(
                        request,
                        purchase_order,
                        tax_amount,
                        payment_method
                    )

            return JsonResponse({'success':True}, status=200)
        else:
            return JsonResponse({'success':False, 'message':'Status is required'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

@login_required
def print_purchase_order(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')

    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')

    return render(request, 'print_purchase_order.html',
        {
            'orders':purchase_order_items,
            'purchase_order':purchase_order
        }
    )

@login_required
def purchase_order_detail(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exist')
        return redirect('inventory:purchase_orders')

    items = costAllocationPurchaseOrder.objects.filter(purchase_order=purchase_order)
    expenses = otherExpenses.objects.filter(purchase_order=purchase_order)
    purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)

    total_received_quantity = purchase_order_items.aggregate(Sum('received_quantity'))['received_quantity__sum'] or 0
    total_expected_profit = purchase_order_items.aggregate(Sum('expected_profit'))['expected_profit__sum'] or 0
    total_expected_dealer_profit = purchase_order_items.aggregate(Sum('dealer_expected_profit'))['dealer_expected_profit__sum'] or 0
    total_quantity = items.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_expense_sum = expenses.aggregate(total_expense=Sum('amount'))['total_expense'] or 0

    logger.info(f'total quantity = { total_received_quantity}')


    if request.GET.get('download') == 'csv':
        return generate_csv_response(items, purchase_order_items)

    return render(request, 'purchase_order_detail.html', {
        'items': items,
        'expenses': expenses,
        'order_items': purchase_order_items,
        'total_quantity': total_received_quantity,# to be changed to total quantity,
        'total_received_quantity': total_received_quantity,
        'total_retail_profit': total_expected_profit,
        'total_expenses': total_expense_sum,
        'purchase_order': purchase_order,
        'total_wholesale_profit':total_expected_dealer_profit
    })

def generate_csv_response(items, po_items):
    """Generate CSV response for the purchase order"""

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="purchase_order.csv"'

    writer = csv.writer(response)

    writer.writerow(['Product', 'Quantity', 'Quantity Received', 'Selling Price', 'Dealer Price'])

    for item in items:
        received_quantity = 0
        if po_items.filter(product__name=item.product).exists():
           received_quantity = po_items.filter(product__name=item.product).first().received_quantity

        writer.writerow([
            item.product,
            item.quantity,
            received_quantity,
            f"${item.selling_price:.2f}",
            f"${item.dealer_price:.2f}",
        ])

    return response

@login_required
def sales_price_list_pdf(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)

        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)

        context = {'items': purchase_order_items}

        template = get_template('pdf_templates/price_list.html')
        html = template.render(context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="price_list.pdf"'

        pisa_status = pisa.CreatePDF(html, dest=response)

        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=400)

        return response
    except PurchaseOrder.DoesNotExist:
            messages.warning(request, f'Purchase order with ID: {order_id} does not exist')
            return redirect('inventory:purchase_orders')

@login_required
def delete_purchase_order(request, purchase_order_id):
    if request.method != "DELETE":
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': f'Purchase order with ID {purchase_order_id} not found'}, status=404)

    try:
        purchase_order.delete()
        return JsonResponse({'success': True, 'message': 'Purchase order deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def receive_order(request, order_id):
    try:
        purchase_order = PurchaseOrder.objects.get(id=order_id)
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')

    try:
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)
    except PurchaseOrderItem.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exists')
        return redirect('inventory:purchase_orders')

    logger.info(purchase_order_items.all().values('product'))

    products = Inventory.objects.filter(branch=request.user.branch).values(
        'dealer_price',
        'price',
        'name',
        'id',
        'branch__name'
    )
    logger.info(f'branch: {request.user.branch}')
    # Convert products queryset to a dictionary for easy lookup by product ID
    product_prices = {product['id']: product for product in products}

    new_po_items =  []
    for item in purchase_order_items:
        if(item.product):
            logger.info(item.product.branch)
            product_name = item.product.id

            product_data = product_prices.get(product_name)
            logger.info(f'product prices {product_data}')
            if product_data:
                item.dealer_price = product_data['dealer_price']
                item.selling_price = product_data['price']
            else:
                item.dealer_price = 0
                item.selling_price = 0
            new_po_items.append(item)

    logger.info(purchase_order_items)


    return render(request, 'receive_order.html',
        {
            'orders':purchase_order_items,
            'purchase_order':purchase_order
        }
    )

@transaction.atomic
def process_received_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            edit = data.get('edit')
            order_item_id = data.get('id')
            quantity = data.get('quantity', 0)
            selling_price = data.get('selling_price', 0)
            dealer_price = data.get('dealer_price', 0)
            expected_profit = data.get('expected_profit', 0)
            dealer_expected_profit = data.get('dealer_expected_profit', 0)

            logger.info('Processing order item')
            logger.info(data)

            order_item = PurchaseOrderItem.objects.get(id=order_item_id)
            cost = order_item.actual_unit_cost

            if edit:
                return edit_purchase_order_item(order_item_id, selling_price, dealer_price, expected_profit, dealer_expected_profit, quantity, cost, request)

            logger.info(order_item)
            order = PurchaseOrder.objects.get(id=order_item.purchase_order.id)

            # Update the order item with received quantity
            order_item.receive_items(quantity)
            order_item.received_quantity = quantity
            order_item.expected_profit = expected_profit
            order_item.dealer_expected_profit = dealer_expected_profit
            order_item.price = selling_price
            order_item.wholesale_pice = dealer_price
            order_item.received = True

            # Update or create inventory
            system_quantity = 0 # if new product
            try:

                with transaction.atomic():
                    inventory = Inventory.objects.get(id = order_item.product.id)
                    logger.info(inventory)

                    system_quantity = inventory.quantity

                    inventory.price = selling_price
                    inventory.dealer_price = dealer_price or 0
                    inventory.quantity += quantity

                    if inventory.batch:
                        inventory.batch += f'{order.batch}, '
                    else:
                        inventory.batch = f'{order.batch}, '

                    cost = average_inventory_cost(inventory.id, order_item.actual_unit_cost, quantity, request.user.branch.id)
                    logger.info(order_item.actual_unit_cost)

                    inventory.cost = Decimal(round(cost, 2))

                    logger.info(f'Inventory cost: {inventory.cost}')

                    inventory.save()

                    log = ActivityLog(
                        purchase_order=order_item.purchase_order,
                        branch=request.user.branch,
                        user=request.user,
                        action='stock in',
                        dealer_price = dealer_price,
                        selling_price = selling_price,
                        inventory=inventory,
                        quantity=quantity,
                        system_quantity=system_quantity,
                        description=f'Stock in from {order_item.purchase_order.batch}',
                        total_quantity=inventory.quantity
                    )
                    log.save()


                    order_item.save()

                    logger.info(f'process order item received: {order_item.product}')

                    return JsonResponse({'success': True, 'message': 'Inventory updated successfully'}, status=200)
            except Product.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Product with ID: {order_item.product.id} does not exist'}, status=404)
        except Exception as e:
            logger.info(e)
            return JsonResponse({'success': False, 'message': f'{e}'}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)



def edit_purchase_order_item(order_item_id, selling_price, dealer_price, expected_profit, dealer_expected_profit, quantity, cost, request):
    try:
        po_item = PurchaseOrderItem.objects.get(id=order_item_id)
        product = po_item.product.id
        try:
            inventory = Inventory.objects.get(id=product, branch=po_item.purchase_order.branch)
            system_quantity = inventory.quantity
            quantity_adjustment = 0
            description = ''
            if po_item.quantity == quantity:
                if inventory.quantity != quantity:
                    # adjust quantity
                    if inventory.quantity < quantity:
                        quantity_adjustment = quantity - inventory.quantity
                        inventory.quantity += quantity_adjustment
                        action = 'purchase edit +'
                        description = f'Stock adjustment ({po_item.purchase_order.batch})'
                        logger.info(f'{quantity_adjustment}: quantity adjusted')
                    elif inventory.quantity > quantity:
                        quantity_adjustment = inventory.quantity - quantity
                        inventory.quantity = quantity
                        # quantity_adjustment = quantity
                        action = 'purchase edit -'
                        description = f'Stock adjustment ({po_item.purchase_order.batch})'
                        logger.info(f'{quantity_adjustment}: quantity adjusted')
                    else:
                        action = 'price edit'
                        logger.info(f'{quantity_adjustment}: quantity adjusted')
                        inventory.quantity = quantity
                        description = f'Price adjustment ({po_item.purchase_order.batch})'
                else:
                    action='price edit'
                    description=f'Price adjustment ({po_item.purchase_order.batch})'
            else:
                # adjust quantity
                if inventory.quantity < quantity:
                    quantity_adjustment = quantity - inventory.quantity
                    inventory.quantity += quantity_adjustment
                    action = 'purchase edit +'
                    description = f'Stock adjustment ({po_item.purchase_order.batch})'
                    logger.info(f'{quantity_adjustment}: quantity adjusted')
                elif inventory.quantity > quantity:
                    quantity_adjustment = inventory.quantity - quantity
                    inventory.quantity = quantity
                    # quantity_adjustment = quantity
                    action = 'purchase edit -'
                    description = f'Stock adjustment ({po_item.purchase_order.batch})'
                    logger.info(f'{quantity_adjustment}: quantity adjusted')
                else:
                    action = 'price edit'
                    logger.info(f'{quantity_adjustment}: quantity adjusted')
                    inventory.quantity = quantity
                    description = f'Price adjustment ({po_item.purchase_order.batch})'

            # Update fields in the PurchaseOrderItem
            with transaction.atomic():
                po_item.selling_price = selling_price
                po_item.dealer_price = dealer_price
                po_item.expected_profit = expected_profit
                po_item.dealer_expected_profit = dealer_expected_profit
                po_item.received_quantity = quantity
                po_item.save()

                inventory.price = selling_price
                inventory.dealer_price = dealer_price

                # cost = average_inventory_cost(inventory.id, po_item.unit_cost, quantity, request.user.branch.id)
                # logger.info(po_item.actual_unit_cost)

                inventory.cost = cost
                inventory.save()

                ActivityLog.objects.create(
                    purchase_order=po_item.purchase_order,
                    branch=request.user.branch,
                    user=request.user,
                    action=action,
                    inventory=inventory,
                    quantity=quantity_adjustment,
                    system_quantity = system_quantity,
                    description=description,
                    total_quantity=inventory.quantity,
                    dealer_price = dealer_price,
                    selling_price = selling_price
                )

        except Inventory.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Inventory not found for the product'}, status=404)

        logger.info('done')
        return JsonResponse({'success': True, 'message': 'Purchase Order Item updated successfully'}, status=200)

    except PurchaseOrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Purchase Order Item not found'}, status=404)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)

@login_required
def mark_purchase_order_done(request, po_id):
    if po_id:
        try:
            with transaction.atomic():
                purchase_order = PurchaseOrder.objects.select_for_update().get(id=po_id)
                purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)

                if purchase_order.received:
                    return JsonResponse({'succes':False, 'message':'Purchase order already marked as received'})

                flag = True
                for item in purchase_order_items:
                    if not item.received:
                        flag = False
                        break

                purchase_order.received = flag
                purchase_order.save()

                if flag:
                    return JsonResponse({'success':True, 'messages':'Purchase order has been successfully confirmed!'})
                else:
                    return JsonResponse({'success':False, 'message':'Purchase order not confirmed, Please receive all items.'})

        except PurchaseOrder.DoesNotExist:
            return JsonResponse({'success':False, 'message': f'Purchase order with ID {po_id} not found'})
        except Exception as e:
            logger.error(f'Error processing purchase order {po_id}: {str(e)}')
            return JsonResponse({'success':False, 'message':'An error occurred while processing the purchase order'})
    else:
        return JsonResponse({'success':False, 'message':'Purchase order ID is required'})

@login_required
def edit_purchase_order(request, po_id):
    if request.method == 'GET':
        purchase_order = PurchaseOrder.objects.get(id=po_id)
        supplier_form = AddSupplierForm()
        product_form = AddProductForm()
        suppliers = Supplier.objects.all()
        note_form = noteStatusForm()
        batch_form = BatchForm()

        batch_codes = BatchCode.objects.all()

        return render(request, 'edit_purchase_order.html', {
            'purchase_order':purchase_order,
            'product_form':product_form,
            'supplier_form':supplier_form,
            'suppliers':suppliers,
            'note_form':note_form,
            'batch_form':batch_form,
            'batch_codes':batch_codes,
         })

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            purchase_order_data = data.get('purchase_order', {})
            purchase_order_items_data = data.get('po_items', [])
            expenses = data.get('expenses', [])
            cost_allocations = data.get('cost_allocations', [])
            overide = data.get('overide')
            hold = data.get('hold')
            purchase_order_id = data.get('purchase_order_id')

            logger.info(purchase_order_items_data)

            # remove duplicates
            unique_expenses = []
            seen = set()
            for expense in expenses:
                expense_tuple = (expense['name'], expense['amount'])
                if expense_tuple not in seen:
                    seen.add(expense_tuple)
                    unique_expenses.append(expense)

            # get previous purchase_order
            last_purchase_order = PurchaseOrder.objects.get(id=po_id)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

        batch = purchase_order_data['batch']
        delivery_date = purchase_order_data['delivery_date']
        status = purchase_order_data['status']
        notes = purchase_order_data['notes']
        total_cost = Decimal(purchase_order_data['total_cost'])
        discount = Decimal(purchase_order_data['discount'])
        tax_amount = Decimal(purchase_order_data['tax_amount'])
        other_amount = Decimal(purchase_order_data['other_amount'])
        payment_method = purchase_order_data.get('payment_method')


        logger.info(f'hold: {hold}')

        if not all([delivery_date, status, total_cost, payment_method]):
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

        try:
            purchase_order = PurchaseOrder.objects.get(pk=purchase_order_id)
            with transaction.atomic():
                purchase_order.batch = batch
                purchase_order.delivery_date = delivery_date
                purchase_order.status = status
                purchase_order.order_date = purchase_order.order_date
                purchase_order.notes = notes
                purchase_order.total_cost = total_cost
                purchase_order.discount = discount
                purchase_order.tax_amount = tax_amount
                purchase_order.other_amount = other_amount
                purchase_order.branch = request.user.branch
                purchase_order.is_partial = False
                purchase_order.received = False
                purchase_order.hold = hold
                purchase_order.save()

                logger.info(f'purchase order item: {purchase_order.total_cost}')


                products = Inventory.objects.filter(branch=request.user.branch)
                suppliers = Supplier.objects.all()
                logs = ActivityLog.objects.filter(purchase_order=last_purchase_order).select_related('inventory')

                products_dict = {product.id: product for product in products}
                suppliers_dict = {supplier.id: supplier for supplier in suppliers}
                logs_dict = {log.inventory_id: log.quantity for log in logs}

                logger.info(products_dict)

                supplier = Supplier.objects.get(id=1)

                logger.info(supplier)

                purchase_order_items_bulk = []
                existing_items = {item.product_id: item for item in PurchaseOrderItem.objects.filter(purchase_order=purchase_order)}

                for item_data in purchase_order_items_data:
                    product_id = int(item_data['product_id'])
                    product = products_dict.get(product_id)
                    log_quantity = logs_dict.get(product_id, 0)

                    if not product:
                        return JsonResponse({'success': False, 'message': 'Invalid product'}, status=400)

                    if product_id in existing_items:
                        # Update the existing item
                        existing_item = existing_items[product_id]
                        existing_item.quantity = item_data['quantity']
                        existing_item.unit_cost = item_data['price']
                        existing_item.actual_unit_cost = item_data['price']
                        existing_item.received_quantity = log_quantity
                        existing_item.supplier = supplier
                        existing_item.wholesale_price = 0
                        existing_item.received = False
                        existing_item.price = 0
                        existing_item.save()
                    else:
                        # Create a new item for bulk creation
                        purchase_order_items_bulk.append(
                            PurchaseOrderItem(
                                purchase_order=purchase_order,
                                product=product,
                                quantity=item_data['quantity'],
                                unit_cost=item_data['price'],
                                actual_unit_cost=item_data['price'],
                                received_quantity=log_quantity,
                                supplier=supplier,
                                wholesale_price=0,
                                received=False,
                                price=0,
                            )
                        )

                    product.price = 0
                    product.save()

                PurchaseOrderItem.objects.bulk_create(purchase_order_items_bulk)

                expense_bulk = []
                for expense in unique_expenses:
                    name = expense['name']
                    amount = expense['amount']
                    expense_bulk.append(
                        otherExpenses(
                            purchase_order=purchase_order,
                            name=name,
                            amount=amount
                        )
                    )
                otherExpenses.objects.bulk_create(expense_bulk)

                costs_list = []

                for cost in cost_allocations:
                    costs_list.append(
                        costAllocationPurchaseOrder(
                            purchase_order = purchase_order,
                            allocated = cost['allocated'],
                            allocationRate = cost['allocationRate'],
                            expense_cost = cost['expCost'],
                            price = cost['price'],
                            quantity = int(cost['quantity']),
                            product = cost['product'],
                            total = cost['total'],
                            total_buying = cost['totalBuying']
                        )
                    )
                costAllocationPurchaseOrder.objects.bulk_create(costs_list)

                # if purchase_order.status in ['Received', 'received']:
                #     if_purchase_order_is_received(
                #         request,
                #         purchase_order,
                #         tax_amount,
                #         payment_method
                #     )

                remove_purchase_order(po_id, request)

        except Exception as e:
            logger.info(e)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

        return JsonResponse({'success': True, 'message': 'Purchase order created successfully'})

def remove_purchase_order(purchase_order_id, request):
    try:
        # Retrieve the purchase order
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)

        #logger.info(f'purchase_order: {purchase_order}')

        with transaction.atomic():

            # Reverse related account transactions
            currency = Currency.objects.filter(default=True).first()

            account_transaction = AccountTransaction.objects.filter(expense__purchase_order=purchase_order).first()
            if account_transaction:
                account_balance = AccountBalance.objects.get(account=account_transaction.account)

                # Reverse account balance adjustments
                account_balance.balance += purchase_order.total_cost
                account_balance.save()

                # Delete account transaction log
                account_transaction.delete()

            # Reverse Cashbook entry
            cashbook_entry = Cashbook.objects.filter(expense__purchase_order=purchase_order).first()
            if cashbook_entry:
                cashbook_entry.delete()

            # Reverse the VAT transaction
            vat_transaction = VATTransaction.objects.filter(purchase_order=purchase_order).first()
            if vat_transaction:
                vat_transaction.delete()

            # Reverse the Expense record
            expense = Expense.objects.filter(purchase_order=purchase_order).first()
            if expense:
                expense.delete()

            # Reverse other expenses related to the purchase order
            other_expenses = otherExpenses.objects.filter(purchase_order=purchase_order)
            if other_expenses.exists():
                other_expenses.delete()

            #deduct product quantity
            items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order, received=True)
            products = Inventory.objects.filter(branch=request.user.branch)

            logger.info(f'products in the branch {products}')

            for item in items:
                for prod in products:
                    if item.product == prod:
                        system_quantity = prod.quantity
                        prod.quantity -= item.received_quantity

                        # eliminate negative stock
                        if prod.quantity < 0:
                            prod.quantity = 0

                        prod.save()

                        ActivityLog.objects.create(
                            branch = request.user.branch,
                            user= request.user,
                            action= 'purchase edit -',
                            inventory=prod,
                            system_quantity=system_quantity,
                            quantity=item.received_quantity,
                            total_quantity=prod.quantity,
                            description=f'Purchase order: {item.purchase_order.batch} edit'
                        )
    except Exception as e:
        logger.info(e)

@login_required
def edit_purchase_order_data(request, po_id):
    try:
        expenses = otherExpenses.objects.filter(purchase_order__id=po_id).values()

        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order__id=po_id).values(
            'purchase_order__id',
            'product__name',
            'product__id',
            'quantity',
            'unit_cost',
            'actual_unit_cost',
            'expected_profit',
            'supplier__name',
            'supplier'
        )

        return JsonResponse({'success':True, 'po_items':list(purchase_order_items), 'expenses':list(expenses)})

    except Exception as e:
        return JsonResponse({"success":False, 'message':f'{e}'})
