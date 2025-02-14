import os
from celery import Celery
from django.conf import settings


# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techcity.settings.development')

# Create the Celery app
app = Celery('techcity')

# Read config from Django settings, the CELERY namespace would make celery 
# config keys has 'CELERY' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')


# Configure timezone
app.conf.timezone = 'UTC'

# Broker settings
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# Auto-discover tasks from all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.task_routes = {
    'apps.inventory.tasks.process_transfer': {'queue': 'transfers'},
    'apps.inventory.tasks.notify_branch_transfer': {'queue': 'notifications'},
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')