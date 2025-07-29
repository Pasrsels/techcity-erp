from django.contrib.auth import login
from .serializers import(
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    LogoutSerializer,
    UserPermissionsSerializer,
    RequestPasswordResetSerializer,
    VerifyOtpSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer
)
from apps.company.models import Branch
from .models import User, UserPermissions
from django.contrib.auth.models import Group
from rest_framework import generics, status, views, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from loguru import logger
from django.conf import Settings
from django.core.mail import send_mail
from datetime import timedelta  
from .models import PasswordResetOTP, EmailVerificationToken
from django.utils import timezone
from django.conf import settings

def send_password_reset_otp(user, otp):
    subject = 'Password Reset OTP'
    message = f'''
    Hello {user.first_name},

    Your OTP for password reset is: {otp}

    This OTP will expire in 10 minutes.

    If you didn't request a password reset, please ignore this email.

    Best regards,
    Posflow Team
    '''
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    logger.info(f'OTP has been sent to {user.email}')


class UserPermissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = UserPermissions.objects.all()
    serializer_class = UserPermissionsSerializer


class BranchSwitch(views.APIView):
    """ Enables the admin or the ownwer to switch between branches """
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id):
        user = request.user
        if user.role == 'Admin' or user.role == 'admin':
            user.branch = Branch.objects.get(id=branch_id)
            user.save()
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        data = {
            'user': user,
            'branch': user.branch
        }
        logger.info(f'User {user.username} changed branch to {user.branch.name}')
        return Response(data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
        An endpoint which allows viewers to be viewed or edited
    """
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class RegisterView(generics.GenericAPIView):
    """
        User registration end point
    """
    serializer_class = RegisterSerializer

    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user_data = serializer.data
        return Response(user_data, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    """
        Login API end point
    """
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutAPIView(generics.GenericAPIView):
    """
        Logout Api End Point
    """
    serializer_class = LogoutSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestPasswordResetView(views.APIView):
    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            if not user.email_verified:
                return Response({"message": "Please verify your email first."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate OTP
            otp = PasswordResetOTP.generate_otp()
            expires_at = timezone.now() + timedelta(minutes=10)
            PasswordResetOTP.objects.create(user=user, otp=otp, expires_at=expires_at)
            send_password_reset_otp(user, otp)

            return Response({"message": "OTP has been sent to your email."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "No user found with this email address."}, status=status.HTTP_404_NOT_FOUND)

class VerifyOtpView(views.APIView):
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
            otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp, is_used=False).latest('created_at')
            if not otp_obj.is_valid():
                otp_obj.increment_attempts()
                return Response({"message": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
            
            otp_obj.mark_as_used()
            request.session['reset_email'] = email
            return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)
        except (User.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return Response({"message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(views.APIView):
    def post(self, request):
        email = request.session.get('reset_email')
        if not email:
            return Response({"message": "Invalid session."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            del request.session['reset_email']
            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class VerifyEmailView(views.APIView):
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        try:
            verification = EmailVerificationToken.objects.get(token=token)
            if not verification.is_valid():
                verification.increment_attempts()
                return Response({"message": "Invalid or expired verification link."}, status=status.HTTP_400_BAD_REQUEST)

            user = verification.user
            user.email_verified = True
            user.save()
            verification.is_verified = True
            verification.save()
            return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)
        except EmailVerificationToken.DoesNotExist:
            return Response({"message": "Invalid verification link."}, status=status.HTTP_404_NOT_FOUND)

