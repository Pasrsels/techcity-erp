from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import json
from loguru import logger

from ..models import Cashbook

@login_required
def cashbook_data(request):
    """AJAX endpoint for cashbook data with filters and pagination"""
    logger.info('Processing cashbook data request')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            page = int(data.get('page', 1))
            per_page = int(data.get('per_page', 20))
            filter_option = data.get('filter', 'this_week')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            search_query = data.get('search', '')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        filter_option = request.GET.get('filter', 'this_week')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        search_query = request.GET.get('search', '')
    
    logger.info(f'filter: {filter_option}')

    now = timezone.now()
    end_date = now

    if filter_option == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday())
    elif filter_option == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    elif filter_option == 'custom':
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = now - timedelta(days=now.weekday())
            end_date = now

    entries = Cashbook.objects.filter(
        issue_date__gte=start_date,
        issue_date__lte=end_date,
        branch=request.user.branch
    )
    
    logger.info(f'Found {entries.count()} entries')

    if search_query:
        entries = entries.filter(
            Q(description__icontains=search_query) |
            Q(accountant__icontains=search_query) |
            Q(manager__icontains=search_query) |
            Q(director__icontains=search_query)
        )

    entries = entries.order_by('-issue_date')

    total_entries = entries.count()
    total_pages = (total_entries + per_page - 1) // per_page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page

    paginated_entries = entries[start_index:end_index]

    balance = 0
    entries_data = []
    for entry in paginated_entries:
        if entry.debit:
            balance += entry.amount
        elif entry.credit:
            balance -= entry.amount

        entries_data.append({
            'id': entry.id,
            'date': entry.issue_date.strftime('%Y-%m-%d %H:%M'),
            'description': entry.description,
            'debit': float(entry.amount) if entry.debit else None,
            'credit': float(entry.amount) if entry.credit else None,
            'balance': float(balance),
            'accountant': entry.accountant,
            'manager': entry.manager,
            'director': entry.director,
            'cancelled': entry.cancelled
        })

    return JsonResponse({
        'entries': entries_data,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_entries': total_entries,
            'has_next': page < total_pages,
            'has_previous': page > 1
        }
    }) 