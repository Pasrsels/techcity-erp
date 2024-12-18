from .models import *
from rest_framework import serializers

class CategorySerializer(serializers.Serializer):
    model = ProductCategory
    fields = ['name']

class InventorySerializer(serializers.Serializer):
    class Meta:
        model = Inventory
        fields = '__all__'

class StockNotificationSerializer(serializers.Serializer):
    class Meta:
        model = StockNotifications
        fields = '__all__'

class PurchaseOrderSerializer(serializers.Serializer):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class InventorySerializer(serializers.Serializer):
    class Meta:
        model = Inventory
        fields = '__all__'