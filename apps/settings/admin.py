from django.contrib import admin
from .models import NotificationsSettings, TaxSettings, FiscalDay, OfflineReceipt, FiscalCounter, WhatsAppConfig

admin.site.register(NotificationsSettings)
admin.site.register(TaxSettings)
admin.site.register(FiscalDay)
admin.site.register(OfflineReceipt)
admin.site.register(FiscalCounter)
admin.site.register(WhatsAppConfig)

