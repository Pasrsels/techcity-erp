from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.urls import reverse
from loguru import logger
from ..models import User, EmailVerificationToken, PasswordResetOTP
from ..forms import UserRegistrationForm
from utils.send_verification_email import *
from django.db import transaction

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
                request.session.set_expiry(28800)
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
                    'redirect_url': next_url if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}) else '/pos/'
                    })
                
                if next_url:
                    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
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
def logout_view(request):
    logout(request)
    return redirect('users:login')

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
