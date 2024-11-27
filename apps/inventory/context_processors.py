from techcity.settings.development import LOW_STOCK_THRESHHOLD
from apps.inventory.models import ProductCategory, Inventory, StockNotifications, TransferItems, Product

def product_category_list(request):
    return {'categories': ProductCategory.objects.all()}

def product_list(request):
    if request.user.id != None:
       return { 'inventory': Inventory.objects.filter(branch=request.user.branch, status=True).order_by('quantity')}
    return {}

def all_products_list(request):
    if request.user.id != None:
       return { 'products': Product.objects.all()}
    return {}

def stock_notification_count(request):
    if request.user.id != None:
       return { 'notis_count': StockNotifications.objects.filter(
           type='stock level',
           status=True,
           inventory__branch=request.user.branch
        ).count()}
    return {}

def transfers(request):
    if request.user.id != None:
        return { 'transfers_count': TransferItems.objects.filter(
           received=False,
           to_branch=request.user.branch,
           transfer__delete = False
        ).count()}
    return {}

def stock_notifications(request):
    if request.user.id != None:
        notifications = StockNotifications.objects.filter(inventory__branch=request.user.branch, inventory__reorder=False, inventory__alert_notification=False)
        return (
            {
                'inv_notifications_count':notifications.count(),
                'stock_notifications':notifications,
            }
        )
    return {}
    