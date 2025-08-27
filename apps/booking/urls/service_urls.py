from django.urls import path
from apps.booking.views import service_views

urlpatterns = [
    path('', service_views.services_view, name='services_view'),
    path('products/', service_views.services, name='services'),
    path('crud/', service_views.service_crud, name='service_crud'),
    path('save_combined/', service_views.save_combined_service, name='save_combined_service'),
]
