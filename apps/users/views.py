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
from .models import User, UserPermissions, EmailVerificationToken, PasswordResetOTP
from .forms import UserRegistrationForm, UserDetailsForm, UserDetailsForm2, UserPermissionsForm
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
from utils.validate_redirect import is_safe_url
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from utils.send_verification_email import *
from django.db import transaction
from django.contrib.auth import authenticate
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
import time
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

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
    form = UserRegistrationForm()
    user_details_form = UserDetailsForm2()
    formPermissions = UserPermissionsForm()

    search_query = request.GET.get('q', '')

    users = User.objects.filter(
        Q(username__icontains=search_query) | Q(email__icontains=search_query),
        is_deleted=False
    ).select_related(
        'branch', 
        'company'
    ).order_by(
        'first_name', 
        'last_name'
    )
    
    if request.method == 'POST':
        try:
            data = request.POST
            user = User()

            user.first_name = data.get('first_name')
            user.email = data.get('email')
            user.phonenumber = data.get('phonenumber')
            user.username = data.get('username')
            user.role = data.get('role')  
            user.company_id = data.get('company')  
            user.branch_id = data.get('branch')  
            
            raw_password = data.get('password')
            if not raw_password:
                return JsonResponse({'success': False, 'message': 'Password is required'}, status=400)

            user.set_password(raw_password)
            user.is_active = True
            user.save()

            return JsonResponse({'success': True, 'message': 'User registered successfully'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return render(request, 'auth/users.html', {
            'users': users,
            'form': form, 
            'user_details_form': user_details_form, 
            'PermData':formPermissions
        }
    )


@never_cache
def login_view(request):
    ip_address = request.META.get('REMOTE_ADDR')
    cache_key = f'login_attempts_{ip_address}'
    attempts = cache.get(cache_key, 0)
    
    if attempts >= 5:
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'success': False,
                'message': 'Too many login attempts. Please try again later.',
                'status': 'error'
            }, status=429)
        messages.error(request, 'Too many login attempts. Please try again later.')
        return render(request, 'auth/login.html', status=429)
    
    if request.method == 'GET':
        return render(request, 'auth/login.html')
    
    if request.method == 'POST':
        email_address = request.POST.get('email_address', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not email_address or not password:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'Please provide both email and password',
                    'status': 'error'
                }, status=400)
            messages.error(request, 'Please provide both email and password')
            return render(request, 'auth/login.html', status=400)
        
        try:
            validate_email(email_address)
        except ValidationError:
            cache.set(cache_key, attempts + 1, 900)  # 15 minutes timeout
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid email format',
                    'status': 'error'
                }, status=400)
            messages.error(request, 'Invalid email format')
            return render(request, 'auth/login.html', status=400)
        
        try:
            user_obj = User.objects.get(email=email_address)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
            time.sleep(0.1)
        
        if user is not None:
            if user.is_active:
                cache.delete(cache_key)
                request.session.set_expiry(3600)
                request.session.set_test_cookie()
                
                login(request, user)
                
                logger.info(f'User: {user.first_name} {user.email} logged in successfully')
                logger.info(f'User role: {user.role}')
                
                next_url = request.POST.get('next') or request.GET.get('next') or request.session.get('next_url')
                
                if 'next_url' in request.session:
                    del request.session['next_url']
                
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': True,
                        'message': 'Login successful',
                        'status': 'success',
                        'redirect_url': next_url if next_url and is_safe_url(next_url, allowed_hosts={request.get_host()}) else '/pos/'
                    })
                
                if next_url:
                    if is_safe_url(next_url, allowed_hosts={request.get_host()}):
                        return redirect(next_url)
                
                return redirect('pos:pos')
            else:
                cache.set(cache_key, attempts + 1, 900)
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'message': 'Your account is not active. Please contact the administrator.',
                        'status': 'error'
                    }, status=403)
                messages.error(request, 'Your account is not active. Please contact the administrator.')
                return render(request, 'auth/login.html', status=403)
        
        cache.set(cache_key, attempts + 1, 900)
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'success': False,
                'message': 'Invalid email or password',
                'status': 'error'
            }, status=401)
        messages.error(request, 'Invalid email or password')
        return render(request, 'auth/login.html', status=401)


@login_required
@transaction.atomic
def user_edit(request, user_id):

    user = User.objects.select_for_update().get(id=user_id)

    logger.info(f'Editing User: {user.first_name + " " + user.email}')

    if request.method == 'POST':
        form = UserDetailsForm2(request.POST, instance=user)

        if form.is_valid():
            form.save()
            
            logger.info('provide')
            messages.success(request, 'User details updated successfully')
            return redirect('users:user_detail', user_id=user.id)
        
        messages.error(request, 'Invalid form data')
        form = UserDetailsForm2(instance=user)

    return render(request, 'auth/users.html', {'user': user, 'form': form})

@login_required
def upload_profile(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

    if 'profile_image' not in request.FILES:
        logger.warning('No profile_image key in request.FILES')
        return JsonResponse({'success': False, 'message': 'No image uploaded'}, status=400)

    image_file = request.FILES['profile_image']
    logger.info(f"Uploaded file: {image_file.name}, type: {image_file.content_type}, size: {image_file.size}")

    if not image_file.content_type.startswith('image/'):
        return JsonResponse({'success': False, 'message': 'Invalid file type. Only images are allowed.'}, status=400)
    
    print('here')
    
    if image_file.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': 'Image too large (max 5MB)'}, status=400)
    
    print('here')

    try:
        # profile = getattr(request.user, 'profile_image', None)
        user = request.user
        
        user.profile_image = image_file
        user.save()
        
        print('saved')

        return JsonResponse({
            'success': True,
            'image_url': user.profile_image.url
        })
    except Exception as e:
        logger.error(f"Error uploading profile image: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while uploading the image.'
        }, status=500)

@login_required
def user_detail(request, user_id):

    user = User.objects.get(id=user_id)
    form = UserDetailsForm()

    logger.info(f'User details: {user.first_name + " " + user.email}')

    if request.method == 'GET':
        return render(request, 'profile.html', {'user': user, 'form': form})
    
    if request.method == 'POST':
        form = UserDetailsForm(request.POST, instance=user)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully')
        else:
            messages.error(request, 'Invalid form data')

        return render(request, 'users/profile.html', {'user': user, 'form': form})

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
                    
                    user.set_password(form.cleaned_data['password'])
                    user.is_active = True
                    
                    user.last_login = None
                    user.failed_login_attempts = 0
                    
                    user.save()
                    
                    messages.success(request, "User registered successfully.")
                    
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}")
                messages.error(request, 'Registration failed. Please try again.')
                
    return render(request, 'auth/register.html', {'form': form})

def verify_email(request, signed_token):
    ip_address = request.META.get('REMOTE_ADDR')
    cache_key = f"verify_email_rate_{ip_address}"
    
    if cache.get(cache_key, 0) >= settings.MAX_VERIFICATION_ATTEMPTS_PER_IP:
        messages.error(request, 'Too many verification attempts. Please try again later.')
        return redirect('login')
    
    cache.set(cache_key, cache.get(cache_key, 0) + 1, timeout=3600)
    
    try:
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
                
                if user.is_active:
                    logger.warning(f"Attempt to re-verify active user {user_id} from IP: {ip_address}")
                    messages.warning(request, 'This account is already verified.')
                    return redirect('users:login')
                
                user.is_active = True
                user.email_verified_at = timezone.now()
                user.save()
            
                verification_token.delete()
                
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
def delete_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False  
        user.is_deleted = True

        user.save()
        return JsonResponse({'success': True, 'message': 'User deleted successfully'})

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@login_required
def logout_view(request):
    logout(request)
    return redirect('users:login')

@login_required
def user_profile(request):
    user = request.user  
    return render(request, 'profile.html', {'user': user})

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

def send_verification_email(user, token):
    subject = 'Verify your email address'
    message = f'''
    Hello {user.first_name},

    Please verify your email address by clicking the link below:
    {settings.SITE_URL}/users/verify-email/{token}/

    This link will expire in 24 hours.

    If you didn't request this verification, please ignore this email.

    Best regards,
    Posflow Team
    '''
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def send_password_reset_otp(user, otp):
    subject = 'Password Reset OTP'
    message = f'''
    Hello {user.first_name},

    Your OTP for password reset is: {otp}

    This OTP will expire in 10 minutes.

    If you didn't request a password reset, please ignore this email.

    Best regards,
    Posflow Team
    '''
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    logger.info(f'OTP has been sent to {user.email}')

def request_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        try:
            user = User.objects.get(email=email)
            
            if user.email_verified:
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'message': 'Please verify your email first.',
                        'status': 'error'
                    }, status=400)
                messages.error(request, 'Please verify your email first.')
                return render(request, 'auth/request_password_reset.html')
            
            # Generate OTP
            otp = PasswordResetOTP.generate_otp()
            expires_at = timezone.now() + timedelta(minutes=10)
            
            # Save OTP
            PasswordResetOTP.objects.create(
                user=user,
                otp=otp,
                expires_at=expires_at
            )
            
            # Send OTP via email
            send_password_reset_otp(user, otp)
            
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': 'OTP has been sent to your email.',
                    'status': 'success'
                })
            messages.success(request, 'OTP has been sent to your email.')
            return redirect('users:verify_otp')
            
        except User.DoesNotExist:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'No user found with this email address.',
                    'status': 'error'
                }, status=404)
            messages.error(request, 'No user found with this email address.')
            return render(request, 'auth/request_password_reset.html')
    
    return render(request, 'auth/request_password_reset.html')

def verify_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        otp = request.POST.get('otp', '').strip()
        
        try:
            user = User.objects.get(email=email)
            otp_obj = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False
            ).latest('created_at')
            
            if not otp_obj.is_valid():
                otp_obj.increment_attempts()
                if request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid or expired OTP.',
                        'status': 'error'
                    }, status=400)
                messages.error(request, 'Invalid or expired OTP.')
                return render(request, 'auth/verify_otp.html')
            
            otp_obj.mark_as_used()
            
            request.session['reset_email'] = email
            
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': 'OTP verified successfully.',
                    'status': 'success',
                    'redirect_url': reverse('users:reset_password')
                })
            return redirect('users:reset_password')
            
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid OTP.',
                    'status': 'error'
                }, status=400)
            messages.error(request, 'Invalid OTP.')
            return render(request, 'auth/verify_otp.html')
    
    return render(request, 'auth/verify_otp.html')

def reset_password(request):
    if request.method == 'POST':
        email = request.session.get('reset_email')
        if not email:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid session.',
                    'status': 'error'
                }, status=400)
            messages.error(request, 'Invalid session.')
            return redirect('users:request_password_reset')
        
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if password != confirm_password:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'Passwords do not match.',
                    'status': 'error'
                }, status=400)
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/reset_password.html')
        
        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
        
            del request.session['reset_email']
            
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': True,
                    'message': 'Password reset successful. Please login with your new password.',
                    'status': 'success',
                    'redirect_url': reverse('users:login')
                })
            messages.success(request, 'Password reset successful. Please login with your new password.')
            return redirect('users:login')
            
        except User.DoesNotExist:
            if request.headers.get('Accept') == 'application/json':
                return JsonResponse({
                    'success': False,
                    'message': 'User not found.',
                    'status': 'error'
                }, status=404)
            messages.error(request, 'User not found.')
            return redirect('users:request_password_reset')
    
    return render(request, 'auth/reset_password.html')

def verify_email(request, token):
    try:
        verification = EmailVerificationToken.objects.get(token=token)
        
        if not verification.is_valid():
            verification.increment_attempts()
            messages.error(request, 'Invalid or expired verification link.')
            return redirect('users:login')
        
        user = verification.user
        user.email_verified = True
        user.save()
        
        verification.is_verified = True
        verification.save()
        
        messages.success(request, 'Email verified successfully. You can now log in.')
        return redirect('users:login')
        
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('users:login')