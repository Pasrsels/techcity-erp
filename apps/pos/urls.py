from django.urls import path
from . views import * 

app_name = 'pos'

urlpatterns = [
    path('', pos, name='pos'),
    path('last_due_invoice/<int:customer_id>/', last_due_invoice, name='last_due_invoice'),

    # end point for mobile
    path('products_list', productsAPIView.as_view(), name='product_list')
]
