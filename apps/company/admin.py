from django.contrib import admin
from apps.company.models import Company, Branch

admin.site.register(Company)
admin.site.register(Branch)