from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from ..models import Customer, CustomerAccount, CustomerDeposit
from ..forms import CustomerForm, customerDepositsForm, customerDepositsRefundForm
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from ..serializers import CustomerSerializer
from loguru import logger

@login_required
def customer(request):
    form = CustomerForm()
    return render(request, 'customer.html', {'form': form})

@login_required
def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'customer_list.html', {'customers': customers})

@login_required
def update_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('finance:customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'update_customer.html', {'form': form})

@login_required
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    customer.delete()
    return redirect('finance:customer_list')

@login_required
def customer_account(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    account = CustomerAccount.objects.filter(customer=customer)
    return render(request, 'customer_account.html', {'account': account, 'customer': customer})

@login_required
@transaction.atomic
def add_customer_deposit(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        form = customerDepositsForm(request.POST)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.customer = customer
            deposit.save()
            return redirect('finance:customer_account', customer_id=customer_id)
    else:
        form = customerDepositsForm()
    return render(request, 'add_deposit.html', {'form': form, 'customer': customer})

@login_required
def deposits_list(request):
    deposits = CustomerDeposit.objects.all()
    return render(request, 'deposits_list.html', {'deposits': deposits})

@login_required
@transaction.atomic
def refund_customer_deposit(request, deposit_id):
    deposit = get_object_or_404(CustomerDeposit, id=deposit_id)
    if request.method == 'POST':
        form = customerDepositsRefundForm(request.POST)
        if form.is_valid():
            refund = form.save(commit=False)
            refund.deposit = deposit
            refund.save()
            return redirect('finance:deposits_list')
    else:
        form = customerDepositsRefundForm()
    return render(request, 'refund_deposit.html', {'form': form, 'deposit': deposit})

# API Views
class CustomersViewset(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)

class AllCustomerAccounts(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = CustomerAccount.objects.all()
        data = [{
            'id': account.id,
            'customer': account.customer.name,
            'balance': account.balance,
            'currency': account.currency.symbol
        } for account in accounts]
        return JsonResponse(data, safe=False)

class CustomerAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, id=customer_id)
        accounts = CustomerAccount.objects.filter(customer=customer)
        data = [{
            'id': account.id,
            'balance': account.balance,
            'currency': account.currency.symbol
        } for account in accounts]
        return JsonResponse(data, safe=False)

class CustomerDepositsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        customer = get_object_or_404(Customer, id=id)
        deposits = CustomerDeposit.objects.filter(customer=customer)
        data = [{
            'id': deposit.id,
            'amount': deposit.amount,
            'date': deposit.date,
            'currency': deposit.currency.symbol
        } for deposit in deposits]
        return JsonResponse(data, safe=False) 