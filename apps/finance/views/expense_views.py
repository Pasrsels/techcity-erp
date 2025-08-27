import csv, json
from ..models import *
from decimal import Decimal
from io import BytesIO
from apps.core.users.models import User
from apps.core.company.models import Branch
from xhtml2pdf import pisa
from django.views import View
from django.db.models import Q
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from utils.utils import generate_pdf
from django.http import JsonResponse
from apps.inventory.models import Inventory
import json, datetime, os, boto3, openpyxl
from utils.account_name_identifier import account_identifier
from ..tasks import send_expense_creation_notification
from pytz import timezone as pytz_timezone
from openpyxl.styles import Alignment, Font
from ..utils import calculate_expenses_totals
from django.utils.dateparse import parse_date
from django.db.models import Sum, DecimalField
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMessage
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from ..forms import (
    ExpenseForm,
    ExpenseCategoryForm,
)
from django.contrib.auth import authenticate
from loguru import logger
from django.core.paginator import Paginator, EmptyPage
import imghdr, base64
from django.core.files.base import ContentFile
import uuid

def decode_base64_file(data):
    if not data:
        return None
    try:
        format, imgstr = data.split(';base64,')
        ext = format.split('/')[-1]
        if ext == 'jpeg':
            ext = 'jpg'
        file_name = f"{uuid.uuid4()}.{ext}"
        return ContentFile(base64.b64decode(imgstr), name=file_name)
    except Exception as e:
        logger.error("Failed to decode base64 image:")
        return None

@login_required
def expenses(request):
    form = ExpenseForm()
    cat_form = ExpenseCategoryForm()

    if request.method == 'GET':
        filter_option = request.GET.get('filter', 'today')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        expenses = Expense.objects.filter(user=request.user).order_by('-issue_date')

        if request.user.role == 'sale':
            expenses = expenses.filter(user=request.user)

        return render(request, 'expenses.html',
            {
                'form':form,
                'cat_form':cat_form,
                'expenses':expenses,
                'filter_option': filter_option,
            }
        )
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            amount = data.get('amount')
            category = data.get('category')
            payment_method = data.get('payment_method', 'cash')
            currency_id = data.get('currency', 'USD')
            branch = request.user.branch.id
            base64_image = data.get('receipt')
            image = decode_base64_file(base64_image)
            is_recurring = data.get('is_recurring') == 'true'
            recurrence_value = data.get('recurrence_value')
            recurrence_unit = data.get('recurrence_unit')

            if not all([name, amount, category, payment_method, currency_id, branch]):
                return JsonResponse({'success': False, 'message': 'Missing required fields.'})

            try:
                category = ExpenseCategory.objects.get(id=category)
            except ExpenseCategory.DoesNotExist:
                return JsonResponse({'success': False, 'message': f'Category with ID {category} does not exist.'})

            currency = get_object_or_404(Currency, name__icontains='usd')
            branch = get_object_or_404(Branch, id=branch)

            account_details = account_identifier(request, currency, payment_method)
            account_name = account_details['account_name']
            account_type = account_details['account_type']

            account, _ = Account.objects.get_or_create(
                name=account_name,
                type=account_type
            )

            account_balance, _ = AccountBalance.objects.get_or_create(
                account=account,
                currency=currency,
                defaults={'currency': currency, 'branch': branch, 'balance': 0}
            )

            if account_balance.balance < Decimal(amount):
                return JsonResponse({'success': False, 'message': f'{account_name} has insufficient balance.'})

            account_balance.balance -= Decimal(amount)
            account_balance.save()

            expense = Expense.objects.create(
                description=name,
                amount=amount,
                category=category,
                user=request.user,
                currency=currency,
                payment_method=payment_method ,
                branch=branch,
                is_recurring=is_recurring,
                recurrence_value=int(recurrence_value) if is_recurring and recurrence_value else None,
                recurrence_unit=recurrence_unit if is_recurring else None,
                receipt=image,
            )

            Cashbook.objects.create(
                amount=amount,
                expense=expense,
                currency=currency,
                credit=True,
                description=f'Expense ({expense.description[:20]})',
                branch=branch
            )
            return JsonResponse({'success': True, 'message': 'Expense recorded successfully.'})
        except Exception as e:
            logger.exception("Error while recording expense:")
            return JsonResponse({'success': False, 'message': str(e)})

@login_required
def get_expenses(request):
    try:
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))
        expenses = Expense.objects.select_related('category', 'branch', 'currency').order_by('-issue_date')
        paginator = Paginator(expenses, limit)
        try:
            paginated_expenses = paginator.page(page)
        except EmptyPage:
            return JsonResponse({'data': [], 'has_next': False})
        results = []
        for expense in paginated_expenses:
            results.append({
                'id': expense.id,
                'created_at': expense.issue_date.isoformat(),
                'note': expense.description,
                'amount': float(expense.amount),
                'category': str(expense.category),
                'branch': expense.branch.name,
                'has_receipt': bool(expense.receipt),
                'receipt_url': expense.receipt.url if expense.receipt else None
            })
        return JsonResponse({'data': results, 'has_next': paginated_expenses.has_next()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def save_expense_split(request):
    try:
        data = json.loads(request.body)
        splits = data.get('splits')
        branch_id = data.get('branch_id')
        expense_id = data.get('expense_id', '')
        today = timezone.now().date()
        cash_up = CashUp.objects.filter(date=today, branch__id=int(branch_id)).first()
        if not cash_up:
            return JsonResponse({'success': False, 'message': 'No cash up record found for today'}, status=404)
        cash_up_expenses = cash_up.expenses.all()
        if expense_id:
            record_expense(expense_id,cash_up_expenses, request)
        else:
            categories = ExpenseCategory.objects.all()
            for split in splits:
                exp_obj = cash_up_expenses.get(id=int(split['expense_id']))
                new_expense = Expense(
                    amount=split['amount'],
                    payment_method=exp_obj.payment_method,
                    currency=exp_obj.currency,
                    category=categories.filter(id=split['category_id']).first(),
                    description=exp_obj.description,
                    user=request.user,
                    branch_id=request.user.branch.id,
                    status=False,
                    receipt=exp_obj.receipt,
                    is_recurring=exp_obj.is_recurring,
                    recurrence_value= exp_obj.recurrence_value if exp_obj.recurrence_value else None,
                    recurrence_unit= exp_obj.recurrence_unit if exp_obj.recurrence_unit else None
                )
                exp_obj.cash_up_status = True
                exp_obj.save()
                new_expense.save()
        return JsonResponse({'success': True, 'message': 'Expenses split and saved successfully'})
    except Exception as e:
        logger.exception("Error in save_expense_split")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

def record_expense(expense_id, cash_up_expenses, request):
    exp_obj = cash_up_expenses.get(id=int(expense_id))
    new_expense = Expense(
        amount=exp_obj.amount,
        payment_method=exp_obj.payment_method,
        currency=exp_obj.currency,
        category=exp_obj.category,
        description=exp_obj.description,
        user=request.user,
        branch_id=request.user.branch.id,
        status=False,
        purchase_order=exp_obj.purchase_order,
        receipt=exp_obj.receipt,
        is_recurring=exp_obj.is_recurring,
        recurrence_value= exp_obj.recurrence_value if exp_obj.recurrence_value else None,
        recurrence_unit= exp_obj.recurrence_unit if exp_obj.recurrence_unit else None
    )
    exp_obj.cash_up_status = True
    exp_obj.save()
    new_expense.save()

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
def add_or_edit_expense(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            description = data.get('description')
            category_id = data.get('category')
            expense_id = data.get('id')
            if not amount or not description or not category_id:
                return JsonResponse({'success': False, 'message': 'Missing fields: amount, description, category.'})
            category = get_object_or_404(ExpenseCategory, id=category_id)
            if expense_id:
                expense = get_object_or_404(Expense, id=expense_id)
                before_amount = expense.amount
                expense.amount = amount
                expense.description = description
                expense.category = category
                expense.save()
                message = 'Expense successfully updated'
                try:
                    cashbook_expense = Cashbook.objects.get(expense=expense)
                    expense_amount = Decimal(expense.amount)
                    if cashbook_expense.amount < expense_amount:
                        cashbook_expense.amount = expense_amount
                        cashbook_expense.description = cashbook_expense.description + f'Expense (update from {before_amount} to {cashbook_expense.amount})'
                    else:
                        cashbook_expense.amount -= cashbook_expense.amount - expense_amount
                        cashbook_expense.description = cashbook_expense.description + f'(update from {before_amount} to {cashbook_expense.amount})'
                    cashbook_expense.save()
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)
            return JsonResponse({'success': True, 'message': message}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@login_required
def add_expense_category(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        category_name = data.get('name', '')
        parent_name = data.get('parent', '')
        new_parent_name = data.get('new_parent', '')
        if not category_name:
            return JsonResponse({'success': False, 'message': 'Category name is required.'}, status=400)
        parent_obj = None
        if new_parent_name:
            parent_obj, _ = ExpenseCategory.objects.get_or_create(name=new_parent_name, parent=None)
        elif parent_name:
            parent_obj = ExpenseCategory.objects.filter(name=parent_name, parent=None).first()
            if not parent_obj:
                return JsonResponse({'success': False, 'message': f'Parent category "{parent_name}" not found.'}, status=404)
        if ExpenseCategory.objects.filter(name=category_name, parent=parent_obj).exists():
            return JsonResponse({'success': False, 'message': f'Category "{category_name}" already exists under this parent.'}, status=400)
        new_category = ExpenseCategory.objects.create(name=category_name, parent=parent_obj)
        return JsonResponse({'success': True, 'id': new_category.id, 'name': new_category.name}, status=201)
    subcategories = ExpenseCategory.objects.filter(parent__isnull=False).values('id', 'name')
    return JsonResponse({'subcategories': list(subcategories)})

def filter_expenses(queryset, filter_option, start_date=None, end_date=None):
    today = timezone.localtime().date()
    if filter_option == 'today':
        return queryset.filter(date=today)
    elif filter_option == 'yesterday':
        yesterday = today - timedelta(days=1)
        return queryset.filter(date=yesterday)
    elif filter_option == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return queryset.filter(date__gte=start_of_week, date__lte=end_of_week)
    elif filter_option == 'last_week':
        end_of_last_week = today - timedelta(days=today.weekday() + 1)
        start_of_last_week = end_of_last_week - timedelta(days=6)
        return queryset.filter(date__gte=start_of_last_week, date__lte=end_of_last_week)
    elif filter_option == 'this_month':
        return queryset.filter(date__year=today.year, date__month=today.month)
    elif filter_option == 'last_month':
        last_month = today.replace(day=1) - timedelta(days=1)
        return queryset.filter(date__year=last_month.year, date__month=last_month.month)
    elif filter_option == 'this_year':
        return queryset.filter(date__year=today.year)
    elif filter_option == 'last_year':
        return queryset.filter(date__year=today.year - 1)
    elif filter_option == 'custom' and start_date and end_date:
        try:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            return queryset.filter(date__gte=start_date, date__lte=end_date)
        except (ValueError, TypeError):
            return queryset
    return queryset

@login_required
@transaction.atomic
def delete_expense(request, expense_id):
    if request.method == 'DELETE':
        try:
            expense = get_object_or_404(Expense, id=expense_id)
            expense.cancel = True
            expense.save()
            Cashbook.objects.create(
                amount=expense.amount,
                debit=True,
                credit=False,
                description=f'Expense ({expense.description}): cancelled'
            )
            return JsonResponse({'success': True, 'message': 'Expense successfully deleted'})
        except Exception as e:
             return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@login_required
def update_expense_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            expense_id = data.get('id')
            status = data.get('status')
            expense = Expense.objects.get(id=expense_id)
            expense.status = status
            expense.save()
            return JsonResponse({'success': True, 'message': 'Status updated successfully.'})
        except Expense.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Expense not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def expenses_report(request):
    template_name = 'reports/expenses.html'
    search = request.GET.get('search', '')
    start_date_str = request.GET.get('startDate', '')
    end_date_str = request.GET.get('endDate', '')
    category_id = request.GET.get('category', '')
    if start_date_str and end_date_str:
        try:
            end_date = datetime.date.fromisoformat(end_date_str)
            start_date = datetime.date.fromisoformat(start_date_str)
        except ValueError:
            return JsonResponse({'messgae':'Invalid date format. Please use YYYY-MM-DD.'})
    else:
        start_date = ''
        end_date= ''
    try:
        category_id = int(category_id) if category_id else None
    except ValueError:
        return JsonResponse({'messgae':'Invalid category or search ID.'})
    expenses = Expense.objects.all()
    if search:
        expenses = expenses.filter(Q('amount=search'))
    if start_date:
        start_date = parse_date(start_date_str)
        expenses = expenses.filter(date__gte=start_date)
    if end_date:
        end_date = parse_date(end_date_str)
        expenses = expenses.filter(date__lte=end_date)
    if category_id:
        expenses = expenses.filter(category__id=category_id)
    return generate_pdf(
        template_name,
        {
            'title': 'Expenses',
            'date_range': f"{start_date} to {end_date}",
            'report_date': datetime.date.today(),
            'total_expenses':calculate_expenses_totals(expenses),
            'expenses':expenses
        }
    )

@login_required
@transaction.atomic
def cash_withdrawal_to_expense(request):
    if request.method == 'GET':
        cwte_id = request.GET.get('id', '')
        withdrawals = CashWithdraw.objects.filter(id=cwte_id).values(
            'user__branch__name', 'amount', 'reason', 'currency__id', 'user__id'
        )
        return JsonResponse(list(withdrawals), safe=False)
    if request.method == 'POST':
        data = json.loads(request.body)
        withdrawal_data = data['withdrawal'][0]
        reason = data['reason']
        category_id = data['category_id']
        withdrawal_id = data['withdrawal_id']
        currency_id = withdrawal_data['currency__id']
        branch_name = withdrawal_data['user__branch__name']
        amount = withdrawal_data['amount']
        try:
            currency = Currency.objects.get(id=currency_id)
            branch = Branch.objects.get(name=branch_name)
            withdrawal = CashWithdraw.objects.get(id=withdrawal_id)
            category = ExpenseCategory.objects.get(id=category_id)
        except:
            return JsonResponse({'success':False,'message':'Invalid form data here'})
        Expense.objects.create(
            category=category,
            amount=amount,
            branch=branch,
            user = request.user,
            currency = currency,
            description=f'Cash withdrawal: {reason}',
            status=True,
            issue_date=withdrawal.date,
            payment_method='cash'
        )
        withdrawal.status=True
        withdrawal.save()
        return JsonResponse({'success':True, 'message':'Successfully added to expenses'}, status=201)
    return JsonResponse({'success':False, 'message':'Invalid form data'}, status=400)

@login_required
def list_expense_categories(request):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)
    categories = ExpenseCategory.objects.filter(parent=None)
    response = []
    for cat in categories:
        subcats = ExpenseCategory.objects.filter(parent=cat)
        response.append({
            "id": cat.id,
            "name": cat.name,
            "subcategories": [{"id": sc.id, "name": sc.name} for sc in subcats]
        })
    return JsonResponse({"categories": response})

def decode_base64_file(data):
    if not data:
        return None
    try:
        format, imgstr = data.split(';base64,')
        ext = format.split('/')[-1]
        if ext == 'jpeg':
            ext = 'jpg'
        file_name = f"{uuid.uuid4()}.{ext}"
        return ContentFile(base64.b64decode(imgstr), name=file_name)
    except Exception as e:
        logger.error("Failed to decode base64 image:")
        return None
