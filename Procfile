web: gunicorn techcity.wsgi  
worker: celery -A techcity worker -Q transfers,notifications --loglevel=info

