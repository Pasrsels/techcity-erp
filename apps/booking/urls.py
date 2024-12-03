from django.urls import path
from .views import *

app_name = 'booking'

urlpatterns = [
    path('', services_view, name='service_view'),
     path('services/', services, name='services'),
    path('service_product_crud/', itemofuseCrud, name='service_product_crud'),
    path('serviceCrud/', ServiceCrud, name='serviceCrud'),
    path('service_crud/', service_crud, name='service_crud'),
    #path('service_range_crud/', service_range_crud, name='service_range_crud'),
    path('unit_measurement_crud/', unit_measurement_crud, name='unit_measurement_crud'),
    #path('service_data/', ServiceData, name = 'service_data'),
    path('member/', members_view, name= 'member'),
    path('member_crud/', member_crud, name= 'members'),
    path('member_acc_crud/', member_acc_crud, name= 'members_acc'),
    path('payments/', payments_crud, name= 'payments'),
]
