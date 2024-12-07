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

    #members
    path('service_personal_details/<int:service_id>/', service_detail, name= 'service_personal_details'),
    path('items_of_use_detail/', service_detail_crud, name= 'service_details_crud'),
    # path('member_acc_crud/', member_acc_crud, name= 'members_acc'),
    # path('payments/', payments_crud, name= 'payments'),

    #category
    path('category_crud/', category_crud, name='category_crud'),

    #item of use
    path('item_of_use_crud', item_of_use_crud, name='item_of_use_crud'),
    path('save_combined_service/', save_combined_service, name='save_combined_service'),
]
