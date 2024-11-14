from django.contrib import admin
from .models import *

admin.site.register(Inventory)
admin.site.register(Product)
admin.site.register(ProductCategory)
admin.site.register(Transfer)
admin.site.register(ActivityLog)
admin.site.register(StockNotifications)
admin.site.register(TransferItems)
admin.site.register(ReorderList)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(BatchCode)
admin.site.register(otherExpenses)
admin.site.register(costAllocationPurchaseOrder)
<<<<<<< HEAD
admin.site.register(Supplier)
=======
admin.site.register(Supplier)
>>>>>>> 9653a2daed53fee3bbe0d2b5199727821e11a90b
