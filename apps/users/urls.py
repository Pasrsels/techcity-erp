from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

app_name = 'users'

router = DefaultRouter()
router.register(r'api/users/', UserViewSet, basename='users')
router.register(r'permissions/', UserPermissionViewSet, basename='userpermissions')

urlpatterns = [
    path('users/', users, name='users'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('user/edit/<int:user_id>/', user_edit, name='user_edit'),
    path('user/detail/<int:user_id>/', user_detail, name='user_detail'),
    path('ajax/load-branches/', load_branches, name='ajax_load_branches'),
    path('ajax/get-user-data/<int:user_id>/', get_user_data, name='ajax_get_user_data'),
    
    #User Permissions
    path('permissions/create-and-read/', UserPermission_CR, name= 'userPermissionsCR'),
    path('permission/update-and-delete/<int:id>/', UserPermission_UD, name= 'userPermissionsUD'),

    #api end point
    path('api/register/', RegisterView.as_view(), name="api_register"),
    path('api/login/', LoginAPIView.as_view(), name="api_login"),
    path('api/logout/', LogoutAPIView.as_view(), name="api_logout"),
    path('api/branch-switch/<int:branch_id>/', BranchSwitch.as_view(), name='api_branch_switch'),
    path('', include(router.urls))
]
