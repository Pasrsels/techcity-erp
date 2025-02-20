web: gunicorn techcity.wsgi:application
worker: celery --app=techcity.celery worker -Q transfers,notifications --loglevel=info
worker2: celery --app=techcity beat -l INFO

