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
    branches = Branch.objects.all()
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
