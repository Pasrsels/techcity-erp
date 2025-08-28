from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.inventory.models import Inventory

class Command(BaseCommand):
    help = 'Deletes duplicate Inventory items with the same name and zero quantity in the ADMINSTRATION branch'

    def handle(self, *args, **kwargs):
        duplicates = (
            Inventory.objects
            .filter(branch__name='ADMINSTRATION', quantity=0)
            .values('name', 'quantity')
            .annotate(name_count=Count('id'))
            .filter(name_count__gt=1)
        )

        total_deleted = 0

        for dup in duplicates:
            print(f'{dup} \n')
            items = Inventory.objects.filter(
                branch__name='ADMINSTRATION',
                quantity=0,
                name=dup['name']
            ).order_by('id') 
  
            for item in items[1:]:  # Skip the first one
                item.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {total_deleted} duplicate zero-quantity inventory items."))
