from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from ..models import CashTransfers, Account, AccountBalance, Cashbook
from ..forms import TransferForm
from django.db.models import Q

@login_required
@transaction.atomic
def cash_transfer(request):
    form = TransferForm()
    transfers = CashTransfers.objects.filter(branch=request.user.branch).select_related(
        'user',
        'currency',
        'to',
        'branch',
        'from_branch'
    )

    account_types = {
        'cash': Account.AccountType.CASH,
        'bank': Account.AccountType.BANK,
        'ecocash': Account.AccountType.ECOCASH,
    }

    if request.method == 'POST':
        form = TransferForm(request.POST)

        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.notification_type = 'Expense'
            transfer.from_branch = request.user.branch
            transfer.branch = request.user.branch
            transfer.received_status = False

            account_name = f"{request.user.branch} {transfer.currency.name} {transfer.transfer_method.capitalize()} Account"

            with transaction.atomic():
                try:
                    account = Account.objects.get(name=account_name, type=account_types[transfer.transfer_method.lower()])
                    account_balance = AccountBalance.objects.select_for_update().get(
                        account=account,
                        currency=transfer.currency,
                        branch=request.user.branch
                    )

                    if account_balance.balance < transfer.amount:
                        messages.error(request, "Insufficient funds in the account.")
                        return redirect('finance:cash_transfer')

                    account_balance.balance -= transfer.amount
                    account_balance.save()
                    transfer.save()

                    Cashbook.objects.create(
                        issue_date=transfer.date,
                        description=f'Cash Transfer to {transfer.to.name}',
                        debit=False,
                        credit=True,
                        amount=transfer.amount,
                        currency=transfer.currency,
                        branch=transfer.branch
                    )

                    messages.success(request, 'Money successfully transferred.')
                    return redirect('finance:cash_transfer')

                except Exception as e:
                    messages.error(request, f"{e}")
                return redirect('finance:cash_transfer')
        else:
            messages.error(request, "Invalid form data. Please correct the errors.")
    return render(request, 'transfers/cash_transfers.html', {'form': form, 'transfers':transfers})

@login_required
@transaction.atomic
def cash_transfer_list(request):
    search_query = request.GET.get('q', '')
    transfers = CashTransfers.objects.filter(to=request.user.branch.id)

    if search_query:
        transfers = transfers.filter(Q(date__icontains=search_query))

    return render(request, 'transfers/cash_transfers_list.html', {'transfers':transfers, 'search_query':search_query})

@login_required
@transaction.atomic
def receive_money_transfer(request, transfer_id):
    if transfer_id:
        transfer = get_object_or_404(CashTransfers, id=transfer_id)
        account_types = {
            'cash': Account.AccountType.CASH,
            'bank': Account.AccountType.BANK,
            'ecocash': Account.AccountType.ECOCASH,
        }

        account_name = f"{request.user.branch} {transfer.currency.name} {transfer.transfer_method.capitalize()} Account"

        with transaction.atomic():
            try:
                account, _ = Account.objects.get_or_create(name=account_name, type=account_types[transfer.transfer_method.lower()])

                account_balance, _ = AccountBalance.objects.get_or_create(
                    account=account,
                    currency=transfer.currency,
                    branch=request.user.branch
                )

                Cashbook.objects.create(
                    issue_date=transfer.date,
                    description=f'Cash Transfer from {transfer.from_branch.name}',
                    debit=True,
                    credit=False,
                    amount=transfer.amount,
                    currency=transfer.currency,
                    branch=transfer.to
                )

                account_balance.balance += transfer.amount
                account_balance.save()

                transfer.received_status = True
                transfer.save()

                return JsonResponse({'message':True})

            except Exception as e:
                return JsonResponse({'success':False, 'message':f"{e}"})
    return JsonResponse({'message':"Transfer ID is needed"})

@login_required
def create_transfer(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.from_branch = request.user.branch
            transfer.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})
