from apps.users.models import User

def users(request):
    return { 'users': User.objects.filter(is_deleted=False, is_active=True)}