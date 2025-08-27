from django.urls import path
from .views import category_views, item_of_use_views, member_views, service_views, unit_measurement_views

app_name = 'booking'

urlpatterns = [
    #services
    path('services/', service_views.services_view, name='services_view'),
    path('services/products/', service_views.services, name='services'),
    path('services/crud/', service_views.service_crud, name='service_crud'),
    path('services/save_combined/', service_views.save_combined_service, name='save_combined_service'),

    #unit_measurement
    path('unit_measurement/crud/', unit_measurement_views.unit_measurement_crud, name='unit_measurement_crud'),

    #members
    path('members/', member_views.members_view, name='members_view'),
    path('members/crud/', member_views.member_crud, name='member_crud'),

    #category
    path('category/crud/', category_views.category_crud, name='category_crud'),

    #item of use
    path('item_of_use/crud/', item_of_use_views.itemofuseCrud, name='itemofuse_crud'),
    path('item_of_use/crud2/', item_of_use_views.item_of_use_crud, name='item_of_use_crud'),
]
