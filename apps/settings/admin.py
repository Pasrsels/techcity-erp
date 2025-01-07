from django.contrib import admin

from .models import NotificationsSettings, TaxSettings

# class APISettingsAdmin(admin.ModelAdmin):
#     list_display = ['name', 'updated_at']
#     readonly_fields = ['updated_at']
#     fields = ['name', 'api_key', 'cert', 'private_key', 'updated_at']

#     def get_form(self, request, obj=None, **kwargs):
#         form = super().get_form(request, obj, **kwargs)
#         if obj:
#             form.base_fields['api_key'].initial = obj.api_key
#             form.base_fields['cert'].initial = obj.cert
#             form.base_fields['private_key'].initial = obj.private_key
#         return form
    
# admin.site.register(APISettings, APISettingsAdmin)
admin.site.register(NotificationsSettings)
admin.site.register(TaxSettings)

