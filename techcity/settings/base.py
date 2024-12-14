"""
Django settings for techcity project.
"""
import environ, os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
from django.apps import apps
from datetime import timedelta

env = environ.Env()   
load_dotenv()

import sys
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    EMAIL_USE_TLS=(bool, False),
    EMAIL_USE_SSL=(bool, False)
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = "django-insecure-rb&d1ur&gv!uedx9&nym9zthkk(32-kdvh1x_b0+c+&^hny!o9"

DEBUG = False
ALLOWED_HOSTS = []
# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "crispy_forms",
    "crispy_bootstrap5",
    'phonenumber_field',
    'django_extensions',
    # 'chartjs',
    # 'django_crontab',
    # 'DjangoAsyncMail',

    'apps.company',
    'apps.users',
    'apps.Dashboard',
    'apps.inventory',
    'apps.finance',
    'apps.pos',
    'apps.settings',
    'apps.Analytics',
    'apps.booking',
    # 'apps.vouchers'
]

LOCAL_APPS = [
   
]

# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

CSRF_TRUSTED_ORIGINS = ['https://web-production-86a7.up.railway.app']

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    # custom middlewares
    'inventory.middleware.RequestMiddleware',
    'company.middleware.CompanySetupMiddleware'
    
]

ROOT_URLCONF = "techcity.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates/'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                
                # inventory
                "company.context_processors.branch_list",
                "inventory.context_processors.product_list",
                "inventory.context_processors.product_category_list",     
                "inventory.context_processors.stock_notification_count",
                "inventory.context_processors.transfers",
                "inventory.context_processors.stock_notifications",
                "inventory.context_processors.all_products_list",
                
                #finance
                "finance.context_processors.client_list",
                "finance.context_processors.currency_list",
                "finance.context_processors.expense_category_list",
                
                #finance
                # "settings.context_processors.tax_method",
            ],
        },
    },
]

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

WSGI_APPLICATION = "techcity.wsgi.application"
ASGI_APPLICATION = 'techcity.wsgi.application'
AUTH_USER_MODEL = 'users.User'

SESSION_AUTH = True
SESSION_COOKIE_AGE = 36000  # Session expires after 10 hours (in seconds)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {

    'default': dj_database_url.config(
        default='postgresql://postgres:TopCprLoVTPDAmezfOhAJoqvDuHLnxhw@autorack.proxy.rlwy.net:26269/railway'
    )
#    'default': {
#      'ENGINE': 'django.db.backends.postgresql',
#        'NAME':  'techcoty',
#        'USER': 'postgres',
#        'PASSWORD': 'neverfail',
#        'HOST': 'localhost',
#        'PORT': '5432'
#  }
    # 'default': {
    #     'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
    #      'NAME': os.getenv('DB_NAME', 'railway'),
    #      'USER': os.getenv('DB_USERNAME', 'postgres'),
    #      'PASSWORD': os.getenv('DB_PASSWORD', 'TopCprLoVTPDAmezfOhAJoqvsaDuHLnxhw'),  
    #      'HOST': os.getenv('DB_HOST', 'autorack.proxy.rlwy.net'),
    #      'PORT': os.getenv('DB_PORT', '26269'),
    #  }
 }

if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

DATABASES["default"]["ATOMIC_REQUESTS"] = True
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# AUTH_USER_MODEL = "users.User"
# # https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
# LOGIN_REDIRECT_URL = "dashboard:dashboard"
# # https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "users:login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Johannesburg"

USE_I18N = True

USE_TZ = True

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = BASE_DIR / "staticfiles"
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [BASE_DIR / "static"]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(BASE_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# celery
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

CELERY_BEAT_SCHEDULE = {
    'run-all-invoices-recurring': {
        'task': 'finance.tasks.generate_recurring_invoices',
        'schedule': 60.0, 
    },
}

# Inventory
LOW_STOCK_THRESHHOLD =  6
INVENTORY_EMAIL_NOTIFICATIONS_STATUS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), # to be changeed
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}
