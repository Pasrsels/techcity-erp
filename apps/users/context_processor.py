from apps.users.models import User
from apps.company.models import Branch

def users(request):
    return { 'users': User.objects.filter(is_deleted=False, is_active=True)}

def branches(request):
    return { 'branches': Branch.objects.filter(disable=False)}