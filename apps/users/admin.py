from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField, UserCreationForm

from apps.users.models import User


class CustomUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'branch',
            'groups',
            'phonenumber',
            'role',
            'password',
            'is_active',
            'is_superuser'
        )

    def clean_password(self):
        return self.initial["password"]


class CustomUserAdmin(DefaultUserAdmin):
    form = CustomUserChangeForm
    add_form = UserCreationForm
    model = User

    # Define fieldsets for user detail view
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phonenumber')}),
        ('Permissions', {'fields': ('is_active', 'is_superuser', 'groups')}),
        ('Custom Fields', {'fields': ('branch', 'code', 'role')}),
    )

    # Define fieldsets for add user view
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
            'username', 'first_name', 'last_name', 'email', 'branch', 'code', 'phonenumber', 'role', 'password1',
            'password2', 'is_active', 'is_superuser', 'groups'),
        }),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_superuser')
    list_filter = ('is_superuser',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups',)


admin.site.register(User, CustomUserAdmin)
