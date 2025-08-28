from django.urls import path
from . views import * 

app_name = 'pos'

urlpatterns = [
    path('', pos, name='pos'),
    path('new_pos/', new_pos, name='new_pos'),
    path('last_due_invoice/<int:customer_id>/', last_due_invoice, name='last_due_invoice'),

    #API URL PATTERNS
    ###################################################################################################
    path('POS/', POS.as_view(), name='api_pos'),
    path('last_due_invoice/<int:customer_id>/', LastDueInvoice.as_view(), name= 'api_last_due_invoice'),
]
