from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.http import JsonResponse
from apps.finance.models import *
from apps.inventory.models import Inventory, ActivityLog, StocktakeItem
from loguru import logger
from apps.inventory.utils import process_stocktake_item_util


def invoice_preview_json(request, invoice_id):
    from django.core.serializers.json import DjangoJSONEncoder
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

    # serialize qr_code
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

def get_or_create_account(user, currency, payment_method):
    logger.info(f"Getting or creating account for user={user}, currency={currency}, payment_method={payment_method}")
    
    account_types = {
        'cash': Account.AccountType.CASH,
        'bank': Account.AccountType.BANK,
        'ecocash': Account.AccountType.ECOCASH,
    }
    account_name = f"{user.branch} {currency.name} {payment_method.capitalize()} Account"
    account, _ = Account.objects.get_or_create(name=account_name, type=account_types[payment_method])
    account_balance, _ = AccountBalance.objects.get_or_create(
        account=account,
        currency=currency,
        branch=user.branch,
        defaults={'balance': 0}
    )
    logger.info(f"Account: {account}, AccountBalance: {account_balance}")
    return account, account_balance

def handle_layby(invoice, layby_dates, amount_due, branch):
    logger.info(f"Handling layby for invoice={invoice.id}, amount_due={amount_due}, branch={branch}")
    layby_obj = layby.objects.create(invoice=invoice, branch=branch)
    layby_dates_list = []
    number_of_dates = len(layby_dates)
    amount_per_due_date = (amount_due / number_of_dates) if number_of_dates > 0 else 0
    for date in layby_dates:
        obj = laybyDates(
            layby=layby_obj,
            due_date=date,
            amount_due=round(amount_per_due_date, 2),
        )
        layby_dates_list.append(obj)
    laybyDates.objects.bulk_create(layby_dates_list)
    logger.info(f"Layby dates created: {layby_dates_list}")

def handle_paylater(invoice, amount_due, pay_later_dates, payment_method, branch):
    logger.info(f"Handling paylater for invoice={invoice.id}, amount_due={amount_due}, branch={branch}")
    paylater_obj = Paylater.objects.create(
        invoice=invoice,
        amount_due=amount_due,
        due_date=pay_later_dates[0] if pay_later_dates else timezone.now().date(),
        payment_method=payment_method,
        branch=branch
    )
    if pay_later_dates:
        amount_per_interval = round(amount_due / len(pay_later_dates), 2)
        for date in pay_later_dates:
            paylaterDates.objects.create(
                paylater=paylater_obj,
                due_date=date,
                amount_due=amount_per_interval,
                payment_method=payment_method
            )
    logger.info(f"Paylater object and dates created for invoice={invoice.id}")

def create_invoice_items(invoice, items_data, vat_rate, user, branch):
    logger.info(f"Creating invoice items for invoice={invoice.id}")
    invoice_items = []
    for item_data in items_data:
        logger.info(f"Processing item_data: {item_data}")
        item = Inventory.objects.get(pk=item_data['inventory_id'])
        item.quantity -= item_data['quantity']
        item.save()
        invoice_item = InvoiceItem.objects.create(
            invoice=invoice,
            item=item,
            quantity=item_data['quantity'],
            unit_price=item_data['price'],
            vat_rate=vat_rate,
            total_amount=int(item_data['quantity']) * float(item_data['price']),
            cash_up_status=False
        )
        invoice_items.append(invoice_item)
        ActivityLog.objects.create(
            branch=branch,
            inventory=item,
            user=user,
            quantity=-item_data['quantity'],
            total_quantity=item.quantity,
            action='Sale',
            invoice=invoice
        )
        logger.info(f"InvoiceItem and ActivityLog created for item={item.id}")
    return invoice_items

def update_stocktake_item(product_id, quantity):
    try:
        stocktake_item = StocktakeItem.objects.get(product_id=product_id, stocktake__status=False, still_open=True)
        stocktake_item.sold_quantity += quantity
        stocktake_item.save()

        logger.info(f"Processing stocktake item for product_id={product_id} with quantity={quantity}")
        
        process_stocktake_item_util(stocktake_item, stocktake_item.quantity)
        logger.info(f"Updated StocktakeItem for product_id={product_id} with quantity={quantity}")
    except StocktakeItem.DoesNotExist:
        logger.warning(f"No open StocktakeItem found for product_id={product_id}")
    

@transaction.atomic
def create_invoice_service(user, invoice_data, items_data, layby_dates=None, request=None):
    logger.info(f"Starting invoice creation for user={user}, invoice_data={invoice_data}")
    try:
        currency = Currency.objects.get(id=invoice_data['currency'])
        account, account_balance = get_or_create_account(user, currency, invoice_data['payment_method'])
        accounts_receivable, _ = ChartOfAccounts.objects.get_or_create(name="Accounts Receivable")
        vat_rate = VATRate.objects.get(status=True)
        customer = Customer.objects.get(id=int(invoice_data['client_id']))
        customer_account = CustomerAccount.objects.get(customer=customer)
        customer_account_balance, _ = CustomerAccountBalances.objects.get_or_create(
            account=customer_account,
            currency=currency,
            defaults={'balance': 0}
        )
        amount_paid = Decimal(invoice_data['amount_paid'])
        invoice_total_amount = Decimal(invoice_data['payable'])
        if amount_paid > invoice_total_amount:
            logger.warning(f"Amount paid ({amount_paid}) greater than invoice total ({invoice_total_amount}), adjusting.")
            amount_paid = invoice_total_amount
            amount_due = 0
        else:
            amount_due = invoice_total_amount - amount_paid

        invoice = Invoice.objects.create(
            invoice_number=Invoice.generate_invoice_number(user.branch.name),
            customer=customer,
            issue_date=timezone.now(),
            amount=invoice_total_amount,
            amount_paid=amount_paid,
            amount_due=amount_due,
            vat=Decimal(invoice_data['vat_amount']),
            payment_status=Invoice.PaymentStatus.PARTIAL if amount_due > 0 else Invoice.PaymentStatus.PAID,
            branch=user.branch,
            user=user,
            currency=currency,
            subtotal=invoice_data['subtotal'],
            reocurring=invoice_data['recourring'],
            payment_terms=invoice_data['paymentTerms'],
            hold_status=invoice_data['hold_status'],
            amount_received=amount_paid,
            products_purchased=''
        )
        logger.info(f"Invoice created: {invoice}")

        category = IncomeCategory.objects.filter(name='sales').first()
        Income.objects.create(
            amount=invoice.amount_paid,
            currency=invoice.currency,
            category=category,
            note=invoice.products_purchased,
            user=invoice.user,
            branch=invoice.branch,
            status=False,
        )
        logger.info(f"Income record created for invoice={invoice.id}")

        FinanceLog.objects.create(
            type='income',
            category='sales',
            amount=invoice.amount_paid,
            description=invoice.products_purchased
        )
        logger.info(f"FinanceLog created for invoice={invoice.id}")

        if invoice.hold_status:
            logger.info(f"Invoice {invoice.id} is on hold. Exiting early.")
            return {'hold': True, 'message': 'Invoice successfully on hold'}

        if invoice.payment_terms == 'layby' and amount_due > 0 and layby_dates:
            handle_layby(invoice, layby_dates, amount_due, user.branch)

        if invoice.payment_terms == 'installment' and invoice.reocurring:
            MonthlyInstallment.objects.create(invoice=invoice, status=False)
            logger.info(f"MonthlyInstallment created for invoice={invoice.id}")

        if invoice.payment_terms == 'pay later' and amount_due > 0:
            handle_paylater(invoice, amount_due, invoice_data.get('pay_later_dates', []), invoice_data['payment_method'], user.branch)
            
        for item_data in items_data:
            update_stocktake_item(item_data['inventory_id'], item_data['quantity'])

        Transaction.objects.create(
            date=timezone.now(),
            description=invoice.products_purchased,
            account=accounts_receivable,
            debit=Decimal(invoice_data['payable']),
            credit=Decimal('0.00'),
            customer=customer
        )
        logger.info(f"Transaction created for invoice={invoice.id}")

        invoice_items = create_invoice_items(invoice, items_data, vat_rate, user, user.branch)

        VATTransaction.objects.create(
            invoice=invoice,
            vat_type=VATTransaction.VATType.OUTPUT,
            vat_rate=vat_rate.rate,
            tax_amount=invoice_data['vat_amount']
        )
        logger.info(f"VATTransaction created for invoice={invoice.id}")

        Sale.objects.create(
            date=timezone.now(),
            transaction=invoice,
            total_amount=invoice_total_amount
        )
        logger.info(f"Sale record created for invoice={invoice.id}")

        Payment.objects.create(
            invoice=invoice,
            amount_paid=amount_paid,
            payment_method=invoice_data['payment_method'],
            amount_due=invoice_total_amount - amount_paid,
            user=user
        )
        logger.info(f"Payment record created for invoice={invoice.id}")

        if invoice.payment_status == 'Partial':
            customer_account_balance.balance += -amount_due
            customer_account_balance.save()
            logger.info(f"Customer account balance updated for partial payment, invoice={invoice.id}")

        account_balance.balance = Decimal(invoice_data['payable']) + Decimal(account_balance.balance)
        account_balance.save()
        logger.info(f"Account balance updated for invoice={invoice.id}")

        logger.info(f"Invoice creation completed successfully for invoice={invoice.id}")
        
        invoice_data = invoice_preview_json(request, invoice.id)
        
        return {'success': True, 'invoice_id': invoice.id, 'invoice_data':invoice_data}

    except Exception as e:
        logger.error(f'Error creating invoice: {e}', exc_info=True)
        raise 