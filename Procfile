web: gunicorn techcity.wsgi:application
worker: celery -A techcity worker -Q transfers,notifications --loglevel=info

