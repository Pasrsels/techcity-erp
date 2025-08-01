"""
Django settings for techcity project.
"""
import environ, os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
from django.apps import apps
from datetime import timedelta
from datetime import timedelta
import sys
from celery.schedules import crontab

env = environ.Env()   
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    EMAIL_USE_TLS=(bool, False),
    EMAIL_USE_SSL=(bool, False)
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = "django-insecure-rb&d1ur&gv!uedx9&nym9zthkk(32-kdvh1x_b0+c+&^hny!o9"

DEBUG = True
ALLOWED_HOSTS = []
# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    "channels",
    # 'debug_toolbar',
    'drf_yasg',
    "crispy_forms",
    "crispy_bootstrap5",
    'phonenumber_field',
    'django_extensions',
    'django_celery_beat',
    # 'chartjs',
    # 'django_crontab',
    # 'DjangoAsyncMail',
    # 'django_browser_reload',

    'apps.company',
    'apps.users',
    'apps.Dashboard',
    'apps.inventory',
    'apps.finance',
    'apps.pos',
    'apps.settings',
    'apps.Analytics',
    'apps.booking',
    # 'apps.vouchers',
    # 'apps.purchase_orders'
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
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
    
    # custom middlewares
    'inventory.middleware.RequestMiddleware',
    'company.middleware.CompanySetupMiddleware',
    # 'users.middleware.LoginRequiredMiddleware',

    # third pard middleware
    # 'django_browser_reload.middleware.BrowserReloadMiddleware',
    
    
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
                "finance.context_processors.salespeople_list",
                
                #finance
                # "settings.context_processors.tax_method",
                
                #users
                "users.context_processor.users"
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
SESSION_COOKIE_AGE = 36000  #
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {

    # 'default': dj_database_url.config(
    #     default=os.environ.get('DATABASE_URL')
    # )
    # 'default': dj_database_url.config(
    #     default=os.environ.get('DATABASE_URL')
    # )

    # 'default': {
    #      'ENGINE': 'django.db.backends.postgresql',
    #      'NAME':  'techcity_db',
    #      'USER': 'postgres',
    #      'PASSWORD': 'neverfail',
    #      'HOST': 'localhost',
    #      'PORT': '5432'
    #  }
    
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':  'testt',
        'USER': 'postgres',
        'PASSWORD': 'neverfail',
        'HOST': 'localhost',
        'PORT': '5432'
    }
}

if os.environ.get('TESTING'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'test_db.sqlite3'),
    
    }
    
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


# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        }
    }
}

# Cache time to live is 15 minutes
CACHE_TTL = 60 * 15

# celery
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

# remote
# CELERY_BROKER_URL="rediss://:p81af2fc64c9b750172375f4b4b521a9a32354997e449c1cb59482e8607f7f227@ec2-44-223-243-234.compute-1.amazonaws.com:23070"
# CELERY_RESULT_BACKEND="rediss://:p81af2fc64c9b750172375f4b4b521a9a32354997e449c1cb59482e8607f7f227@ec2-44-223-243-234.compute-1.amazonaws.com:23070"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

REDIS_OPTIONS = {
    'ssl': True,
    'ssl_cert_reqs': None,  # Set to None to bypass certificate verification temporarily
    'socket_connect_timeout': 30
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": ["127.0.0.1:6379"],
            "symmetric_encryption_keys": [SECRET_KEY],
            "ssl_cert_reqs": None,  
        },
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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60), # to be changeed
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}


#Verificatioin retries
VERIFICATION_TOKEN_EXPIRY_HOURS = 24
MAX_VERIFICATION_ATTEMPTS = 5
MAX_VERIFICATION_ATTEMPTS_PER_IP = 10
MAX_EMAIL_VERIFICATION_ATTEMPTS_PER_DAY = 3

# Default from Email
DEFAULT_FROM_EMAIL = 'admin@techcity.co.zw' #to be dynamically


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = "1025"
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False

#ZIMRA
DEVICE_REGISTER = False
REPORTING_FREQUENCY = 5


CELERY_BEAT_SCHEDULE = {
    'ping-every-5-seconds': {
        'task': 'utils.zimra.ping',
        'schedule': REPORTING_FREQUENCY * 60
    },
}


# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'products_api.log',
        },
    },
    'loggers': {
        '__main__': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}