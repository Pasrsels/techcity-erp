from apps.inventory.models import Inventory
from rest_framework import serializers


class ProductsSerializers(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'
        depth = 1