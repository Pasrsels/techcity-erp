from .models import Inventory, Product, PurchaseOrderItem
from django.db.models import F, Sum, FloatField, Q
from loguru import logger
from django.db.models.functions import Coalesce
import datetime
from django.core.files.base import ContentFile
from io import BytesIO
from xhtml2pdf import pisa
from django.template.loader import get_template
from apps.inventory.models import ActivityLog

def calculate_inventory_totals(inventory_queryset):
    logger.info("Calculating inventory totals...")
    totals = inventory_queryset.aggregate(
        total_cost=Sum(F('quantity') * Coalesce(F('cost'), 0), output_field=FloatField()),
        total_price=Sum(F('quantity') * Coalesce(F('price'), 0), output_field=FloatField())
    )
    total_cost = totals.get('total_cost') or 0
    total_price = totals.get('total_price') or 0
    logger.info(f"Total cost: {total_cost}, Total price: {total_price}")
    return total_cost, total_price

def average_inventory_cost(product_id, new_cost, new_units, branch_id):
    logger.info(f"Calculating average inventory cost for product_id={product_id}, branch_id={branch_id}")
    try:
        product = Inventory.objects.get(id=product_id, branch__id=branch_id)
    except Exception as e:
        logger.error(f"Error fetching product: {e}")
        return 0

    old_units = product.quantity or 0
    old_cost = product.cost or 0
    logger.info(f"Old units: {old_units}, Old cost: {old_cost}, New cost: {new_cost}, New units: {new_units}")

    try:
        average_cost = ((old_cost * old_units) + (new_cost * new_units)) / (new_units + old_units)
    except ZeroDivisionError:
        logger.warning("ZeroDivisionError: No units available for average cost calculation.")
        average_cost = 0

    logger.info(f"Weighted Average Cost: {average_cost}")
    return average_cost

def best_price(id):
    logger.info(f"Finding best price for product_id={id}")
    purchase_orders = PurchaseOrderItem.objects.filter(product_id=id).select_related('supplier')
    supplier_prices = []
    for item in purchase_orders:
        supplier_prices.append(
            {
                'id': item.supplier.id,
                'supplier': item.supplier.name,
                'price': item.unit_cost
            }
        )
    supplier_prices_sorted = sorted(supplier_prices, key=lambda x: x['price'])
    logger.info(f"Best 3 supplier prices: {supplier_prices_sorted[:3]}")
    return supplier_prices_sorted[:3]

def generete_delivery_note(purchase_order, purchase_order_items, request):
    logger.info("Generating delivery note (function not implemented).")
    pass

def get_inventory_movements(product, branch=None):
    logger.info(f"Getting inventory movements for product_id={product.id}, branch={branch}")
    filters = Q(inventory=product)
    if branch:
        filters &= Q(branch=branch)

    sold = ActivityLog.objects.filter(filters & Q(action='Sale')).aggregate(total=Sum('quantity'))['total'] or 0
    received = ActivityLog.objects.filter(filters & Q(action='stock in')).aggregate(total=Sum('quantity'))['total'] or 0
    transferred = ActivityLog.objects.filter(filters & Q(action='transfer out')).aggregate(total=Sum('quantity'))['total'] or 0

    logger.info(f"Movements - Sold: {sold}, Received: {received}, Transferred: {transferred}")
    return {
        'sold': abs(sold),
        'received': abs(received),
        'transferred': abs(transferred),
    }

def process_stocktake_item_util(stocktake_item, physical_quantity):
    logger.info(f"Processing stocktake item: {stocktake_item.id} with physical_quantity: {physical_quantity}")
    product = stocktake_item.product

    expected_quantity = stocktake_item.now_quantity + stocktake_item.received_quantity - stocktake_item.sold_quantity - stocktake_item.transfer_quantity - stocktake_item.transfer_quantity

    logger.info(f"Expected quantity: {expected_quantity}")

    phy_quantity = int(physical_quantity)
    difference = phy_quantity - expected_quantity
    logger.info(f"Physical quantity: {phy_quantity}, Difference: {difference}")

    stocktake_item.quantity = phy_quantity
    stocktake_item.quantity_difference = difference
    stocktake_item.cost = product.cost * difference

    stocktake_item.stocktake.negative = difference
    stocktake_item.stocktake.positive = phy_quantity

    stocktake_item.recorded = True
    stocktake_item.stocktake.save()
    stocktake_item.save()

    logger.info(
        f"Stocktake item updated: id={stocktake_item.id}, "
        f"difference={difference}, expected_quantity={expected_quantity},"
    )

    return {
        'item_id': stocktake_item.id,
        'difference': difference,
        'expected_quantity': expected_quantity,
    }