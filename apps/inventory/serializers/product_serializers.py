from ..models import *
from rest_framework import serializers

class AddInventorySerializer(serializers.ModelSerializer):
    category = serializers.CharField(write_only=True)

    class Meta:
        model = Inventory
        fields = [
            'id', 'name', 'quantity', 'category', 'cost', 'price', 'dealer_price',
            'tax_type', 'stock_level_threshold', 'description',
            'end_of_day', 'service', 'image'
        ]

    def create(self, validated_data):
        category_name = validated_data.pop('category')
        category, _ = ProductCategory.objects.get_or_create(name=category_name)
        
        validated_data['category'] = category
        validated_data['branch'] = self.context['request'].user.branch
        
        return Inventory.objects.create(**validated_data)

class CategorySerializer(serializers.Serializer):
    model = ProductCategory
    fields = ['name']


class InventorySerializer(serializers.Serializer):
    class Meta:
        model = Inventory
        fields = '__all__'