from django.urls import path, include
from . views import *
from rest_framework import routers
from . consumer import InventoryConsumer
from rest_framework.routers import DefaultRouter

from .api import *
from apps.finance.apis.cashbook_apis import *

router = DefaultRouter()
# router.register(r'products', InventoryViewset, basename='api_products')

app_name = 'inventory'

urlpatterns = [
    path('', inventory_index, name='inventory'),
    path('inventory/', inventory, name='inventory_list'),
    path('product/list/', product_list, name='product_list'),
    path('delete-inventory/', delete_inventory, name='delete_inventory'),
    path('notifications/', notifications_json, name='notifications_json'),
    path('add_category/', add_product_category, name='add_product_category'),
    path('inventory/branches/', branches_inventory, name='branches_inventory'),
    path('product/json/', inventory_index_json, name='inventory_index_json'),
    path('edit/<str:product_id>/', edit_inventory, name='edit_inventory'),
    path('activate/product/<int:product_id>/', activate_inventory, name='activate_inventory'),
    path('defective_product_list/', defective_product_list, name='defective_product_list'),
    path('inventory/branches/json', branches_inventory_json, name='branches_inventory_json'),
    path('detail/<int:id>/', inventory_detail, name='inventory_detail' ),
    path('create/product/', product, name='product'),
    path('delete_product', delete_product, name='delete'),
    path('add-inventory', add_inventory_view, name="add-inventory"),
    path('logs/page/', logs_page, name='logs-page'),
    
    # settings
    path('settings/', settings, name='settings'),
    path('update_notification_settings', update_notification_settings, name='update_notification_settings'),

    #Stocktake
    path('stocktake/', stock_take_index, name='stocktake'),
    path('process_stock_take_item/', process_stock_take_item, name='process_stock_take_item'),
    path('stocktake/detail/<int:stocktake_id>/', stock_take_detail, name='stock_take_detail'),
    path('accept_stock_take/', accept_stocktake_item, name='accept_stocktake_item'),
    path('confirm_stocktake/<int:stocktake_id>/', confirm_stocktake, name='confirm_stocktake'),
    path('stocktake_pdf/',  stocktake_pdf, name="stocktake_pdf"),
    path('undo_accept_stocktake/', undo_accept_stocktake_item, name='undo_accept_stocktake'),
    
    #batch_code 
    path('batch_code/', batch_code, name='batch_code'),
    
    # suppliers
    path("suppliers/", supplier_view, name="suppliers"),
    path('supplier/json/list/', supplier_list_json, name='supplier_list_json'),
    path("suppliers/delete/<int:supplier_id>/", supplier_delete, name="delete_supplier"),
    path("suppliers/edit/<int:supplier_id>/", supplier_edit, name="edit_supplier"),
    path('supplier_prices/<int:product_id>/', supplier_prices, name='supplier_prices'),
    path("suppliers/payment-history/<int:supplier_id>/", PaymentHistory, name="payment-history"),
    path('suppliers/supplier-information/<int:supplierId>/', supplier_details_view, name = 'supplier_details'),

    # defective
    path('add/defective/product/', create_defective_product, name='create_defective_product'),
    
    # re-oder
    path('reorder/list', reorder_list, name='reorder_list'),
    path('create/order/list/', create_order_list, name='create_order_list'),
    path('reorder/list/json', reorder_list_json, name='reorder_list_json'),
    path('clear/reorder/list/', clear_reorder_list, name='clear_reorder_list'),
    path('reorder/from/notifications/', reorder_from_notifications, name='reorder_from_notifications'),
    path('add/reoder/quantity', add_reorder_quantity, name='add_reoder_quantity'),
    path('settings/', reorder_settings, name='reorder_settings'),
    
    # purchase_order
    path('purchase_orders/list/', purchase_orders, name='purchase_orders'),
    path('print/purchase_order/<int:order_id>/', print_purchase_order, name='print_purchase_order'),
    path('purchase_order/create/', create_purchase_order, name='create_purchase_order'),
    path('purchase_order/receive/<int:order_id>/', receive_order, name='receive_order'),
    path('process/purchase_order/', process_received_order, name='process_received_order'),
    path('purchase_order/detail/<int:order_id>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchase_order/delete/<int:purchase_order_id>/', delete_purchase_order, name='delete_purchase_order'),
    path('purchase_orders/status/<int:order_id>/', change_purchase_order_status, name='change_purchase_order_status'),
    path('purchase_order/delete/<int:purchase_order_id>/', delete_purchase_order, name='delete_purchase_order'),
    path('edit_purchase_order_data/<int:po_id>/', edit_purchase_order_data, name='edit_po_data'),
    path('edit_purchase_order/<int:po_id>/', edit_purchase_order, name='edit_po'),
    path('mark_purchase_order_done/<int:po_id>/', mark_purchase_order_done, name='mark_done'),
    path('sales_price_list_pdf/<int:order_id>/', sales_price_list_pdf, name='sales_price_list'),
    path('confirm-purchase-order/<int:po_id>/', confirm_purchase_order_items, name='confirm_purchase_order'),
    path('temporary_purchase_order/', temporary_purchase_order, name='temporary_purchase_order'),
    path('get_temporary_purchase_order_items/<int:temp_po_id>/', get_temporary_purchase_order_items, name='get_temporary_purchase_order_items'),

    # delivery note
    path('download_delivery_note/<int:po_id>/', download_delivery_note, name='download_delivery_note'),

    # transfers
    path('transfers', inventory_transfer_index, name='transfers'),
    path('transfer_items_data/<int:id>/', inventory_transfer_item_data, name='inventory_transfer_data'),
    path('print/transfer/<int:transfer_id>/', print_transfer, name='print_transfer'),
    path('receive/transfer/', receive_inventory, name='receive_inventory'),
    path('receive/transfer/json/', receive_inventory_json, name='receive_inventory_json'),
    path('over_less_list/', over_less_list_stock, name='over_less_list_stock'),
    path('delete/transfer/<int:transfer_id>/', delete_transfer, name='delete_transfer'),
    path('add/transfer/', add_inventory_transfer, name='add_transfer'),
    path('transfer/detail/<int:transfer_id>/', transfer_details, name='transfer_details'),
    path('process-transfer-cart/', ProcessTransferCartView.as_view(), name='process_transfer_cart'),
    path('held_transfer_json/<int:transfer_id>/', held_transfer_json, name='held_transfer'),
    path('held/transfers/', held_transfers, name='h_transfers'),
    path('process/held/transfer/<int:transfer_id>/', process_held_transfer, name='process_held'),
    path('edit_transfer_item/<int:transfer_item_id>/', edit_transfer_item, name='edit_transfer_item'),
    path('add_transfer_item/<int:transfer_id>/', add_transfer_item, name='add_transfer_item'),
    
    #reporting
    path('inventory-pdf', inventory_pdf, name='inventory_pdf'),
    path('transfers-report', transfers_report, name='transfers_report'),
    
    #websocket
    path('ws/inventory/<int:branchId>/', InventoryConsumer.as_asgi()),

    #accessories
    path('get_accessory/<int:product_id>/', get_accessory, name='accessory_detail'),
    path('accessory_view/<int:product_id>/', accessory_view, name='accessory_view'),

    path('vue_view/', vue_view, name='vue'),

    #loss management
    path('loss_management/', loss_management, name='loss_management'),
    path('loss_management_accounts/<str:account_name>/', loss_management_accounts, name='loss_management_accounts'),
    path('shrinkage/', create_shrinkage, name='create_shrinkage'),
    path('defective/', create_defective, name='create_defective'),
    path('write_off/', create_write_off, name='create_write_off'),

    #API ENDPOINTS
    ################################################################################################

     path('get-cart-items/', get_cart_items, name='get_cart_items'),
]