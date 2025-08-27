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
def notifications_json(request):
    notifications = StockNotifications.objects.filter(inventory__branch=request.user.branch).select_related('inventory, inventory__branch').values(
        'inventory__product__name', 'type', 'notification', 'inventory__id'
    )
    return JsonResponse(list(notifications), safe=False)

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
            return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

@login_required
def branches_inventory(request):
    return render(request, 'branches_inventory.html')

@login_required
def branches_inventory_json(request):
    branches_inventory = Inventory.objects.filter(status=True).values(
        'product__name', 'price', 'quantity', 'branch__name'
    ).select_related('compay')
    return JsonResponse(list(branches_inventory), safe=False)


from django.apps import apps



# requires a good name for the view
@login_required
def inventory(request):
    product_id = request.GET.get('id', '')

    if product_id:
        inventory_items = Inventory.objects.filter(
            id=product_id,
            status=True
        ).filter(
            branch=request.user.branch
        ).values()

        if inventory_items:
            return JsonResponse(list(inventory_items), safe=False)
        else:
            return JsonResponse({'error': 'Product not found in allowed branches'}, status=404)

    return JsonResponse({'error': 'Product ID is required'}, status=400)

@login_required
def add_inventory_view(request):
    try:
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        category_name = request.POST.get('category')
        cost = request.POST.get('cost_price')
        price = request.POST.get('selling_price')
        dealer_price = request.POST.get('wholesale_price') or 0
        tax_type = request.POST.get('tax_type')
        min_stock = request.POST.get('min_stock_level')
        description = request.POST.get('description')
        end_of_day = request.POST.get('end_of_day') == 'on'
        service = request.POST.get('service') == 'on'
        image = request.FILES.get('image')

        category, _ = ProductCategory.objects.get_or_create(name=category_name)

        inventory = Inventory.objects.create(
            branch=request.user.branch,
            quantity=quantity,
            name=name,
            cost=cost,
            price=price,
            dealer_price=dealer_price,
            stock_level_threshold=min_stock,
            category=category,
            tax_type=tax_type,
            description=description,
            end_of_day=end_of_day,
            service=service,
            image=image
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Product added successfully!',
            'product': {
                'id': inventory.id,
                'name': inventory.name
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def inventory_index(request):
    form = ServiceForm()
    q = request.GET.get('q', '')
    category = request.GET.get('category', '')

    now = timezone.now()
    today = now.date()

    accessories = Accessory.objects.all()
    inventory = Inventory.objects.filter(
        branch=request.user.branch,
        status=True,
        disable=False,
        category__name=category
    ).select_related(
        'category',
        'branch'
    ).order_by('name')

    logs = ActivityLog.objects.filter(branch=request.user.branch).select_related('branch').order_by('-id')

    grouped_logs = {}
    ordered_grouped_logs = {}

    for log in logs:
        log_date = log.timestamp.date()

        if log_date == today:
            date_key = 'Today'
        elif log_date == today - timedelta(days=1):
            date_key = 'Yesterday'
        else:
            date_key = log_date.strftime('%A, %d %B %Y')

        if not log.invoice:
            if date_key not in grouped_logs:
                grouped_logs[date_key] = {'logs': []}
            grouped_logs[date_key]['logs'].append(log)

    for special_day in ['Today', 'Yesterday']:
        if special_day in grouped_logs:
            ordered_grouped_logs[special_day] = grouped_logs[special_day]

    remaining_dates = sorted(
        [(k, v) for k, v in grouped_logs.items() if k not in ['Today', 'Yesterday']],
        key=lambda x: datetime.datetime.strptime(x[0], '%A, %d %B %Y') if not x[0] in ['Today', 'Yesterday'] else today
    )

    for date_key, data in remaining_dates:
        ordered_grouped_logs[date_key] = data


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

            categories = Inventory.objects.filter(branch=request.user.branch).values_list('category__name', flat=True).distinct()
            for category in categories:
                products_in_category = products.filter(branch__name=branch, category__name=category)
                if products_in_category.exists():
                    worksheet['A' + str(row_offset + 1)] = category
                    cell = worksheet['A' + str(row_offset + 1)]
                    cell.font = Font(color='FFFFFF')
                    cell.fill = PatternFill(fgColor='0066CC', fill_type='solid')
                    worksheet.merge_cells('A' + str(row_offset + 1) + ':D' + str(row_offset + 1))
                    row_offset += 2

                for product in products.filter(branch__name=branch):
                    if product.category:
                        if category == product.category.name:
                            worksheet.append([product.name, product.cost, product.price, product.quantity])
                            row_offset += 1

        workbook.save(response)
        return response

    context = {
        'form': form,
        'total_cost': inventory.aggregate(total_cost=Sum(F('quantity') * F('cost')))['total_cost'] or 0,
        'total_price': inventory.aggregate(total_price=Sum(F('quantity') * F('price')))['total_price'] or 0,
        'search_query': q,
        'category': category,
        'accessories': accessories,
        'grouped_logs':ordered_grouped_logs
    }

    return render(request, 'inventory.html', context)

def logs_page(request):
    page_number = request.GET.get('page', 1)
    logs = ActivityLog.objects.select_related('inventory').order_by('-timestamp')
    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, 'partials/logs_page.html', {
        'logs': page_obj.object_list,
        'has_next': page_obj.has_next(),
        'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None
    })


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
    logger.info(f'debits {total_credits_quantity}')

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
        elif log.action == 'sale return':
            if month_year in transfer_data:
                transfer_data[month_year] += abs(log.quantity)
            else:
                transfer_data[month_year] = abs(log.quantity)

        if month_year not in labels:
            labels.append(month_year)

    """ download a log or stock account pdf """

    # if request.GET.get('logs'):
    #     download_stock_logs_account('logs', logs, inventory)
    # elif request.GET.get('account'):
    #     download_stock_logs_account('account', logs, inventory)

    logger.info(stock_account_data)

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

        if log.action == 'sale return':
            inventory_cost = getattr(log.inventory, 'cost', Decimal('0.00'))
            cost = abs(log.quantity) * inventory_cost

            logger.info(f'action : {log.action}')
            logger.info(f'quantity : {abs(log.quantity)}')
            logger.info(f'inventory cost : {inventory_cost}')
            logger.info(f'cost : {cost}')

            stock_account.append({
                'type': entry_type,
                'description': log.action,
                'quantity': abs(log.quantity),
                'cost': cost,
                # 'currency': 'USD',
                'timestamp': log.timestamp,
                'user': log.user.username if log.user else 'Unknown',
                'branch': log.branch.name,
            })
            logger.info(stock_account)
        else:
            inventory_cost = getattr(log.inventory, 'cost', Decimal('0.00'))
            cost = abs(log.quantity) * inventory_cost

            logger.info(f'action : {log.action}')
            logger.info(f'quantity : {log.quantity}')
            logger.info(f'inventory cost : {inventory_cost}')
            logger.info(f'cost : {cost}')

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
            logger.info(stock_account)
    return stock_account



@login_required
def update_notification_settings(request):
    settings, created = InventoryNotificationSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        settings.low_stock = 'low_stock' in request.POST
        settings.out_of_stock = 'out_of_stock' in request.POST
        settings.movement_create = 'movement_create' in request.POST
        settings.movement_update = 'movement_update' in request.POST
        settings.movement_delete = 'movement_delete' in request.POST
        settings.movement_transfer = 'movement_transfer' in request.POST
        settings.save()
        messages.success(request, "Notification settings updated successfully.")
        return redirect('inventory:settings')

    return render(request, 'inventory/settings.html', {'settings': settings})

@login_required
def settings(request):
    return render(request, 'settings.html')


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
@transaction.atomic
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

            logger.info(f'product ID: {product_id}')

        except Exception as e:
            return JsonResponse({'success':False, 'message':'Invalid data'})

        image_data = data.get('image')

        # if image_data: revisit
        #     try:
        #         format, imgstr = image_data.split(';base64,')
        #         ext = format.split('/')[-1]
        #         image = ContentFile(base64.b64decode(imgstr), name=f'{data['name']}.{ext}')
        #     except Exception as e:
        #         logger.error(f'Error decoding image: {e}')
        #         return JsonResponse({'success': False, 'message': 'Invalid image data'})

        try:
            category = ProductCategory.objects.get(id=data['category'])
        except ProductCategory.DoesNotExist:
            return JsonResponse({'success':False, 'message':f'Category Doesnt Exists'})

        if product_id:
            """editing the product"""
            with transaction.atomic():
                product = Inventory.objects.select_for_update().get(id=product_id, branch=request.user.branch)
                logger.info(f'Editing product: {product.name} ')
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
                product.save()

        else:
            """creating a new product"""

            # validation for existance
            if Inventory.objects.filter(name__exact=data['name'], branch=request.user.branch).exists():
                return JsonResponse({'success':False, 'message':f'Product {data['name']} exists'})

            logger.info(f'Creating product: {data['name']}: {request.user.branch}')

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

        return JsonResponse({'success':True}, status=200)

    if request.method == 'GET': # to be dynamic
        products = Inventory.objects.filter(
            Q(branch=request.user.branch),
            status=True,
            disable=False
        ).values(
            'id',
            'name',
            'quantity'
        ).order_by('name')

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

@login_required
def accessory_view(request, product_id):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            logger.info(f'Accessories: {data}')
            product_id = data.get('product_id')
            accessory_data = data.get('accessories', [])

            logger.info(accessory_data)

            product = Inventory.objects.get(id=product_id)
            logger.info(product)
            current_accessories = Accessory.objects.filter(main_product=product).values('accessory_product', 'quantity')
            current_ids = set(current_accessories.values_list('accessory_product', flat=True))

            logger.info(f'current ids: {current_ids}')

            input_data = {acc['id']: acc['quantity'] for acc in accessory_data}
            input_ids = set(input_data.keys())

            accessories_to_add = input_ids - current_ids
            accessories_to_remove = current_ids - input_ids

            logger.info(f'accessories to remove: {accessories_to_remove}')

            if Accessory.objects.filter(main_product=product).exists():
                acc = Accessory.objects.get(main_product=product)
            else:
                acc = Accessory.objects.create(main_product=product, quantity=0)

            if accessories_to_add:
                accessories_to_add_objs = Inventory.objects.filter(id__in=accessories_to_add)

                logger.info(f'Accessories to add: {accessories_to_add_objs}')

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

                logger.info('done')

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
            logger.info(e)
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

def vue_view(request):
    return render(request, 'vue.html')


@login_required
def get_cart_items(request):
    try:
        items = TemporaryPurchaseOrderItem.objects.filter(
            temporary_purchase_order__user=request.user,
            temporary_purchase_order__branch=request.user.branch
        ).select_related('product', 'supplier')

        items_data = [{
            'id': item.id,
            'product': item.product.name,
            'product_id': item.product.id,
            'supplier': item.supplier.name,
            'quantity': item.quantity,
            'price': float(item.price) if item.price else 0.0
        } for item in items]

        return JsonResponse({
            'success': True,
            'items': items_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)
