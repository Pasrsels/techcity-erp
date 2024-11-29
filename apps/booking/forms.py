from django import forms
from .models import *
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Services
        exclude = ['delete']

class Service_productForm(forms.ModelForm):
    class Meta:
        model = Service_product
        fields = '__all__'

class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit_Measurement
        fields = '__all__'

class RangeForm(forms.ModelForm):
    class Meta:
        model = Service_range
        fields = '__all__'