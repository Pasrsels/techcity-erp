from django import forms
from .models import *
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Services
        exclude = ['delete']

class Service_productForm(forms.ModelForm):
    class Meta:
        model = ServiceProduct
        fields = '__all__'

class UnitForm(forms.ModelForm):
    class Meta:
        model = UnitMeasurement
        fields = '__all__'

class RangeForm(forms.ModelForm):
    class Meta:
        model = ServiceRange
        fields = '__all__'
