from celery import shared_task
from celery.schedules import crontab
from datetime import datetime, time
from django.utils import timezone
from apps.settings.models import FiscalDay
from utils.zimra import ZIMRA
from loguru import logger
from utils.whatsapp import send_whatsapp_message

def should_send_notification():
    now = timezone.localtime()
    start_time = now.replace(hour=17, minute=30, second=0, microsecond=0)
    end_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
    return start_time <= now < end_time

@shared_task(
    name='close_day_notification',
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3
)
def close_day_notification(self, user_id=None):
    if not should_send_notification():
        logger.info("Skipping notification as it's outside the 17:30-18:00 window")
        return "Notification skipped - outside 17:30-18:00 window"

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id) if user_id else None
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return f"Error: User with ID {user_id} not found"

    fiscal_day = FiscalDay.objects.filter(is_open=True).first()
    if not fiscal_day:
        logger.info("No open fiscal day found")
        return "No open fiscal day found"
        
    result = send_whatsapp_message(user, f"Please close the fiscal day now: {fiscal_day.day_no}")
    logger.info(f"Notification result: {result}")
    return result


