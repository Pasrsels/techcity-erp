from .models import *
from rest_framework import serializers


class BranchSerializer(serializers.Serializer):
    class Meta:
        model = Branch
        fields = '__all__'