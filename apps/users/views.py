from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render, redirect
from loguru import logger
from django.contrib.auth import get_user_model
from apps.company.models import Branch
from apps.settings.models import NotificationsSettings
from utils.authenticate import authenticate_user
from .models import User, UserPermissions
from .forms import UserRegistrationForm, UserDetailsForm, UserDetailsForm2, UserPermissionsForm
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
import json

def UserPermission_CR(request):
    if request.method == 'GET':
        permission_data = UserPermissions.objects.all().values()
        logger.info(list(permission_data))
        return JsonResponse({'success': True, 'Permissiondata': list(permission_data)}, status = 200)
    elif request.method == 'POST':
        user_permission_form = UserPermissionsForm(request.POST)
        name = request.POST.get('name')
        name.lower()
        if user_permission_form.is_valid():
            if  not UserPermissions.objects.filter(name = name).exists():
                user_permission_form.save()
                return JsonResponse({'success':True}, status = 201)
            return JsonResponse({'success': False, 'message': 'Permission already exists'}, status = 400)
        return JsonResponse({'success': False, 'message': 'Invalid form data'}, 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

def UserPermission_UD(request,id):
    if request.method == 'GET':
        permissions_data = User.objects.filter(id = id).values()
        logger.info(permissions_data)
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

        

def users(request):
    search_query = request.GET.get('q', '')
    users = User.objects.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query)).order_by(
        'first_name', 'last_name')
    form = UserRegistrationForm()
    user_details_form = UserDetailsForm2()
    formPermissions = UserPermissionsForm()
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'User successfully added')
        else:
            messages.error(request, 'Invalid form data')

    return render(request, 'auth/users.html', {'users': users, 'form': form, 'user_details_form': user_details_form, 'PermData':formPermissions})


def login_view(request):
    if request.method == 'POST':
        email_address = request.POST['email_address']
        password = request.POST['password']

        logger.info(email_address)

        # Validate email
        try:
            validate_email(email_address)
        except ValidationError:
            messages.error(request, 'Invalid email format')
            return render(request, 'auth/login.html')

        user = authenticate_user(email=email_address, password=password)
        logger.info(f'User: {user}')
        if user is not None:
            if user.is_active:
                login(request, user)
                logger.info(f'User: {user.first_name + " " + user.email} logged in')
                logger.info(f'User role: {user.role}')
                if user.role == 'accountant':
                    logger.info(f'User: {user.first_name + " " + user.email} is an accountant')
                    return redirect('dashboard:dashboard')
                return redirect('pos:pos')
            else:
                messages.error(request, 'Your account is not active, contact admin')
                return render(request, 'auth/login.html')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'auth/login.html')
    
    if request.method == 'GET':
        return render(request, 'auth/login.html')


def user_edit(request, user_id):
    user = User.objects.get(id=user_id)
    logger.info(f'User details: {user.first_name + " " + user.email}')
    if request.method == 'POST':
        form = UserDetailsForm2(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully')
            return redirect('users:user_detail', user_id=user.id)
        else:
            messages.error(request, 'Invalid form data')
    else:
        form = UserDetailsForm2(instance=user)
    return render(request, 'auth/users.html', {'user': user, 'form': form})


def user_detail(request, user_id):
    user = User.objects.get(id=user_id)
    form = UserDetailsForm()
    logger.info(f'User details: {user.first_name + " " + user.email}')
    # render user details
    if request.method == 'GET':
        return render(request, 'user_detail.html', {'user': user, 'form': form})
    if request.method == 'POST':
        form = UserDetailsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully')
        else:
            messages.error(request, 'Invalid form data')
        return render(request, 'users/user_detail.html', {'user': user, 'form': form})

def register(request):
    form = UserRegistrationForm()
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password'])
            user.save()

            # create notifications settings for the user
            NotificationsSettings.objects.create(user=user)

            messages.success(request, 'User successfully added')
        else:
            messages.error(request, 'Error')
    return render(request, 'auth/register.html', {
        'form': form
    })


def load_branches(request):
    """
    we use this view to load branches using js
    """
    company_id = request.GET.get('company_id')
    branches = Branch.objects.filter(company_id=company_id).order_by('name')
    logger.info(f'Branches: {branches.values("id", "name")}')
    return JsonResponse(list(branches.values('id', 'name')), safe=False)


def get_user_data(request, user_id):
    user = User.objects.get(id=user_id)
    user_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'username': user.username,
        'phonenumber': user.phonenumber,
        'company': user.company.id if user.company else None,
        'branch': user.branch.id if user.branch else None,
        'role': user.role,
    }
    logger.info(f'User data: {user_data}')
    return JsonResponse(user_data)


def logout_view(request):
    logout(request)
    return redirect('users:login')

##############################################################################################################################################################
""" User API End points """

from django.contrib.auth import login
from .serializers import(
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    LogoutSerializer,
    UserPermissionsSerializer,
)
from .models import User, UserPermissions
from django.contrib.auth.models import Group
from rest_framework import generics, status, views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

class UserPermissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = UserPermissions.objects.all()
    serializer_class = UserPermissionsSerializer

class BranchSwitch(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, branch_id):
        """ Enables the admin or the ownwe to switch between branches """
        user = request.user
        if user.role == 'Admin' or user.role == 'admin':
            user.branch = Branch.objects.get(id=branch_id)
            user.save()
        else:
            return Response('You are not authorized', status = status.HTTP_401_UNAUTHORIZED)
        return redirect('pos:pos')


class UserViewSet(viewsets.ModelViewSet):
    """
    An endpoint which allows viewers to be viewed or edited
    """
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class RegisterView(generics.GenericAPIView):
    """
        User registration end point
    """
    serializer_class = RegisterSerializer

    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data
        return Response(user_data, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    """
        Login API end point
    """
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutAPIView(generics.GenericAPIView):
    """
        Logout Api End Point
    """
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)