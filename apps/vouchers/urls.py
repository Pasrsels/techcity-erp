from . import views
from django.urls import path

app_name = 'vouchers'

urlpatterns = [
    path('voucherLogs/', views.voucherLog, name='voucherLogs'),
    path('addCategory/', views.addCategory, name='addCategory'),
    path("voucherList/", views.vouchersList,  name="voucherList"),
    path("voucherFiles/", views.voucherFiles,  name="voucherFiles"),
    path('printVoucher/<int:pk>/', views.printVoucher, name='printVoucher'),
    path('addVoucherUser/<int:pk>/', views.addVoucherUser, name='addVoucherUser'),
    path("populateVouchers/<int:pk>", views.populateVouchers,  name="populateVouchers"),
]
