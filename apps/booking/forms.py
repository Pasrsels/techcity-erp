from django import forms
from .models import *

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Services
        exclude = ['delete']