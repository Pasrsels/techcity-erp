import json
from django.core.management.base import BaseCommand, CommandError
from apps.inventory.models import StockTake, StocktakeItem, Product  # adjust model paths

class Command(BaseCommand):
    help = 'Adjust now_quantity for StockTakeItems from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('stocktake_id', type=int, help='ID of the StockTake to adjust')
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing loss data')

    def handle(self, *args, **options):
        stocktake_id = options['stocktake_id']
        json_file = options['json_file']

        try:
            stocktake = StockTake.objects.get(id=stocktake_id)
        except StockTake.DoesNotExist:
            raise CommandError(f'StockTake with id {stocktake_id} does not exist')

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f'Error reading JSON file: {e}')

        items = StocktakeItem.objects.filter(stocktake=stocktake)
        updated_count = 0

        for item in items:
            for entry in data:
                if item.product.name.strip().lower() == entry['product'].strip().lower():
                    print(item.product)
                    item.now_quantity = 0
                    item.save()
                 

        if updated_count == 0:
            self.stdout.write(self.style.WARNING("⚠️  No matching products were updated."))
        else:
            self.stdout.write(self.style.SUCCESS(f"🎯 Successfully updated {updated_count} items."))
