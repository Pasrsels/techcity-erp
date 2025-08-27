from django.urls import path
from apps.booking.views import member_views

urlpatterns = [
    path('', member_views.members_view, name='members_view'),
    path('crud/', member_views.member_crud, name='member_crud'),
]
