from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from ..models import Company, Branch
from apps.core.users.models import User
from utils.validate_json import validate_company_registration_payload
from loguru import logger
import json
from apps.core.settings.models import TaxSettings
from apps.core.users.views.authentication_views import login_view

def create_tax_methods():
    tax_methods = ['No tax', 'Inclusice', 'Exclusive']

    tax_obj_list = []
    for method in tax_methods:
        tax_obj_list.append(TaxSettings(
            name=method,
            selected=False
        ))

    TaxSettings.objects.bulk_create(tax_obj_list)


def register_company_view(request):
    """
    Company registration view invoked by middleware that checks if a company
    exists in the DB. If not, this view is returned.
    """
    if request.method == 'GET':
        if Company.objects.exists():
            return redirect('users:login')

    if request.method == 'POST':
        payload = json.loads(request.body)
        logger.info(f"Company registration payload: {payload}")

        is_valid, message = validate_company_registration_payload(payload)
        logger.info(f"is valid: {is_valid}")

        if not is_valid:
            return JsonResponse(
                {
                    "success": False,
                    "message": message
                },
                status=400
            )

        try:
            with transaction.atomic():
                company_data = payload['company_data']
                company = Company(
                    name=company_data['name'],
                    description=company_data['description'],
                    address=company_data['address'],
                    domain=company_data['domain'],
                    logo=company_data['logo'],
                    email=company_data['email'],
                    phone_number=company_data['phone_number'],
                )
                company.save()
                logger.info(f"Company created: {company}")

                branch = Branch(company=company, name='Warehouse')
                branch.save()

                user_data = payload['user_data']
                user = User(
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    username=user_data['username'],
                    email=company.email,
                    company=company,
                    phonenumber=company.phone_number,
                    role='admin',
                    branch=branch,
                )
                user.set_password(user_data['password'])
                user.save()

                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(str(user.pk).encode())

                current_site = get_current_site(request)
                verification_url = f"http://{current_site.domain}/verify/{uid}/{token}/"

                subject = "Activate Your Account"
                message = render_to_string('activation_email.html', {
                    'user': user,
                    'verification_url': verification_url,
                })
                send_mail(subject, message, 'no-reply@yourdomain.com', [user.email])

            return JsonResponse(
                {
                    "success": True,
                    "message": "Company registration successful. Please check your email to verify your account."
                },
                status=200
            )

        except Exception as e:
            logger.error(f"Error during registration: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Failed to register company: {str(e)}"
                },
                status=500
            )

    return render(request, 'registration.html')

def verify_email(request, uidb64, token):
    """ email verification view for the company admin checks the token assigned to a user if so the the user is set to
        active. then is logged in to the system
    """
    try:

        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()

            login_view(request, user)

        else:
            return redirect('verification_failed')

    except Exception:
        return redirect('verification_failed')
