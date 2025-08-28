from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import json
import logging
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.conf import settings
from django.db.models import Sum

from ..models import Cashbook
from ..utils import validate_request_data, handle_api_error, rate_limit

logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@handle_api_error
@rate_limit()
def cashbook_data(request):
    """Get cashbook data with pagination and filtering."""
    try:
        data = json.loads(request.body)
        validate_request_data(data, ['page', 'per_page'])
        
        page = int(data.get('page', 1))
        per_page = int(data.get('per_page', 20))
        filter_type = data.get('filter', 'all')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        search = data.get('search', '').strip()
        
        # Build query
        query = {}
        if filter_type != 'all':
            query['type'] = filter_type
        if start_date:
            query['date__gte'] = start_date
        if end_date:
            query['date__lte'] = end_date
        if search:
            query['description__icontains'] = search
            
        # Get data with caching
        cache_key = f'cashbook_data_{hash(str(query))}_{page}_{per_page}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return JsonResponse(cached_data)
            
        entries = Cashbook.objects.filter(**query).order_by('-date')
        
        # Calculate totals
        totals = {
            'cash_in': entries.filter(type='in').aggregate(total=Sum('amount'))['total'] or 0,
            'cash_out': entries.filter(type='out').aggregate(total=Sum('amount'))['total'] or 0
        }
        totals['balance'] = totals['cash_in'] - totals['cash_out']
        
        # Paginate results
        paginator = Paginator(entries, per_page)
        page_obj = paginator.get_page(page)
        
        response_data = {
            'entries': [{
                'id': entry.id,
                'date': entry.date.strftime('%Y-%m-%d %H:%M:%S'),
                'description': entry.description,
                'amount': float(entry.amount),
                'type': entry.type,
                'created_by': entry.created_by.username
            } for entry in page_obj],
            'totals': totals,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            }
        }
        
        # Cache the response
        cache.set(cache_key, response_data, timeout=300)  # Cache for 5 minutes
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        raise APIError('Invalid JSON data')
    except ValueError as e:
        raise APIError(str(e))

@login_required
def cashbook_data_old(request):
    """AJAX endpoint for cashbook data with filters and pagination"""
    logger.info('Processing cashbook data request')
    
    # Get parameters from either GET or POST request
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
    
    # Calculate totals
    total_cash_in = entries.filter(credit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
    total_cash_out = entries.filter(debit=True, cancelled=False).aggregate(total=Sum('amount'))['total'] or 0
    total_balance = total_cash_in - total_cash_out

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
        logger.info(f'Entry: {entry}')
        entries_data.append({
            'id': entry.id,
            'date': entry.issue_date.strftime('%Y-%m-%d %H:%M:%S'),
            'description': entry.description,
            'debit': float(entry.amount) if entry.debit else None,
            'credit': float(entry.amount) if entry.credit else None,
            'balance': float(balance),
            'accountant': entry.accountant,
            'manager': entry.manager,
            'director': entry.director,
            'status': entry.status
        })

    return JsonResponse({
        'entries': entries_data,
        'totals': {
            'cash_in': float(total_cash_in),
            'cash_out': float(total_cash_out),
            'balance': float(total_balance)
        },
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_entries': total_entries,
            'has_next': page < total_pages,
            'has_previous': page > 1
        }
    }) 