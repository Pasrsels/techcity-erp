from .models import *
from rest_framework import serializers

class CategorySerializer(serializers.Serializer):
    model = ProductCategory
    fields = ['name']

class InventorySerializer(serializers.Serializer):
    class Meta:
        model = Inventory
        fields = '__all__'