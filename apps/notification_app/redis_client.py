# redis_client.py
import json
import redis
from django.conf import settings
import time
from datetime import datetime

class NotificationRedisClient:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_NOTIFICATION_DB,
            decode_responses=True
        )
        self.pub_sub = self.redis.pubsub()
    
    # Real-time notification delivery
    def publish_notification(self, user_id, notification_data):
        """Publish notification for real-time delivery"""
        channel = f"user:{user_id}:notifications"
        self.redis.publish(channel, json.dumps(notification_data))
    
    # Notification queuing
    def queue_notification(self, notification_id, priority=0):
        """Add notification to delivery queue"""
        queue_key = "notifications:delivery:queue"
        self.redis.zadd(queue_key, {str(notification_id): priority})
    
    def get_queued_notifications(self, count=10):
        """Get notifications ready for processing"""
        queue_key = "notifications:delivery:queue"
        notification_ids = self.redis.zrange(queue_key, 0, count-1)
        if notification_ids:
            self.redis.zrem(queue_key, *notification_ids)
        return [int(nid) for nid in notification_ids]
    
    # Scheduled notifications
    def schedule_notification(self, notification_id, delivery_time):
        """Schedule notification for later delivery"""
        if isinstance(delivery_time, datetime):
            score = delivery_time.timestamp()
        else:
            score = delivery_time
        
        schedule_key = "notifications:scheduled"
        self.redis.zadd(schedule_key, {str(notification_id): score})
    
    def get_due_notifications(self):
        """Get notifications that are due for delivery"""
        now = time.time()
        schedule_key = "notifications:scheduled"
        notification_ids = self.redis.zrangebyscore(schedule_key, 0, now)
        if notification_ids:
            self.redis.zrem(schedule_key, *notification_ids)
        return [int(nid) for nid in notification_ids]
    
    # User preferences caching
    def cache_user_preferences(self, user_id, preferences):
        """Cache user notification preferences"""
        key = f"user:{user_id}:preferences"
        self.redis.hmset(key, preferences)
        self.redis.expire(key, 3600)  # Cache for 1 hour
    
    def get_user_preferences(self, user_id):
        """Get cached user preferences"""
        key = f"user:{user_id}:preferences"
        preferences = self.redis.hgetall(key)
        return preferences if preferences else None
    
    # Rate limiting
    def check_rate_limit(self, user_id, channel, max_per_minute=10):
        """Check if user rate limit is exceeded"""
        key = f"ratelimit:{user_id}:{channel}"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 60) 
        return count <= max_per_minute
    
    # Notification batching
    def add_to_batch(self, user_id, notification_id, batch_key):
        """Add notification to a batch for combined delivery"""
        key = f"batch:{batch_key}:{user_id}"
        self.redis.sadd(key, notification_id)
        # Set expiry if this is new batch
        if self.redis.ttl(key) < 0:
            self.redis.expire(key, 300)  #
    
    def get_batch(self, user_id, batch_key):
        """Get all notifications in a batch"""
        key = f"batch:{batch_key}:{user_id}"
        return [int(nid) for nid in self.redis.smembers(key)]