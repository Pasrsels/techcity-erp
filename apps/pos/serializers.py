from rest_framework import serializers
from apps.inventory.models import Inventory

class SalesProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = ['id', 'name', 'selling_price', 'dealer_price']
