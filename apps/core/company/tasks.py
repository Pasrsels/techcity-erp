from apps.inventory.models import Supplier, Inventory


def merge_branch(from_branch, to_branch, options):

    products = Inventory.objects.filter(branch=from_branch)

    for product in products:
        new_product = Inventory.objects.create(
            branch=to_branch,
            name=product.name,
            cost=product.cost,
            price=product.price,
            dealer_price=product.dealer_price,
            quantity=product.quantity,
            status=product.status,
            stock_level_threshold=product.stock_level_threshold,
            reorder=product.reorder,
            alert_notification=product.alert_notification,
            batch=product.batch,
            category=product.category,
            tax_type=product.tax_type,
            description=product.description,
            end_of_day=product.end_of_day,
            service=product.service,
            image=product.image,  
        )
        new_product.suppliers = product.suppliers.all()