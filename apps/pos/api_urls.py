from django.urls import path
from .apis.api_views import POS, LastDueInvoice

urlpatterns = [
    # API URLS
    path('pos/', POS.as_view(), name='api_pos'),
    path('last_due_invoice/<int:customer_id>/', LastDueInvoice.as_view(), name= 'api_last_due_invoice'),
]
