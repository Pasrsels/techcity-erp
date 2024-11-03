# my_project/settings/development.py
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*', 'web-production-86a7.up.railway.app']

# Development-specific apps or middleware
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Set up email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# system email 
SYSTEM_EMAIL = 'system@techcity.co.zw'

