from django.shortcuts import get_list_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from utils.utils import generate_pdf
from apps.inventory.models import Inventory, TransferItems
from apps.inventory.utils import calculate_inventory_totals
import datetime
from datetime import timedelta

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
