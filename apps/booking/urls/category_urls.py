from django.urls import path
from apps.booking.views import category_views

urlpatterns = [
    path('crud/', category_views.category_crud, name='category_crud'),
]
