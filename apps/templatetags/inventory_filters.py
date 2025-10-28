from django import template
from decimal import Decimal
from apps.finance.models import InvoiceItem
from django.utils import timezone
from dateutil.relativedelta import relativedelta

register = template.Library()

@register.filter
def calculate_gp(product):
    try:
        if product.price and product.cost and product.price > 0:
            gp = ((product.price - product.cost) / product.price) * 100
            return round(gp, 2)
        return Decimal('0.00')
    except (TypeError, ZeroDivisionError):
        return Decimal('0.00')

@register.filter
def calculate_average_sales(product):
    try:
        invoice_items = InvoiceItem.objects.filter(item=product, invoice__branch=product.branch)
    
        if not invoice_items.exists():
            return Decimal('0.00')
        
        first_invoice_date = invoice_items.earliest('invoice__issue_date').invoice.issue_date.date
        total_months = (timezone.now().date().year - first_invoice_date.year) * 12 + (timezone.now().date().month - first_invoice_date.month)

        if timezone.now().date().day < first_invoice_date.day:
            total_months -= 1
        total_months = max(total_months, 1)
        
        total_quantity = sum(invoice_item.quantity for invoice_item in invoice_items)
        
        average = total_quantity / total_months
        return round(average, 2)
    except (TypeError, ZeroDivisionError):
        return Decimal('0.00')
    except Exception as e:
        return Decimal('0.00')