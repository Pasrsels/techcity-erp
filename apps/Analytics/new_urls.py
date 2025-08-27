from django.urls import path
from apps.Analytics.views import analytics_views

app_name = 'analytics'

urlpatterns = [
    path('', analytics_views.analytics, name='analytics'),
    path('sales_chart_image/', analytics_views.sales_chart_image, name='sales_chart_image'),
    path('customers_chart_image/', analytics_views.customers_chart_image, name='customers_chart_image'),
    path('sales_by_hour/', analytics_views.sales_by_hour, name='sales_by_hour'),
]
