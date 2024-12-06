from django.utils import timezone
import json, datetime, openpyxl
from os import system 
import csv, base64
from django.core.files.base import ContentFile
from django.http import HttpResponse
from datetime import timedelta
from openpyxl.styles import Alignment, Font, PatternFill
from . models import *
from . tasks import (
    send_transfer_email,
    download_stock_logs_account
)
from decimal import Decimal
from django.views import View
from django.db.models import Q
from django.db.models import Sum
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
from . utils import (
    calculate_inventory_totals, 
    average_inventory_cost
)
from . forms import (
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
    PurchaseOrderStatus,
    ReorderSettingsForm,
    EditSupplierForm
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


@login_required
def notifications_json(request):
    notifications = StockNotifications.objects.filter(inventory__branch=request.user.branch).values(
        'inventory__product__name', 'type', 'notification', 'inventory__id'
    )
    return JsonResponse(list(notifications), safe=False)

@login_required
def service(request):
    form = ServiceForm()
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service_obj = form.save(commit=False)
            service_obj.cost = 0
            service_obj.branch = request.user.branch
            service_obj.save()
            messages.success(request, 'Service successfully created')
            return redirect('inventory:inventory')
        messages.warning(request, 'Invalid form data')
    return redirect('inventory:inventory')
    
@login_required
def batch_code(request):
    if request.method == 'GET':
        
        batch_codes = BatchCode.objects.all().values(
            'id',
            'code'
        )
        logger.info(batch_codes)
        return JsonResponse(list(batch_codes), safe=False)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('batch_code')

            BatchCode.objects.create(code=code)
            return JsonResponse({'success':True}, status=200)
        except Exception as e:
            logger.info(e)
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

@login_required
def product_list(request): 
    """ for the pos """
    queryset = Inventory.objects.filter(branch=request.user.branch, status=True)
    services = Service.objects.all().order_by('-name')

    search_query = request.GET.get('q', '') 
    product_id = request.GET.get('product', '')
    category_id = request.GET.get('category', '')

    if category_id:
        queryset = queryset.filter(product__category__id=category_id)
    if search_query:
        queryset = queryset.filter(
            Q(product__name__icontains=search_query) | 
            Q(product__description__icontains=search_query) 
        )
    if product_id:
        queryset = queryset.filter(id=product_id)

    inventory_data = list(queryset.values(
        'id', 
        'name', 
        'description', 
        'category__id', 
        'category__name',  
        'end_of_day',
        'price', 
        'quantity',
        'dealer_price',
        'image'
    ))
    
    merged_data = [{
        'inventory_id': item['id'],
        'product_id': item['id'],
        'product_name':item['name'],
        'description': item['description'],
        'category': item['category__id'],
        'category_name': item['category__name'],
        'end_of_day':item['end_of_day'],
        'price': item['price'],
        'quantity': item['quantity'],
        'dealer_price':item['dealer_price'],
        'image':item['image']
    } for item in inventory_data]
    return JsonResponse(merged_data, safe=False)

@login_required
def branches_inventory(request):
    return render(request, 'branches_inventory.html')

@login_required
def branches_inventory_json(request):
    branches_inventory = Inventory.objects.filter(status=True).values(
        'product__name', 'price', 'quantity', 'branch__name'
    )
    return JsonResponse(list(branches_inventory), safe=False)
        
class AddProductView(LoginRequiredMixin, View):
    form_class = AddProductForm()
    initial = {'key':'value'}
    template_name = 'add_product.html'
    
    def get(self, request, *args, **kwargs):
        form = self.form_class
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            form = AddProductForm(request.POST)
            product_name = request.POST['name']
            
            try:
                product = Inventory.objects.get(name=product_name, branch=request.user.branch)                
                messages.warning(request, f'Product with name {product_name} exists.')
                return redirect('inventory:add_product')
            except Inventory.DoesNotExist:
                if form.is_valid():
                    product = form.save()
                    message = 'Product successfully created'
                    log_action = 'stock in'
                else:
                    messages.warning(request, 'Invalid form data')
                    return redirect('inventory:inventory')
                
            self.create_branch_inventory(product, log_action)
            
            messages.success(request, message)
        return redirect('inventory:inventory')


    def create_branch_inventory(self, product, log_action):
        try:
            inv = Inventory.objects.get(product__name=product.name)
            inv.quantity += product.quantity
            inv.price = product.price
            inv.cost = product.cost
            inv.save()
            self.activity_log(log_action, inv, inv)
        except Inventory.DoesNotExist:
            inventory = Inventory.objects.create(
                product=product,
                quantity=product.quantity,
                price=product.price,
                cost=product.cost,
                branch=self.request.user.branch,
                stock_level_threshold=product.min_stock_level
            )
            self.activity_log(log_action, inventory, inv=0)  
    
    def activity_log(self, action, inventory, inv):
        ActivityLog.objects.create(
            branch = self.request.user.branch,
            user=self.request.user,
            action= action,
            inventory=inventory,
            quantity=inventory.quantity,
            total_quantity=inventory.quantity + inv.quantity if action == 'update' else inventory.quantity
        )

class ProcessTransferCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        """it have two main functions to create a held transfer and to create a new transfer"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                action = data['action']
                branches = data['branches_to']
                transfer_id = data.get('transfer_id', '')

                logger.info(f'branches: {branches}')
                
                # create list of branch objects
                branch_obj_list = []
                branch_names = ''
                for branch in branches:
                    branch_names += f'{branch['name']} '
                    if branch.get('value'):
                        branch_obj_list.append(Branch.objects.get(id=branch['value']))
                    else:
                        branch_obj_list.append(Branch.objects.get(name=branch['name']))
                        
                
                # check for hold or new transfer
                if not transfer_id:
                    transfer = Transfer.objects.create(
                        branch = request.user.branch,
                        user = request.user,
                        transfer_ref = Transfer.generate_transfer_ref(request.user.branch.name, branch_names),
                        description = 'transfer' #to be actioned
                    )
                else:
                    logger.info('here')
                    transfer = Transfer.objects.get(id=transfer_id)
                
                #assign many2many objects to transfer branch
                transfer.transfer_to.set(branch_obj_list),

                if action == 'process':
                    logger.info(f'branches: {branch_obj_list}')
                    for branch_obj in branch_obj_list:
                        for item in data['cart']:
                            logger.info(f'Cart Item: {item}')
                            
                            product = Inventory.objects.get(id=item['product_id'], branch=request.user.branch)

                            logger.info(f'Transfered product: {product.name}')

                            branch_name = item['branch_name']

                            logger.info(f'branch name: {branch_name}')

                            if branch_name == branch_obj.name:
                                transfer_item = TransferItems(
                                    transfer=transfer,
                                    product = product,
                                    cost = item['cost'],
                                    price=item['price'],
                                    dealer_price = item['dealer_price'],
                                    quantity=item['quantity'],
                                    from_branch= request.user.branch,
                                    to_branch= branch_obj,
                                    description=f'from {request.user.branch} to {branch_obj} '
                                ) 
                                         
                                transfer_item.save()

                                logger.info(f'Transfered product: product saved')
                                
                                self.deduct_inventory(transfer_item)
                                self.transfer_update_quantity(transfer_item, transfer) 
              
                    # send email for transfer alert
                    # transaction.on_commit(lambda: send_transfer_email(request.user.email, transfer.id, transfer.transfer_to.id))

                    # held transfer items 
                    transfer_items = Holdtransfer.objects.filter(transfer__id=transfer.id)
                    transfer_items.delete()

                    # save the transfer
                    transfer.hold = False
                    transfer.date = datetime.datetime.now()
                    transfer.save()  
                                
                else:
                    self.hold_transfer(branch_obj_list, data, transfer, request)
            return JsonResponse({'success': True})     
        except Exception as e:
            logger.info(e)
            return JsonResponse({'success': False, 'data': str(e)})
        
    def hold_transfer(self, branch_obj_list, data, transfer, request):
        logger.info('Processing Hoding Transfers ------')
        logger.info(f'branches: {branch_obj_list}')
        logger.info(f'data: {data}')
        logger.info(f'transfer: {transfer}')

        with transaction.atomic():
            for branch_obj in branch_obj_list:
                for item in data['cart']:
                    product = Product.objects.get(name=item['product'])

                    branch_name = item['branch_name']

                    logger.info(f'branch name: {branch_name}')
                    logger.info(f'cost: {item['cost']}')

                    try:
                        if branch_name == branch_obj.name:
                            transfer_item = Holdtransfer(
                                transfer=transfer,
                                product = product,
                                cost = item['cost'],
                                price=item['price'],
                                dealer_price = item['dealer_price'],
                                quantity=item['quantity'],
                                from_branch= request.user.branch,
                                to_branch= branch_obj,
                                description=f'from {request.user.branch} to {branch_obj}'
                            ) 
                            transfer.hold = True
                            transfer.save()         
                            transfer_item.save()
                            logger.info('Transfer has been hold')
                    except Exception as e:
                        return JsonResponse({'success':False, 'message':f'{e}'})

    def deduct_inventory(self, transfer_item):
        logger.info(f'from branch -> {transfer_item.from_branch}')
        branch_inventory = Inventory.objects.get(id=transfer_item.product.id, branch__name=transfer_item.from_branch)
        
        branch_inventory.quantity -= int(transfer_item.quantity)
        branch_inventory.save()
        self.activity_log('Transfer', branch_inventory, transfer_item)
        
    def transfer_update_quantity(self, transfer_item, transfer):
        transfer = Transfer.objects.get(id=transfer.id)
        transfer.quantity += transfer_item.quantity
        transfer.save()
       
    def activity_log(self,  action, inventory, transfer_item):
        logger.info(f'selling_price transfered {transfer_item.dealer_price}: {transfer_item.price}')
        ActivityLog.objects.create(
            invoice = None,
            product_transfer = transfer_item,
            branch = self.request.user.branch,
            user=self.request.user,
            action= action,
            dealer_price = transfer_item.dealer_price,
            selling_price = transfer_item.price,
            inventory=inventory,
            system_quantity = inventory.quantity,
            quantity=transfer_item.quantity,
            total_quantity=inventory.quantity
        )

@login_required
def delete_transfer(request, transfer_id):
    try:
        transfer = get_object_or_404(Transfer, id=transfer_id)

        if transfer.receive_status:
            return JsonResponse({'success':False, 'message':f'Cancel failed the transfer is already received.'})

        transfer_items = TransferItems.objects.filter(transfer=transfer)

        with transaction.atomic():
            for item in transfer_items:
                logger.info(f'From branch {item.from_branch}')

                product = Inventory.objects.get(branch=item.from_branch, product=item.product)
                product.quantity += item.quantity
                product.save()

                logger.info(f'returned product {product}')

                ActivityLog.objects.create(
                    invoice = None,
                    product_transfer = item,
                    branch = request.user.branch,
                    user=request.user,
                    action= 'transfer cancel',
                    inventory=product,
                    selling_price = item.price,
                    dealer_price = item.dealer_price,
                    quantity=item.quantity,
                    total_quantity=product.quantity,
                    description = 'Transfer cancelled'
                )
            transfer.delete = True
            transfer.save()

        return JsonResponse({'success':True})
    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'})
        
        
@login_required       
def transfer_details(request, transfer_id):
    transfer = TransferItems.objects.filter(id=transfer_id).values(
        'product__name', 'transfer__transfer_ref', 'quantity', 'price', 'from_branch__name', 'to_branch__name'
    )
    return JsonResponse(list(transfer), safe=False)

@login_required
def inventory(request):
    product_id = request.GET.get('id', '')
    logger.info(f'product id: {product_id}')
    if product_id:
        logger.info(list(Inventory.objects.\
            filter(id=product_id, branch=request.user.branch, status=True).values()))
        return JsonResponse(list(Inventory.objects.\
            filter(id=product_id, branch=request.user.branch, status=True).values()), safe=False)
    return JsonResponse({'error':'product doesnt exists'})

from django.db.models import Count


@login_required
def inventory_index(request):
    form = ServiceForm()
    q = request.GET.get('q', '')  
    category = request.GET.get('category', '')    
    
    services = Service.objects.all().order_by('-name')
    accessories = Accessory.objects.all()
    inventory = Inventory.objects.filter(branch=request.user.branch, status=True).order_by('name')

    # # Step 1: Get the inventory products with quantity 0 and not logged in ActivityLog
    # products_with_zero_quantity = Inventory.objects.filter(
    #     branch=request.user.branch, 
    #     status=True, 
    #     quantity=0
    # ).exclude(
    #     id__in=ActivityLog.objects.values('inventory_id') 
    # )

    # print(products_with_zero_quantity)
    # print(products_with_zero_quantity)

    # # Step 2: Find duplicate products based on name
    # duplicates = products_with_zero_quantity.values('name').annotate(
    #     count=Count('name')
    # ).filter(count__gt=1)  # Only consider products with more than 1 instance
    # # Step 2: Find duplicate products based on name
    # duplicates = products_with_zero_quantity.values('name').annotate(
    #     count=Count('name')
    # ).filter(count__gt=1)  # Only consider products with more than 1 instance

    # # Step 3: For each group of duplicates, delete all but the first product
    # for product in duplicates:
    #     # Get all products with the same name
    #     product_group = products_with_zero_quantity.filter(name=product['name'])
    # # Step 3: For each group of duplicates, delete all but the first product
    # for product in duplicates:
    #     # Get all products with the same name
    #     product_group = products_with_zero_quantity.filter(name=product['name'])
        
    #     # Keep the first product and delete the rest
    #     first_product = product_group.first()  # Get the first product
    #     product_group.exclude(id=first_product.id).delete() 
    #     logger.info(f'{first_product}, deleted') # 
    #     # Keep the first product and delete the rest
    #     first_product = product_group.first()  # Get the first product
    #     product_group.exclude(id=first_product.id).delete() 
    #     logger.info(f'{first_product}, deleted') # 

    # if category:
    #     if category == 'inactive':
    #         inventory = Inventory.objects.filter(branch=request.user.branch, status=False)
    #     else:
    #         inventory = inventory.filter(category__name=category)
                
    if 'download' and 'excel' in request.GET:
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename={request.user.branch.name} stock.xlsx'
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        
        # Add products data
        products = Inventory.objects.all()
        branches = Branch.objects.all().values_list('name', flat=True).distinct()
        row_offset = 0
        for branch in branches:
            worksheet['A' + str(row_offset + 1)] = f'{branch} Products'
            worksheet.merge_cells('A' + str(row_offset + 1) + ':D' + str(row_offset + 1))
            cell = worksheet['A' + str(row_offset + 1)]
            cell.alignment = Alignment(horizontal='center')
            cell.font = Font(size=16, bold=True)
            cell.fill = PatternFill(fgColor='AAAAAA', fill_type='solid')

            row_offset += 1 
            
            category_headers = ['Name', 'Cost', 'Price', 'Quantity']
            for col_num, header_title in enumerate(category_headers, start=1):
                cell = worksheet.cell(row=3, column=col_num)
                cell.value = header_title
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')

            categories = Inventory.objects.filter(branch=request.user.branch).values_list('product__category__name', flat=True).distinct()
            for category in categories:
                products_in_category = products.filter(branch__name=branch, product__category__name=category)
                if products_in_category.exists():
                    worksheet['A' + str(row_offset + 1)] = category
                    cell = worksheet['A' + str(row_offset + 1)]
                    cell.font = Font(color='FFFFFF')
                    cell.fill = PatternFill(fgColor='0066CC', fill_type='solid')
                    worksheet.merge_cells('A' + str(row_offset + 1) + ':D' + str(row_offset + 1))
                    row_offset += 2

                for product in products.filter(branch__name=branch):
                    if category == product.product.category.name:
                        worksheet.append([product.product.name, product.cost, product.price, product.quantity])
                        row_offset += 1

        workbook.save(response)
        return response
    
    all_branches_inventory = Inventory.objects.filter(branch=request.user.branch)
    
    totals = calculate_inventory_totals(all_branches_inventory.filter(status=True))
    logger.info(inventory.values('image'))
  
    return render(request, 'inventory.html', {
        'form': form,
        'services':services,
        'inventory': inventory,
        'search_query': q,
        'category':category,
        'total_price': totals[1],
        'total_cost':totals[0],
        'accessories':accessories
    })

@login_required
def edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    if request.method == 'GET':
        form = ServiceForm(instance=service)
        return render(request, 'edit_service.html', {'form': form, 'service': service})
    
    elif request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f'{service.name} successfully edited')
            return redirect('inventory:inventory')
        else:
            messages.warning(request, 'Please correct the errors below')
    
    else:
        messages.warning(request, 'Invalid request')
        return redirect('inventory:inventory')
    
    return render(request, 'edit_service.html', {'form': form, 'service': service})
        
@login_required   
def inventory_index_json(request):
    inventory = Inventory.objects.filter(branch=request.user.branch, status=True).values(
        'id', 'product__name', 'product__quantity', 'product__id', 'price', 'cost', 'quantity', 'reorder'
    ).order_by('product__name')
    return JsonResponse(list(inventory), safe=False)

@login_required 
@transaction.atomic
def activate_inventory(request, product_id):
    product = get_object_or_404(Inventory, id=product_id)
    product.status=True
    product.save()
    
    ActivityLog.objects.create(
        invoice = None,
        product_transfer = None,
        branch = request.user.branch,
        user=request.user,
        action= 'activated',
        inventory=product,
        quantity=product.quantity,
        total_quantity=product.quantity
    )
    
    messages.success(request, 'Product succefully activated')
    return redirect('inventory:inventory')

@login_required
def edit_inventory(request, product_id):
    inv_product = Inventory.objects.get(id=product_id, branch=request.user.branch)

    if request.method == 'POST':
        end_of_day = request.POST.get('end_of_day')

        if end_of_day:
            inv_product.end_of_day = True
        
        selling_price = Decimal(request.POST['price'])
        dealer_price = Decimal(request.POST['dealer_price'])
        
        # think through
        quantity = inv_product.quantity
        inv_product.name=request.POST['name']
        # inv_product.batch=request.POST['batch_code']
        inv_product.description=request.POST['description']
        
        inv_product.price = Decimal(request.POST['price'])
        inv_product.cost = Decimal(request.POST['cost'])
        inv_product.dealer_price = Decimal(request.POST['dealer_price'])
        inv_product.stock_level_threshold = request.POST['min_stock_level']
        inv_product.dealer_price = dealer_price
        inv_product.quantity = request.POST['quantity']
        
        inv_product.save()
        
        ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= 'Edit',
            inventory=inv_product,
            quantity=quantity,
            total_quantity=inv_product.quantity,
            dealer_price = dealer_price,
            selling_price = selling_price
        )
        
        messages.success(request, f'{inv_product.name} update succesfully')
        return redirect('inventory:inventory')
    return render(request, 'inventory_form.html', {'product':inv_product, 'title':f'Edit >>> {inv_product.name}'})

from django.db.models.functions import Extract

@login_required
def inventory_detail(request, id):
    purchase_order_items = PurchaseOrderItem.objects.all()
    inventory = Inventory.objects.get(id=id, branch=request.user.branch)
    logs = ActivityLog.objects.filter(
        inventory=inventory,
        branch=request.user.branch
    ).order_by('-timestamp__date', '-timestamp__time')

    # stock account data and totals (costs and quantities)
    stock_account_data = get_stock_account_data(logs)
    total_debits = sum(entry['cost'] for entry in stock_account_data if entry['type'] == 'debits')
    total_credits = sum(entry['cost'] for entry in stock_account_data if entry['type'] == 'credits')

    total_debits_quantity = sum(entry['quantity'] for entry in stock_account_data if entry['type'] == 'debits')
    total_credits_quantity = sum(entry['quantity'] for entry in stock_account_data if entry['type'] == 'credits')

    logger.info(f'debits {total_debits_quantity}')

    remaining_stock_quantity = total_debits_quantity - total_credits_quantity

    """ get inventory value based on the currencies in the system """
    inventory_value = []
    inventory_sold_value = []
    inventory_total_cost = inventory.cost * inventory.quantity

    for currency in Currency.objects.all():
        inventory_value.append(
            {
                'name': f'{currency.name}',
                'value': float(inventory_total_cost * currency.exchange_rate )if currency.exchange_rate == 1\
                        else float(inventory_total_cost * currency.exchange_rate)
            }
        )
        inventory_sold_value.append(
            {
                'name': f'{currency.name}',
                'value': logs.filter(invoice__invoice_return = False, invoice__currency=currency).\
                        aggregate(Sum('invoice__amount'))['invoice__amount__sum'] or 0
            }
        )
    
    logger.info(f'inventory value: {inventory_sold_value}')

    # logs = ActivityLog.objects.annotate(hour=Extract('timestamp', 'hour')).order_by('-hour')

    """ create log data structure for the activity log graph """
    sales_data = {}
    stock_in_data = {}
    transfer_data = {}
    labels = []

    for log in logs:
        month_name = log.timestamp.strftime('%B')  
        year = log.timestamp.strftime('%Y')
        month_year = f"{month_name} {year}"  

        if log.action == 'Sale':
            if month_year in sales_data:
                sales_data[month_year] += log.quantity
            else:
                sales_data[month_year] = log.quantity
        elif log.action in ('stock in', 'Update'):
            if month_year in stock_in_data:
                stock_in_data[month_year] += log.quantity
            else:
                stock_in_data[month_year] = log.quantity
        elif log.action == 'Transfer':
            if month_year in transfer_data:
                transfer_data[month_year] += log.quantity
            else:
                transfer_data[month_year] = log.quantity

        if month_year not in labels:
            labels.append(month_year)

    """ download a log or stock account pdf """

    if request.GET.get('logs'):
        print(request.GET.get('logs'))
        download_stock_logs_account('logs', logs, inventory)
    elif request.GET.get('account'):
        download_stock_logs_account('account', logs, inventory)
    
    return render(request, 'inventory_detail.html', {
        'inventory': inventory,
        'remaining_stock_quantity':remaining_stock_quantity,
        'stock_account_data':stock_account_data,
        'inventory_value':inventory_value,
        'inventory_sold_value':inventory_sold_value,
        'total_debits':total_debits,
        'total_credits':total_credits,
        'logs': logs,
        'items':purchase_order_items,
        'sales_data': list(sales_data.values()), 
        'stock_in_data': list(stock_in_data.values()),
        'transfer_data': list(transfer_data.values()),
        'labels': labels,
    })

def get_stock_account_data(logs):
    """ 
    logs data structure with both debits and credits, using default currency 
    debits => stock in,  transfer_in, sales_returns, positive_adjustments
    credits => transfer_out, supplier_returns, negative_adjustments, sale
"""
    stock_account = []
    for log in logs:
        if log.action in ['stock in', 'transfer_in', 'sale return', 'purchase edit +', 'stock adjustment']:
            entry_type = 'debits'
        elif log.action in ['transfer', 'returns', 'Sale', 'purchase edit -', 'write off']:
            entry_type = 'credits'
        else:
            continue  
        
        # Calculate cost (ensure inventory cost is handled correctly)
        inventory_cost = getattr(log.inventory, 'cost', Decimal('0.00'))
        cost = log.quantity * inventory_cost
        
        # Append entry to stock account
        stock_account.append({
            'type': entry_type,
            'description': log.action,
            'quantity': log.quantity,
            'cost': cost,
            # 'currency': 'USD',
            'timestamp': log.timestamp,
            'user': log.user.username if log.user else 'Unknown',
            'branch': log.branch.name,
        })
    
    return stock_account


@login_required    
def inventory_transfers(request):
    form = addTransferForm()
    q = request.GET.get('q', '') 
    branch_id = request.GET.get('branch', '')

    transfer_items = TransferItems.objects.filter(
        Q(from_branch=request.user.branch) |
        Q(to_branch = request.user.branch),
        transfer__delete=False
    )
    
    transfers = Transfer.objects.filter(
        Q(branch=request.user.branch) |
        Q(transfer_to__in = [request.user.branch]),
        delete=False
    ).annotate(
        total_quantity=Sum('transferitems__quantity'),
    ).order_by('-time').distinct()

    logger.info(f'transfers: {transfers}')
    
    if q:
        transfers = transfers.filter(Q(transfer_ref__icontains=q) | Q(date__icontains=q) )
        
    if branch_id: 
        transfers = transfers.filter(transfer_to__id=branch_id)

    total_transferred_value = (
    transfer_items.annotate(total_value=F('quantity') * F('cost'))\
        .aggregate(total_sum=Sum('total_value'))['total_sum'] or 0
    )

    total_received_value = (
    transfer_items.annotate(total_value=F('quantity') * F('cost'))\
        .aggregate(total_sum=Sum('total_value'))['total_sum'] or 0
    )

    logger.info(f'value: {total_transferred_value}, received {total_received_value}')
        
    return render(request, 'transfers.html', {
        'transfers': transfers,
        'search_query': q, 
        'form':form, 
        'transfer_items':transfer_items,
        'transferred_value':total_transferred_value,
        'received_value':total_received_value,
        'hold_transfers_count':Transfer.objects.filter(
                Q(branch=request.user.branch) |
                Q(transfer_to__in=[request.user.branch]),
                delete=False, 
                hold=True
            ).count()
        }
    )

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
    logger.info(f'held transfers: {transfers}')
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
    
@login_required
@transaction.atomic
def receive_inventory(request):
    if request.method == 'POST':
        try:  
            transfer_id = request.POST['id']
            quantity_received = int(request.POST['quantity'])
            received = request.POST['received']

            logger.info(f'transfer item data{received}')

            branch_transfer = get_object_or_404(TransferItems, id=transfer_id, to_branch=request.user.branch)
            transfer_obj = get_object_or_404(Transfer, id=branch_transfer.transfer.id, transfer_to=request.user.branch)

            if quantity_received > branch_transfer.quantity:
                return JsonResponse({'success': 'false', 'message': 'Quantity received cannot be more than quantity transferred'}, status=400)

            if received:
                if quantity_received != branch_transfer.quantity:
                    branch_transfer.over_less_quantity = branch_transfer.quantity - quantity_received
                    branch_transfer.over_less = True
                    branch_transfer.save()

                product, created = Inventory.objects.get_or_create(
                    name=branch_transfer.product.name,
                    branch=request.user.branch,
                    defaults={
                        'cost': branch_transfer.cost,
                        'price': branch_transfer.price,
                        'quantity': branch_transfer.quantity,
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
                    description=f'received {quantity_received} out of {branch_transfer.quantity}'
                )

                product.batch += f'{branch_transfer.product.batch}, '
                product.save()

            branch_transfer.quantity_track = branch_transfer.quantity - quantity_received
            branch_transfer.receieved_quantity += quantity_received
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

    # Handle GET requests
    transfers = TransferItems.objects.filter(to_branch=request.user.branch).order_by('-date')
    all_transfers = Transfer.objects.filter(transfer_to=request.user.branch, delete=False).order_by('-time')
    return render(request, 'receive_inventory.html', {'r_transfers': transfers, 'transfers': all_transfers})


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
@transaction.atomic
def over_less_list_stock(request):
    form = DefectiveForm()
    search_query = request.GET.get('search_query', '')
    
    transfers =  TransferItems.objects.filter(to_branch=request.user.branch)

    if search_query:
        transfers = transfers.filter(
            Q(transfer__product__name__icontains=search_query)|
            Q(transfer__transfer_ref__icontains=search_query)|
            Q(date__icontains=search_query)
        )
        
    def activity_log(action, inventory, branch_transfer):
        ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= action,
            inventory=inventory,
            quantity=branch_transfer.over_less_quantity,
            total_quantity=inventory.quantity,
            product_transfer=branch_transfer
        )
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        action = data['action']
        transfer_id = data['transfer_id']
        reason = data['reason']
        status = data['status']
        branch_loss = data['branch_loss']
        quantity= data['quantity']
  
        branch_transfer = get_object_or_404(transfers, id=transfer_id)
        transfer = get_object_or_404(Transfer, id=branch_transfer.transfer.id)
        product = Inventory.objects.get(product=branch_transfer.product, branch=request.user.branch)
       
        if int(branch_transfer.over_less_quantity) > 0:
            if action == 'write_off':    
                product.quantity += branch_transfer.over_less_quantity 
                product.save()
                
                description='write_off'
                
                activity_log('Stock in', product, branch_transfer)
                
                DefectiveProduct.objects.create(
                    product = product,
                    branch = request.user.branch,
                    quantity = quantity,
                    reason = reason,
                    status = status,
                    branch_loss = get_object_or_404(Branch, id=branch_loss),
                )
                
                product.quantity -= branch_transfer.over_less_quantity 
                branch_transfer.over_less_description = description
                branch_transfer.action_by = request.user
                branch_transfer.over_less = False
                
                transfer.defective_status = True
                
                transfer.save()
                branch_transfer.save()
                product.save()
                
                activity_log('write off', product, branch_transfer )
                
                messages.success(request, f'{product.product.name} write-off successfull')        

                return JsonResponse({'success':True}, status=200)
            
            if action == 'accept':
                product.quantity += branch_transfer.over_less_quantity 
                product.save()
                description='returned back'
                activity_log('stock in', product, branch_transfer )
                
                branch_transfer.over_less = False
                branch_transfer.over_less_description = description
                branch_transfer.save()
                
                messages.success(request, f'{product.product.name} accepted back successfully') 

                return JsonResponse({'success':True}, status=200)
            
            if action == 'back':
                description=f'transfered to {branch_transfer.to_branch}'
                product.quantity += branch_transfer.over_less_quantity 
                product.save()
                
                activity_log('stock in', product, branch_transfer )
                
                branch_transfer.received = False
                branch_transfer.quantity = branch_transfer.over_less_quantity
                branch_transfer.save()
                
                product.quantity -= branch_transfer.over_less_quantity 
                product.save()
            
                activity_log('transfer', product, branch_transfer )
                
                branch_transfer.over_less = False
                branch_transfer.over_less_description = description
                branch_transfer.save()
                 
                return JsonResponse({'success':True}, status=200)
            
            return JsonResponse({'success':False, 'messsage':'Invalid form'}, status=400)
            
        return JsonResponse({'success':False, 'messsage':'Invalid form'}, status=400)
                  
    return render(request, 'over_less_transfers.html', {'over_less_transfers':transfers, 'form':form})

@login_required
@transaction.atomic
def defective_product_list(request):
    form = RestockForm()
    defective_products = DefectiveProduct.objects.filter(branch=request.user.branch)
    
    # loss calculation
    if request.method == 'POST':
        data = json.loads(request.body)
        
        defective_id = data['product_id']
        quantity = data['quantity']
        
        try:
            d_product = DefectiveProduct.objects.get(id=defective_id, branch=request.user.branch)
            product = Inventory.objects.get(product__id=d_product.product.id, branch=request.user.branch)
        except:
            return JsonResponse({'success': False, 'message':'Product doesnt exists'}, status=400)
    
        product.quantity += quantity
        product.status = True if product.status == False else product.status
        product.save()
        
        d_product.quantity -= quantity
        d_product.save()
        
        ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= 'stock in',
            inventory=product,
            quantity=quantity,
            total_quantity=product.quantity,
            description = 'from defective products'
        )
        return JsonResponse({'success':True}, status=200)
    
    quantity = defective_products.aggregate(Sum('quantity'))['quantity__sum'] or 0
    price = defective_products.aggregate(Sum('product__cost'))['product__cost__sum'] or 0
    
    return render(request, 'defective_products.html', 
        {
            'total_cost': quantity * price,
            'defective_products':defective_products,
            'form':form,
        }
    )
    
@login_required
@transaction.atomic
def create_defective_product(request):
    form = AddDefectiveForm()
    if request.method == 'POST':
        form = AddDefectiveForm(request.POST)

        if form.is_valid():
            branch = request.user.branch
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            
            # validation
            if quantity > product.quantity:
                messages.warning(request, 'Defective quantity cannot more than the products quantity')
                return redirect('inventory:create_defective_product')
            elif quantity == 0:
                messages.warning(request, 'Defective quantity cannot be less than zero')
                return redirect('inventory:create_defective_product')
            
            product.quantity -= quantity
            product.save()
        
            d_obj = form.save(commit=False)
            d_obj.branch = branch
            d_obj.branch_loss = branch
            
            d_obj.save()
            
            ActivityLog.objects.create(
                branch = branch,
                user=request.user,
                action= 'defective',
                inventory=product,
                quantity=quantity,
                total_quantity=product.quantity,
                description = ''
            )
            messages.success(request, 'Product successfuly saved')
            return redirect('inventory:defective_product_list')
        else:
            messages.success(request, 'Invalid form data')
    return render(request, 'add_defective_product.html', {'form':form})
        

@login_required
def add_inventory_transfer(request):
    form = addTransferForm()
    inventory = Inventory.objects.filter(branch=request.user.branch).order_by('-quantity')
    return render(request, 'add_transfer.html', {'fornm':form, 'inventory':inventory})

@login_required
@admin_required
def delete_inventory(request):
    product_id = request.GET.get('product_id', '')
    
    if product_id:
        inv = Inventory.objects.get(id=product_id, branch=request.user.branch)
        inv.status = False
        inv.save()
    
    ActivityLog.objects.create(
            branch = request.user.branch,
            user=request.user,
            action= 'deactivated',
            inventory=inv,
            quantity=inv.quantity,
            total_quantity=inv.quantity
        )
    
    messages.success(request, 'Product successfully deleted')
    return redirect('inventory:inventory')

@login_required
# @admin_required
def add_product_category(request):
    
    if request.method == 'GET': 
        categories = ProductCategory.objects.all().values()
        logger.info(categories)
        return JsonResponse(list(categories), safe=False)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        category_name = data['name']
        
        if ProductCategory.objects.filter(name=category_name).exists():
            return JsonResponse({'success':False, 'message':'Category Exists'})
        
        category = ProductCategory.objects.create(
            name=category_name
        )
        return JsonResponse({'success':True, 'id': category.id, 'name':category.name})        

@login_required
def reorder_list(request):
    reorder_list = ReorderList.objects.filter(branch=request.user.branch)
        
    if request.method == 'GET':
        if 'download' in request.GET:
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={request.user.branch.name} order.xlsx'
            workbook = openpyxl.Workbook()
            worksheet = workbook.active

            row_offset = 0
            
            worksheet['A' + str(row_offset + 1)] = f'Order List'
            worksheet.merge_cells('A' + str(row_offset + 1) + ':D' + str(row_offset + 1))
            cell = worksheet['A' + str(row_offset + 1)]
            cell.alignment = Alignment(horizontal='center')
            cell.font = Font(size=14, bold=True)
            cell.fill = PatternFill(fgColor='AAAAAA', fill_type='solid')

            row_offset += 1 
                
            category_headers = ['Name', 'Quantity']
            for col_num, header_title in enumerate(category_headers, start=1):
                cell = worksheet.cell(row=3, column=col_num)
                cell.value = header_title
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')

            categories = reorder_list.values_list('product__product__category__name', flat=True).distinct()
            for category in categories:
                products_in_category = reorder_list.filter(product__product__category__name=category)
                if products_in_category.exists():
                    worksheet['A' + str(row_offset + 1)] = category
                    cell = worksheet['A' + str(row_offset + 1)]
                    cell.font = Font(color='FFFFFF')
                    cell.fill = PatternFill(fgColor='0066CC', fill_type='solid')
                    worksheet.merge_cells('A' + str(row_offset + 1) + ':D' + str(row_offset + 1))
                    row_offset += 2

                for product in reorder_list:
                    if category == product.product.product.category.name:
                        worksheet.append([product.product.product.name])
                        row_offset += 1

            workbook.save(response)
            return response
        return render(request, 'reorder_list.html', {'form':ReorderSettingsForm()})
        
@login_required
def reorder_list_json(request):
    order_list = ReorderList.objects.filter(branch=request.user.branch).values(
        'id', 
        'product__product__name',  
        'product__quantity',
        'quantity'
    )
    return JsonResponse(list(order_list), safe=False)

@login_required
@transaction.atomic
def clear_reorder_list(request):
    if request.method == 'GET':
        reorders = ReorderList.objects.filter(branch=request.user.branch)
        
        for item in reorders:
            inventory_items = Inventory.objects.filter(id=item.product.id)
            for product in inventory_items:
                product.reorder = False
                product.save()
            
        reorders.delete()
        
        messages.success(request, 'Reoder list success fully cleared')
        return redirect('inventory:reorder_list')

    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data['product_id']
    
        product = ReorderList.objects.get(id=product_id, branch=request.user.branch)
     
        inventory = Inventory.objects.get(id=product.product.id)
    
        product.delete()
        
        inventory.reorder=False
        inventory.save()
        
        return JsonResponse({'success':True}, status=200)
    
        
@login_required
@transaction.atomic
def create_order_list(request):
    if request.method == 'GET':
        products_below_five = Inventory.objects.filter(branch=request.user.branch, quantity__lte = 5).values(
            'id', 
            'product__id', 
            'product__name',
            'product__description',
            'quantity', 
            'reorder',
            'product__category__id',
            'product__category__name'
        )
        return JsonResponse(list(products_below_five), safe=False)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data['id']
        
        product = get_object_or_404(Inventory, id=product_id, branch=request.user.branch)
        ReorderList.objects.create(product=product, branch=request.user.branch)
        
        product.reorder = True
        product.save()
        return JsonResponse({'success': True}, status=201)
    return JsonResponse({'success': False, 'message':'Failed to add the product'}, status=400)
        
    

@login_required
def inventory_pdf(request):
    template_name = 'reports/inventory_pdf.html'
    category = request.GET.get('category', '')

    inventory = get_list_or_404(Inventory, branch=request.user.branch.id, product__category__name=category) if category else get_list_or_404(Inventory, branch=request.user.branch.id)
    title = f'{category} Inventory' if category else 'All Inventory'
    
    totals = calculate_inventory_totals(inventory)
    
    return generate_pdf(
        template_name, {
            'inventory':inventory,
            'title': f'{request.user.branch.name}: {title}',
            'date':datetime.date.today(),
            'total_cost':totals[0],
            'total_price':totals[1],
            'pdf_name':'Inventory'
        }
    )

@login_required
def transfers_report(request):
    
    template_name = 'reports/transfers.html'

    view = request.GET.get('view', '')
    choice = request.GET.get('type', '') 
    time_frame = request.GET.get('timeFrame', '')
    branch_id = request.GET.get('branch', '')
    product_id = request.GET.get('product', '')
    transfer_id = request.GET.get('transfer_id', '')
    
    transfers = TransferItems.objects.filter().order_by('-date') 
    
    today = datetime.date.today()
    
    if choice in ['All', '', 'Over/Less']:
        transfers = transfers
    
    if product_id:
        transfers = transfers.filter(product__id=product_id)
    if branch_id:
        transfers = transfers.filter(to_branch_id=branch_id)
    
    def filter_by_date_range(start_date, end_date):
        return transfers.filter(date__range=[start_date, end_date])
    
    date_filters = {
        'All': lambda: transfers, 
        'today': lambda: filter_by_date_range(today, today),
        'yesterday': lambda: filter_by_date_range(today - timedelta(days=1), today - timedelta(days=1)),
        'this week': lambda: filter_by_date_range(today - timedelta(days=today.weekday()), today),
        'this month': lambda: transfers.filter(date__month=today.month, issue_date__year=today.year),
        'this year': lambda: transfers.filter(date__year=today.year),
    }
    
    
    if time_frame in date_filters:
        transfers = date_filters[time_frame]()
         
    if view:
        return JsonResponse(list(transfers.values(
                'date',
                'product__name', 
                'price',
                'quantity', 
                'from_branch__name',
                'from_branch__id',
                'to_branch__id',
                'to_branch__name',
                'received_by__username',
                'date_received',
                'description',
                'received',
                'declined'
            )), 
            safe=False
        )
    
    if transfer_id:
        
        return JsonResponse(list(transfers.filter(id=transfer_id).values(
                'date',
                'product__name', 
                'price',
                'quantity', 
                'from_branch__name',
                'from_branch__id',
                'to_branch__id',
                'to_branch__name',
                'received_by__username',
                'date_received',
                'description',
                'received',
                'declined'
            )), 
            safe=False
        )
    
    return generate_pdf(
        template_name,
        {
            'title': 'Transfers', 
            'date_range': time_frame if time_frame else 'All',
            'report_date': datetime.date.today(),
            'transfers':transfers
        },
    )


@login_required
def reorder_from_notifications(request):
    if request.method == 'GET':
        notifications = StockNotifications.objects.filter(inventory__branch=request.user.branch, inventory__reorder=False, inventory__alert_notification=False).values(
            'quantity',
            'inventory__product__name', 
            'inventory__id', 
            'inventory__quantity' 
        )
        return JsonResponse(list(notifications), safe=False)
    
    if request.method == 'POST':
        # payload
        """
            inventory_id
        """
        
        data = json.loads(request.body)
        
        inventory_id = data['inventory_id']
        action_type = data['action_type']
        
        try:
            inventory = Inventory.objects.get(id=inventory_id)
            stock_notis = StockNotifications.objects.get(inventory=inventory)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
        
        if action_type == 'add':
            inventory.reorder=True
            inventory.save()
            ReorderList.objects.create(
                quantity=0,
                product=inventory, 
                branch=request.user.branch
            )
            
        elif action_type == 'remove':
            inventory.alert_notification=True
            inventory.save()
    
        return JsonResponse({'success':True}, status=200)
    
    return JsonResponse({'success':False, 'message': 'Invalid request'}, status=400)

@login_required
def add_reorder_quantity(request):
    """
    Handles adding a quantity to a reorder item.

    Payload:
    - reorder_id: ID of the reorder item
    - quantity: Quantity to add
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

    reorder_id = data.get('reorder_id')
    reorder_quantity = data.get('quantity')

    if not reorder_id:
        return JsonResponse({'success': False, 'message': 'Reorder ID is required'}, status=400)

    if not reorder_quantity:
        return JsonResponse({'success': False, 'message': 'Reorder quantity is required'}, status=400)

    try:
        reorder_quantity = int(reorder_quantity)
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid reorder quantity'}, status=400)

    try:
        reorder = ReorderList.objects.get(id=reorder_id)
        reorder.quantity = reorder_quantity
        reorder.save()
        logger.info(reorder.quantity)
        return JsonResponse({'success': True, 'message': 'Reorder quantity updated successfully'}, status=200)
    except ReorderList.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Reorder item not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({'success': False, 'message': 'An error occurred'}, status=500)


@login_required
def purchase_orders(request):
    form = CreateOrderForm()
    status_form = PurchaseOrderStatus()
    orders = PurchaseOrder.objects.filter(branch = request.user.branch).order_by('-order_date')

    items = PurchaseOrderItem.objects.filter(purchase_order__id=5)

    # Update the 'received' field for each item
    for item in items:
        item.expected_profit
        item.received_quantity
        item.save()
        

    # Perform a bulk update on the 'received' field
    PurchaseOrderItem.objects.bulk_update(items, ['expected_profit', 'received_quantity'])
   
    return render(request, 'purchase_orders.html', 
        {
            'form':form,
            'orders':orders,
            'status_form':status_form 
        }
    )


@login_required
def create_purchase_order(request):
    if request.method == 'GET':
        supplier_form = AddSupplierForm()
        product_form = AddProductForm()
        suppliers = Supplier.objects.all()
        note_form = noteStatusForm()
        batch_form = BatchForm()
        products = Inventory.objects.filter(branch=request.user.branch, status=True, disable=False).order_by('name')

        batch_codes = BatchCode.objects.all()
        return render(request, 'create_purchase_order.html',
            {
                'product_form':product_form,
                'supplier_form':supplier_form,
                'suppliers':suppliers,
                'note_form':note_form,
                'batch_form':batch_form,
                'batch_codes':batch_codes,
                'products':products
            }
        )
     
    if request.method == 'POST':
        try:
            data = json.loads(request.body) 
            purchase_order_data = data.get('purchase_order', {})
            purchase_order_items_data = data.get('po_items', [])
            expenses = data.get('expenses', [])
            cost_allocations = data.get('cost_allocations', [])
            hold = data.get('hold', False)
            supplier_payment_data = data.get('supplier_data')

            unique_expenses = []

            seen = set()
            for expense in expenses:
                expense_tuple = (expense['name'], expense['amount'])
                if expense_tuple not in seen:
                    seen.add(expense_tuple)
                    unique_expenses.append(expense)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

        # Extract data from purchase_order_data
        batch = purchase_order_data['batch']
        delivery_date = purchase_order_data['delivery_date']
        status = purchase_order_data['status']
        notes = purchase_order_data['notes']
        total_cost = Decimal(purchase_order_data['total_cost'])
        discount = Decimal(purchase_order_data['discount'])
        tax_amount = Decimal(purchase_order_data['tax_amount'])
        other_amount = Decimal(purchase_order_data['other_amount'])
        payment_method = purchase_order_data.get('payment_method')

        if not all([batch, delivery_date, status, total_cost, payment_method]):
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

        try:
            with transaction.atomic():
                purchase_order = PurchaseOrder(
                    order_number=PurchaseOrder.generate_order_number(),
                    batch=batch,
                    delivery_date=delivery_date,
                    status=status,
                    notes=notes,
                    total_cost=total_cost,
                    discount=discount,
                    tax_amount=tax_amount,
                    other_amount=other_amount,
                    branch=request.user.branch,
                    is_partial=False,
                    received=False,
                    hold=hold
                )
                purchase_order.save()

                purchase_order_items_bulk = []
                for item_data in purchase_order_items_data:
                    product_id = item_data['product_id']
                    product_name = item_data['product']
                    quantity = int(item_data['quantity'])
                    unit_cost = Decimal(item_data['price'])
                    actual_unit_cost = Decimal(item_data['actualPrice'])
                    supplier_id = item_data.get('supplier', [])

                    logger.info(f'Supplier id {{ supplier_id }}')

                    if not all([product_name, quantity, unit_cost, product_id]):
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'message': 'Missing fields in item data'}, status=400)

                    try:
                        product = Inventory.objects.get(id=product_id, branch=request.user.branch)
                    except Inventory.DoesNotExist:
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'message': f'Product with Name {product_name} not found'}, status=404)

                    supplier = Supplier.objects.get(id=supplier_id)

                    po_item = PurchaseOrderItem.objects.create(
                        purchase_order=purchase_order,
                        product=product,
                        quantity=quantity,
                        unit_cost=unit_cost,
                        actual_unit_cost=actual_unit_cost,
                        received_quantity=0,
                        received=False,
                        supplier = supplier,
                        price=0,
                        wholesale_price=0
                    )
                    product.suppliers.add(po_item.supplier.id)
                    product.batch += f'{batch}, '
                    product.price = 0
                    product.save()

                # Handle expenses
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

                # Cost allocations
                costs_list = []
                for cost in cost_allocations:
                    costs_list.append(
                        costAllocationPurchaseOrder(
                            purchase_order=purchase_order,
                            allocated=cost['allocated'],
                            allocationRate=cost['allocationRate'],
                            expense_cost=cost['expCost'],
                            price=cost['price'],
                            quantity=float(cost['price']),
                            product=cost['product'],
                            total=cost['total'],
                            total_buying=cost['totalBuying']
                        )
                    )
                costAllocationPurchaseOrder.objects.bulk_create(costs_list)

                # # Process finance updates
                # if not purchase_order.hold:
                #     if purchase_order.status.lower() == 'received':
                #         # if_purchase_order_is_received(
                #         #     request, 
                #         #     purchase_order, 
                #         #     tax_amount, 
                #         #     payment_method
                #         # ) 
                #         #
                #         # supplier_payments(purchase_order, supplier_payment_data, request)
                          
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        return JsonResponse({'success': True, 'message': 'Purchase order created successfully'})

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
                logger.info(f'actual product cost {item.actual_unit_cost}')
                logger.info(f'actual product cost {item.price}')
                logger.info(f'dummy {item.unit_cost}')
                inventory_updates.append(
                    Inventory(
                        id=item.product.id,
                        quantity=item.product.quantity + item.received_quantity,
                        price=item.price,
                        dealer_price=item.wholesale_price,
                        cost=item.actual_unit_cost
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

    products = Inventory.objects.filter(branch=request.user.branch).values(
        'dealer_price', 
        'price', 
        'product__name'
    )

    # Convert products queryset to a dictionary for easy lookup by product ID
    product_prices = {product['product__name']: product for product in products}

    for item in items:
        product_name = item.product  
        product_data = product_prices.get(product_name)

        if product_data:
            item.dealer_price = product_data['dealer_price']
            item.selling_price = product_data['price']
        else:
            item.dealer_price = 0  
            item.selling_price = 0 

    if request.GET.get('download') == 'csv':
        return generate_csv_response(items, purchase_order_items)

    return render(request, 'purchase_order_detail.html', {
        'items': items,
        'expenses': expenses,
        'order_items': purchase_order_items,  
        'total_quantity': total_quantity,
        'total_received_quantity': total_received_quantity,
        'total_expected_profit': total_expected_profit,
        'total_expenses': total_expense_sum,
        'purchase_order': purchase_order,
        'total_expected_dealer_profit':total_expected_dealer_profit
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
    except PurchaseOrder.DoesNotExist:
        messages.warning(request, f'Purchase order with ID: {order_id} does not exist')
        return redirect('inventory:purchase_orders')

    items = costAllocationPurchaseOrder.objects.filter(purchase_order=purchase_order)
    purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order=purchase_order)

    products = Inventory.objects.filter(branch=request.user.branch).values(
        'dealer_price', 
        'price', 
        'product__name',
        'product__description',
        'quantity'
    )

    # Convert products queryset to a dictionary for easy lookup by product ID
    product_prices = {product['product__name']: product for product in products}
   
    for item in items:
        product_name = item.product
        logger.info(product_name)
        product_data = product_prices.get(product_name)
        description = ''

        if product_data:
            description = item.description = product_data['product__description'] 

        if product_data:
            item.dealer_price = product_data['dealer_price']
            item.selling_price = product_data['price']
            item.description = description
        else:
            item.dealer_price = 0
            item.selling_price = 0
            item.description = description
            
    context = {'items': items}

    template = get_template('pdf_templates/price_list.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="price_list.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=400)
    return response

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
        'name'
    )
    logger.info(f'branch: {request.user.branch}')
    # Convert products queryset to a dictionary for easy lookup by product ID
    product_prices = {product['name']: product for product in products}

    new_po_items =  []
    for item in purchase_order_items:
        if(item.product):
            product_name = item.product.name  
            product_data = product_prices.get(product_name)
            logger.info(product_name)
            if product_data:
                item.dealer_price = product_data['dealer_price']
                item.selling_price = product_data['price']
            else:
                item.dealer_price = 0  
                item.selling_price = 0 
            new_po_items.append(item)

    logger.info(f'Purchase order items: {new_po_items}')
    
    return render(request, 'receive_order.html', 
        {
            'orders':purchase_order_items,
            'purchase_order':purchase_order
        }
    )

@login_required
@transaction.atomic
def process_received_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            edit = data.get('edit')
            order_item_id = data.get('id')
            quantity = data.get('quantity', 0)
            wholesale_price = data.get('wholesale_price', 0)
            selling_price = data.get('selling_price', 0)
            dealer_price = data.get('dealer_price', 0)
            expected_profit = data.get('expected_profit', 0)
            dealer_expected_profit = data.get('dealer_expected_profit', 0)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload'}, status=400)

        if edit:
            return edit_purchase_order_item(
                order_item_id, 
                selling_price, 
                dealer_price, 
                expected_profit, 
                dealer_expected_profit, 
                quantity, 
                request
            )

        if quantity == 0:
            return JsonResponse({'success': False, 'message': 'Quantity cannot be zero.'}, status=400)

        try:
            order_item = PurchaseOrderItem.objects.get(id=order_item_id)
            order = PurchaseOrder.objects.get(id=order_item.purchase_order.id)
        except PurchaseOrderItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': f'Purchase Order Item with ID: {order_item_id} does not exist'}, status=404)

        # Update the order item with received quantity
        order_item.receive_items(quantity)
        order_item.received_quantity = quantity
        order_item.expected_profit = expected_profit
        order_item.dealer_expected_profit = dealer_expected_profit
        order_item.received = True
        order_item.wholesale_price = wholesale_price
        order_item.price = selling_price

        order_item.save()

        # order_item.check_received()

        return JsonResponse({'success': True, 'message': 'Inventory updated successfully'}, status=200)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def edit_purchase_order_item(order_item_id, selling_price, dealer_price, expected_profit, dealer_expected_profit, quantity, request):
    try:
        po_item = PurchaseOrderItem.objects.get(id=order_item_id)

        po_item.price = selling_price
        po_item.wholesale_price = dealer_price
        po_item.expected_profit = expected_profit
        po_item.dealer_expected_profit = dealer_expected_profit
        po_item.received_quantity = quantity
        po_item.save()

        logger.info('done')
        return JsonResponse({'success': True, 'message': 'Purchase Order Item updated successfully'}, status=200)
    
    except PurchaseOrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Purchase Order Item not found'}, status=404)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)


@login_required
def mark_purchase_order_done(request, po_id):
    purchase_order = PurchaseOrder.objects.get(id=po_id)
    purchase_order.received = True
    purchase_order.save()

    messages.info(request, 'Purchase order done')
    return redirect('inventory:purchase_orders')

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
            'batch_codes':batch_codes

         })
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            purchase_order_data = data.get('purchase_order', {})
            purchase_order_items_data = data.get('po_items', [])
            expenses = data.get('expenses', [])
            cost_allocations = data.get('cost_allocations', [])

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
    
        if not all([delivery_date, status, total_cost, payment_method]):
            return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)

        try:
            with transaction.atomic():
                purchase_order = PurchaseOrder(
                    batch = batch,
                    order_number=PurchaseOrder.generate_order_number(),
                    delivery_date=delivery_date,
                    status=status,
                    notes=notes,
                    total_cost=total_cost,
                    discount=discount,
                    tax_amount=tax_amount,
                    other_amount=other_amount,
                    branch = request.user.branch,
                    is_partial = False,
                    received = False
                )
                purchase_order.save()
                
                purchase_order_items_bulk = []

                # preload the logs with previous received stock
                logs = ActivityLog.objects.filter(purchase_order=last_purchase_order)
                logger.info(f'logs {purchase_order_items_data}')
                logger.info(f'cist {cost_allocations}')

                for item_data in purchase_order_items_data:
                    product_id = item_data['product_id']
                    product_name = item_data['product']
                    quantity = int(item_data['quantity'])
                    unit_cost = Decimal(item_data['price'])
                    actual_unit_cost = Decimal(item_data['actualPrice'])
                    supplier_id = item_data.get('supplier', [])

                    logger.info(f'quantity: {quantity}')

                    if not all([product_name, quantity, unit_cost]):
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'message': 'Missing fields in item data'}, status=400)

                    try:
                        product = Inventory.objects.get(id=product_id, branch=request.user.branch)
                    except Inventory.DoesNotExist:
                        transaction.set_rollback(True)
                        return JsonResponse({'success': False, 'message': f'Product with Name {product_name} not found'}, status=404)

                    supplier = Supplier.objects.get(id=supplier_id)

                    # get the log with the quantity received for replacing po_item quantity 
                    log_quantity = logs.filter(inventory = product).values('quantity')
                    logger.info(log_quantity)
                    purchase_order_items_bulk.append(
                        PurchaseOrderItem(
                            purchase_order=purchase_order,
                            product=product,
                            quantity= 0 if not quantity else quantity,
                            unit_cost=unit_cost,
                            actual_unit_cost=actual_unit_cost,
                            received_quantity= 0 if not log_quantity else log_quantity[0]['quantity'],
                            received=False,
                            supplier = supplier
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
                    #logger.info(f'editted quantity: {cost['quantity']}
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
                    
                # update finance accounts (vat, cashbook, expense, account_transaction_log)
                if purchase_order.status in ['Received', 'received']:
                    if_purchase_order_is_received(
                        request, 
                        purchase_order, 
                        tax_amount, 
                        payment_method
                    )
                
                remove_purchase_order(po_id, request)
                
        except Exception as e:
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

            # Remove PurchaseOrderItems
            PurchaseOrderItem.objects.filter(purchase_order=purchase_order).delete()

            # Finally, delete the purchase order itself
            purchase_order.delete()
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

#testing delete
@login_required
def supplier_delete(request, supplier_id):
    '''
        name,contact_person,email,product,address
    '''
    if request.method == 'GET':
        supplier = Supplier.objects.filter(id=supplier_id).values()
        logger.info(supplier)
        return JsonResponse({'success':True, 'data':list(supplier)})
         

    if request.method == "DELETE":
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            supplier.delete = True
            supplier.save()

            return JsonResponse({'success':True}, status = 200)
        except Exception as e:
            logger.info(e)
            return JsonResponse({"success":False, "message":f"{e}"})
    return JsonResponse({"success":False, "message":"Invalid Request"})


#testing edit view
@login_required
def supplier_edit(request, supplier_id):
    if request.method == 'GET':
        supplier = Supplier.objects.filter(id=supplier_id).values()
        logger.info(supplier)
        return JsonResponse({'success':True, 'data':list(supplier)})
         
    if request.method == "POST":
         
        try:
            data = json.loads(request.body)
            logger.info(data)

            name = data.get('name')
            contact_person = data.get('contact_person')
            email = data.get('email')
            address = data.get('address')
            phone = data.get('phone')

            supplier = Supplier.objects.get(phone=phone)

            supplier.name=name
            supplier.contact_person=contact_person
            supplier.email=email
            supplier.phone=phone
            supplier.address=address
            
            supplier.save()
            logger.info(f'{supplier} saved')

            return JsonResponse({'success':True}, status = 200)
        except Exception as e:
            logger.info(e)
            return JsonResponse({"success":False, "message":f"{e}"})
    return JsonResponse({"success":False, "message":"Invalid Request"})

#payments
def supplier_payments(po, payment_data):
    #add payment
    data = PurchaseOrderItem.objects.filter(purchase_order=po).values('id', 'quantity', 'unit_cost', 'purchase_order__id', 'product__name', 'supplier_id')
    list_entries= []
    for item in data:
        item_id = item['id']
        quantity = item['quantity']
        unit_cost = item['unit_cost']

        for items in list_entries:
            t_amount = 0
            if items['id'] == item_id:
                amount = quantity * unit_cost
                t_amount = items['amount'] + amount
                items['amount'] =  t_amount
            else:
                amount = quantity * unit_cost
                items.append({'id': item_id, 'amount': amount})

    
        """
            [list_entries we have supplier id and total amount of goods he/she provided]
            [payment data supplier id, amount paid to the supplier, currency, payment method]   
            1. we want to create a payment for each supplier
            2. we want calculate the balance for each supplier and update the balance
            3. if the account the supplier doesnt exist we need to create it
        """

        for payment_info in payment_data:
            currency = Currency.objects.get(id=payment_info['currency'])
            supplier = Supplier.objects.get(id=payment_info['id'])

            account, _ = SupplierAccount.objects.get_or_create(
                supplier = supplier,
                defaults={
                    'currency':currency,
                    'balance':0
                }
            )

            SupplierAccountsPayments.objets.create(
                account=account,
                currency=currency,
                amount=payment_info['amount'],
                payment_method=payment_info['payment_method']
            ) 

            calucalateSupplierBalance(account, currency, payment_info['amount'])


        def calucalateSupplierBalance(account, currency, paid_amount):
            for supplier in list_entries:
                if account.supplier.id == supplier:
                    use_account = SupplierAccount.objets.get(currency=currency, account=account)
                    use_account.balance = supplier['amount'] - paid_amount
                

#Payment history
@login_required
def PaymentHistory(request, supplier_id):
    """
        order name
        purchase order amount
    """
    if request.method == 'GET':
        supplier_history = SupplierAccountsPayments.objects.filter(account__supplier_id = supplier_id).\
        values(
            'timestamp', 
            'amount',
            'account__balance',
            'user__username',
            'currency__name'
        )
        supplier_purchase_order_details = PurchaseOrderItem.objects.filter(supplier__id = supplier_id)
        list_details = {}
        for items in supplier_purchase_order_details:
            if items.purchase_order.order_number == list_details.get('order_number'):
                list_details['amount'] = items.quantity * items.unit_cost
            else:
                list_details['order_number'] = items.purchase_order.order_number
                list_details['amount']= items.quantity * items.unit_cost
        logger.info(list_details)
        logger.info(list(supplier_history))
        return JsonResponse({'success':True, 'history':list(supplier_history), 'pOrder': list_details}, status=200)
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=500)


#individual supplier details
@login_required
def supplier_details_view(request,supplierId):
    if request.method == 'GET':
        try:
            supplier_details = Supplier.objects.get(id = supplierId)
            supplier_data = {
                'name': supplier_details.name,
                'contact_person': supplier_details.contact_person,
                'phone': supplier_details.phone,
                'email': supplier_details.email,
                'address': supplier_details.address 
            }

            logger.info(supplier_data)
            return JsonResponse({'success': True, 'data': supplier_data}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    return JsonResponse({'success': False, 'response': 'invalid request'}, status = 500)

#life time details
@login_required
def view_LifeTimeOrders(request, supplier_id):
    #count of orders
    # total cost of all orders
    if request.method == 'GET':
        purchaseOrderDetails = PurchaseOrderItem.objects.get(supplier__id = supplier_id).values(
            'purchase_order__order_number', 'unit_cost', 'quantity'
        )
        list_entries = [{'id': supplier_id, 'number of orders': 0, 'total cost': 0}]
        count = 0
        for items in purchaseOrderDetails:
            if items['id'] == list_entries['id']:
                count += 1
                amount = (items['unit cost'] * items['quantity']) + list_entries['total cost']
                list_entries['total cost'] = amount
                list_entries['number of orders'] = count        
        return JsonResponse({'success': True, 'Data': list_entries}, status = 200)
    return JsonResponse({'success': True,  'response': 'invalid request'}, status = 500)

@login_required
def supplier_view(request):
    if request.method == 'GET':
        supplier_products = Product.objects.all()
        supplier_balances = SupplierAccount.objects.all().values('supplier__id', 'balance', 'date')
        purchase_orders = PurchaseOrderItem.objects.all()
        # try:
        # list_orders = {}
        # supplier = {}
        # for item in purchase_orders:
        #     po = PurchaseOrder.objects.get(id=item.purchase_order.id)
        #     received_quantity = item.received_quantity
        #     unit_cost = item.unit_cost
        #     if item.supplier:
        #         logger.info(f'supplier: {item.supplier}')
        #         if list_orders:
        #             if list_orders.get(item.supplier):
        #                 supplier = list_orders.get(item.supplier)
        #                 logger.info(f'supplier object: {supplier}')

        #                 if supplier['purchase_order'] == po:
        #                     logger.info('existing ')
        #                     supplier['count'] = supplier['count']
        #                     logger.info(f'{supplier}:{supplier['count']}')
        #                 else:
        #                     logger.info('new')
        #                     supplier['count'] += 1
        #                     logger.info(f'supplier {supplier}')
        #                     logger.info('count')
        #                     logger.info(f'{supplier}:{supplier['count']}')
        #                     supplier['amount'] += (unit_cost * received_quantity)
        #                     logger.info(f'Amount {supplier}:{supplier['amount']}')
        #                     supplier['quantity'] += item.quantity
        #                     supplier['quantity_received'] += item.received_quantity
        #                     supplier['returned'] = supplier['returned'] + (item.quantity - item.received_quantity)
                    
        #         else:
        #             account_info = SupplierAccount.objects.filter()
        #             for supplier in account_info:
        #                 for item in purchase_orders:
        #                     if supplier.id == item.supplier.id:
        #                         list_orders[item.supplier] = {
        #                             'supplier_id': item.supplier.id,
        #                             'amount': item.unit_cost * item.received_quantity,
        #                             'purchase_order': po,
        #                             'category': item.product.category.name,
        #                             'quantity': item.quantity,
        #                             'quantity_received': item.received_quantity,
        #                             'returned': item.quantity - item.received_quantity,
        #                             'date': supplier.date,
        #                             'balance': supplier.balance,
        #                             'count': 1
        #                         }                       
        # logger.info([list_orders])
        # # logger.info(f'supplier: {.values()}')

        # for prod in supplier_products.values('name','suppliers'):
        #     logger.info(f'suppliers: {prod}')

        list_orders = {}

        for items in purchase_orders:
            if list_orders.get(items.supplier.id):
                
                supplier = list_orders.get(items.supplier.id)
                logger.info(f'quantity: {supplier}')
                supplier['quantity'] += items.quantity
                supplier['received_quantity'] += items.received_quantity
                supplier['returned'] += (items.quantity - items.received_quantity)
                supplier['amount'] += (items.unit_cost * items.received_quantity)

                if items.purchase_order.id == supplier['order_id']:
                    supplier['count'] = supplier['count']
                else:
                    supplier['count'] += 1
                    supplier['order_id'] = items.purchase_order.id
            else:
                list_orders[items.supplier.id] = {
                    'order_id': items.purchase_order.id,
                    'quantity' : items.quantity,
                    'received_quantity' : items.received_quantity,
                    'returned' : (items.quantity - items.received_quantity),
                    'amount' : (items.unit_cost * items.received_quantity),
                    'count' : 1
                }
                

        logger.info([list_orders])
        logger.info(supplier_balances)
        form = AddSupplierForm()
        suppliers = Supplier.objects.filter(delete = False)
        logger.info(suppliers)
        return render(request, 'Supplier/Suppliers.html', {
            'form':form,
            'products':supplier_products,
            'balances':supplier_balances,
            'life_time': [list_orders],
            'suppliers':suppliers
        })
        # except Exception as e:
        #     # logger.info(e)
        #     messages.error(request, f'{e}')
        #     return redirect('inventory:suppliers')
            
    if request.method == 'POST':
        """
        payload = {
            name,
            contact_person,
            email,
            product,
            address
        }
        """
        try:
            data = json.loads(request.body)
            logger.info(data)

            name = data.get('name')
            contact_person = data.get('contact_person')
            email = data.get('email')
            phone = data.get('phone')
            address = data.get('address')

            logger.info(name)
            
            # check if all data exists
            if not name or not contact_person or not email or not phone or not address:
                return JsonResponse({'success': False, 'message':'Fill in all the form data'}, status=400)

            # check is supplier exists
            if Supplier.objects.filter(email=email).exists() and Supplier.objects.filter(delete = True).exists():
                bring_back =  Supplier.objects.filter(email = email)
                bring_back.delete = False
                bring_back.update()
                logger.info(bring_back.delete)
                return JsonResponse({'success': True, 'response':f'Supplier{name} brought back'}, status=200)
            elif Supplier.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'response':f'Supplier{name} already exists'}, status=400)
           
            with transaction.atomic():
                if not Currency.objects.filter(name = 'USD').exists() and not Currency.objects.filter(name = 'ZIG').exists():
                    Currency.objects.create(
                        code = '001',
                        name = 'USD',
                        symbol = '$',
                        exchange_rate = 1,
                        default = True
                    )
                    Currency.objects.create(
                        code = '002',
                        name = 'ZIG',
                        symbol = 'Z',
                        exchange_rate = 26.78,
                        default =  False
                    )

                supplier = Supplier.objects.create(
                    name = name,
                    contact_person = contact_person,
                    email = email,
                    phone = phone,
                    address = address,
                    delete = False
                )
                SupplierAccount.objects.create(
                    supplier = supplier,
                    currency = Currency.objects.get(default = True),
                    balance = 0,
                )
                SupplierAccount.objects.create(
                    supplier = supplier,
                    currency = Currency.objects.get(default = False),
                    balance = 0,
                )
            return JsonResponse({'success': True}, status=200)
        except Exception as e:
            logger.info(e)
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False, 'message':'Invalid request'}, status=200)


@login_required
def supplier_list_json(request):
    suppliers = Supplier.objects.all().values(
        'id',
        'name'
    )
    return JsonResponse(list(suppliers), safe=False)

@login_required
def supplier_account(request, supplier_id):
    try:
        supplier_account = SupplierAccount.objects.get(id=supplier_id)
        return render(request, 'suppliers/supplier_account.html')
    except Exception as e:
        messages.warning(request, 'Supplier account doesnt exists')
        return redirect('inventory:suppliers')


@login_required
def supplier_prices(request, product_id):
    """
        {
            product_id: id
        }
    """
    try:
        best_three_prices = best_price(product_id)
        logger.info(best_three_prices)
        return JsonResponse({'success': True, 'suppliers': best_three_prices})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

#product   
@login_required
def product(request):
    if request.method == 'POST':
        # payload
        """
            id,
            name,
            cost: float,
            quantity: int,
            category,
            tax_type,
            min_stock_level,
            description
        """
        try:
            data = json.loads(request.body)
            product_id = data.get('id', '')
            logger.info(product_id)
            
        except Exception as e:
            return JsonResponse({'success':False, 'message':'Invalid data'})

        image_data = data.get('image')
        if image_data:
            try:
                format, imgstr = image_data.split(';base64,') 
                ext = format.split('/')[-1]
                image = ContentFile(base64.b64decode(imgstr), name=f'{data['name']}.{ext}')
            except Exception as e:
                logger.error(f'Error decoding image: {e}')
                return JsonResponse({'success': False, 'message': 'Invalid image data'})

        try:
            category = ProductCategory.objects.get(id=data['category'])
        except ProductCategory.DoesNotExist:
            return JsonResponse({'success':False, 'message':f'Category Doesnt Exists'})
        
        if product_id:
            """editing the product"""
            logger.info(f'Editing product ')
            product = Inventory.objects.get(id=product_id, branch=request.user.branch)
            product.name = data['name']
            product.price = data.get('price', 0)
            product.cost = data.get('cost', 0)    
            product.quantity = data.get('quantity', 0)  
            product.category = category  
            product.tax_type = data['tax_type']
            product.stock_level_threshold = data['min_stock_level']
            product.description = data['description']
            product.end_of_day = True if data.get('end_of_day') else False
            product.service = True if data.get('service') else False
            product.image=product.image
            product.batch = product.batch
        else:
            """creating a new product"""
            
            # validation for existance
            if Inventory.objects.filter(name=data['name']).exists():
                return JsonResponse({'success':False, 'message':f'Product {data['name']} exists'})
            logger.info(f'Creating ')
            product = Inventory.objects.create(
                batch = '',
                name = data['name'],
                price = 0,
                cost = 0,
                quantity = 0,
                category = category,
                tax_type = data['tax_type'],
                stock_level_threshold = data['min_stock_level'],
                description = data['description'], 
                end_of_day = True if data['end_of_day'] else False,
                service = True if data['service'] else False,
                branch = request.user.branch,
                # image = image,
                status = True
            )
        product.save()
        
        return JsonResponse({'success':True}, status=200)

            
    if request.method == 'GET':
        products = Inventory.objects.filter(branch = request.user.branch, status=True, disable=False).values(
            'id',
            'name',
            'quantity'
        ).order_by('name')  
        logger.info(products)         
        return JsonResponse(list(products), safe=False)
    
    return JsonResponse({'success':False, 'message':'Invalid request'}, status=400)

@login_required
def delete_product(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('id', '')

            product = Inventory.objects.get(id=product_id, branch=request.user.branch)

            logger.info(product)
            if product.quantity > 0:
                product.disable = True
                return JsonResponse({'False': True, 'message': 'Product cannot be deleted it have quantity more than zero.'})
            else:
                product.disable = True
            product.save()

            return JsonResponse({'success': True, 'message': 'Product deleted successfully.'})

        except Inventory.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
        except Exception as e:
            logger.info(e)
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

#reorder settings
@login_required
def reorder_settings(request):
    """ method to set reorder settings"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quantity_suggestion = data.get('suggestion')
            order_enough = data.get('enough')
            supplier = data.get('supplier', 'all')
            days_from = data.get('from')
            days_to = data.get('to')

            if not quantity_suggestion or not order_enough or not supplier:
                return JsonResponse({'success':False, 'message':'Please fill all required data.'})

            settings = reorderSettings.objects.get_or_create(id=1)

            settings.supplier=supplier,
            settings.quantity_suggestion = True if quantity_suggestion else False,
            settings.order_enough_stock = True if order_enough else False
            
            if order_enough:
                # validate days 
                if not days_from or not days_to:
                    return JsonResponse({'success':False, 'message':'Please fill in the days.'})
                settings.number_of_days_from = days_from
                settings.number_of_days_to = days_to
                settings.save()
            
            return JsonResponse({'success':True, 'message':'Reorder Settings Succefully Saved.'}, status=200)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
    
    if request.method == 'GET':
        try:
            settings = reorderSettings.objects.filter(id=1).values()
            JsonResponse({'success':True, 'data':settings}, status=200)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)
        return JsonResponse({'success':False, 'message':'Invalid request'}, status=500)


#stocktake
@login_required
def stock_take(request):
    if request.method == 'GET':
        products = Inventory.objects.filter(branch=request.user.branch)
        return render(request, 'stocktake/stocktake.html',{
            'products':products
        })
    
    if request.method == 'POST':
       """
         payload = {
            product_id:int
            pyhsical_quantity:int
        }
       """
       data = json.loads(request.body)
       prod_id = data.get('product_id')
       phy_quantity = data.get('physical_quantity')

       try:
           """
            1. get the product
            2. get the quantity
            3. condition to check between physical_quantity and quantity of the product
            4. json to the front {id:inventory.id, different:difference}
           """
           
           inventory_details = Inventory.objects.filter(product_id = prod_id).values('product__name', 'quantity','id')

           quantity = inventory_details['quantity']
           inventory_id = inventory_details['id']

           if quantity >= 0:
               descripancy_value =  quantity - phy_quantity
               details_inventory= {'inventory_id': inventory_id, 'difference': descripancy_value}
               return JsonResponse({'success': True, 'data': details_inventory }, status = 200)
           return JsonResponse({'success': False }, status = 400)
           
       except Exception as e:
           return JsonResponse({'success': False, 'response': e}, status = 400)

#supplier payments
@login_required
def payments(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            supplier_id = data.get('id')
            supplier_amount = data.get('amount')
            supplier_currency_used = data.get('currency')
            supplier_method = data.get('payment_method')

            supplier_details = Supplier.objects.get(id = supplier_id)
            supplier_currency = Currency.objects.get(name = supplier_currency_used)
            supplier_payment = SupplierAccountsPayments.objects.filter(account__supplier__id = supplier_id)\
            .values('user', 'timestamp', 'amount', 'account__balance', 'payment_method')

            supplier_balance = supplier_payment['account__balance']
            # supplier_timestamp = supplier_payment['timestamp']
            # supplier_user = supplier_payment['amount']
            #supplier_pay_method = supplier_payment['payment_method']

            if supplier_balance <= 0:
                return JsonResponse({'success': True, 'response': 'We donot owe this supplier'})
            else:
                if supplier_method == 'USD':
                    new_balance = supplier_balance - supplier_amount
                else:
                    exchange_rate = Currency.objects.filter(name = supplier_method)
                    new_balance_zig = (supplier_balance * exchange_rate['exchange_rate'] ) - supplier_amount
                    new_balance = new_balance_zig/exchange_rate['exchange_rate']
            
            with transaction.Atomic():
                supplier_acc = SupplierAccount.objects.update(
                    suppliers = supplier_details,
                    currency = supplier_currency,
                    balance = new_balance,
                )

                SupplierAccountsPayments.objects.create(
                    account = supplier_acc,
                    payment_method = supplier_method,
                    currency = supplier_currency,
                    amount = supplier_amount,
                )
                return JsonResponse({'success': True, 'response': 'Data saved'})
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
# @login_required
def accessory_view(request, product_id):
    if request.method == 'GET':
        accessories = Accessory.objects.filter(product__id=product_id).values('id', 'product__name')
        return JsonResponse({'success': True, 'data': list(accessories)}, status=200)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f'Accessories: {data}')
            accessory_ids = data.get('accessories', [])

            logger.info(accessory_ids)

            product = Inventory.objects.get(id=product_id)
            current_accessories = Accessory.objects.filter(main_product=product).values('accessory_product')
            current_ids = set(current_accessories.values_list('id', flat=True))

            logger.info(f'current ids: {current_ids}')

            input_ids = {acc['id'] for acc in accessory_ids}
            
            accessories_to_add = input_ids - current_ids
            accessories_to_remove = current_ids - input_ids

            logger.info(f'accessories to remove: {accessories_to_remove}')

            if Accessory.objects.filter(main_product=product).exists():
                acc = Accessory.objects.get(main_product=product)
            else:
                acc = Accessory.objects.create(main_product = product)

            if accessories_to_add:
                accessories_to_add_objs = Inventory.objects.filter(id__in=accessories_to_add)

                logger.info(f'Accessories to add: {accessories_to_add_objs}')

                for accessory in accessories_to_add_objs:
                    acc.accessory_product.add(accessory)
                    acc.save()

            if accessories_to_remove:
                accessories_to_remove_objs = Inventory.objects.filter(id__in=accessories_to_remove)

                logger.info(f'Accessories to add: {accessories_to_remove_objs}')

                for accessory in accessories_to_remove_objs:
                    acc.accessory_product.remove(accessory)
                    acc.save()

            updated_accessories = Accessory.objects.filter(main_product=product).values('id', 'main_product__name', 'accessory_product__name')
            return JsonResponse({'success': True, 'data': list(updated_accessories)}, status=200)
        
        except Inventory.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
        except Exception as e:
            logger.info(e)
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

def vue_view(request):
    return render(request, 'vue.html')



    
        