# services/notification_service.py
import json
from django.utils import timezone
from django.template import Template, Context
from ..models import Notification, NotificationTemplate, UserNotificationPreference
from ..redis_client import NotificationRedisClient

class NotificationService:
    def __init__(self):
        self.redis_client = NotificationRedisClient()
    
    def create_notification(
            self, 
            user, 
            event_type, 
            context_data, 
            related_object=None, 
            scheduled_for=None, 
            priority=0
        ):
        
        """
        Create a notification based on an event type and context data
        """
        # Get user preferences
        preferences = self._get_user_preferences(user)
        if not preferences:
            return None
            
        # Check if user wants this notification type
        preference_field = f"receive_{event_type}"
        if hasattr(preferences, preference_field) and not getattr(preferences, preference_field):
            return None
        
        # Determine which channels to send through based on preferences
        channels = self._get_enabled_channels(preferences, event_type)
        if not channels:
            return None
            
        notifications = []
        
        # Create notification for each enabled channel
        for channel in channels:
            # Get appropriate template
            template = self._get_template(event_type, channel)
            if not template:
                continue
                
            # Render template with context data
            title, message = self._render_template(template, context_data)
            
            # Create notification object
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                channel=channel,
                template=template,
                scheduled_for=scheduled_for,
                status='pending',
                priority=priority
            )
            
            # Set related object if provided
            if related_object:
                notification.content_object = related_object
                notification.save()
                
            notifications.append(notification)
            
            # Handle delivery timing
            if scheduled_for:
                self.redis_client.schedule_notification(notification.id, scheduled_for)
            else:
                # Check for batching opportunity
                if event_type in ['order_update', 'inventory_update']:
                    self.redis_client.add_to_batch(user.id, notification.id, event_type)
                else:
                    # Queue for immediate delivery with priority
                    self.redis_client.queue_notification(notification.id, priority)
                    
                # Send real-time if in-app notification
                if channel == 'in_app':
                    self._send_realtime_notification(notification)
                    
        return notifications
    
    def _get_user_preferences(self, user):
        """Get user notification preferences, from cache if available"""
        # Try to get from Redis cache first
        cached_prefs = self.redis_client.get_user_preferences(user.id)
        if cached_prefs:
            return cached_prefs
            
        # Otherwise get from database and cache
        try:
            prefs = UserNotificationPreference.objects.get(user=user)
            
            # Cache for future use
            pref_dict = {
                'email_enabled': str(int(prefs.email_enabled)),
                'push_enabled': str(int(prefs.push_enabled)),
                'sms_enabled': str(int(prefs.sms_enabled)),
                'in_app_enabled': str(int(prefs.in_app_enabled)),
                'receive_order_updates': str(int(prefs.receive_order_updates)),
                'receive_payment_updates': str(int(prefs.receive_payment_updates)),
                'receive_system_alerts': str(int(prefs.receive_system_alerts)),
            }
            self.redis_client.cache_user_preferences(user.id, pref_dict)
            
            return prefs
        except UserNotificationPreference.DoesNotExist:
            # Create default preferences
            return UserNotificationPreference.objects.create(user=user)
    
    def _get_enabled_channels(self, preferences, event_type):
        """Determine which channels to send notification through"""
        channels = []
        
        # Check quiet hours
        current_time = timezone.localtime().time()
        in_quiet_hours = False
        
        if (preferences.quiet_hours_start and preferences.quiet_hours_end and 
            current_time >= preferences.quiet_hours_start and 
            current_time <= preferences.quiet_hours_end):
            in_quiet_hours = True
        
        # Add enabled channels
        if preferences.email_enabled and not in_quiet_hours:
            channels.append('email')
            
        if preferences.push_enabled and not in_quiet_hours:
            channels.append('push')
            
        if preferences.sms_enabled and not in_quiet_hours:
            # Only send SMS for high priority events
            if event_type in ['system_alerts', 'payment_updates']:
                channels.append('sms')
                
        if preferences.in_app_enabled:
            # In-app always delivered regardless of quiet hours
            channels.append('in_app')
            
        return channels
    
    def _get_template(self, event_type, channel):
        """Get appropriate template for notification type and channel"""
        template_name = f"{event_type}_{channel}"
        try:
            return NotificationTemplate.objects.get(name=template_name, channel=channel)
        except NotificationTemplate.DoesNotExist:
            # Fallback to default template for channel
            try:
                return NotificationTemplate.objects.get(name=f"default_{channel}", channel=channel)
            except NotificationTemplate.DoesNotExist:
                return None
    
    def _render_template(self, template, context_data):
        """Render notification template with context data"""
        # Simple template rendering using Django's template engine
        subject_template = Template(template.subject)
        content_template = Template(template.content)
        
        ctx = Context(context_data)
        title = subject_template.render(ctx)
        message = content_template.render(ctx)
        
        return title, message
    
    def _send_realtime_notification(self, notification):
        """Send notification in real-time via Redis pub/sub"""
        notification_data = {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'created_at': notification.created_at.isoformat(),
            'related_url': self._get_related_url(notification),
        }
        
        self.redis_client.publish_notification(
            notification.user.id, notification_data
        )
        
    def _get_related_url(self, notification):
        """Get URL for the related object if any"""
        if notification.related_object and hasattr(notification.related_object, 'get_absolute_url'):
            return notification.related_object.get_absolute_url()
        return None