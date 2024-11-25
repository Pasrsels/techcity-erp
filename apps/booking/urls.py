from django.urls import path
from . views import *
from .views import service_crud



app_name = 'booking'

urlpatterns = [
    path('', services_view, name='service'),
    path('member/', members_view, name= 'member'),
    path('office/',offices_view, name= 'office'),

    path('service_crud/', service_crud, name='service_crud'),
    path('types_crud/', type_crud, name= 'types'),
    path('member_crud/', member_crud, name= 'members'),
    path('service-crud/', service_crud, name='service_crud'),
]

