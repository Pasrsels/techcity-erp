from django.urls import path
from .apis import products_api

urlpatterns = [
    path('products/', products_api.ProductsListView.as_view(), name='product_list_create'),
    path('products/<int:pk>/', products_api.ProductsListView.as_view(), name='product_detail'),
]
