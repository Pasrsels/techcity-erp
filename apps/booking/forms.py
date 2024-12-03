from django import forms
from .models import *
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Services
        exclude = ['delete']

class UnitForm(forms.ModelForm):
    class Meta:
        model = UnitMeasurement
        fields = '__all__'

class RangeForm(forms.ModelForm):
    class Meta:
        model = ServiceRange
        fields = '__all__'

class InventoryForm(forms.ModelForm):
    class Meta:
        model = inventory
        fields = '__all__'
        # fields = ['name', 'cost', 'category', 'quantity']