from .models import *
from rest_framework import serializers

class StockNotificationSerializer(serializers.Serializer):
    class Meta:
        model = StockNotifications
        fields = '__all__'

class PurchaseOrderSerializer(serializers.Serializer):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class DefectiveProductSerializer(serializers.Serializer):
    class Meta:
        models = DefectiveProduct
        fields = ['product', 'quantity', 'reason', 'status',]

class StockTakeSerializer(serializers.Serializer):
    class Meta:
        model = StockTake
        exclude = ['branch', 's_t_number']

class TransferSerializer(serializers.Serializer):
    class Meta:
        model = Transfer
        fields = '__all__'