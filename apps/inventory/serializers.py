from .models import *
from rest_framework import serializers

class CategorySerializer(serializers.Serializer):
    model = ProductCategory
    fields = '__all__'