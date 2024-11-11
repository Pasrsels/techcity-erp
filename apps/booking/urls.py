from django.urls import path
from . views import *

app_name = 'booking'

urlpatterns = [
    path('', services_view, name='service'),
    path('booking/service_crud/', service_crud, name='service_crud'),
    path('booking/types_crud/', type_crud, name= 'types'),
    path('booking/member_crud/', member_crud, name= 'members'),
    path('booking/member_acc_crud/', member_acc_crud, name= 'members_acc'),
    path('booking/payments/', payments_crud, name= 'payments'),
    path('booking/office/', office_crud, name= 'office'),
]
