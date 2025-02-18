web: gunicorn techcity.wsgi:application
worker: celery --app=techcity.celery worker -Q transfers,notifications --loglevel=info


