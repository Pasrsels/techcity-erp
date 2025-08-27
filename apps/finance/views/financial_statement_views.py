from django.shortcuts import render
from django.views import View
from django.utils import timezone
from django.db.models import Sum, DecimalField
import json
from datetime import timedelta
from decimal import Decimal
from ..models import AccountBalance, Sale, Expense

class Finance(View):
    template_name = 'finance.html'

    def get(self, request, *args, **kwargs):
        if request.user.role == 'sales':
            return redirect('finance:expenses')

        period = request.GET.get('period', 'this_month')
        start_date, end_date = self.get_date_range(period)

        balances = AccountBalance.objects.filter(branch=request.user.branch)
        recent_sales = Sale.objects.filter(transaction__branch=request.user.branch).order_by('-date')[:5]
        expenses_by_category = Expense.objects.values('category__name').annotate(
            total_amount=Sum('amount', output_field=DecimalField())
        )

        graph_data = self.get_graph_data(request.user.branch, period, start_date, end_date)
        metrics = self.calculate_metrics(request.user.branch, start_date, end_date)

        context = {
            'balances': balances,
            'recent_transactions': recent_sales,
            'expenses_by_category': expenses_by_category,
            'graph_data': json.dumps(graph_data),
            'metrics': metrics,
            'current_period': period,
        }

        return render(request, self.template_name, context)

    def get_date_range(self, period):
        now = timezone.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else: # Default to this month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        return start_date, end_date

    def get_graph_data(self, branch, period, start_date, end_date):
        if period == 'today':
            labels = ['6 AM', '9 AM', '12 PM', '3 PM', '6 PM', '9 PM']
            sales_data = []
            expenses_data = []
            for i, hour in enumerate([6, 9, 12, 15, 18, 21]):
                hour_start = start_date.replace(hour=hour)
                hour_end = hour_start + timedelta(hours=3)
                sales = Sale.objects.filter(
                    transaction__branch=branch,
                    date__range=[hour_start, hour_end]
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                expenses = Expense.objects.filter(
                    branch=branch,
                    date__range=[hour_start, hour_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                sales_data.append(float(sales))
                expenses_data.append(float(expenses))
        elif period == 'last_week':
            labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            sales_data = []
            expenses_data = []
            for i in range(7):
                day_start = start_date + timedelta(days=i)
                day_end = day_start + timedelta(days=1)
                sales = Sale.objects.filter(
                    transaction__branch=branch,
                    date__range=[day_start, day_end]
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                expenses = Expense.objects.filter(
                    branch=branch,
                    date__range=[day_start, day_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                sales_data.append(float(sales))
                expenses_data.append(float(expenses))
        elif period == 'this_month':
            labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
            sales_data = []
            expenses_data = []
            for week in range(4):
                week_start = start_date + timedelta(weeks=week)
                week_end = week_start + timedelta(weeks=1)
                if week_end > end_date:
                    week_end = end_date
                sales = Sale.objects.filter(
                    transaction__branch=branch,
                    date__range=[week_start, week_end]
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                expenses = Expense.objects.filter(
                    branch=branch,
                    date__range=[week_start, week_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                sales_data.append(float(sales))
                expenses_data.append(float(expenses))
        elif period == 'year':
            labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            sales_data = []
            expenses_data = []
            for month in range(1, 13):
                month_start = start_date.replace(month=month, day=1)
                if month == 12:
                    month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
                else:
                    month_end = month_start.replace(month=month + 1, day=1)
                if month_end > end_date:
                    month_end = end_date
                sales = Sale.objects.filter(
                    transaction__branch=branch,
                    date__range=[month_start, month_end]
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                expenses = Expense.objects.filter(
                    branch=branch,
                    date__range=[month_start, month_end]
                ).aggregate(total=Sum('amount'))['total'] or 0
                sales_data.append(float(sales))
                expenses_data.append(float(expenses))

        return {
            'labels': labels,
            'sales': sales_data,
            'expenses': expenses_data
        }

    def calculate_metrics(self, branch, start_date, end_date):
        total_sales = Sale.objects.filter(
            transaction__branch=branch,
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_expenses = Expense.objects.filter(
            branch=branch,
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        cogs = Expense.objects.filter(
            branch=branch,
            category__name__icontains='cogs',
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        gross_profit = total_sales - cogs
        net_profit = total_sales - total_expenses

        if total_sales > 0:
            gp_margin = (gross_profit / total_sales) * 100
        else:
            gp_margin = Decimal('0')

        operating_expenses = total_expenses - cogs

        return {
            'total_sales': total_sales,
            'total_expenses': total_expenses,
            'cogs': cogs,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'gp_margin': gp_margin,
            'operating_expenses': operating_expenses,
        }
