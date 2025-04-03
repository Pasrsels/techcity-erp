from . models import Invoice, Payment, Account, AccountBalance, Cashbook
from loguru import logger
from decimal import Decimal
from django.db import transaction
from io import BytesIO
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa  
from django.shortcuts import get_object_or_404
from apps.finance.models import Qoutation, QoutationItems
from django.conf import settings

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



