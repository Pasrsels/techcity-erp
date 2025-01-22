from django import forms
from loguru import logger
from apps.company.models import Company, Branch
from apps.users.models import User, UserPermissions
from django.contrib.auth.forms import UserCreationForm


class UserRegistrationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'username',
            'email',
            'phonenumber',
            'company',
            'branch',
            'role',
            'password'
        ]


class UserDetailsForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phonenumber',
            'company',
            'branch',
            'role',
        ]

class UserDetailsForm2(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phonenumber',
            'company',
            'branch',
            'role',
        ]

class UserPermissionsForm(forms.ModelForm):
    class Meta:
        model = UserPermissions
        fields = ['name', 'category']
        