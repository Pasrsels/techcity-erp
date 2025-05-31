from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from ..models import Cashbook, CashWithdrawals, CashTransfer
from ..forms import CashWithdrawForm, TransferForm, cashDepositForm
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from loguru import logger
import csv
from datetime import datetime, timedelta

@login_required
def cashbook_view(request):
    entries = Cashbook.objects.filter(branch=request.user.branch).order_by('-issue_date')
    return render(request, 'cashbook.html', {'entries': entries})

@login_required
def download_cashbook_report(request):
    filter_option = request.GET.get('filter', 'this_week')
    now = datetime.now()
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
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        start_date = now - timedelta(days=now.weekday())
        end_date = now

    entries = Cashbook.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date, branch=request.user.branch).order_by('issue_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cashbook_report_{filter_option}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Expenses', 'Income', 'Balance'])

    balance = 0
    for entry in entries:
        if entry.debit:
            balance += entry.amount
        elif entry.credit:
            balance -= entry.amount

        writer.writerow([
            entry.issue_date,
            entry.description,
            entry.amount if entry.debit else '',
            entry.amount if entry.credit else '',
            balance
        ])

    return response

@login_required
@transaction.atomic
def cash_transfer(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()
            return redirect('finance:cash_transfer_list')
    else:
        form = TransferForm()
    return render(request, 'cash_transfer.html', {'form': form})

@login_required
def cash_transfer_list(request):
    transfers = CashTransfer.objects.filter(branch=request.user.branch).order_by('-date')
    return render(request, 'cash_transfer_list.html', {'transfers': transfers})

@login_required
@transaction.atomic
def receive_money_transfer(request, transfer_id):
    transfer = get_object_or_404(CashTransfer, id=transfer_id)
    if request.method == 'POST':
        transfer.status = 'received'
        transfer.save()
        return redirect('finance:cash_transfer_list')
    return render(request, 'receive_transfer.html', {'transfer': transfer})

@login_required
def cashWithdrawals(request):
    form = CashWithdrawForm()
    withdrawals = CashWithdrawals.objects.filter(branch=request.user.branch).order_by('-date')
    return render(request, 'cash_withdrawals.html', {'form': form, 'withdrawals': withdrawals})

@login_required
@transaction.atomic
def cash_withdrawal_to_expense(request):
    if request.method == 'POST':
        form = CashWithdrawForm(request.POST)
        if form.is_valid():
            withdrawal = form.save(commit=False)
            withdrawal.user = request.user
            withdrawal.save()
            return redirect('finance:cash_withdrawals')
    return JsonResponse({'success': False})

@login_required
def delete_withdrawal(request, withdrawal_id):
    withdrawal = get_object_or_404(CashWithdrawals, id=withdrawal_id)
    withdrawal.delete()
    return redirect('finance:cash_withdrawals')

# API Views
class CashbookView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = Cashbook.objects.filter(branch=request.user.branch).order_by('-issue_date')
        data = [{
            'id': entry.id,
            'date': entry.issue_date,
            'description': entry.description,
            'amount': entry.amount,
            'type': 'debit' if entry.debit else 'credit'
        } for entry in entries]
        return JsonResponse(data, safe=False)

class CashTransfer(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = TransferForm(request.data)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.user = request.user
            transfer.save()
            return JsonResponse({'id': transfer.id}, status=201)
        return JsonResponse(form.errors, status=400)

class CashTransferList(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        transfers = CashTransfer.objects.filter(branch=request.user.branch).order_by('-date')
        data = [{
            'id': transfer.id,
            'amount': transfer.amount,
            'from_account': transfer.from_account.name,
            'to_account': transfer.to_account.name,
            'status': transfer.status,
            'date': transfer.date
        } for transfer in transfers]
        return JsonResponse(data, safe=False)

class ReceiveMoneyTransfer(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, transfer_id):
        transfer = get_object_or_404(CashTransfer, id=transfer_id)
        transfer.status = 'received'
        transfer.save()
        return JsonResponse({'success': True})

class CashWithdrawalsViewset(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        withdrawals = CashWithdrawals.objects.filter(branch=request.user.branch).order_by('-date')
        data = [{
            'id': withdrawal.id,
            'amount': withdrawal.amount,
            'description': withdrawal.description,
            'date': withdrawal.date
        } for withdrawal in withdrawals]
        return JsonResponse(data, safe=False) 