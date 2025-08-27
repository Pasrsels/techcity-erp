# update_prices.py
from django.db import transaction
from apps.inventory.models import Inventory  

PRICE_UPDATES = {
    "samsung A05S": 130,
    "samsung Galaxy M14": 120,
    "samsung Galaxy M16 - 128/4GB": 150,
    "Itel A06": 80,
    "Itel city 100 - itel phone": 100,
    "Tecno pop 10 Pro": 100,
    "Infinix hot 60i - 128gb": 110,
    "Infinix hot 60i - 256gb": 125,
    "Infinix smart 10T plus": 105,
    "Pop 10c - 64/2GB": 90,
}

@transaction.atomic
def run():
    for product in Inventory.objects.all():
        print(product.name)
    # for name, new_price in PRICE_UPDATES.items():
    #     print(Inventory.objects.all())
    #     products = Inventory.objects.filter(name__icontains=name)
    #     # if products.exists():
    #     #     count = products.update(price=new_price)
    #     #     print(f"✅ Updated {count} products for '{name}' → ${new_price}")
    #     # else:
    #     #     print(f"❌ No product found for '{name}'")
run()
