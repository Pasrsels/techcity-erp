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
        model = Inventory
        fields = '__all__'