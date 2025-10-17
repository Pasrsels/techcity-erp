from celery import shared_task
from django.utils import timezone
from .models import DatabaseBackupSchedule
import subprocess
from loguru import logger

@shared_task
def run_scheduled_db_backup():
    now = timezone.localtime()
    schedules = DatabaseBackupSchedule.objects.filter(enabled=True)
    for schedule in schedules:
        if now.time().hour == schedule.time.hour and now.time().minute == schedule.time.minute:
            #to change
            backup_file = f"/path/to/backups/db_backup_{now.strftime('%Y%m%d_%H%M')}.sql"
            try:
                subprocess.run(
                    ["pg_dump", "your_db_name", "-U", "your_db_user", "-f", backup_file],
                    check=True
                )
                schedule.last_run = now
                schedule.save()
                logger.info(f"Database backup completed: {backup_file}")
            except Exception as e:
                logger.error(f"Database backup failed: {e}")