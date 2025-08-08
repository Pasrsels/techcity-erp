import json
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render, redirect
from loguru import logger
from django.contrib.auth import get_user_model
from apps.company.models import Branch
from apps.settings.models import NotificationsSettings
from utils.authenticate import authenticate_user
from ..models import User, UserPermissions, EmailVerificationToken, PasswordResetOTP
from ..forms import UserRegistrationForm, UserDetailsForm, UserDetailsForm2, UserPermissionsForm
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password
from utils.validate_redirect import is_safe_url
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from utils.send_verification_email import *
from django.db import transaction
from django.contrib.auth import authenticate
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
import time
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.conf import settings