from . models import Inventory, Product, PurchaseOrderItem
from django.db.models import F, Sum, FloatField
from loguru import logger
from django.db.models.functions import Coalesce


def calculate_inventory_totals(inventory_queryset):
    """
    Optimized calculation of total cost and total price for inventory items,
    handling null values for cost and price.
    """
    totals = inventory_queryset.aggregate(
        total_cost=Sum(F('quantity') * Coalesce(F('cost'), 0), output_field=FloatField()),
        total_price=Sum(F('quantity') * Coalesce(F('price'), 0), output_field=FloatField())
    )

    total_cost = totals.get('total_cost') or 0
    total_price = totals.get('total_price') or 0

    return total_cost, total_price

def average_inventory_cost(product_id, new_cost, new_units, branch_id):
    """ method for calculating Weighted Average Cost Price (WAC)"""
    average_cost = 0
    try:
        product = Inventory.objects.get(id=product_id, branch__id=branch_id)
    except Exception as e:
        logger.info(f'{e}')

    old_units = product.quantity or 0
    old_cost = product.cost or 0

    logger.info(f' product: {product}, old: {old_units}, {old_cost}, new: {new_cost}, {new_units}')

    average_cost = ((old_cost * old_units) + (new_cost * new_units)) / (new_units + old_units)
    logger.info(f'Average stock: {average_cost}')
    return average_cost

def best_price(id):
    """ utility for calculating the best 3 suppliers per product"""
    purchase_orders = PurchaseOrderItem.objects.filter(product_id=id).select_related('supplier')

    supplier_prices = []
    for item in purchase_orders:
        supplier_prices.append(
            {
                'id':item.supplier.id,
                'supplier': item.supplier.name, 
                'price': item.unit_cost
            }
        )

    supplier_prices_sorted = sorted(supplier_prices, key=lambda x: x['price'])

    return supplier_prices_sorted[:3]






