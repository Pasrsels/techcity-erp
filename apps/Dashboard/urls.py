from django.urls import path
from .views import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_views.dashboard, name='dashboard'),
    path('pos/', dashboard_views.POS, name='pos'),
    path('get_partial_invoice_details/<int:invoice_id>/', dashboard_views.get_partial_invoice_details, name='get_partial_invoice_details'),
]
