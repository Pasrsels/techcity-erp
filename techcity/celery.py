import os
from celery import Celery
from django.conf import settings


# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techcity.settings')

# Create the Celery app
app = Celery('techcity')

# Read config from Django settings, the CELERY namespace would make celery 
# config keys has 'CELERY' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Beat Settings
app.conf.beat_schedule = {
    # Add periodic tasks here if needed
}

# Configure timezone
app.conf.timezone = 'UTC'

# Broker settings
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# Task settings
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_expires = 3600  # Results expire in 1 hour
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_concurrency = 4  # Number of worker processes

# Auto-discover tasks from all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')