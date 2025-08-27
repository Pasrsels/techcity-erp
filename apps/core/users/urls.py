from django.urls import path, include
from .views import (
    authentication_views,
    profile_views,
    permission_views
)

app_name = 'users'

urlpatterns = [
    # User management
    path('users/', profile_views.users, name='users'),
    path('delete/user/<int:user_id>/', profile_views.delete_user, name='delete'),
    path('user/edit/<int:user_id>/', profile_views.user_edit, name='user_edit'),
    path('user/detail/<int:user_id>/', profile_views.user_detail, name='user_detail'),
    path('ajax/load-branches/', profile_views.load_branches, name='ajax_load_branches'),
    path('ajax/get-user-data/<int:user_id>/', profile_views.get_user_data, name='ajax_get_user_data'),

    # Authentication
    path('auth/login/', authentication_views.login_view, name='login'),
    path('auth/logout/', authentication_views.logout_view, name='logout'),
    path('auth/register/', authentication_views.register, name='register'),
    path('auth/verify-email/<str:signed_token>/', authentication_views.verify_email, name='verify_email'),
    path('auth/request-password-reset/', authentication_views.request_password_reset, name='request_password_reset'),
    path('auth/verify-otp/', authentication_views.verify_otp, name='verify_otp'),
    path('auth/reset-password/', authentication_views.reset_password, name='reset_password'),

    # Profile
    path('profile/', profile_views.user_profile, name='profile'),
    path('profile/upload/', profile_views.upload_profile, name='upload_profile'),

    # User Permissions
    path('permissions/create-and-read/', permission_views.UserPermission_CR, name='userPermissionsCR'),
    path('permissions/update-and-delete/<int:id>/', permission_views.UserPermission_UD, name='userPermissionsUD'),

    path('api/', include('apps.core.users.api_urls')),
]
