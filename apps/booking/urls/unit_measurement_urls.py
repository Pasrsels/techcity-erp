from django.urls import path
from apps.booking.views import unit_measurement_views

urlpatterns = [
    path('crud/', unit_measurement_views.unit_measurement_crud, name='unit_measurement_crud'),
]
