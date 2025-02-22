# tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Notification
from .redis_client import NotificationRedisClient

redis_client = NotificationRedisClient()

@shared_task
def process_notification_queue():
    """Process pending notifications from Redis queue"""
    notification_ids = redis_client.get_queued_notifications(count=50)
    
    if not notification_ids:
        return "No notifications to process"
    
    notifications = Notification.objects.filter(id__in=notification_ids)
    
    for notification in notifications:
        notification.status = 'processing'
        notification.save(update_fields=['status'])
        
        try:
            # Dispatch based on channel
            if notification.channel == 'email':
                send_email_notification.delay(notification.id)
            elif notification.channel == 'sms':
                send_sms_notification.delay(notification.id)
            elif notification.channel == 'push':
                send_push_notification.delay(notification.id)
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save(update_fields=['status', 'error_message'])
    
    return f"Processed {len(notification_ids)} notifications"

@shared_task
def check_scheduled_notifications():
    """Check for scheduled notifications that are due"""
    notification_ids = redis_client.get_due_notifications()
    
    if notification_ids:
        for notification_id in notification_ids:
            redis_client.queue_notification(notification_id)
    
    return f"Queued {len(notification_ids)} due notifications"

@shared_task
def process_notification_batches():
    """Process batched notifications"""
    # Implement batch processing logic here
    pass

@shared_task
def send_email_notification(notification_id):
    """Send an email notification"""
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Skip if user has no email
        if not notification.user.email:
            notification.status = 'failed'
            notification.error_message = 'User has no email address'
            notification.save(update_fields=['status', 'error_message'])
            return
        
        # Get HTML content if available
        html_content = None
        if notification.template and notification.template.html_content:
            html_content = notification.template.html_content
        
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        notification.status = 'delivered'
        notification.save(update_fields=['status'])
        
        return f"Email notification {notification_id} sent successfully"
    except Exception as e:
        notification = Notification.objects.get(id=notification_id)
        notification.status = 'failed'
        notification.error_message = str(e)
        notification.save(update_fields=['status', 'error_message'])
        return f"Failed to send email notification {notification_id}: {str(e)}"

@shared_task
def send_sms_notification(notification_id):
    """Send an SMS notification"""
    # Implement SMS delivery logic here
    # You would typically use a service like Twilio
    pass

@shared_task
def send_push_notification(notification_id):
    """Send a push notification"""
    # Implement push notification logic here
    # You would typically use Firebase Cloud Messaging or similar
    pass

@shared_task
def clean_old_notifications():
    """Archive old notifications to maintain performance"""
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    
    # Mark old notifications as archived
    # In a real implementation, you might move them to a separate table
    count = Notification.objects.filter(
        created_at__lt=thirty_days_ago,
        status__in=['delivered', 'read']
    ).update(status='archived')
    
    return f"Archived {count} old notifications"