from django.contrib import admin
from apps.vouchers.models import *

admin.site.register(vouchers)
admin.site.register(voucherFile)
admin.site.register(voucherLogs)
admin.site.register(voucherUser)
admin.site.register(voucherCategory)

