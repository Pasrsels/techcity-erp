from django.urls import path, include
from .views import company_views, branch_views

app_name = 'company'

urlpatterns = [
    # Company URLs
    path('register/', company_views.register_company_view, name='register'),
    # path('verify/<str:uidb64>/<str:token>/', company_views.verify_email, name='verify_email'),

    # Branch URLs
    path('branches/', branch_views.branch_list, name='branches'),
    path('branches/add/', branch_views.add_branch, name='add_branch'),
    path('branches/edit/<int:branch_id>/', branch_views.edit_branch, name='edit_branch'),
    path('branches/delete/<int:branch_id>/', branch_views.delete_branch, name='delete_branch'),
    path('branches/switch/<int:branch_id>/', branch_views.branch_switch, name='branch_switch'),

    path('api/', include('apps.core.company.api_urls')),
]
