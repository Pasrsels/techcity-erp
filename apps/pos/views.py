import os, json
import datetime
from decimal import Decimal
from django.http import JsonResponse
from django.db import transaction
from apps.finance.forms import CashWithdrawForm
from django.utils import timezone
from apps.finance.models import Invoice
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from loguru import logger
from apps.settings.models import TaxSettings
from apps.inventory.models import ProductCategory, Inventory
from django.core.cache import cache
from django.conf import settings
from apps.finance.models import (
    Account, 
    AccountBalance, 
    ChartOfAccounts, 
    Customer, 
    CustomerAccount, 
    CustomerAccountBalances, 
    VATRate, 
    COGS, 
    COGSItems, 
    InvoiceItem, 
    VATTransaction, 
    Transaction, 
    Payment, 
    Sale, 
    layby, 
    laybyDates, 
    Paylater,
    paylaterDates,
    Currency
)
from apps.inventory.models import ActivityLog
from datetime import timedelta
from django.template.loader import render_to_string

@login_required
@transaction.atomic
def pos(request):
    form = CashWithdrawForm()
    invoice_count = Invoice.objects.filter(issue_date=timezone.now(), branch=request.user.branch).count()
    held_invoices_count = Invoice.objects.filter(hold_status=True, branch=request.user.branch).count()
            
    return render(request, 'pos.html', {
        'invoice_count':invoice_count, 
        'form':form, 
        'count':held_invoices_count,
    })
    
@login_required
def new_pos(request):
    cache_key = f'pos_data_{request.user.branch.id}'
    cached_data = cache.get(cache_key)
    tax_rate = VATRate.objects.get(status=True).rate
    
    if cached_data is None:
        product_categories = ProductCategory.objects.all().values('id', 'name')
        products = Inventory.objects.filter(branch=request.user.branch).select_related('product_category', 'branch').values(
            'id', 'name', 'category__name', 'quantity', 'price', 'dealer_price', 'image')
        
        cached_data = {
            'product_categories': list(product_categories),
            'products': list(products)
        }
        
        cache.set(cache_key, cached_data, settings.CACHE_TTL)
        
        logger.info("Data fetched from database and cached")
    else:
        logger.info("Data fetched from cache")
        product_categories = cached_data['product_categories']
        products = cached_data['products']
    
    return render(request, 'new_pos.html', 
        {
            'product_categories': product_categories, 
            'products': products,
            'tax_rate': tax_rate
        }
    )

@login_required
def paylaters(request):
    paylaters = Paylater.objects.all()
    paylaters_dates = paylaterDates.objects.all()
    
    html = render_to_string('partials/paylaters.html')
    
    return JsonResponse({'success':True, 'html':html})

@login_required
def laybyes(request):
    laybys= layby.objects.all()
    layby_dates = laybyDates.objects.all()
    
    html = render_to_string('partials/paylaters.html')
    
    return JsonResponse({'success':True, 'html':html})



@login_required
@transaction.atomic 
def create_invoice(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            invoice_data = data['data'][0]  
            items_data = data.get('cart')
            layby_data = data.get('layby_data')
            paylater_data = data.get('paylater_data')
            customer_id = data.get('customer_id')
            products_total = data.get('products_total')
            payment_method = data.get('payment_method')
            payment_amount = data.get('payment_amount')
            payment_notes = data.get('payment_notes')
            payment_subtotal = data.get('products_total')
            
            if not items_data:
                return JsonResponse({'success': False, 'error': 'No items in cart'})
            
            if layby_data:
                payment_terms = 'layby'
            elif paylater_data:
                payment_terms = 'pay later'
            else:
                payment_terms = payment_method
            
            # get currency
            currency = Currency.objects.get(id=invoice_data['currency'])
            
            # create or get accounts
            account_types = {
                'cash': Account.AccountType.CASH,
                'bank': Account.AccountType.BANK,
                'ecocash': Account.AccountType.ECOCASH,
            }

            account_name = f"{request.user.branch} {currency.name} {payment_method.capitalize()} Account"
            
            account, _ = Account.objects.get_or_create(name=account_name, type=account_types[payment_method])
            
            account_balance, _ = AccountBalance.objects.get_or_create(
                account=account,
                currency=currency,
                branch=request.user.branch,
                defaults={'balance': 0}  
            )

            logger.info(f"Account Balance: {account_balance}")

            # accounts_receivable
            accounts_receivable, _ = ChartOfAccounts.objects.get_or_create(name="Accounts Receivable")
            
            # VAT rate
            vat_rate = VATRate.objects.get(status=True)

            # customer
            customer = Customer.objects.get(id=customer_id) 
            
            # customer account
            customer_account = CustomerAccount.objects.get(customer=customer)

            # customer Account + Balances
            customer_account_balance, _ = CustomerAccountBalances.objects.get_or_create(
                account=customer_account,
                currency=currency, 
                defaults={'balance': 0}
            )
            
            # amount_paid = update_latest_due(customer, Decimal(invoice_data['amount_paid']), request, invoice_data['paymentTerms'], customer_account_balance)
            payment_amount = Decimal(payment_amount)
            
            logger.info(f'Amount paid: {payment_amount}')

            products_total = Decimal(products_total)

            # prevent to record greater amount paid than the invoice amount 
            if payment_amount > products_total:
                payment_amount = products_total
            else:
                payment_amount = payment_amount

            amount_due = products_total - payment_amount  

            cogs = COGS.objects.create(amount=Decimal(0))
            
            products_purchased = f"""{', '.join([f'{item['product_name']} x {item['quantity']} ' for item in items_data])}"""
            
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    customer=customer,
                    issue_date=timezone.now(),
                    amount=products_total,
                    amount_paid=payment_amount,
                    amount_due=amount_due,
                    vat=Decimal(invoice_data['vat_amount']),
                    payment_status = Invoice.PaymentStatus.PARTIAL if amount_due > 0 else Invoice.PaymentStatus.PAID,
                    branch = request.user.branch,
                    user=request.user,
                    currency=currency,
                    subtotal=payment_subtotal,
                    reocurring = False,
                    products_purchased = products_purchased,
                    payment_terms = payment_terms,
                    hold_status = invoice_data['hold_status'],
                    amount_received = payment_amount
                )

                logger.info(f'Invoice created for customer: {invoice}')

                # create paylater object
                if payment_terms == 'pay later':
                    if amount_due > 0:
                        paylater_obj = Paylater.objects.create(
                            invoice=invoice,
                            amount_due=amount_due,
                            due_date=paylater_data['startDate'],
                            payment_method=payment_method
                        )

                # create layby object
                if payment_terms == 'layby':
                    if amount_due > 0:
                        layby_obj = layby.objects.create(
                            invoice=invoice,
                            branch=request.user.branch,
                            amount_paid=layby_data['deposit'],
                            amount_due= products_total - layby_data['deposit'],
                            due_date=layby_data['startDate'],
                            payment_method=payment_method
                        )
                        
                        for date in range(paylater_data['interval'], 1):
                            due_date = paylater_data['startDate'] + timedelta(days=date)                            
                            laybyDates.objects.create(
                                layby=layby_obj,
                                due_date=due_date,
                                amount_due= round((products_total - layby_data['deposit']) / paylater_data['interval'], 2)
                            )
                    
                # #create transaction
                Transaction.objects.create(
                    date=timezone.now(),
                    description=invoice.products_purchased,
                    account=accounts_receivable,
                    debit=Decimal(invoice_data['payable']),
                    credit=Decimal('0.00'),
                    customer=customer
                )

                logger.info(f'Creating transaction obj for invoice: {invoice}')
            
                # Create InvoiceItem objects
                invoice_items = []
                for item_data in items_data:
                    item = Inventory.objects.get(pk=item_data['inventory_id'])
                    
                    item.quantity -= item_data['quantity']
                    item.save()

                    invoice_items.append(
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            item=item,
                            quantity=item_data['quantity'],
                            unit_price=item_data['price'],
                            vat_rate = vat_rate,
                            vat_amount = Decimal(item_data['vat_amount']),
                            total_amount = int(item_data['quantity']) * float(item_data['price']),
                            cash_up_status = False
                        )
                    )
                
                    # stock log  
                    ActivityLog.objects.create(
                        branch=request.user.branch,
                        inventory=item,
                        user=request.user,
                        quantity = -item_data['quantity'],
                        total_quantity = item.quantity,
                        action='Sale',
                        invoice=invoice
                    )
                        
                # Create VATTransaction
                VATTransaction.objects.create(
                    invoice=invoice,
                    vat_type=VATTransaction.VATType.OUTPUT,
                    vat_rate=VATRate.objects.get(status=True).rate,
                    tax_amount=invoice_data['vat_amount']
                )                                                          
                # Create Sale object
                sale = Sale.objects.create(
                    date=timezone.now(),
                    transaction=invoice,
                    total_amount=products_total
                )
                sale.save()
                
                #payment
                Payment.objects.create(
                    invoice=invoice,
                    amount_paid=payment_amount,
                    payment_method=payment_method,
                    amount_due=products_total - payment_amount,
                    user=request.user
                )
                
                # for tax purpose Zimra
                logger.info(invoice_items)

                try:
                    # sig_data, receipt_data = generate_receipt_data(invoice, invoice_items, request)
                    # logger.info(sig_data)
                    # hash_sig_data = run(sig_data)
                    
                    # logger.info(hash_sig_data)
                    # submit_receipt_data(request, receipt_data, hash_sig_data['hash'], hash_sig_data['signature'])
                    
                    invoice_data = invoice_preview_json(request, invoice.id)
                    logger.info(invoice_data)

                except Exception as e:
                    logger.info(e)
                    return JsonResponse({'success': False, 'error': str(e)})

                logger.info(f'inventory creation successfully done: {invoice}')

                return JsonResponse({'success':True, 'invoice_id': invoice.id, 'invoice_data':invoice_data})

        # except (KeyError, json.JSONDecodeError, Customer.DoesNotExist, Inventory.DoesNotExist, Exception) as e:
        #     return JsonResponse({'success': False, 'error': str(e)})
        except Exception as e:
            logger.info(e)

    return render(request, 'invoices/add_invoice.html')

    
@login_required
def last_due_invoice(request, customer_id):
    invoice = Invoice.objects.filter(customer__id=customer_id, payment_status=Invoice.PaymentStatus.PARTIAL)\
            .order_by('-issue_date').values('invoice_number')
    logger.info(invoice)
    return JsonResponse(list(invoice), safe=False)

def invoice_preview_json(request, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({"error": "Invoice not found"}, status=404)

    dates = {}
    if invoice.payment_terms == 'layby':
        dates = laybyDates.objects.filter(layby__invoice=invoice).values('due_date')

    invoice_items = InvoiceItem.objects.filter(invoice=invoice).values(
        'item__name',
        'quantity',
        'item__description',
        'total_amount',
        'unit_price'
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

    # Safely serialize qr_code
    if invoice.qr_code and hasattr(invoice.qr_code, 'url'):
        try:
            invoice_dict['qr_code'] = request.build_absolute_uri(invoice.qr_code.url)
            logger.info(invoice_dict['qr_code'])
        except Exception as e:
            invoice_dict['qr_code'] = None
            logger.info(f"Error generating QR code URL: {e}")
    else:
        invoice_dict['qr_code'] = None

    invoice_data = {
        'invoice': invoice_dict,
        'invoice_items': list(invoice_items),
        'dates': list(dates)
    }
    return invoice_data


#API EndPoint
################################################################################################################
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class POS(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        invoice_count = Invoice.objects.filter(issue_date=timezone.now(), branch=request.user.branch).count()
        held_invoices_count = Invoice.objects.filter(hold_status=True, branch=request.user.branch).count()
        data = {
            'invoice count': invoice_count,
            'held invoice count': held_invoices_count
        }        
        return Response(data, status= status.HTTP_200_OK)

class LastDueInvoice(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, customer_id):
        invoice = Invoice.objects.filter(customer__id=customer_id, payment_status=Invoice.PaymentStatus.PARTIAL)\
        .order_by('-issue_date').values('invoice_number')
        logger.info(invoice)
        return Response(invoice, status= status.HTTP_200_OK)