from django.urls import path
from .apis import api_views

urlpatterns = [
    # API URLs
    path('branch-list-post/', api_views.BranchListandPost.as_view(), name='api_branch_list_post'),
    path('branch-edit-delete/<int:branch_id>/', api_views.BranchEditandDelete.as_view(), name='api_branch_edit_delete'),
    path('company-list/', api_views.CompanyList.as_view(), name='api_company_crud'),
    path('company-register/', api_views.RegisterCompany.as_view(), name='api_register_company'),
]
