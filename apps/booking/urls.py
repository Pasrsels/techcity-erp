from django.urls import path
from . views import *

app_name = 'booking'

urlpatterns = [
    path('', services_view, name='service'),
    path('service_crud/', service_crud, name='service_crud'),
    
]
