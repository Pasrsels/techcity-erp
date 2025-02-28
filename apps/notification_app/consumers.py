# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Notification

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.notification_group_name = f"user_{self.user.id}_notifications"
        
        # Join user's notification group
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send unread notifications on connect
        unread = await self.get_unread_notifications()
        if unread:
            await self.send(text_data=json.dumps({
                'type': 'unread_notifications',
                'notifications': unread
            }))
    
    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Handle marking notifications as read
        if data.get('type') == 'mark_read':
            notification_id = data.get('notification_id')
            if notification_id:
                await self.mark_notification_read(notification_id)
                await self.send(text_data=json.dumps({
                    'type': 'notification_marked_read',
                    'notification_id': notification_id
                }))
    
    async def notification_message(self, event):
        """Handle notification message from Redis via channel layer"""
        notification = event['notification']
        
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': notification
        }))
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Get unread notifications for the user"""
        notifications = Notification.objects.filter(
            user=self.user,
            status='delivered',
            channel='in_app'
        ).order_by('-created_at')[:10]
        
        return [
            {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'created_at': notification.created_at.isoformat(),
                'related_url': (notification.related_object.get_absolute_url() 
                               if notification.related_object and hasattr(notification.related_object, 'get_absolute_url')
                               else None)
            }
            for notification in notifications
        ]
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            notification.status = 'read'
            notification.save(update_fields=['status'])
            return True
        except Notification.DoesNotExist:
            return False

