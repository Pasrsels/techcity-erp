# models.py
from django.db import models
from apps.users.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType



class NotificationTemplate(models.Model):
    """Templates for different notification types"""
    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    html_content = models.TextField(blank=True)
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    ]
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_display()})"

class UserNotificationPreference(models.Model):
    """User's notification preferences"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Which notification types the user wants to receive
    receive_order_updates = models.BooleanField(default=True)
    receive_payment_updates = models.BooleanField(default=True)
    receive_system_alerts = models.BooleanField(default=True)
    
    # Through which channels
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    
    # Do not disturb settings
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user',)

class Notification(models.Model):
    """Individual notification instances"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # For linking to related object (e.g., an order, invoice)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Delivery details
    channel = models.CharField(max_length=20, choices=NotificationTemplate.CHANNEL_CHOICES)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # For grouping related notifications
    group_id = models.CharField(max_length=100, blank=True)
    priority = models.IntegerField(default=0) 
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['scheduled_for']),
        ]