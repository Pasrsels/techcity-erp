from django.urls import path, include
from .views import stocktake_views, supplier_views, loss_management_views, purchase_order_views, report_views
from . import views
from .consumer import InventoryConsumer

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_index, name='inventory'),
    path('inventory/', views.inventory, name='inventory_list'),
    path('notifications/', views.notifications_json, name='notifications_json'),
    path('inventory/branches/', views.branches_inventory, name='branches_inventory'),
    path('inventory/branches/json', views.branches_inventory_json, name='branches_inventory_json'),
    path('detail/<int:id>/', views.inventory_detail, name='inventory_detail' ),
    path('logs/page/', views.logs_page, name='logs-page'),

    # Products
    path('products/', views.inventory_index, name='product_list'),
    path('products/add/', views.add_inventory_view, name='add_product'),
    path('products/edit/<int:product_id>/', views.product, name='edit_inventory'),
    path('products/delete/', views.delete_product, name='delete_product'),
    path('products/category/add/', views.add_product_category, name='add_product_category'),
    
    # settings
    path('settings/', views.settings, name='settings'),
    path('update_notification_settings', views.update_notification_settings, name='update_notification_settings'),

    #Stocktake
    path('stocktake/', stocktake_views.stock_take_index, name='stocktake'),
    path('stocktake/process_item/', stocktake_views.process_stock_take_item, name='process_stock_take_item'),
    path('stocktake/detail/<int:stocktake_id>/', stocktake_views.stock_take_detail, name='stock_take_detail'),
    path('stocktake/undo_accept/', stocktake_views.undo_accept_stocktake_item, name="undo_accept_stocktake"),
    path('stocktake/accept/', stocktake_views.accept_stocktake_item, name='accept_stocktake_item'),
    path('stocktake/confirm/<int:stocktake_id>/', stocktake_views.confirm_stocktake, name='confirm_stocktake'),
    path('stocktake/pdf/',  stocktake_views.stocktake_pdf, name="stocktake_pdf"),
    path('stocktake/<int:stocktake_id>/report/<str:report_type>/', stocktake_views.stocktake_report_data, name='stocktake_report_data'),
    path('stocktake/<int:stocktake_id>/download/<str:report_type>/', stocktake_views.stocktake_report_download, name='stocktake_report_download'),
    path('stocktake/adjust_quantity/', stocktake_views.adjust_stocktake_quantity, name='adjust_stocktake_quantity'),
    #batch_code 
    path('batch_code/', views.batch_code, name='batch_code'),
    
    # suppliers
    path("suppliers/", supplier_views.payments, name="suppliers"),

    # defective
    path('add/defective/product/', loss_management_views.create_defective, name='create_defective_product'),
    
    # re-oder
    path('reorder/list', views.reorder_list, name='reorder_list'),
    path('create/order/list/', views.create_order_list, name='create_order_list'),
    path('reorder/list/json', views.reorder_list_json, name='reorder_list_json'),
    path('clear/reorder/list/', views.clear_reorder_list, name='clear_reorder_list'),
    path('reorder/from/notifications/', views.reorder_from_notifications, name='reorder_from_notifications'),
    path('add/reoder/quantity', views.add_reorder_quantity, name='add_reoder_quantity'),
    path('reorder/settings/', views.reorder_settings, name='reorder_settings'),
    
    # purchase_order
    path('purchase_orders/receive/<int:order_id>/', purchase_order_views.receive_order, name='receive_order'),
    path('purchase_orders/process/', purchase_order_views.process_received_order, name='process_received_order'),
    path('purchase_orders/detail/<int:order_id>/', purchase_order_views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase_orders/delete/<int:purchase_order_id>/', purchase_order_views.delete_purchase_order, name='delete_purchase_order'),
    path('purchase_orders/status/<int:order_id>/', purchase_order_views.change_purchase_order_status, name='change_purchase_order_status'),
    path('purchase_orders/edit/<int:po_id>/', purchase_order_views.edit_purchase_order, name='edit_po'),
    path('purchase_orders/mark_done/<int:po_id>/', purchase_order_views.mark_purchase_order_done, name='mark_done'),
    path('purchase_orders/sales_price_list_pdf/<int:order_id>/', purchase_order_views.sales_price_list_pdf, name='sales_price_list'),
    path('purchase_orders/confirm-items/<int:po_id>/', purchase_order_views.confirm_purchase_order_items, name='confirm_purchase_order'),
    path('purchase_orders/temporary/', purchase_order_views.temporary_purchase_order, name='temporary_purchase_order'),
    path('purchase_orders/get_temporary_items/<int:temp_po_id>/', purchase_order_views.get_temporary_purchase_order_items, name='get_temporary_purchase_order_items'),
    path('purchase_orders/print/<int:order_id>/', purchase_order_views.print_purchase_order, name='print_purchase_order'),
    # delivery note
    path('download_delivery_note/<int:po_id>/', purchase_order_views.download_delivery_note, name='download_delivery_note'),

    # transfers
    path('transfers/', views.inventory_transfer_index, name='transfers'),
    path('transfers/items_data/<int:id>/', views.inventory_transfer_item_data, name='inventory_transfer_data'),
    path('transfers/print/<int:transfer_id>/', views.print_transfer, name='print_transfer'),
    path('transfers/receive/', views.receive_inventory, name='receive_inventory'),
    path('transfers/receive/json/', views.receive_inventory_json, name='receive_inventory_json'),
    path('transfers/over_less_list/', views.over_less_list_stock, name='over_less_list_stock'),
    path('transfers/delete/<int:transfer_id>/', views.delete_transfer, name='delete_transfer'),
    path('transfers/add/', views.add_inventory_transfer, name='add_transfer'),
    path('transfers/detail/<int:transfer_id>/', views.transfer_details, name='transfer_details'),
    path('transfers/process-cart/', views.ProcessTransferCartView.as_view(), name='process_transfer_cart'),
    path('transfers/held_transfer_json/<int:transfer_id>/', views.held_transfer_json, name='held_transfer'),
    path('transfers/held/', views.held_transfers, name='h_transfers'),
    path('transfers/process/held/<int:transfer_id>/', views.process_held_transfer, name='process_held'),
    path('transfers/edit_item/<int:transfer_item_id>/', views.edit_transfer_item, name='edit_transfer_item'),
    path('transfers/add_item/<int:transfer_id>/', views.add_transfer_item, name='add_transfer_item'),
    
    #reporting
    path('reports/inventory-pdf', report_views.inventory_pdf, name='inventory_pdf'),
    path('reports/transfers-report', report_views.transfers_report, name='transfers_report'),
    
    #websocket
    path('ws/inventory/<int:branchId>/', InventoryConsumer.as_asgi()),

    #accessories
    path('get_accessory/<int:product_id>/', views.get_accessory, name='accessory_detail'),
    path('accessory_view/<int:product_id>/', views.accessory_view, name='accessory_view'),

    path('vue_view/', views.vue_view, name='vue'),

    #loss management
    path('loss_management/', loss_management_views.loss_management, name='loss_management'),
    path('loss_management/accounts/<str:account_name>/', loss_management_views.loss_management_accounts, name='loss_management_accounts'),
    path('loss_management/shrinkage/', loss_management_views.create_shrinkage, name='create_shrinkage'),
    path('loss_management/defective/', loss_management_views.create_defective, name='create_defective'),
    path('loss_management/write_off/', loss_management_views.create_write_off, name='create_write_off'),

    path('get-cart-items/', views.get_cart_items, name='get_cart_items'),

    path('api/', include('apps.inventory.api_urls')),
]
