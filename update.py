# update_prices.py
from django.db import transaction
from apps.inventory.models import Inventory  

PRICE_UPDATES = {
    "Itel A06": 80,
}

@transaction.atomic
def run():

    for name, new_price in PRICE_UPDATES.items():
        products = Inventory.objects.filter(name__icontains=name)
        if products.exists():
            count = products.update(price=new_price)
            print(f"✅ Updated {count} products for '{name}' → ${new_price}")
            print(products.values('price', 'name'))
        else:
            print(f"❌ No product found for '{name}'")
PRICE_UPDATES = {
    "Itel A06": 80,
}