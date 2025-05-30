from django.urls import path
from . views import *

app_name = 'settings'

urlpatterns = [
    path('', settings, name='settings'),
    
    # printing
    path('printer/scan/', scan_for_printers, name='scan_for_printers'),
    path('printer/create_update/', update_or_create_printer, name='update_or_create_printer'),

    # system printers (by lee man)
    path('printer/system/scan-printers/', scan_printers, name='scan_printers'),
    path('printer/system/add-printer/', add_printer, name='add_printer'),
    path('printer/system/get-printers/', get_printers, name='get_printers'),
    path('identify-pc-info', identify_pc, name='identify_pc'),

    # email
    path('email/config/save/',  save_email_config, name='save_email_config'),
    path('email/notification/status/', email_notification_status, name='email_notification_status'),
    
    # tax settings
    path('update_tax_method/', update_tax_method, name='update_tax_method'),
]