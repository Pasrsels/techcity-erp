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