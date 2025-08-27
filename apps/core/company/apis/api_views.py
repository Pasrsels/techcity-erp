from rest_framework import views, status
from rest_framework.response import Response
from ..models import Branch, Company
from ..serializers import BranchSerializer
from loguru import logger
from django.db import transaction
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from apps.core.users.models import User
from utils.validate_json import validate_company_registration_payload

class BranchListandPost(views.APIView):
    def get(self, request):
        branches = Branch.objects.all().values()
        return Response({'branches': branches}, status.HTTP_200_OK)
    def post(self, request):
        if request.data:
            data = request.data

            company = data.get('company')
            name = data.get('name')
            phonenumber = data.get('phonenumber')
            email = data.get('email')
            address = data.get('address')
            if Branch.objects.filter(name = name).exists():
                return Response({'Branch already exists'}, status.HTTP_400_BAD_REQUEST)
            else:
                company_instance = Company.objects.get(id = company)
                Branch.objects.create(
                    company = company_instance,
                    name = name,
                    address = address,
                    phonenumber = phonenumber,
                    email = email
                )
                return Response(status.HTTP_200_OK)
        else:
            return Response({'message': 'Empty!'}, status.HTTP_400_BAD_REQUEST)

class BranchEditandDelete(views.APIView):
    def put(self, request, branch_id):
        if request.data:
            data = request.data

            company = data.get('company')
            name = data.get('name')
            phonenumber = data.get('phonenumber')
            email = data.get('email')
            address = data.get('address')

            if Branch.objects.filter(id = branch_id).exists():
                company_instance = Company.objects.get(id = company)
                branch_instance = Branch.objects.get(id = branch_id)
                branch_instance.company =  Company.objects.get(id = company)
                branch_instance.name = name,
                branch_instance.address = address,
                branch_instance.phonenumber = phonenumber,
                branch_instance.email = email
                branch_instance.save()
                return Response({'Branch updated'}, status.HTTP_202_ACCEPTED)
            else:
                return Response(status.HTTP_404_NOT_FOUND)
        else:
            return Response({'message': 'Empty!'}, status.HTTP_400_BAD_REQUEST)

    def delete(self, request, branch_id):
        branch_instance = Branch.objects.get(id = branch_id)
        branch_instance.delete()
        return Response(status.HTTP_202_ACCEPTED)

class CompanyList(views.APIView):
    def get(self, request):
        company = Company.objects.all().values()
        return Response(company, status.HTTP_200_OK)

class RegisterCompany(views.APIView):
    def post(self, request):
        """
        Company registration view invoked by middleware that checks if a company
        exists in the DB. If not, this view is returned.
        """
        payload = request.data
        logger.info(f"Company registration payload: {payload}")

        is_valid, message = validate_company_registration_payload(payload)
        logger.info(f"is valid: {is_valid}")

        if not is_valid:
            return Response(
                {
                    "success": False,
                },
                status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                company_data = payload['company_data']
                company = Company(
                    name=company_data.get('name'),
                    description=company_data.get('description'),
                    address=company_data.get('address'),
                    domain=company_data.get('domain'),
                    logo=company_data.get('logo'),
                    email=company_data.get('email'),
                    phone_number=company_data.get('phone_number'),
                )
                company.save()
                logger.info(f"Company created: {company}")

                branch = Branch(company=company, name='Warehouse')
                branch.save()

                user = User(
                    first_name=company_data.get('first_name'),
                    last_name=company_data.get('last_name'),
                    username=company_data.get('username'),
                    email=company.email,
                    company=company,
                    phonenumber=company.phone_number,
                    role='admin',
                    branch=branch,
                )
                user.set_password(company_data.get('password'))
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

            return Response(
                {
                    "success": True,
                    "message": "Company registration successful. Please check your email to verify your account."
                },
                status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error during registration: {e}")
            return Response(
                {
                    "success": False,
                    "message": f"Failed to register company: {str(e)}"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
