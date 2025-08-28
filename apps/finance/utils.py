from . models import Invoice, Payment, Account, AccountBalance, Cashbook
from loguru import logger
from decimal import Decimal
from django.db import transaction
from io import BytesIO
from django.template.loader import get_template
from django.http import HttpResponse, JsonResponse
from xhtml2pdf import pisa  
from django.shortcuts import get_object_or_404
from apps.finance.models import Qoutation, QoutationItems
from django.conf import settings
from django.core.cache import cache
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def handle_api_error(view_func):
    """Decorator to handle API errors."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except APIError as e:
            logger.warning(f"API Error in {view_func.__name__}: {str(e)}")
            return JsonResponse({'error': str(e)}, status=e.status_code)
        except Exception as e:
            logger.error(f"Unexpected error in {view_func.__name__}: {str(e)}")
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
    return wrapper

def validate_request_data(data, required_fields):
    """Validate request data against required fields."""
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise APIError(f"Missing required fields: {', '.join(missing_fields)}")
    return data

def rate_limit(limit=100, period=3600):
    """Rate limiting decorator."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            key = f'rate_limit_{request.user.id}_{view_func.__name__}'
            count = cache.get(key, 0)
            
            if count >= limit:
                raise APIError('Rate limit exceeded', status_code=429)
                
            cache.set(key, count + 1, timeout=period)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def format_currency(amount):
    """Format amount as currency."""
    try:
        return f"${amount:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def get_pagination_data(page, per_page, total_items):
    """Get pagination data."""
    total_pages = (total_items + per_page - 1) // per_page
    has_next = page < total_pages
    has_previous = page > 1
    
    return {
        'current_page': page,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_previous': has_previous,
        'total_items': total_items
    }

def clear_cache_pattern(pattern):
    """Clear cache entries matching pattern."""
    try:
        cache.delete_pattern(pattern)
    except Exception as e:
        logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")

def validate_date_range(start_date, end_date):
    """Validate date range."""
    if start_date and end_date and start_date > end_date:
        raise APIError('Start date must be before end date')
    return True

def validate_amount(amount):
    """Validate amount."""
    try:
        amount = float(amount)
        if amount <= 0:
            raise APIError('Amount must be greater than 0')
        return amount
    except ValueError:
        raise APIError('Invalid amount value')

def validate_transaction_type(transaction_type):
    """Validate transaction type."""
    if transaction_type not in ['in', 'out']:
        raise APIError('Invalid transaction type')
    return transaction_type

def get_user_permissions(user):
    """Get user permissions."""
    return {
        'can_add_transaction': user.has_perm('finance.add_cashbookentry'),
        'can_edit_transaction': user.has_perm('finance.change_cashbookentry'),
        'can_delete_transaction': user.has_perm('finance.delete_cashbookentry'),
        'can_view_reports': user.has_perm('finance.view_report'),
        'can_manage_categories': user.has_perm('finance.manage_category')
    }

def calculate_expenses_totals(expense_queryset):
    """Calculates the total cost of all expenses in a queryset."""
    total_cost = 0
    for item in expense_queryset:
        total_cost += item.amount
    return total_cost

def update_latest_due(customer, amount_received, request, payment_method, customer_account_balance):
    try:
        invoice = Invoice.objects.filter(customer=customer, payment_status=Invoice.PaymentStatus.PARTIAL, cancelled=False, invoice_return=False)\
        .order_by('-issue_date').first()

        logger.info(f"Checking if invoice.amount_due: {invoice.amount_due} < amount_received: {Decimal(amount_received)}")

        with transaction.atomic():
            if invoice:
                logger.info(f'Invoice amount due: {invoice.amount_due}')

                if invoice.amount_due < amount_received:
                    amount_paid = invoice.amount_due
                    invoice.amount_paid += amount_paid
                    invoice.amount_due = 0
                    invoice.payment_status=Invoice.PaymentStatus.PAID

                # get the latest payment for the invoice
                latest_payment = Payment.objects.filter(invoice=invoice).order_by('-payment_date').first()
                amount_due = latest_payment.amount_due - amount_paid 

                logger.info(f'Latest Amount Due {amount_due}')

                payment = Payment.objects.create(
                    invoice=invoice,
                    amount_paid=amount_paid,
                    amount_due=amount_due, 
                    payment_method=payment_method,
                    user=request.user
                )

                account, _ = Account.objects.get_or_create(
                    name=f"{request.user.branch} {invoice.currency.name} {payment.payment_method.capitalize()} Account",
                    type=Account.AccountType[payment.payment_method.upper()] 
                )
                account_balance, _ = AccountBalance.objects.get_or_create(
                    account=account,
                    currency=invoice.currency,
                    branch=request.user.branch,
                    defaults={'balance': 0}
                )

                account_balance.balance += amount_paid
                if customer_account_balance.balance < 0:
                    customer_account_balance.balance += amount_paid
                else:
                    customer_account_balance.balance -= amount_paid

                balance = amount_received - amount_paid

                Cashbook.objects.create(
                    invoice = invoice,
                    issue_date=invoice.issue_date,
                    description=f'Sale update for {invoice.products_purchased}({invoice.invoice_number})',
                    debit=True,
                    credit=False,
                    amount=balance,
                    currency=invoice.currency,
                    branch=invoice.branch
                )

                account_balance.save()
                customer_account_balance.save()
                invoice.save()
                payment.save()

                logger.info(f'Invoice balance amount: {balance}')

                return balance
    except Exception as e:
        return amount_received

def generate_quote_pdf(quote_id, request):
    """
    Generate PDF from qoute using pdfkit (wkhtmltopdf wrapper)
    """
    import pdfkit
    from django.template.loader import render_to_string
    
    qoute = get_object_or_404(Qoutation, id=quote_id)
    quote_items = QoutationItems.objects.filter(qoute=qoute)
    
    context = {
        'qoute': qoute,
        'qoute_items': quote_items,
        'request': {
            'user': {
                'branch': qoute.branch,
                'first_name': request.user.first_name if hasattr(qoute, 'created_by') else '',
                'phonenumber': request.user.phonenumber if hasattr(qoute, 'created_by') else ''
            }
        },
        'static_url': settings.STATIC_URL
    }
    
    html_string = render_to_string('quotation_pdf.html', context)
    
    pdf = pdfkit.from_string(
        html_string, 
        False,  
        options={
            'page-size': 'Letter',
            'encoding': 'UTF-8',
            'no-outline': None,
            'quiet': ''
        }
    )
    
    return pdf



