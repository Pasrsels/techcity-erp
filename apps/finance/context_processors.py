from apps.users.models import User
from apps.finance.models import ExpenseCategory, Customer, Currency

def expense_category_list(request):
    return {'expense_categories': ExpenseCategory.objects.all()}

def client_list(request):
    return {'clients': Customer.objects.all()}

def currency_list(request):
    return {'currencies': Currency.objects.all()}

def salespeople_list(request):
    return {'salespeople': User.objects.filter(is_active=True, role='sales')}



