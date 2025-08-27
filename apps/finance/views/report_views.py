import datetime
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from utils.utils import generate_pdf
from ..models import Expense, Sale, COGSItems, Invoice
from ..utils import calculate_expenses_totals
from django.shortcuts import render
from django.template.loader import render_to_string
from datetime import timedelta
from ..models import Branch

@login_required
def expenses_report(request):

    template_name = 'reports/expenses.html'

    search = request.GET.get('search', '')
    start_date_str = request.GET.get('startDate', '')
    end_date_str = request.GET.get('endDate', '')
    category_id = request.GET.get('category', '')

    if start_date_str and end_date_str:
        try:
            end_date = datetime.date.fromisoformat(end_date_str)
            start_date = datetime.date.fromisoformat(start_date_str)
        except ValueError:
            return JsonResponse({'messgae':'Invalid date format. Please use YYYY-MM-DD.'})
    else:
        start_date = ''
        end_date= ''

    try:
        category_id = int(category_id) if category_id else None
    except ValueError:
        return JsonResponse({'messgae':'Invalid category or search ID.'})

    expenses = Expense.objects.all()

    if search:
        expenses = expenses.filter(Q(amount=search))
    if start_date:
        start_date = parse_date(start_date_str)
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date_str)
        expenses = expenses.filter(date__lte=end_date)
    if category_id:
        expenses = expenses.filter(category__id=category_id)

    return generate_pdf(
        template_name,
        {
            'title': 'Expenses',
            'date_range': f"{start_date} to {end_date}",
            'report_date': datetime.date.today(),
            'total_expenses':calculate_expenses_totals(expenses),
            'expenses':expenses
        }
    )

def get_previous_month():
    first_day_of_current_month = datetime.datetime.now().replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    return last_day_of_previous_month.month

def get_current_month():
    return datetime.datetime.now().month

@login_required
def pl_overview(request):
    filter_option = request.GET.get('filter')
    today = datetime.date.today()
    previous_month = get_previous_month()
    current_year = today.year
    current_month = today.month

    sales = Sale.objects.filter(transaction__branch=request.user.branch)
    expenses = Expense.objects.filter(branch=request.user.branch)
    cogs = COGSItems.objects.filter(invoice__branch=request.user.branch)

    if filter_option == 'today':
        date_filter = today
    elif filter_option == 'last_week':
        last_week_start = today - datetime.timedelta(days=today.weekday() + 7)
        last_week_end = last_week_start + datetime.timedelta(days=6)
        date_filter = (last_week_start, last_week_end)
    elif filter_option == 'this_month':
        date_filter = (datetime.date(current_year, current_month, 1), today)
    elif filter_option == 'year':
        year = int(request.GET.get('year', current_year))
        date_filter = (datetime.date(year, 1, 1), datetime.date(year, 12, 31))
    else:
        date_filter = (datetime.date(current_year, current_month, 1), today)

    if filter_option == 'today':
        current_month_sales = sales.filter(date=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = expenses.filter(issue_date=date_filter).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = cogs.objects.filter(date=date_filter).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0
    elif filter_option == 'last_week':
        current_month_sales = sales.filter(date__range=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = expenses.filter(issue_date__range=date_filter).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = cogs.filter(date__range=date_filter).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0
    else:
        current_month_sales = sales.filter(date__range=date_filter).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
        current_month_expenses = expenses.filter(issue_date__range=date_filter).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
        cogs_total = cogs.filter(date__range=date_filter).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0

    previous_month_sales = sales.filter(date__year=current_year, date__month=previous_month).aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0
    previous_month_expenses = expenses.filter(issue_date__year=current_year, issue_date__month=previous_month).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0
    previous_cogs =  cogs.filter(date__year=current_year, date__month=previous_month).aggregate(total_cogs=Sum('product__cost'))['total_cogs'] or 0

    current_net_income = current_month_sales
    previous_net_income = previous_month_sales
    current_expenses = current_month_expenses

    current_gross_profit = current_month_sales - cogs_total
    previous_gross_profit = previous_month_sales - previous_cogs

    current_net_profit = current_gross_profit - current_month_expenses
    previous_net_profit = previous_gross_profit - previous_month_expenses

    current_gross_profit_margin = (current_gross_profit / current_month_sales * 100) if current_month_sales != 0 else 0
    previous_gross_profit_margin = (previous_gross_profit / previous_month_sales * 100) if previous_month_sales != 0 else 0

    data = {
        'net_profit':current_net_profit,
        'cogs_total':cogs_total,
        'current_expenses':current_expenses,
        'current_net_profit': current_net_profit,
        'previous_net_profit':previous_net_profit,
        'current_net_income': current_net_income,
        'previous_net_income': previous_net_income,
        'current_gross_profit': current_gross_profit,
        'previous_gross_profit': previous_gross_profit,
        'current_gross_profit_margin': f'{current_gross_profit_margin:.2f}',
        'previous_gross_profit_margin': previous_gross_profit_margin,
    }

    return JsonResponse(data)

@login_required
def income_json(request):
    current_month = get_current_month()
    today = datetime.date.today()

    month = request.GET.get('month', current_month)
    day = request.GET.get('day', today.day)

    sales = Sale.objects.filter(transaction__branch=request.user.branch)

    if request.GET.get('filter') == 'today':
        sales_total = sales.filter(date=today).aggregate(Sum('total_amount'))
    else:
        sales_total = sales.filter(date__month=month).aggregate(Sum('total_amount'))

    return JsonResponse({'sales_total': sales_total['total_amount__sum'] or 0})

@login_required
def expense_json(request):
    current_month = get_current_month()
    today = datetime.date.today()

    month = request.GET.get('month', current_month)
    day = request.GET.get('day', today.day)

    expenses = Expense.objects.filter(branch=request.user.branch)

    if request.GET.get('filter') == 'today':
        expense_total = expenses.filter(issue_date=today, status=False).aggregate(Sum('amount'))
    else:
        expense_total = expenses.filter(issue_date__month=month, status=False).aggregate(Sum('amount'))

    return JsonResponse({'expense_total': expense_total['amount__sum'] or 0})

@login_required
def daily_summary(request, date=None):
    from ..models import Cashflow, CashUp
    if date is None:
        date = datetime.now().date()

    daily_cashflows = Cashflow.objects.filter(date=date)
    daily_cashups = CashUp.objects.filter(date=date)

    total_income = daily_cashflows.aggregate(Sum('income'))['income__sum'] or 0
    total_expense = daily_cashflows.aggregate(Sum('expense'))['expense__sum'] or 0
    net_total = total_income - total_expense

    context = {
        'date': date,
        'daily_cashflows': daily_cashflows,
        'daily_cashups': daily_cashups,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_total': net_total,
    }
    return render(request, 'cashflow/daily_summary.html', context)

@login_required
def branch_summary(request, branch_id):
    from ..models import Cashflow, CashUp
    branch = get_object_or_404(Branch, id=branch_id)

    branch_cashflows = Cashflow.objects.filter(branch=branch)
    branch_cashups = CashUp.objects.filter(branch=branch)

    context = {
        'branch': branch,
        'cashflows': branch_cashflows,
        'cashups': branch_cashups,
        'total_income': branch_cashflows.aggregate(Sum('income'))['income__sum'] or 0,
        'total_expense': branch_cashflows.aggregate(Sum('expense'))['expense__sum'] or 0,
    }
    return render(request, 'cashflow/branch_summary.html', context)

def get_date_range_from_time_frame(time_frame, request):
    today = datetime.date.today()
    if time_frame == 'today':
        return today, today

    elif time_frame == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    elif time_frame == 'monthly':
        return today.replace(day=1), today

    elif time_frame == 'yearly':
        return today.replace(month=1, day=1), today

    elif time_frame == 'custom':
        start_date = parse_date(request.POST.get('startDate'))
        end_date = parse_date(request.POST.get('endDate'))
        return start_date, end_date

    return today, today

@login_required
def generate_financial_report(request):
    report_type = request.POST.get('reportType')
    time_frame = request.POST.get('timeFrame')
    report_branch = request.POST.get('reportBranch')

    start_date, end_date = get_date_range_from_time_frame(time_frame, request)

    if report_branch == "all":
        branch = None
    else:
        branch = Branch.objects.filter(id=report_branch).first()

    invoices = Invoice.objects.filter(
        cancelled=False,
        invoice_return=False,
        status=True,
        issue_date__date__range=[start_date, end_date]
    )

    if branch:
        invoices = invoices.filter(branch=branch)

    expenses = Expense.objects.filter(
        status=False,
        issue_date__date__range=[start_date, end_date]
    ).select_related('category', 'category__parent', 'currency')

    total_sales = invoices.aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    if report_type == 'profit_loss':
        invoice_items = InvoiceItem.objects.filter(invoice__in=invoices)
        total_cost = invoice_items.aggregate(
            cost=Sum(
                ExpressionWrapper(
                    F('quantity') * F('item__price'),
                    output_field=DecimalField(max_digits=15, decimal_places=2)
                )
            )
        )['cost'] or 0

        gross_profit = total_sales - total_cost
        net_profit = gross_profit - total_expenses

        expenses_by_category = {}
        for expense in expenses:
            parent_category = expense.category.parent or expense.category
            parent_id = parent_category.id

            if parent_id not in expenses_by_category:
                expenses_by_category[parent_id] = {
                    'category': parent_category,
                    'items': [],
                    'total': 0
                }

            if expense.category.parent is not None:
                expenses_by_category[parent_id]['items'].append(expense)

            expenses_by_category[parent_id]['total'] += expense.amount

        html = render_to_string('reports/partials/p_l_report.html', {
            'sales': total_sales,
            'expenses_by_category': expenses_by_category.values(),
            'total_expenses': total_expenses,
            'cost_of_sales': total_cost,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'start_date': start_date,
            'end_date': end_date,
            'branch':branch
        })

        return JsonResponse({
            'success': True,
            'html': html,
        })

    elif report_type == 'sales':
        total_paid = invoices.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_unpaid = total_sales - total_paid
        invoice_count = invoices.count()

        invoice_items = InvoiceItem.objects.filter(invoice__in=invoices)

        total_cost = invoice_items.aggregate(
            cost=Sum(
                ExpressionWrapper(
                    F('quantity') * F('item__price'),
                    output_field=DecimalField(max_digits=15, decimal_places=2)
                )
            )
        )['cost'] or 0

        gross_profit = total_sales - total_cost

        product_summary = invoice_items.values(
            name=F('item__name')
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('total_amount'),
        ).order_by('-total_sales')

        html = render_to_string('reports/partials/sales_report_products.html', {
            'products': product_summary,
            'total_sales': round(total_sales, 2),
            'total_paid': round(total_paid, 2),
            'total_unpaid': round(total_unpaid, 2),
            'invoice_count': invoice_count,
            'branch': branch
        })

        return JsonResponse({
            'success': True,
            'html': html,
            'start_date': start_date,
            'end_date': end_date,
        })

    elif report_type == 'expenses':
        html = render_to_string('reports/partials/expense_report_table.html', {
            'expenses': expenses,
            'total_expenses': total_expenses,
            'start_date': start_date,
            'end_date': end_date,
            'branch': branch
        }, request=request)

        return JsonResponse({
            'success': True,
            'report_type': report_type,
            'time_frame': time_frame,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'total_expenses': float(total_expenses),
            'html': html,
        })

    return JsonResponse({'status': 'error', 'message': 'Unsupported report type'}, status=400)
