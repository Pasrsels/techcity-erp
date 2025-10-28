from django import template
from decimal import Decimal
from apps.finance.models import InvoiceItem
from django.utils import timezone

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
    #$ to skip,, ifs zero
    try:
        invoice_items = InvoiceItem.objects.filter(item=product, invoice__branch=product.branch)
    
        if not invoice_items.exists():
            return Decimal('0.00')
        
        first_invoice = invoice_items.earliest('invoice__issue_date')
        first_invoice_date = first_invoice.invoice.issue_date
        
        today = timezone.now().date()
        total_months = (today.year - first_invoice_date.year) * 12 + (today.month - first_invoice_date.month)
        if today.day < first_invoice_date.day:
            total_months -= 1
        total_months = max(total_months, 1)
        
        total_quantity = sum(invoice_item.quantity for invoice_item in invoice_items)
        
        average = total_quantity / total_months
        return round(average, 2)
    except (TypeError, ZeroDivisionError) as e:
        print(f"Error in calculate_average_sales: {e}")
        return Decimal('0.00')
    except Exception as e:
        print(f"Unexpected error in calculate_average_sales: {e}")
        return Decimal('0.00')


# gp
# lesser the returns
# more sales than other products in its category with the same branch
