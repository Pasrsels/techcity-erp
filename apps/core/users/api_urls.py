from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .apis import api_views

router = DefaultRouter()
router.register(r'v1/users', api_views.UserViewSet, basename='users')
router.register(r'permissions', api_views.UserPermissionViewSet, basename='userpermissions')

urlpatterns = [
    # API v1
    path('v1/register/', api_views.RegisterView.as_view(), name="api_register"),
    path('v1/login/', api_views.LoginAPIView.as_view(), name="api_login"),
    path('v1/logout/', api_views.LogoutAPIView.as_view(), name="api_logout"),
    path('v1/branch-switch/<int:branch_id>/', api_views.BranchSwitch.as_view(), name='api_branch_switch'),
    path('v1/password-reset/', api_views.RequestPasswordResetView.as_view(), name='request_password_reset'),
    path('v1/verify-otp/', api_views.VerifyOtpView.as_view(), name='verify_otp'),
    path('v1/reset-password/', api_views.ResetPasswordView.as_view(), name='reset_password'),
    path('v1/verify-email/', api_views.VerifyEmailView.as_view(), name='verify_email'),
    path('', include(router.urls))
]
