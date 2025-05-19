import json
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
from utils.validate_redirect import is_safe_url
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from utils.send_verification_email import *
from django.db import transaction

@login_required
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

@login_required
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

        
@login_required
def users(request):
    """
        View function to handle user management.
        This view handles the display and registration of users. It supports both
        GET and POST requests. On a GET request, it displays a list of users filtered
        by a search query if provided. On a POST request, it processes the user
        registration form and adds a new user if the form is valid.
        Args:
            request (HttpRequest): The HTTP request object.
        Returns:
            HttpResponse: The rendered 'auth/users.html' template with the context
            containing the list of users, user registration form, user details form,
            and user permissions form.
        Context:
            users (QuerySet): A queryset of User objects filtered by the search query.
            form (UserRegistrationForm): The user registration form.
            user_details_form (UserDetailsForm2): The user details form.
            PermData (UserPermissionsForm): The user permissions form.
    """

    form = UserRegistrationForm()
    user_details_form = UserDetailsForm2()
    formPermissions = UserPermissionsForm()

    search_query = request.GET.get('q', '')

    users = User.objects.filter(
        Q(username__icontains=search_query) | 
        Q(email__icontains=search_query)

    ).select_related(
        'branch', 
        'company'
    ).order_by(
        'first_name', 
        'last_name'
    )
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            
            # branches = form.cleaned_data['branches']
            # user.branch.set(branches)
            
            # hash the user password
            user.password = make_password(form.cleaned_data['password'])
            user.save()

            messages.success(request, 'User successfully added')
        else:
            messages.error(request, 'Invalid form data')

    return render(request, 'auth/users.html', {
        'users': users,
        'form': form, 
        'user_details_form': user_details_form, 
        'PermData':formPermissions
        }
    )


def login_view(request):
    """
    Handle user login requests.
    This view handles both GET and POST requests for user login. On a GET request,
    it renders the login page. On a POST request, it processes the login form,
    validates the email, authenticates the user, and logs them in if the credentials
    are correct and the account is active.
    Args:
        request (HttpRequest): The HTTP request object.
    Returns:
        HttpResponse: The HTTP response object. It returns the login page on GET requests,
                      and on POST requests, it either redirects to the next URL or the POS
                      page if login is successful, or re-renders the login page with an
                      error message if login fails.
    """

    if request.method == 'GET':
        return render(request, 'auth/login.html')
    
    if request.method == 'POST':
        email_address = request.POST['email_address']
        password = request.POST['password']

        # Validate email
        try:
            validate_email(email_address)
        except ValidationError:
            messages.error(request, 'Invalid email format')
            return render(request, 'auth/login.html')

        user = authenticate_user(email=email_address, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)

                logger.info(f'User: {user.first_name + " " + user.email} logged in')
                logger.info(f'User role: {user.role}')

                # next_url = request.POST.get('next') or request.GET.get('next') or request.session.get('next_url')
                
                # if 'next_url' in request.session:
                #     del request.session['next_url']
                
                # if next_url:
                #     # Validate the URL to prevent open redirect vulnerability
                #     if is_safe_url(next_url, allowed_hosts={request.get_host()}):
                #         return redirect(next_url)
                    
                return redirect('pos:pos')
            else:
                messages.error(request, 'Your account is not active, contact admin')
                return render(request, 'auth/login.html')
        
        messages.error(request, 'Invalid username or password')
        return render(request, 'auth/login.html')


@login_required
@transaction.atomic
def user_edit(request, user_id):

    with transaction.atomic:
        user = User.objects.get(id=user_id)

        logger.info(f'User details: {user.first_name + " " + user.email}')

        if request.method == 'POST':
            form = UserDetailsForm2(request.POST, instance=user)

            if form.is_valid():
                form.save()
                messages.success(request, 'User details updated successfully')
                return redirect('users:user_detail', user_id=user.id)
            
            messages.error(request, 'Invalid form data')
            form = UserDetailsForm2(instance=user)

    return render(request, 'auth/users.html', {'user': user, 'form': form})


@login_required
def user_detail(request, user_id):

    user = User.objects.get(id=user_id)
    form = UserDetailsForm()

    logger.info(f'User details: {user.first_name + " " + user.email}')

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

@login_required
@transaction.atomic
def register(request):
    if request.method == 'GET':
        form = UserRegistrationForm()
    else:
        form = UserRegistrationForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    
                    user.password = make_password(form.cleaned_data['password'])
                    user.is_active = False
                    
                    user.last_login = None
                    user.failed_login_attempts = 0
                    
                    user.save()

                    # Send verification email
                    # try:
                    #     send_verification_email(user, request)
                    #     messages.success(
                    #         request, 
                    #         f'Account created successfully. Please notify {user.first_name} to check their email to verify their account.'
                    #     )
                    # except EmailRateLimitExceeded:
                    #     messages.error(
                    #         request,
                    #         'Too many verification emails sent. Please try again tomorrow.'
                    #     )
                    # except Exception as e:
                    #     logger.error(f"Error in registration process: {str(e)}")
                    #     messages.error(
                    #         request,
                    #         'An error occurred during registration. Please try again.'
                    #     )
                    #     raise
            
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}")
                messages.error(request, 'Registration failed. Please try again.')
                
    return render(request, 'auth/register.html', {'form': form})

def verify_email(request, signed_token):
    # Rate limit verification attempts by IP
    ip_address = request.META.get('REMOTE_ADDR')
    cache_key = f"verify_email_rate_{ip_address}"
    
    if cache.get(cache_key, 0) >= settings.MAX_VERIFICATION_ATTEMPTS_PER_IP:
        messages.error(request, 'Too many verification attempts. Please try again later.')
        return redirect('login')
    
    cache.set(cache_key, cache.get(cache_key, 0) + 1, timeout=3600)
    
    try:
        # Verify signed token
        user_id, token = verify_signed_token(signed_token)
        if not user_id or not token:
            logger.warning(f"Invalid token attempt from IP: {ip_address}")
            messages.error(request, 'Invalid verification link.')
            return redirect('users:login')
        
        with transaction.atomic():
            verification_token = EmailVerificationToken.objects.select_for_update().get(
                token=token,
                user_id=user_id
            )
            
            if verification_token.is_valid():
                user = verification_token.user
                
                # Verify user isn't already active
                if user.is_active:
                    logger.warning(f"Attempt to re-verify active user {user_id} from IP: {ip_address}")
                    messages.warning(request, 'This account is already verified.')
                    return redirect('users:login')
                
                user.is_active = True
                user.email_verified_at = timezone.now()
                user.save()
                
                # Delete the used token
                verification_token.delete()
                
                # Clear rate limit caches
                cache.delete(f"email_verification_rate_{user.id}")
                
                messages.success(request, 'Email verified successfully. You can now log in.')
                logger.info(f"User {user_id} successfully verified from IP: {ip_address}")
                
            else:
                verification_token.increment_attempts()
                messages.error(request, 'Verification link has expired or too many attempts.')
                logger.warning(f"Invalid verification attempt for user {user_id} from IP: {ip_address}")
                
    except EmailVerificationToken.DoesNotExist:
        logger.warning(f"Verification attempt with non-existent token from IP: {ip_address}")
        messages.error(request, 'Invalid verification link.')
    except Exception as e:
        logger.error(f"Error during email verification: {str(e)}")
        messages.error(request, 'An error occurred during verification.')
    
    return redirect('lusers:login')

@login_required
def load_branches(request):
    """
    we use this view to load branches using js
    """
    company_id = request.GET.get('company_id')
    branches = Branch.objects.filter(company_id=company_id).order_by('name')
    logger.info(f'Branches: {branches.values("id", "name")}')
    return JsonResponse(list(branches.values('id', 'name')), safe=False)


@login_required
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

@login_required
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
from apps.company.models import Branch
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
    """ Enables the admin or the ownwer to switch between branches """
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id):
        user = request.user
        if user.role == 'Admin' or user.role == 'admin':
            user.branch = Branch.objects.get(id=branch_id)
            user.save()
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        data = {
            'user': user,
            'branch': user.branch
        }
        logger.info(data)
        return Response(data, status=status.HTTP_200_OK)


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