from django.urls import path
from .views import main_views, tax_views, notification_views, printer_views, email_views

app_name = 'settings'

urlpatterns = [
    path('', main_views.settings, name='settings'),

    # Printer URLs
    path('printer/scan/', printer_views.scan_for_printers, name='scan_for_printers'),
    path('printer/update/', printer_views.update_or_create_printer, name='update_or_create_printer'),
    path('printer/add/', printer_views.add_printer, name='add_printer'),
    path('printer/scan_local/', printer_views.scan_printers, name='scan_printers'),
    path('printer/identify_pc/', printer_views.identify_pc, name='identify_pc'),
    path('printer/get_printers/', printer_views.get_printers, name='get_printers'),

    # Email URLs
    path('email/save_config/', email_views.save_email_config, name='save_email_config'),

    # Notification URLs
    path('notification/status/', notification_views.email_notification_status, name='email_notification_status'),

    # Tax URLs
    path('tax/update/', tax_views.update_tax_method, name='update_tax_method'),
]
