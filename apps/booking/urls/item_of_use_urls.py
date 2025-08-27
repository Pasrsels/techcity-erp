from django.urls import path
from apps.booking.views import item_of_use_views

urlpatterns = [
    path('crud/', item_of_use_views.itemofuseCrud, name='itemofuse_crud'),
    path('crud2/', item_of_use_views.item_of_use_crud, name='item_of_use_crud'),
]
