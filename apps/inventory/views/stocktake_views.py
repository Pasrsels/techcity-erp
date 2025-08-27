from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, F, ExpressionWrapper, FloatField, Count, Q
from apps.inventory.models import StockTake, StocktakeItem, Inventory, ActivityLog
from apps.finance.models import UserAccount, UserTransaction, Expense, Cashbook, Currency, ExpenseCategory
from django.db import transaction
from loguru import logger
import json
from utils.utils import generate_pdf
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from apps.inventory.forms import StockTakeForm

@login_required
def stock_take_index(request):
    if request.method == 'GET':
        form = StockTakeForm()
        stock_takes = StockTake.objects.filter(branch=request.user.branch)
        stock_take_items = StocktakeItem.objects.filter(stocktake__branch=request.user.branch)

        for stock_take in stock_takes:
            stock_take.annotated_items = StocktakeItem.objects.filter(
                stocktake=stock_take
            ).annotate(
                product_cost=F('product__cost'),
                product_price=F('product__price'),
                total_cost=ExpressionWrapper(F('quantity_difference') * F('product__cost'), output_field=FloatField()),
                total_price=ExpressionWrapper(F('quantity_difference') * F('product__price'), output_field=FloatField())
            )

            negative_items = stock_take.annotated_items.filter(quantity_difference__lt=0)
            positive_items = stock_take.annotated_items.filter(quantity_difference__gt=0)

            stock_take.negative_cost_total = negative_items.aggregate(
                total=Sum('total_cost')
            )['total'] or 0

            stock_take.negative_price_total = negative_items.aggregate(
                total=Sum('total_price')
            )['total'] or 0

            stock_take.positive_cost_total = positive_items.aggregate(
                total=Sum('total_cost')
            )['total'] or 0

            stock_take.positive_price_total = positive_items.aggregate(
                total=Sum('total_price')
            )['total'] or 0

        cost = 0
        for stock_take_item in stock_take_items:

            cost += stock_take_item.quantity_difference * stock_take_item.product.cost

        negative_items = stock_take_items.filter(quantity_difference__lt=0)
        negative = negative_items.aggregate(
            total_qty_diff=Sum('quantity_difference'),
            total_cost=Sum(ExpressionWrapper(F('quantity_difference') * F('product__cost'), output_field=FloatField())),
            total_price=Sum(ExpressionWrapper(F('quantity_difference') * F('product__price'), output_field=FloatField())),
        )

        positive_items = stock_take_items.filter(quantity_difference__gt=0)
        positive = positive_items.aggregate(
            total_qty_diff=Sum('quantity_difference'),
            total_cost=Sum(ExpressionWrapper(F('quantity_difference') * F('product__cost'), output_field=FloatField())),
            total_price=Sum(ExpressionWrapper(F('quantity_difference') * F('product__price'), output_field=FloatField())),
        )

    if request.method == 'POST':
        form = StockTakeForm(request.POST)
        if form.is_valid():
            try:
                stock_take = form.save(commit=False)
                branch = request.user.branch
                stock_take.branch = branch
                stock_take.status = False
                stock_take.s_t_number = StockTake().stocktake_number(branch.name)
                stock_take.result = 0
                stock_take.save()

                form.save_m2m()

                inventory = Inventory.objects.filter(branch=branch, disable=False)
                stocktake_items = [
                    StocktakeItem(
                        stocktake=stock_take,
                        product=product,
                        now_quantity=product.quantity,
                        has_diff=False,
                        accepted=False,
                        company_loss=False,
                        note='',
                        cost=0,
                        recorded=False,
                        quantity=0,
                        quantity_difference=0
                    )
                    for product in inventory
                ]

                StocktakeItem.objects.bulk_create(stocktake_items)

                stock_takes = StockTake.objects.all()
                return render(request, 'stocktake/stocktake.html', {
                    'stocktakes': stock_takes,
                    'form': StockTakeForm(),
                    'success': 'Stock take created successfully!'
                })

            except Exception as e:
                logger.error(f"Error in stock take creation: {e}")
                return render(request, 'stocktake/stocktake.html', {
                    'form': form,
                    'error': str(e),
                    'stocktakes': StockTake.objects.all()
                })

    return render(request, 'stocktake/stocktake.html', {
        'negative': negative,
        'positive': positive,
        'stocktakes': stock_takes,
        'form': form
    })

@login_required
def confirm_stocktake(request, stocktake_id):
    try:
        stocktake = StockTake.objects.get(id=stocktake_id)
        stocktakes = StocktakeItem.objects.filter(stocktake__id=stocktake_id)

        flag = True

        if flag:
            stocktake.status = True
            stocktake.save()
            return JsonResponse({'success':True}, status=200)
        else:
            return JsonResponse({'success':False, 'message':'Please record all stock take items.'}, status=400)
    except Exception as e:
        logger.error(f'Error saving stocktake, {e}')
        return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

@login_required
def stock_take_detail(request, stocktake_id):
    if request.method == 'GET':

        products = StocktakeItem.objects.filter(stocktake__id=stocktake_id)
        stocktake  = StockTake.objects.get(id=stocktake_id)
        return render(request, 'stocktake/stocktake_detail.html', {
            'products':products,
            'stocktake':stocktake
        })

    if request.method == 'POST':

        data = json.loads(request.body)
        id = data.get('inventory_id')

        if id:
            inventory = Inventory.objects.get(id=id, branch=request.user.branch)
            logs = ActivityLog.objects.filter(
                inventory=inventory,
                branch=request.user.branch
            ).select_related(
                'branch', 'inventory'
            ).order_by(
                '-timestamp__date', '-timestamp__time'
            )

            html = render_to_string('stocktake/partials/inventory_detail_partials.html', {
                'inventory': inventory,
                'logs': logs,
            })

            return JsonResponse({'success':True, 'html':html}, status=200)
        return JsonResponse({'success':False, 'message':'Error processing your request.'}, status=400)


def undo_accept_stocktake_item(request):
    try:
        data = json.loads(request.body)
        stocktake_id = data.get('product_id')
        stocktake_item = StocktakeItem.objects.select_related('product').get(id=stocktake_id)
        adjustment_log = ActivityLog.objects.filter(stocktake=stocktake_item.stocktake, inventory=stocktake_item.product).order_by('-id').first()
        product = Inventory.objects.get(id=stocktake_item.product.id)

        with transaction.atomic():
            if adjustment_log:
                if adjustment_log.quantity > 0:
                    product.quantity += abs(adjustment_log.quantity)
                else:
                    product.quantity -= abs(adjustment_log.quantity)
            product.save()

            UserTransaction.objects.filter(description=stocktake_item.note, amount=stocktake_item.cost).delete()

            expense = Expense.objects.filter(
                description=stocktake_item.note,
                amount=stocktake_item.cost,
                user=request.user
            ).first()

            if expense:
                Cashbook.objects.filter(expense=expense).delete()
                expense.delete()

            stocktake_item.cost = 0
            stocktake_item.recorded = False
            stocktake_item.has_diff = False
            stocktake_item.accepted = False
            stocktake_item.note = ''
            stocktake_item.company_loss = False
            stocktake_item.save()

            ActivityLog.objects.create(
                branch=request.user.branch,
                user=request.user,
                stocktake=stocktake_item.stocktake,
                action='Stocktake adjustments',
                inventory=stocktake_item.product,
                quantity= 0,
                total_quantity= stocktake_item.product.quantity,
                description=f'Stock adjustment(undo): #{stocktake_item.stocktake.id}'
            )

            return JsonResponse({'success': True, 'message': 'Undo successful', 'quantity': stocktake_item.now_quantity, 'product_id':stocktake_item.id}, status=200)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def accept_stocktake_item(request):
    try:
        data = json.loads(request.body)
        stocktake_id = data.get('product_id')
        users = data.get('users')
        note = data.get('note')
        company = data.get('company')

        with transaction.atomic():
            stocktake = StocktakeItem.objects.get(id=stocktake_id)

            stocktake.product.quantity += stocktake.quantity_difference
            stocktake.product.save()
            stocktake.cost = stocktake.quantity_difference * stocktake.product.cost
            stocktake.has_diff = True

            stocktake.save()

            stocktake.note = note
            stocktake.accepted = True

            if users:
                user_accounts = UserAccount.objects.all()
                user_accounts_transactons = []
                for user in users:
                    account = user_accounts.filter(user__id=int(user)).first()
                    account = create_user_account(int(user)) if not account else account
                    user_accounts_transactons.append(
                        UserTransaction(
                            account=account,
                            transaction_type='Stock loss',
                            amount = stocktake.cost,
                            description = note,
                            debit = stocktake.cost,
                            credit = 0,
                            received_by = request.user
                        )
                    )
                UserTransaction.objects.bulk_create(user_accounts_transactons)

            if company:
                stocktake.company_loss = True

            stocktake.save()

            credit = False
            debit = False

            if stocktake.quantity_difference < 0:
                credit=True
            else:
                debit=True

            currency=Currency.objects.get(default=True)
            category, _ = ExpenseCategory.objects.get_or_create(name='Stock Loss')

            expense = Expense.objects.create(
                amount = stocktake.cost,
                payment_method = 'cash',
                currency=currency,
                description=stocktake.note,
                user=request.user,
                branch=request.user.branch,
                is_recurring=True,
                category=category
            )

            Cashbook.objects.create(
                expense=expense,
                description=note,
                credit=debit,
                debit=credit,
                branch=request.user.branch,
                created_by=request.user,
                updated_by=request.user,
                currency=currency,
                amount = stocktake.cost,
            )

            ActivityLog.objects.create(
                branch=request.user.branch,
                user=request.user,
                stocktake=stocktake.stocktake,
                action='Stocktake adjustments',
                inventory=stocktake.product,
                quantity=stocktake.quantity_difference,
                total_quantity=stocktake.product.quantity,
                description=f'Stock adjustment: #{stocktake.id}'
            )

            return JsonResponse({'success':True, 'message':'success', 'quantity':stocktake.now_quantity}, status=201)

    except Exception as e:
        return JsonResponse({'success':False, 'message':f'{e}'}, status=400)

def adjust_stocktake_quantity(request):
    try:
        data = json.loads(request.body)
        stocktake_id = data.get('stocktake_id')

        stocktake_item = StocktakeItem.objects.filter(stocktake__id=stocktake_id)

        cost = 0
        selling = 0
        for stocktake_item in stocktake_item:
            if not stocktake_item.product.status:
                stocktake_item.delete()
            else:
                stocktake_item.now_quantity = stocktake_item.product.quantity
                stocktake_item.quantity_difference = stocktake_item.quantity - stocktake_item.now_quantity
                stocktake_item.cost = stocktake_item.product.cost * stocktake_item.quantity_difference
                stocktake_item.save()

                cost += stocktake_item.quantity_difference * stocktake_item.product.cost
                selling += stocktake_item.quantity_difference * stocktake_item.product.price

        return JsonResponse({'success': True, 'message': 'Quantity adjusted successfully', 'quantity': stocktake_item.quantity}, status=200)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

def create_user_account(id):
    account = UserAccount.objects.create(
        user_id=id,
        account_type='',
        balance=0,
        total_credits=0,
        total_debits=0,
    )

    return account

@login_required
def process_stock_take_item(request):
     if request.method == 'POST':
       try:
           data = json.loads(request.body)
           phy_quantity = data.get('quantity')
           stocktake_id =data.get('stocktake_id')

           s_item = StocktakeItem.objects.get(id=stocktake_id)
           s_item.quantity = int(phy_quantity)

           difference = int(phy_quantity) - s_item.now_quantity

           s_item.quantity_difference = difference
           s_item.cost = s_item.product.cost * s_item.quantity_difference

           s_item.stocktake.negative += difference
           s_item.stocktake.positive += int(phy_quantity)

           s_item.stocktake.negative_cost += difference * s_item.product.cost
           s_item.stocktake.positive_cost += int(phy_quantity)  * s_item.product.cost
           s_item.recorded = True
           s_item.stocktake.save()
           s_item.save()

           descripancy_value =  s_item.quantity_difference
           details_inventory= {'item_id': s_item.id, 'difference': descripancy_value}
           return JsonResponse({'success': True, 'data': details_inventory }, status = 200)
       except Exception as e:
           return JsonResponse({'success': False, 'response': e}, status = 400)

@login_required
def stocktake_pdf(request):
    try:
        data = json.loads(request.body)
        type = data.get('type')
        stocktake_id = data.get('stocktake_id')
        template_name = 'reports/stocktake.html'

        stock_take = StockTake.objects.get(id=stocktake_id)

        stock_items = None

        if type == 'negative':
            stock_items = StocktakeItem.objects.filter(stocktake=stock_take, quantity_difference__lt=0)
        elif type == 'positve':
            stock_items = StocktakeItem.objects.filter(stocktake=stock_take, quantity_difference__gt=0)
        elif type == 'all':
            stock_items = StocktakeItem.objects.all()

        total_cost = stock_items.aggregate(total=Sum('product__cost'))['total'] or 0

        stock_items = stock_items.annotate(
            selling_value=ExpressionWrapper(
                F('product__price') * F('quantity_difference'),
                output_field=FloatField()
            ),
            cost_value=ExpressionWrapper(
                F('product__cost') * F('quantity_difference'),
                output_field=FloatField()
            )
        )

        total_selling_value = stock_items.aggregate(
            total=Sum('selling_value')
        )['total'] or 0

        total_cost_value = stock_items.aggregate(
            total=Sum('cost_value')
        )['total'] or 0

        return generate_pdf(
            template_name, {
                'stocktake_items':stock_items,
                'stock_take':stock_take,
                'total_cost_value':total_cost_value,
                'total_selling_value':total_selling_value
            }
        )

    except Exception as e:
        return JsonResponse({'success':False, 'message':str(e)}, status=400)

@login_required
def stocktake_report_data(request, stocktake_id, report_type):
    """
    API endpoint to fetch stocktake report data
    """
    try:
        stocktake = get_object_or_404(StockTake, id=stocktake_id, branch=request.user.branch)
        base_queryset = StocktakeItem.objects.filter(stocktake=stocktake).select_related('product', 'product__category')

        # Filter based on report type
        if report_type == 'negative':
            items_queryset = base_queryset.filter(quantity_difference__lt=0)
        elif report_type == 'positive':
            items_queryset = base_queryset.filter(quantity_difference__gt=0)
        elif report_type == 'all':
            items_queryset = base_queryset
        elif report_type == 'product':
            # Group by product
            items_queryset = base_queryset.values('product__name', 'product__category__name').annotate(
                total_difference=Sum('quantity_difference'),
                total_value=Sum(F('quantity_difference') * F('product__price')),
                total_cost=Sum(F('quantity_difference') * F('product__cost'))
            ).order_by('product__name')
        elif report_type == 'category':
            items_queryset = base_queryset.values('product__category__name').annotate(
                total_difference=Sum('quantity_difference'),
                total_value=Sum(F('quantity_difference') * F('product__price')),
                total_cost=Sum(F('quantity_difference') * F('product__cost'))
            ).order_by('product__category__name')
        else:
            return JsonResponse({'error': 'Invalid report type'}, status=400)

        summary_stats = items_queryset.aggregate(
            total_items=Count('id'),
            total_quantity_diff=Sum('quantity_difference'),
            total_value_diff=Sum(F('quantity_difference') * F('product__price')),
            total_cost_diff=Sum(F('quantity_difference') * F('product__cost')),
            negative_items=Count('id', filter=Q(quantity_difference__lt=0)),
            positive_items=Count('id', filter=Q(quantity_difference__gt=0)),
            negative_value=Sum(F('quantity_difference') * F('product__price'), filter=Q(quantity_difference__lt=0)),
            positive_value=Sum(F('quantity_difference') * F('product__price'), filter=Q(quantity_difference__gt=0))
        )

        stock_items = base_queryset.annotate(
            selling_value=ExpressionWrapper(
                F('product__price') * F('quantity_difference'),
                output_field=FloatField()
            ),
            cost_value=ExpressionWrapper(
                F('product__cost') * F('quantity_difference'),
                output_field=FloatField()
            )
        )

        total_selling_value = stock_items.aggregate(
            total=Sum('selling_value')
        )['total'] or 0

        total_cost_value = stock_items.aggregate(
            total=Sum('cost_value')
        )['total'] or 0

        items_data = []
        if report_type in ['all', 'negative', 'positive']:
            for item in items_queryset:
                items_data.append({
                    'product_name': item.product.name,
                    'category_name': item.product.category.name if item.product.category else 'N/A',
                    'expected_quantity': item.quantity or 0,
                    'actual_quantity': item.now_quantity,
                    'quantity_difference': item.quantity_difference,
                    'value_difference': float(item.quantity_difference * item.product.price) if item.product.price else 0,
                    'cost_difference': float(item.quantity_difference * item.product.cost) if item.product.cost else 0,
                    'has_diff': item.has_diff,
                    'accepted': item.accepted,
                    'company_loss': item.company_loss
                })
        elif report_type == 'product':
            for item in items_queryset:
                items_data.append({
                    'product_name': item['product__name'],
                    'category_name': item['product__category__name'] or 'N/A',
                    'total_difference': item['total_difference'],
                    'total_value': float(item['total_value']) if item['total_value'] else 0,
                    'total_cost': float(item['total_cost']) if item['total_cost'] else 0
                })
        elif report_type == 'category':
            for item in items_queryset:
                items_data.append({
                    'category_name': item['product__category__name'] or 'N/A',
                    'total_difference': item['total_difference'],
                    'total_value': float(item['total_value']) if item['total_value'] else 0,
                    'total_cost': float(item['total_cost']) if item['total_cost'] else 0
                })

        response_data = {
            'stocktake_id': stocktake.id,
            'stocktake_number': stocktake.s_t_number,
            'stocktake_date': stocktake.date.strftime('%Y-%m-%d') if stocktake.date else None,
            'conductor': stocktake.conductor.username if stocktake.conductor else 'N/A',
            'report_type': report_type,
            'total_items': summary_stats['total_items'] or 0,
            'quantity_difference': summary_stats['total_quantity_diff'] or 0,
            'value_difference': float(summary_stats['total_value_diff']) if summary_stats['total_value_diff'] else 0,
            'cost_difference': abs(float(summary_stats['total_cost_diff'])) if summary_stats['total_cost_diff'] else 0,
            'negative_items': summary_stats['negative_items'] or 0,
            'positive_items': summary_stats['positive_items'] or 0,
            'negative_value': float(summary_stats['negative_value']) if summary_stats['negative_value'] else 0,
            'positive_value': float(summary_stats['positive_value']) if summary_stats['positive_value'] else 0,
            'items': items_data
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def stocktake_report_download(request, stocktake_id, report_type):
    """
    API endpoint to download stocktake report as PDF
    """
    try:
        stocktake = get_object_or_404(StockTake, id=stocktake_id, branch=request.user.branch)

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        else:
            from django.test import RequestFactory
            factory = RequestFactory()
            temp_request = factory.get('/')
            temp_request.user = request.user

            response = stocktake_report_data(temp_request, stocktake_id, report_type)
            if response.status_code != 200:
                return response
            data = json.loads(response.content)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,
        )

        title = Paragraph(f"Stocktake Report - {data['report_type'].title()}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))

        summary_data = [
            ['Stocktake Number:', data['stocktake_number']],
            ['Date:', data['stocktake_date']],
            ['Conductor:', data['conductor']],
            ['Report Type:', data['report_type'].title()],
            ['Total Items:', str(data['total_items'])],
            ['Quantity Difference:', str(data['quantity_difference'])],
            ['Value Difference:', f"${data['value_difference']:.2f}"],
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        if data['items']:
            if report_type in ['all', 'negative', 'positive']:
                headers = ['Product', 'Category', 'Expected', 'Actual', 'Difference', 'Value Diff']
                table_data = [headers]
                for item in data['items']:
                    table_data.append([
                        item['product_name'],
                        item['category_name'],
                        str(item['expected_quantity']),
                        str(item['actual_quantity']),
                        str(item['quantity_difference']),
                        f"${item['value_difference']:.2f}"
                    ])
            elif report_type == 'product':
                headers = ['Product', 'Category', 'Total Diff', 'Total Value']
                table_data = [headers]
                for item in data['items']:
                    table_data.append([
                        item['product_name'],
                        item['category_name'],
                        str(item['total_difference']),
                        f"${item['total_value']:.2f}"
                    ])
            elif report_type == 'category':
                headers = ['Category', 'Total Diff', 'Total Value']
                table_data = [headers]
                for item in data['items']:
                    table_data.append([
                        item['category_name'],
                        str(item['total_difference']),
                        f"${item['total_value']:.2f}"
                    ])

            items_table = Table(table_data)
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(items_table)

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="stocktake_{report_type}_{stocktake_id}.pdf"'

        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
