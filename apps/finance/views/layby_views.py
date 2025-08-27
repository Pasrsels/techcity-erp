from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from ..models import layby, laybyDates, Invoice, Payment, CustomerAccount, CustomerAccountBalances, Account, AccountBalance, Cashbook
from decimal import Decimal
import json
from django.utils import timezone

@login_required
def laybys(request):
    laybys = layby.objects.all().select_related('invoice').order_by('-date')
    return JsonResponse({'laybys': list(laybys.values())})

@login_required
def layby_data(request):
    if request.method == 'GET':
        layby_data = layby.objects.all().select_related(
            'invoice',
            'branch'
        ).values()
        return JsonResponse(list(layby_data), safe=False)

    if request.method == 'POST':
        data = json.loads(request.body)
        invoice_id = data.get('invoice_id')
        if not invoice_id:
            return JsonResponse({'success': False, 'message': 'Invoice ID is required.'})
        laby_dates = laybyDates.objects.filter(layby__invoice__id=invoice_id).values()
        return JsonResponse({'success': True, 'data': list(laby_dates)})

@login_required
@transaction.atomic
def layby_payment(request, layby_date_id):
    try:
        data = json.loads(request.body)
        amount_paid = Decimal(data.get('amount_paid'))
        payment_method = data.get('payment_method')

        layby_date = laybyDates.objects.get(id=layby_date_id)
        layby_obj = layby.objects.get(id=layby_date.layby.id)
        invoice = layby_obj.invoice

        account = CustomerAccount.objects.get(customer=invoice.customer)
        customer_account_balance = CustomerAccountBalances.objects.get(account=account, currency=invoice.currency)

        account_types = {
            'cash': Account.AccountType.CASH,
            'bank': Account.AccountType.BANK,
            'ecocash': Account.AccountType.ECOCASH,
        }

        customer_account_balance.balance -= amount_paid

        account_name = f"{request.user.branch} {invoice.currency.name} {'cash'.capitalize()} Account"
        account = Account.objects.get(name=account_name, type=account_types['cash'])
        account_balance = AccountBalance.objects.get(account=account, currency=invoice.currency, branch=request.user.branch)

        account_balance.balance -= amount_paid

        amount_due = layby_date.amount_due

        with transaction.atomic():
            account_balance.save()
            customer_account_balance.save()

            Payment.objects.create(
                invoice=invoice,
                amount_paid=amount_paid,
                amount_due=amount_due,
                payment_method=payment_method,
                user=request.user
            )

            Cashbook.objects.create(
                issue_date=timezone.now(),
                description=f'Layby payment ({layby_date.layby.invoice.invoice_number})',
                debit=False,
                credit=True,
                amount=amount_paid,
                currency=layby_date.layby.invoice.currency,
                branch=request.user.branch
            )

            if amount_paid >= amount_due:
                layby_date.paid = True
                layby_date.save()
                layby_obj.fully_paid = True
                layby_obj.save()
                invoice.payment_status = Invoice.PaymentStatus.PAID
                invoice.save()
                layby_obj.check_payment_status()
                return JsonResponse({'success': True, 'message': 'Layby payment successfully completed.'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid amount paid.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'{e}'})
