from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

app_name = 'users'

router = DefaultRouter()
router.register(r'api/v1/users/', UserViewSet, basename='users')
router.register(r'permissions/', UserPermissionViewSet, basename='userpermissions')

urlpatterns = [
    path('users/', users, name='users'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('delete/user/<int:user_id>/', delete_user, name='delete'),
    path('user/edit/<int:user_id>/', user_edit, name='user_edit'),
    path('user/detail/<int:user_id>/', user_detail, name='user_detail'),
    path('ajax/load-branches/', load_branches, name='ajax_load_branches'),
    path('ajax/get-user-data/<int:user_id>/', get_user_data, name='ajax_get_user_data'),
    
    path('profile/', user_profile, name='profile'),
    path('upload-profile/', upload_profile, name='upload-profile'),
    
    # Password Reset Flow
    path('request-password-reset/', request_password_reset, name='request_password_reset'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('reset-password/', reset_password, name='reset_password'),
    
    #User Permissions
    path('permissions/create-and-read/', UserPermission_CR, name= 'userPermissionsCR'),
    path('permission/update-and-delete/<int:id>/', UserPermission_UD, name= 'userPermissionsUD'),

    #api v1/end point
    path('api/v1/register/', RegisterView.as_view(), name="api_register"),
    path('api/v1/login/', LoginAPIView.as_view(), name="api_login"),
    path('api/v1/logout/', LogoutAPIView.as_view(), name="api_logout"),
    path('api/v1/branch-switch/<int:branch_id>/', BranchSwitch.as_view(), name='api_branch_switch'),
    path('', include(router.urls))
]
