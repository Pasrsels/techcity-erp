from django.urls import path, include
from .views import pos_views, invoice_views, payment_views

app_name = 'pos'

urlpatterns = [
    # POS URLs
    path('', pos_views.pos, name='pos'),
    path('new/', pos_views.new_pos, name='new_pos'),

    # Invoice URLs
    path('invoice/create/', invoice_views.create_invoice, name='create_invoice'),
    path('invoice/last-due/<int:customer_id>/', invoice_views.last_due_invoice, name='last_due_invoice'),
    path('invoice/preview/json/<int:invoice_id>/', invoice_views.invoice_preview_json, name='invoice_preview_json'),

    # Payment URLs
    path('payment/paylaters/', payment_views.paylaters, name='paylaters'),
    path('payment/laybyes/', payment_views.laybyes, name='laybyes'),

    path('api/', include('apps.pos.api_urls')),
]
