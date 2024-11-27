import json

from django.contrib.auth.hashers import make_password

from django.db.transaction import atomic
from django.http import JsonResponse

from django.shortcuts import render, redirect, get_object_or_404

from loguru import logger

from apps.finance.models import VATRate
from apps.users.models import User
from utils.validate_json import validate_company_registration_payload

from .models import Branch, Company
from apps.inventory.models import Inventory
from django.contrib import messages

from .forms import BranchForm

from django.contrib.auth import get_user_model
from apps.settings.models import TaxSettings
from django.db import transaction


def registration(request):
    User = get_user_model()
    logger.info(User)
    if not User.objects.exists():
        logger.info('here')
        return redirect('company:register_company')
    return render(request, 'registration.html')


def register_company_view(request):
    """
    payload = {
        'company_data' : {},
        'user_data': {}
    }
    """
    if request.method == 'GET':
        if Company.objects.exists():
            return redirect('users:login')

    if request.method == 'POST':
        payload = json.loads(request.body)
        logger.info(f"Company registration payload: {payload}")

        # validate json data
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
                # create company
                logger.info("creating company")
                company_data = payload['company_data']
                logger.info(f"company data: {company_data}")

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
                logger.info(f"company created: {company}")

                # create branch for the initial user:
                branch = Branch(
                    company=company,
                    name='Warehouse'
                )
                branch.save()
                # to be removed
                VATRate.objects.create(
                    rate=15.00,
                    description='standard rate',
                    status=True
                )

                # create user (user is owner)
                user_data = payload['user_data']
                logger.info(f"user data: {user_data}")

                user = User()
                user.first_name = user_data['first_name']
                user.last_name = user_data['last_name']
                user.username = user_data['username']
                user.email = company.email
                user.company = company
                user.phonenumber = company.phone_number
                user.role = 'admin'
                user.branch = branch

                logger.info(user.branch)
                user.password = user_data['password']
                logger.info(user.password)
                user.save()

                # create tax methods
                #create_tax_methods()

            # return message
            return JsonResponse(
                {
                    "success": True,
                    "message": "Company registration successful"
                },
                status=200
            )
        except Exception as e:
            logger.info(e)
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Failed: {e}"
                },
                status=500
            )
    return render(request, 'registration.html')

def create_tax_methods():
    tax_methods = ['No tax', 'Inclusice', 'Exclusive']

    tax_obj_list = []
    for method in tax_methods:
        tax_obj_list.append(TaxSettings(
            name=method,
            selected=False
        ))
    
    TaxSettings.objects.bulk_create(tax_obj_list)


def branch_list(request):
    branches = Branch.objects.all()
    return render(request, 'branches.html', {'branches': branches})


def branch_switch(request, branch_id):
    logger.info('here')
    user = request.user
    if user.role == 'Admin' or user.role == 'admin':
        user.branch = Branch.objects.get(id=branch_id)
        user.save()
    else:
        messages.error(request, 'You are not authorized')
    return redirect('pos:pos')


def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch_obj = form.save()

            branch =  Branch.objects.get(name='ADMIN')
            product_list = []
            for product in Inventory.objects.filter(branch__name='ADMIN'):
                product_list.append(
                    Inventory(
                        branch=branch,
                        name=product.name,
                        cost = product.cost,
                        price = product.price,
                        dealer = product.dealer_price,
                        quantity = product.quantity,
                        status = product.status,
                        stock_level_threshold = product.stock_level_threshold,
                        reorder = product.reorder,
                        alert_notifications = product.alert_notification,
                        batch = product.batch,
                        category = product.category,
                        tax_type = product.tax_type,
                        suppliers = product.suppliers,
                        description = product.description,
                        end_of_day = product.end_of_day,
                        service = product.service,
                        image = product.image,
                    )
                )
            Inventory.objects.bulk_create(product_list)
            
            messages.success(request, 'Branch added successfully!')
            return redirect('company:branch_list')
    else:
        form = BranchForm()
    return render(request, 'add_branch.html', {'form': form})


# @permissions(['Admin'])
def edit_branch(request, branch_id):
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
