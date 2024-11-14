from django.contrib import admin

from .models import NotificationsSettings, TaxSettings

admin.site.register(NotificationsSettings)
admin.site.register(TaxSettings)

