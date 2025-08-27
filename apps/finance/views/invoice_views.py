from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views import View
from django.db import transaction
from django.db.models import Q, Sum, Max
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from ..models import (
    Invoice, InvoiceItem, Customer, CustomerAccount, CustomerAccountBalances,
    Payment, Account, AccountBalance, Sale, VATTransaction, VATRate,
    Paylater, paylaterDates, Currency, layby, laybyDates, Qoutation, QoutationItems,
    StockTransaction, Cashbook
)
from apps.inventory.models import ActivityLog, Inventory
from ..forms import InvoiceForm
from utils.utils import generate_pdf
from utils.zimra import ZIMRA
from utils.zimra_sig_hash import run
from apps.pos.utils.submit_receipt_data import submit_receipt_data
from ..tasks import send_invoice_email_task
from collections import defaultdict
from loguru import logger
import json
import io
import os
from twilio.rest import Client
import boto3
from xhtml2pdf import pisa
from pytz import timezone as pytz_timezone
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

zimra = ZIMRA()

@login_required
def invoice(request):
    form = InvoiceForm()
    invoices = Invoice.objects.filter(branch=request.user.branch, status=True, cancelled=False).select_related(
        'branch',
        'currency',
        'user'
    ).order_by('-invoice_number')

    query_params = request.GET
    if query_params.get('q'):
        search_query = query_params['q']
        invoices = invoices.filter(
            Q(customer__name__icontains=search_query) |
            Q(invoice_number__icontains=search_query) |
            Q(issue_date__icontains=search_query)
        )

    user_timezone_str = request.user.timezone if hasattr(request.user, 'timezone') else 'UTC'
    user_timezone = pytz_timezone(user_timezone_str)

    def filter_by_date_range(start_date, end_date):
        start_datetime = user_timezone.localize(
            timezone.datetime.combine(start_date, timezone.datetime.min.time())
        )
        end_datetime = user_timezone.localize(
            timezone.datetime.combine(end_date, timezone.datetime.max.time())
        )
        return invoices.filter(issue_date__range=[start_datetime, end_datetime])

    now = timezone.now().astimezone(user_timezone)
    today = now.date()

    date_filters = {
        'today': lambda: filter_by_date_range(today, today),
        'yesterday': lambda: filter_by_date_range(today - timezone.timedelta(days=1), today - timezone.timedelta(days=1)),
        't_week': lambda: filter_by_date_range(today - timezone.timedelta(days=today.weekday()), today),
        'l_week': lambda: filter_by_date_range(today - timezone.timedelta(days=today.weekday() + 7), today - timezone.timedelta(days=today.weekday() + 1)),
        't_month': lambda: invoices.filter(issue_date__month=today.month, issue_date__year=today.year),
        'l_month': lambda: invoices.filter(issue_date__month=today.month - 1 if today.month > 1 else 12, issue_date__year=today.year if today.month > 1 else today.year - 1),
        't_year': lambda: invoices.filter(issue_date__year=today.year),
    }

    if query_params.get('day') in date_filters:
        invoices = date_filters[query_params['day']]()

    total_partial = invoices.filter(payment_status='Partial').aggregate(Sum('amount'))['amount__sum'] or 0
    total_paid = invoices.filter(payment_status='Paid').aggregate(Sum('amount'))['amount__sum'] or 0
    total_amount = invoices.aggregate(Sum('amount'))['amount__sum'] or 0

    grouped_invoices = defaultdict(list)

    for inv in invoices:
        issue_date = inv.issue_date.date()
        if issue_date == today:
            grouped_invoices['Today'].append(inv)
        elif issue_date == today - timezone.timedelta(days=1):
            grouped_invoices['Yesterday'].append(inv)
        else:
            grouped_invoices[issue_date.strftime('%A, %d %B %Y')].append(inv)

    return render(request, 'invoices/invoice.html', {
        'form': form,
        'grouped_invoices': dict(grouped_invoices),
        'total_paid': total_paid,
        'total_due': total_partial,
        'total_amount': total_amount,
    })

@login_required
@transaction.atomic
def update_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    customer_account = get_object_or_404(CustomerAccount, customer=invoice.customer)
    customer_account_balance = get_object_or_404(
        CustomerAccountBalances, account=customer_account, currency=invoice.currency
    )

    if request.method == 'POST':
        data = json.loads(request.body)
        amount_paid = Decimal(data['amount_paid'])

        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        customer_account_balance = CustomerAccountBalances.objects.select_for_update().get(pk=customer_account_balance.pk)

        if amount_paid <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid amount paid.'}, status=400)

        if amount_paid >= invoice.amount_due:
            invoice.payment_status = Invoice.PaymentStatus.PAID
            invoice.amount_due = 0
        else:
            invoice.amount_due -= amount_paid

        invoice.amount_paid += amount_paid

        latest_payment = Payment.objects.filter(invoice=invoice).order_by('-payment_date').first()
        if latest_payment:
            amount_due = latest_payment.amount_due - amount_paid
        else:
            amount_due = invoice.amount - invoice.amount_paid

        payment = Payment.objects.create(
            invoice=invoice,
            amount_paid=amount_paid,
            amount_due=amount_due,
            payment_method=data['payment_method'],
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

        description = ''
        if invoice.hold_status:
            description = 'Held invoice payment'
            sale = Sale.objects.create(
                date=timezone.now(),
                transaction=invoice,
                total_amount=invoice.amount
            )

            VATTransaction.objects.create(
                invoice=invoice,
                vat_type=VATTransaction.VATType.OUTPUT,
                vat_rate=VATRate.objects.get(status=True).rate,
                tax_amount=invoice.vat
            )
        else:
            description = 'Invoice payment update'

        Cashbook.objects.create(
            issue_date=invoice.issue_date,
            description=f'({description} {invoice.invoice_number})',
            debit=True,
            credit=False,
            amount=invoice.amount_paid,
            currency=invoice.currency,
            branch=invoice.branch
        )

        invoice.hold_status = False
        account_balance.save()
        customer_account_balance.save()
        invoice.save()
        payment.save()

        return JsonResponse({'success': True, 'message': 'Invoice successfully updated'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

def held_invoice(items_data, invoice, request, vat_rate):
    for item_data in items_data:
        item = Inventory.objects.get(pk=item_data['inventory_id'])
        item.quantity -= item_data['quantity']
        item.save()

        InvoiceItem.objects.create(
            invoice=invoice,
            item=item,
            quantity=item_data['quantity'],
            unit_price=item_data['price'],
            vat_rate = vat_rate
        )

        ActivityLog.objects.create(
            branch=request.user.branch,
            inventory=item,
            user=request.user,
            quantity=item_data['quantity'],
            total_quantity = item.quantity,
            action='Sale',
            invoice=invoice
        )

@login_required
def submit_invoice_data_zimra(request):
    try:
        data = json.loads(request.body)
        hash_val = data.get('hash', '')
        signature = data.get('signature', '')
        receipt_data = data.get('receipt_data')
        invoice_id = data.get('invoice_id')

        if not hash_val:
            return JsonResponse({'success':False,'message':f'Hash data is missing!'}, status=400)

        if not signature:
            return JsonResponse({'success':False,'message':f'Signature data is missing!'}, status=400)

        try:
            submit_receipt_data(request, receipt_data, hash_val, signature)
        except Exception as e:
            return JsonResponse(
                {'success':False, 'messsage':f'{e}'}, status=400
            )

        invoice_data = invoice_preview_json(request, invoice_id)
        return JsonResponse({'success':True, 'message':'data received', 'data':invoice_data}, status=200)
    except Exception as e:
        return JsonResponse({'message':f'{e}', 'success':False}, status=200)


@login_required
def get_signature_data(request):
    try:
        data = json.loads(request.body)
        hash_val = data.get('hash', '')
        signature = data.get('signature', '')

        if not hash_val:
            return JsonResponse({'success':False,'message':f'Hash data is missing!'}, status=400)

        if not signature:
            return JsonResponse({'success':False,'message':f'Signature data is missing!'}, status=400)

        return JsonResponse({'success':True, 'message':'data received'}, status=200)
    except Exception as e:
        return JsonResponse({'success':False,'message':f'{e}'}, status=400)


@login_required
def held_invoice_view(request):
    form = InvoiceForm()
    invoices = Invoice.objects.filter(branch=request.user.branch, status=True, hold_status=True).order_by('-invoice_number')
    return render(request, 'invoices/held_invoices.html', {'invoices':invoices, 'form':form})

@login_required
@transaction.atomic
def invoice_returns(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    account = get_object_or_404(CustomerAccount, customer=invoice.customer)
    customer_account_balance = get_object_or_404(CustomerAccountBalances, account=account, currency=invoice.currency)

    sale = get_object_or_404(Sale, transaction=invoice)
    invoice_payment = get_object_or_404(Payment, invoice=invoice)
    vat_transaction = get_object_or_404(VATTransaction, invoice=invoice)
    activity = ActivityLog.objects.filter(invoice=invoice)

    if invoice.payment_status == Invoice.PaymentStatus.PARTIAL:
        customer_account_balance.balance -= invoice.amount_due

    account_types = {
        'cash': Account.AccountType.CASH,
        'bank': Account.AccountType.BANK,
        'ecocash': Account.AccountType.ECOCASH,
    }

    account = get_object_or_404(
        Account,
        name=f"{request.user.branch} {invoice.currency.name} {invoice_payment.payment_method.capitalize()} Account",
        type=account_types.get(invoice_payment.payment_method, None)
    )
    account_balance = get_object_or_404(AccountBalance, account=account, currency=invoice.currency, branch=request.user.branch)
    account_balance.balance -= invoice.amount_paid

    for stock_transaction in activity:
        product = Inventory.objects.get(id=stock_transaction.inventory.id, branch=request.user.branch)
        product.quantity += stock_transaction.quantity
        product.save()

        ActivityLog.objects.create(
            invoice=invoice,
            branch=request.user.branch,
            user=request.user,
            action='returns',
            inventory=product,
            quantity=stock_transaction.quantity,
            total_quantity=product.quantity
        )

    InvoiceItem.objects.filter(invoice=invoice).delete()
    StockTransaction.objects.filter(invoice=invoice).delete()
    Payment.objects.filter(invoice=invoice).delete()

    account_balance.save()
    customer_account_balance.save()
    sale.delete()
    vat_transaction.delete()
    invoice.invoice_return=True
    invoice.save()

    return JsonResponse({'message': f'Invoice {invoice.invoice_number} successfully deleted'})


@login_required
@transaction.atomic
def delete_invoice(request, invoice_id):
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id)
        account = get_object_or_404(CustomerAccount, customer=invoice.customer)
        customer_account_balance = get_object_or_404(CustomerAccountBalances, account=account, currency=invoice.currency)

        sale = get_object_or_404(Sale, transaction=invoice)
        payments = Payment.objects.filter(invoice=invoice)
        vat_transaction = get_object_or_404(VATTransaction, invoice=invoice)
        activity = ActivityLog.objects.filter(invoice=invoice)

        with transaction.atomic():
            if invoice.payment_status == Invoice.PaymentStatus.PARTIAL:
                customer_account_balance.balance -= invoice.amount_due

            account_types = {
                'cash': Account.AccountType.CASH,
                'bank': Account.AccountType.BANK,
                'ecocash': Account.AccountType.ECOCASH,
            }

            for payment in payments:
                account = get_object_or_404(
                    Account,
                    name=f"{request.user.branch} {invoice.currency.name} {payment.payment_method.capitalize()} Account",
                    type=account_types.get(payment.payment_method, None)
                )
                account_balance = get_object_or_404(AccountBalance, account=account, currency=invoice.currency, branch=request.user.branch)
                account_balance.balance -= payment.amount_paid
                account_balance.save()

            for stock_transaction in activity:
                product = Inventory.objects.get(id=stock_transaction.inventory.id, branch=request.user.branch)
                product.quantity += abs(stock_transaction.quantity)
                product.save()

                ActivityLog.objects.create(
                    invoice=invoice,
                    branch=request.user.branch,
                    user=request.user,
                    action='sale return',
                    inventory=product,
                    quantity=stock_transaction.quantity,
                    total_quantity=product.quantity
                )

            InvoiceItem.objects.filter(invoice=invoice).delete()
            StockTransaction.objects.filter(invoice=invoice).delete()
            payments.delete()
            customer_account_balance.save()
            sale.delete()
            vat_transaction.delete()
            invoice.cancelled = True
            invoice.save()

        return JsonResponse({'success': True, 'message': f'Invoice {invoice.invoice_number} successfully deleted'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"{e}"})

@login_required
def invoice_details(request, invoice_id):
    invoice = Invoice.objects.filter(id=invoice_id, branch=request.user.branch).values(
        'invoice_number',
        'customer__id',
        'customer__name',
        'products_purchased',
        'payment_status',
        'amount'
    )
    return JsonResponse(list(invoice), safe=False)

@login_required
def invoice_preview(request, invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    invoice_items = InvoiceItem.objects.filter(invoice=invoice)
    return render(request, 'Pos/printable_receipt.html', {'invoice_id':invoice_id, 'invoice':invoice, 'invoice_items':invoice_items})

@login_required
def remove_item(request, item_id):
    if request.method == 'DELETE':
        try:
            item = InvoiceItem.objects.get(id=item_id)
            item.delete()
            return JsonResponse({'success': True})
        except InvoiceItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)

@login_required
def replace_item(request, item_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        new_item_id = data.get('newItemId')

        try:
            item = InvoiceItem.objects.get(id=item_id)
            new_item = InvoiceItem.objects.get(id=new_item_id)

            item.name = new_item.name
            item.price = new_item.price
            item.quantity = new_item.quantity
            item.save()

            return JsonResponse({'success': True})
        except (InvoiceItem.DoesNotExist, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid item'}, status=404)

@login_required
def invoice_preview_data(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({"error": "Invoice not found"}, status=404)

    dates = {}
    if invoice.payment_terms == 'layby':
        dates = laybyDates.objects.filter(layby__invoice=invoice).values('due_date')

    invoice_items = InvoiceItem.objects.filter(invoice=invoice).values(
        'item__name', 'quantity', 'item__description', 'total_amount', 'unit_price'
    )

    invoice_dict = {}
    invoice_dict['customer_name'] = invoice.customer.name
    invoice_dict['customer_email'] = invoice.customer.email
    invoice_dict['customer_cell'] = invoice.customer.phone_number
    invoice_dict['customer_address'] = invoice.customer.address
    invoice_dict['currency_symbol'] = invoice.currency.symbol
    invoice_dict['amount_paid'] = invoice.amount_paid
    invoice_dict['payment_terms'] = invoice.payment_terms
    invoice_dict['amount'] = invoice.amount
    invoice_dict['invoice_number'] = invoice.invoice_number
    invoice_dict['receipt_hash'] = invoice.receipt_hash
    invoice_dict['subtotal'] = invoice.subtotal
    invoice_dict['vat'] = round(invoice.vat, 2)
    invoice_dict['device_id'] = os.getenv("DEVICE_ID")
    invoice_dict['device_serial_number'] = os.getenv("DEVICE_SERIAL_NUMBER")
    invoice_dict['code'] =  invoice.code
    invoice_dict['fiscal_day'] = invoice.fiscal_day

    if invoice.branch:
        invoice_dict['branch_name'] = invoice.branch.name
        invoice_dict['branch_phone'] = invoice.branch.phonenumber
        invoice_dict['branch_email'] = invoice.branch.email

    invoice_dict['user_username'] = invoice.user.username
    invoice_dict['receipt_signature'] = invoice.receiptServerSignature if invoice.receiptServerSignature else None

    if invoice.qr_code and hasattr(invoice.qr_code, 'url'):
        try:
            invoice_dict['qr_code'] = request.build_absolute_uri(invoice.qr_code.url)
        except Exception as e:
            invoice_dict['qr_code'] = None
    else:
        invoice_dict['qr_code'] = None

    invoice_data = {
        'invoice': invoice_dict,
        'invoice_items': list(invoice_items),
        'dates': list(dates)
    }
    return JsonResponse(invoice_data, safe=False)

def invoice_preview_json(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({"error": "Invoice not found"}, status=404)

    dates = {}
    if invoice.payment_terms == 'layby':
        dates = laybyDates.objects.filter(layby__invoice=invoice).values('due_date')

    invoice_items = InvoiceItem.objects.filter(invoice=invoice).values(
        'item__name', 'quantity', 'item__description', 'total_amount', 'unit_price'
    )

    invoice_dict = {}
    invoice_dict['customer_name'] = invoice.customer.name
    invoice_dict['customer_email'] = invoice.customer.email
    invoice_dict['customer_cell'] = invoice.customer.phone_number
    invoice_dict['customer_address'] = invoice.customer.address
    invoice_dict['currency_symbol'] = invoice.currency.symbol
    invoice_dict['amount_paid'] = invoice.amount_paid
    invoice_dict['payment_terms'] = invoice.payment_terms
    invoice_dict['amount'] = invoice.amount
    invoice_dict['invoice_number'] = invoice.invoice_number
    invoice_dict['receipt_hash'] = invoice.receipt_hash
    invoice_dict['subtotal'] = invoice.subtotal
    invoice_dict['vat'] = round(invoice.vat, 2)
    invoice_dict['device_id'] = os.getenv("DEVICE_ID")
    invoice_dict['device_serial_number'] = os.getenv("DEVICE_SERIAL_NUMBER")
    invoice_dict['code'] =  invoice.code
    invoice_dict['fiscal_day'] = invoice.fiscal_day

    if invoice.branch:
        invoice_dict['branch_name'] = invoice.branch.name
        invoice_dict['brach_address'] = invoice.branch.address
        invoice_dict['branch_phone'] = invoice.branch.phonenumber
        invoice_dict['branch_email'] = invoice.branch.email

    invoice_dict['user_username'] = invoice.user.username
    invoice_dict['receipt_signature'] = invoice.receiptServerSignature if invoice.receiptServerSignature else None

    if invoice.qr_code and hasattr(invoice.qr_code, 'url'):
        try:
            invoice_dict['qr_code'] = request.build_absolute_uri(invoice.qr_code.url)
        except Exception as e:
            invoice_dict['qr_code'] = None
    else:
        invoice_dict['qr_code'] = None

    invoice_data = {
        'invoice': invoice_dict,
        'invoice_items': list(invoice_items),
        'dates': list(dates)
    }
    return invoice_data

@login_required
def invoice_pdf(request):
    template_name = 'reports/invoice.html'
    invoice_id = request.GET.get('id', '')
    if invoice_id:
        try:
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            invoice_items = InvoiceItem.objects.filter(invoice=invoice)
        except Invoice.DoesNotExist:
            return HttpResponse("Invoice not found")
    else:
        return HttpResponse("Invoice ID is required")

    return generate_pdf(
        template_name,
        {
            'title': 'Invoice',
            'report_date': timezone.now().date(),
            'invoice':invoice,
            'invoice_items':invoice_items
        }
    )

@login_required
def send_invoice_email(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        invoice_id = data['invoice_id']
        invoice = Invoice.objects.get(id=invoice_id)
        invoice_items = InvoiceItem.objects.filter(invoice=invoice)
        account = CustomerAccount.objects.get(customer__id = invoice.customer.id)

        html_string = render_to_string('Pos/receipt.html', {'invoice': invoice, 'invoice_items':invoice_items, 'account':account})
        buffer = io.BytesIO()

        pisa.CreatePDF(html_string, dest=buffer)

        email = EmailMessage(
            'Your Invoice',
            'Please find your invoice attached.',
            'your_email@example.com',
            ['recipient_email@example.com'],
        )

        buffer.seek(0)
        email.attach(f'invoice_{invoice.invoice_number}.pdf', buffer.getvalue(), 'application/pdf')
        email.send()

        task = send_invoice_email_task.delay(data['invoice_id'])
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'

        return response
    return JsonResponse({'success': False, 'error':'error'})

@login_required
def send_invoice_whatsapp(request, invoice_id):
    try:
        invoice = Invoice.objects.get(pk=invoice_id)
        invoice_items = InvoiceItem.objects.filter(invoice=invoice)
        img = settings.STATIC_URL + "/assets/logo.png"

        html_string = render_to_string('Pos/invoice_template.html', {'invoice': invoice, 'request':request, 'invoice_items':invoice_items, 'img':img})
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)
        if not pisa_status.err:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            invoice_filename = f"invoice_{invoice.invoice_number}.pdf"
            s3.put_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=f"invoices/{invoice_filename}",
                Body=pdf_buffer.getvalue(),
                ContentType="application/pdf",
                ACL="public-read",
            )
            s3_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/invoices/{invoice_filename}"

            account_sid = 'AC6890aa7c095ce1315c4a3a86f13bb403'
            auth_token = '897e02139a624574c5bd175aa7aaf628'
            client = Client(account_sid, auth_token)
            from_whatsapp_number = 'whatsapp:' + '+14155238886'
            to_whatsapp_number = 'whatsapp:' + '+263778587612'

            message = client.messages.create(
                from_=from_whatsapp_number,
                body="Your invoice is attached.",
                to=to_whatsapp_number,
                media_url=s3_url
            )
            return JsonResponse({"success": True, "message_sid": message.sid})
        else:
            return JsonResponse({"error": "PDF generation failed"})
    except Invoice.DoesNotExist:
        return JsonResponse({"error": "Invoice not found"})
    except Exception as e:
        return JsonResponse({"error": "Error sending invoice via WhatsApp"})

@login_required
def invoice_payment_track(request):
    invoice_id = request.GET.get('invoice_id', '')

    if invoice_id:
        payments = Payment.objects.filter(invoice__id=invoice_id).order_by('-payment_date').values(
            'payment_date', 'amount_paid', 'payment_method', 'user__username'
        )
    return JsonResponse(list(payments), safe=False)
