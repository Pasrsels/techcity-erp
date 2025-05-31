from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from ..models import Expense, ExpenseCategory, Account, AccountBalance, Cashbook
from ..forms import ExpenseForm, ExpenseCategoryForm
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from loguru import logger
from ..tasks import send_expense_creation_notification
from utils.account_name_identifier import account_identifier
from decimal import Decimal

@login_required
def expenses(request):
    form = ExpenseForm()
    cat_form = ExpenseCategoryForm()
    expenses = Expense.objects.filter(user=request.user).order_by('-issue_date')
    return render(request, 'expenses.html', {
        'form': form,
        'cat_form': cat_form,
        'expenses': expenses
    })

@login_required
@transaction.atomic
def add_expense_category(request):
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            return JsonResponse({'success': True, 'id': category.id})
    return JsonResponse({'success': False})

@login_required
def get_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    data = {
        'id': expense.id,
        'amount': expense.amount,
        'description': expense.description,
        'category': expense.category.id
    }
    return JsonResponse({'success': True, 'data': data})

@login_required
@transaction.atomic
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    return JsonResponse({'success': True})

@login_required
def update_expense_status(request):
    expense_id = request.POST.get('expense_id')
    status = request.POST.get('status')
    expense = get_object_or_404(Expense, id=expense_id)
    expense.status = status
    expense.save()
    return JsonResponse({'success': True})

# API Views
class ExpenseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expenses = Expense.objects.filter(user=request.user)
        data = [{
            'id': expense.id,
            'amount': expense.amount,
            'description': expense.description,
            'category': expense.category.name,
            'date': expense.issue_date
        } for expense in expenses]
        return JsonResponse(data, safe=False)

class ExpenseDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        data = {
            'id': expense.id,
            'amount': expense.amount,
            'description': expense.description,
            'category': expense.category.name,
            'date': expense.issue_date
        }
        return JsonResponse(data)

class AddExpenseCategory(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = ExpenseCategoryForm(request.data)
        if form.is_valid():
            category = form.save()
            return JsonResponse({'id': category.id}, status=201)
        return JsonResponse(form.errors, status=400)

class EditExpense(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        expense = get_object_or_404(Expense, id=id)
        form = ExpenseForm(request.data, instance=expense)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse(form.errors, status=400)

class DeleteExpense(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, expense_id):
        expense = get_object_or_404(Expense, id=expense_id)
        expense.delete()
        return JsonResponse({'success': True})

class UpdateExpenseStatus(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        expense = get_object_or_404(Expense, id=id)
        status = request.data.get('status')
        if status:
            expense.status = status
            expense.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False}, status=400) 