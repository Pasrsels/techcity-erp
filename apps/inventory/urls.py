from django.urls import path, include
from . views import *
from rest_framework import routers
from . consumer import InventoryConsumer
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'products', InventoryViewset, basename='api_products')

app_name = 'inventory'

urlpatterns = [
    path('', inventory_index, name='inventory'),
    path('inventory/', inventory, name='inventory_list'),
    path('product/list/', product_list, name='product_list'),
    path('add-product/', AddProductView.as_view(), name='add_product'),
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

    #Stocktake
    path('stocktake/', stock_take_index, name= 'stocktake'),
    path('process_stock_take_item/', process_stock_take_item, name='process_stock_take_item'),
    path('stocktake/detail/<int:stocktake_id>/', stock_take_detail, name='stock_take_detail'),

    #batch_code 
    path('batch_code/', batch_code, name='batch_code'),
    
    # product
    path('create/product/', product, name='product'),
    path('delete_product', delete_product, name='delete'),
    
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
    
    # services
    path('create/service/', service, name='create_service'),
    path('edit/service/<int:service_id>/', edit_service, name='edit_service'),
    
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

    #Categories
    path('api/v1/categories', CategoriesList.as_view(), name = 'api_categories'),
    path('api/v1/categories-add', AddCategories.as_view(), name = 'api_add_categories'),

    #Products
    path('api/v1/products', Products.as_view(), name = 'api_products'),
    path('api/v1/products-add-and-edit', AddProducts.as_view(), name = 'api_add_and_edit_products'),
    path('api/v1/products-delete', DeleteProducts.as_view(), name = 'api_delete_products'),

    #Inventory
    path('api/v1/inventory-list/<int:id>/', InventoryList.as_view(), name = 'api_inventory_list'),
    path('api/v1/inventory-delete/<int:id>/', DeleteInventory.as_view(), name = 'api_delete_inventory'),
    path('api/v1/inventory-edit/<int:product_id>/', EditInventory.as_view(), name = 'api_edit_inventory'),
    path('api/v1/inventory-index', InventoryIndexJson.as_view(), name = 'api_inventory_index_json'),
    path('api/v1/inventory-activate/<int:product_id>/', ActivateInventory.as_view(), name = 'api_inventory_activate'),
    path('api/v1/inventory-branch', BranchesInventory.as_view(), name = 'api_inventory_branch'),

    #Notification
    path('api/v1/notification-json', NotificationJson.as_view(), name = 'api_notification_json'),

    #Stock Take
    path('api/v1/stocktake-view-and-edit', StockTakeViewEdit.as_view(), name = 'api_stock_take'),
    path('api/v1/process-stocktake-item', ProcessStockTakeItem.as_view(), name = 'api_process_stock_take'),
    path('api/v1/stocktake-details', StockTakeDetail.as_view(), name = 'api_stock_take_detail'),

    #Branch
    path('api/v1/branch-view-and-add', BranchCode.as_view(), name = 'api_branch_code'),

    #Supplier
    path('api/v1/supplier-view-add', SupplierViewAdd.as_view(), name= 'api_supplier_view_add'),
    path('api/v1/supplier-list-json', SupplierListJson.as_view(), name= 'api_supplier_list'),
    path('api/v1/supplier-delete-edit/<int:supplier_id>/', SupplierDelete.as_view(), name= 'api_supplier_delete'),
    path('api/v1/supplier-prices/<int:product_id>/', SupplierPrices.as_view(), name= 'api_supplier_prices'),
    path('api/v1/supplier-payment-history/<int:supplier_id>/', SupplierPaymentHistory.as_view(), name= 'api_supplier_payment_history'),
    path('api/v1/supplier-view/<int:supplier_id>/', SupplierView.as_view(), name= 'api_supplier_view'),

    #Reorder
    path('api/v1/reorder-create-and-get', CreateandGetOrder.as_view(), name= 'api_create_get_reorder'),
    path('api/v1/reorder-list-json', ReorderListJson.as_view(), name= 'api_reorder_list_json'),
    path('api/v1/reorder-from-notification', ReorderFromNotification.as_view(), name= 'api_reorder_from_notification'),
    path('api/v1/reorder-add-quantity', AddReorderQuantity.as_view(), name= 'api_add_reorder_quantity'),
    path('api/v1/reorder-settings', ReorderSettings.as_view(), name= 'api_reorder_settings'),

    #Purchase Order
    path('api/v1/purchase-order-list-create', PurchaseOrderListandCreate.as_view(), name= 'api_purchase_order_list_create'),
    path('api/v1/purchase-order-delete-update/<int:purchase_order_id>/', PurchaseOrderDeleteandEdit.as_view(), name= 'api_purchase_order_delete_edit'),
    path('api/v1/purchase-order-print/<int:order_id>/', PrintPurchaseOrder.as_view(), name= 'api_purchase_order_print'),
    path('api/v1/purchase-receive-order/<int:order_id>/', ReceiveOrder.as_view(), name= 'api_purchase_order_receive'),
    path('api/v1/purchase-process-received-order', ProcessReceivedOrder.as_view(), name= 'api_purchase_order_received'),
    path('api/v1/purchase-order-detail', PurchaseOrderDetail.as_view(), name= 'api_purchase_order_detail'),
    path('api/v1/purchase-order-status/<int:order_id>/', PurchaseOrderStatus.as_view(), name= 'api_purchase_order_status'),
    path('api/v1/purchase-order-mark-done/<int:order_id>/', MarkPurchaseOrderDone.as_view(), name= 'api_purchase_order_mark'),
    path('api/v1/purchase-order-sales-price-list-pdf/<int:order_id>/', SalesPriceListPDF.as_view(), name= 'api_purchase_order_sales_price_list_pdf'),
    path('api/v1/purchase-order-confirm-item/<int:order_id>/', PurchaseOrderConfirmOrderItem.as_view(), name= 'api_purchase_order_confirm'),

    #Transfer
    path('api/v1/transfer-print/<int:transfer_id>/', PrintTransfer.as_view(), name= 'api_print_transfer'),
    path('api/v1/transfer-recieve-inventory', RecieveInventory.as_view(), name= 'api_recieve_inventory'),
    path('api/v1/transfer-over-list-stock', OverListStock.as_view(), name= 'api_over_list_stock'),
    path('api/v1/transfer-delete/<int:transfer_id>/', TransferDelete.as_view(), name= 'api_transfer_delete'),
    path('api/v1/transfer-add', AddTransferInventory.as_view(), name= 'api_add_transfer'),
    path('api/v1/transfer-details/<int:transfer_id>/', TransferDetails.as_view(), name= 'api_transfer_details'),
    path('api/v1/transfer-held-json/<int:transfer_id>/', HeldTransferJson.as_view(), name= 'api_transfer_held'),
    path('api/v1/transfer-held', HeldTransfers.as_view(), name= 'api_transfers_held'),
    path('api/v1/process-transfer-held/<int:transfer_id>/', ProcessHeldTransfer.as_view(), name= 'api_process_transfer_held'),

    #Report
    path('api/v1/inventory-pdf', InventoryPDF.as_view(), name='api_inventory_pdf'),
    path('api/v1/inventory-report', InventoryReport.as_view(), name='api_inventory_report'),

    #Accessories
    path('api/v1/accessories_view/<int:product_id>/', AccessoriesView.as_view(), name='api_accessories_view'),
]