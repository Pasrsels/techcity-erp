from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import UserPermissions
from ..forms import UserPermissionsForm
import json

@login_required
def UserPermission_CR(request):
    if request.method == 'GET':
        permission_data = UserPermissions.objects.all().values()
        return JsonResponse({'success': True, 'Permissiondata': list(permission_data)}, status = 200)

    elif request.method == 'POST':
        user_permission_form = UserPermissionsForm(request.POST)
        name = request.POST.get('name')
        name.lower()

        if user_permission_form.is_valid():
            if not UserPermissions.objects.filter(name = name).exists():
                user_permission_form.save()
                return JsonResponse({'success':True}, status = 201)

            return JsonResponse({'success': False, 'message': 'Permission already exists'}, status = 400)
        return JsonResponse({'success': False, 'message': 'Invalid form data'}, 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

@login_required
def UserPermission_UD(request,id):
    if request.method == 'GET':
        permissions_data = UserPermissions.objects.filter(id = id).values()
        return JsonResponse({'success':True, 'data':list(permissions_data)}, status = 200)

    if request.method == 'PUT':
        data = json.loads(request.body)
        name = data.get('name')

        if UserPermissions.objects.filter(id = id).exists():
            permissions_data = UserPermissions.objects.get(id = id)
            permissions_data.name = name
            permissions_data.save()

            return JsonResponse({'success': True}, status = 200)
        return JsonResponse({'success': False, 'message': 'permission doesnot exist'}, status = 400)

    elif request.method == 'DELETE':
        data = json.loads(request.body)

        if UserPermissions.objects.filter(id = id).exists():
            permission_delete = UserPermissions.objects.get(id = id)
            permission_delete.delete()

            return JsonResponse({'success': True}, status = 200)

        return JsonResponse({'success': False, 'message': 'permission doesnot exist'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
