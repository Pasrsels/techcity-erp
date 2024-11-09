from django.urls import path
from . views import *

app_name = 'booking'

urlpatterns = [
    path('', services_view, name='service')
    
]
