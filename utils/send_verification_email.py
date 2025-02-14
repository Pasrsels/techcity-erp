from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.core.signing import TimestampSigner, BadSignature
from django.utils.crypto import get_random_string
from loguru import logger
from apps.users.models import EmailVerificationToken
from django.core.cache import cache


class EmailRateLimitExceeded(Exception):
    pass

def generate_signed_token(user_id, token):
    """Generate a signed token that includes user ID for additional security"""
    signer = TimestampSigner()
    return signer.sign(f"{user_id}:{token}")

def verify_signed_token(signed_token):
    """Verify the signed token and extract user ID and token"""
    signer = TimestampSigner()
    try:
        # Verify signature and check max age (24 hours)
        value = signer.unsign(signed_token, max_age=timedelta(days=1))
        user_id, token = value.split(':')
        return int(user_id), token
    except (BadSignature, ValueError):
        return None, None

def check_email_rate_limit(user):
    """Check if user has exceeded email rate limit"""
    cache_key = f"email_verification_rate_{user.id}"
    attempts = cache.get(cache_key, 0)
    
    if attempts >= settings.MAX_EMAIL_VERIFICATION_ATTEMPTS_PER_DAY:
        raise EmailRateLimitExceeded("Daily email limit exceeded")
    
    cache.set(cache_key, attempts + 1, timeout=86400)

def send_verification_email(user, request):
    try:
        check_email_rate_limit(user)
        
        token, created = EmailVerificationToken.objects.get_or_create(
            user=user,
            defaults={
                'expires_at': timezone.now() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRY_HOURS)
            }
        )
        
        if not created and not token.is_valid():
            token.delete()
            token = EmailVerificationToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRY_HOURS)
            )

        signed_token = generate_signed_token(user.id, str(token.token))
        
        # Build verification URL with signed token
        verify_url = request.build_absolute_uri(
            reverse('verify_email', args=[signed_token])
        )
        
        # Add request tracking parameters
        verify_url = f"{verify_url}?rid={get_random_string(8)}"
        
        subject = 'Verify your email address'
        message = f'''
            Hi {user.get_full_name()},
        
            Please verify your email address by clicking the link below:

            {verify_url}

            This link will expire in {settings.VERIFICATION_TOKEN_EXPIRY_HOURS} hours.
            Do not share this link with anyone.

            If you didn't create an account, please ignore this email and report this incident.

            Best regards,
            Management

        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to user {user.id}")
        
    except EmailRateLimitExceeded:
        logger.warning(f"Email rate limit exceeded for user {user.id}")
        raise
    except Exception as e:
        logger.error(f"Error sending verification email to user {user.id}: {str(e)}")
        raise
