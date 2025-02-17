import os, ssl
from celery import Celery
from django.conf import settings


# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techcity.settings.development')

# Create the Celery app
app = Celery('techcity')

app.conf.update(
    BROKER_URL=os.environ.get('REDIS_URL'),
    CELERY_RESULT_BACKEND=os.environ.get('REDIS_URL'),
    BROKER_USE_SSL={
        'ssl_cert_reqs': ssl.CERT_NONE,  
    },
    CELERY_REDIS_BACKEND_USE_SSL={
        'ssl_cert_reqs': ssl.CERT_NONE,  
    }
)

# Read config from Django settings, the CELERY namespace would make celery 
# config keys has 'CELERY' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')


# Configure timezone
app.conf.timezone = 'UTC'

# Auto-discover tasks from all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

app.conf.task_routes = {
    'apps.inventory.tasks.process_transfer': {'queue': 'transfers'},
    'apps.inventory.tasks.notify_branch_transfer': {'queue': 'notifications'},
}



@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')