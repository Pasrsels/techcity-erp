import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from loguru import logger
from apps.finance.models import VATRate
from apps.users.models import User
from utils.validate_json import validate_company_registration_payload
from .models import Branch, Company
from django.contrib import messages
from .forms import BranchForm
from apps.settings.models import TaxSettings
from django.db import transaction
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from apps.company.models import Company, Branch
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from apps.users.views import login_view
from apps.users.models import User
from django.contrib.auth.decorators import login_required


def register_company_view(request):
    """ 
    Company registration view invoked by middleware that checks if a company 
    exists in the DB. If not, this view is returned.
    """
    if request.method == 'GET':
        # Check if a company already exists, if so, redirect to login
        if Company.objects.exists():
            return redirect('users:login')

    if request.method == 'POST':
        payload = json.loads(request.body)
        logger.info(f"Company registration payload: {payload}")

        # Validate the registration payload
        is_valid, message = validate_company_registration_payload(payload)
        logger.info(f"is valid: {is_valid}")

        if not is_valid:
            messages.error(request, message)
            return JsonResponse(
                {
                    "success": False,
                    "message": message
                },
                status=400
            )

        try:
            with transaction.atomic():
                # Create company
                logger.info("Creating company...")
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

                # Create a default branch
                branch = Branch(company=company, name='Warehouse')
                branch.save()

                # Create the user (admin of the company)
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

                # Generate token and UID for email verification
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(str(user.pk).encode())

                # Build verification URL
                current_site = get_current_site(request)
                verification_url = f"http://{current_site.domain}/verify/{uid}/{token}/"

                # Send verification email
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

        # Validate token
        if default_token_generator.check_token(user, token):
            user.is_active = True  
            user.save()

            login_view(request, user)

        else:
            return redirect('verification_failed')  

    except Exception:
        return redirect('verification_failed') 

def create_tax_methods():
    tax_methods = ['No tax', 'Inclusice', 'Exclusive']

    tax_obj_list = []
    for method in tax_methods:
        tax_obj_list.append(TaxSettings(
            name=method,
            selected=False
        ))
    
    TaxSettings.objects.bulk_create(tax_obj_list)

@login_required
def branch_list(request):
    """ list all the branches in the system """
    form = BranchForm
    branches = Branch.objects.filter(disable=False)
    return render(request, 'branches.html', {
        'branches': branches,
        'form':form
    })

@login_required
def branch_switch(request, branch_id):
    """ Enables the admin or the ownwe to switch between branches """
    user = request.user
    if user.role == 'Admin' or user.role == 'admin':
        user.branch = Branch.objects.get(id=branch_id)
        user.save()
    else:
        messages.error(request, 'You are not authorized')
    return redirect('pos:pos')

@login_required
def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        merge_from_branch = request.POST.get('from_branch')
        if form.is_valid():
            """ take data for merging data"""
            merge_from_branch = form.cleaned_data.get('from_branch')
            selected_options = form.cleaned_data.get('options')
            
            logger.info(f'product option {selected_options}')
            form.save()
            return JsonResponse({'success': True, 'message': 'Branch added successfully!'})
        else:
            return JsonResponse({'success': False, 'message': 'Form submission failed. Please check the inputs.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


# @permissions(['Admin'])
@login_required
def edit_branch(request, branch_id):
    """ edit/branch update view"""
    branch = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch updated successfully!')
            return redirect('company:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(
        request,
        'edit_branch.html',
        {
            'form': form,
            'branch': branch
        }
    )

@login_required
def delete_branch(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
        logger.info(branch)
        branch.disable=True
        branch.save()
        return redirect('company:branch_list')
    except Exception as e:
        messages(request, f'{e}')
    return redirect('company:branch_list')

#API
###########################################################################################################
from rest_framework import views, status
from rest_framework.response import Response
from .serializers import *

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
            # serializer = BranchSerializer(data = request.data)
            # if serializer.is_valid():
            #     serializer.save()
            #     return Response({'message': 'Branch added successfully!'}, status.HTTP_201_CREATED)
            # else:
            #     return Response({'message': 'Form submission failed. Please check the inputs.'}, status.HTTP_400_BAD_REQUEST)
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

        # Validate the registration payload
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
                # Create company
                logger.info("Creating company...")
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

                # Create a default branch
                branch = Branch(company=company, name='Warehouse')
                branch.save()

                # Create the user (admin of the company)
                #user_data = payload['user_data']
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

                # Generate token and UID for email verification
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(str(user.pk).encode())

                # Build verification URL
                current_site = get_current_site(request)
                verification_url = f"http://{current_site.domain}/verify/{uid}/{token}/"

                # Send verification email
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