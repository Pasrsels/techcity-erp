from django.contrib import admin
from apps.core.company.models import Company, Branch

admin.site.register(Company)
admin.site.register(Branch)