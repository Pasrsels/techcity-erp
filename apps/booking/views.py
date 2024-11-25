from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from .models import *
from django.shortcuts import get_object_or_404
import json
from django.http.response import HttpResponse, JsonResponse
from django.db import transaction
from utils import *

@login_required
def services_view(request):
    services = Services.objects.filter(delete=False)
    return render(request, 'services.html')

@login_required
def members_view(request):
    member = Services.objects.filter(delete=False)
    return render(request, 'members.html')

@login_required
def offices_view(request):
    office = Services.objects.filter(delete=False)
    return render(request, 'offices.html')

#services
@login_required
def service_crud(request):
    if request.method == "GET":#View
        service = Services.objects.all()
        return JsonResponse({'success':True, 'data':list(service), 'status': 200})
    elif request.method == "POST":#ADD
        data = json.loads(request.body)

        try:
            service_name = data[0]['service_name']

            type_name = data[1]['type_name']
            type_price = data[1]['type_price']
            type_service_duration = data[1]['type_service_duration']
            type_promotion = data[1]['type_promotion']

            if Services.objects.filter(Name = service_name).exists() or Services.objects.filter(Name = type_name).exists():
                return JsonResponse({'success': False, 'response': 'added item already exists'}, status=  400)
            elif not service_name or not type_name or \
                not type_price or not type_service_duration or not type_promotion:
                return JsonResponse({'success': True, 'response': 'please fill in missing fields'}, status = 400)
            
            with transaction.atomic():
                type_add = Types(
                    Name = type_name, 
                    Price = type_price, 
                    Duration = type_service_duration, 
                    Promotion = type_promotion
                    )
                type_add.save()
                service_add = Services(
                    Name = service_name,
                    Types = type_add
                    )
                service_add.save()
                type_add.save()
                Logs.objects.create(
                    action = 'create'
                )
                return JsonResponse({'succes':True}, status = 200)
        except Exception as e:
            return JsonResponse({'succes':False, 'response': f'{e}'}, status = 400)
    #update
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            service_id = data[0]['service_id']
            service = Services.objects.get(id=service_id)

            service_name = data[0]['service_name']

            type_id = data[1]['type_id']
            type_name = data[1]['type_name']
            type_price = data[1]['type_price']
            type_service_duration = data[1]['type_service_duration']
            type_promotion = data[1]['type_promotion']
            
            with transaction.Atomic():
                service=Services(
                    Name = service_name,
                    id = service_id
                    )
                type_add = Types(
                    id = type_id,
                    Name = type_name, 
                    Price = type_price, 
                    Duration = type_service_duration, 
                    Promotion = type_promotion
                    )
                service.save()
                type_add.save()
            return JsonResponse({'success':True},status = 200)
        except Exception as e:
            return JsonResponse({'success':False, 'response':f'{e}'})
    
    elif request.method == "DELETE":

        data = json.loads(request.body)
        service_id = data[0]['service_id']
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete()
            return JsonResponse({'success':True}, status=200)
        return JsonResponse({'success': False, 'response': 'cannot delete none existing field'}, status = 400)
    return JsonResponse({'success':False, 'response': 'invalid request'}, status =  400)
#types
@login_required
def type_crud(request):
    if request.method == "GET":#View
        type_view = Types.objects.all()
        return JsonResponse({'success':True, 'data':list(type_view), 'status': 200})
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            type_id = data.get('service_id')
            if Services.objects.filter(id = type_id).exists():
                service_del = Services.objects.get(id= type_id)
                service_del.delete()
                return JsonResponse({'success':True}, status=200)
            return JsonResponse({'success': False, 'response': 'cannot delete none existing field'}, status = 400)
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'}, status = 400)
    return JsonResponse({'success':False, 'response': 'invalid request'}, status = 400)
#member
@login_required
def member_crud(request):
    #Read
    if request.method == "GET":
        member = Members.objects.all()
        return JsonResponse({'success': True, 'data': list(member)}, status = 200)
    #Add
    elif request.method == "POST":
        #json format
        '''service_data = {
            'service': 1,
        }'''
        #get data part of file
        data = json(request.body)

        #selecting specific part of data
        member_data = data.get('member_data', {})
        service_data = data.get('service_data', {})
        member_acc_data = data.get('member_acc_data',{})
        office_data = data.get('office_data',{})
        payments_data = data.get('payments_data',{})
        type_data = data.get('types_data',{})

        #getting different parts within the data 
        
        office_name = office_data.get('Name')

        s_name = service_data.get('Name')
        s_del = service_data.get('delete')
        s_type_name = type_data.get('Name')
        service_amount = type_data.get('Price')
        service_duration = type_data.get('Duration')
        promotion = type_data.get('Promotion')

        member_balance = member_acc_data.get('Balance')
        payments_date = payments_data.get('Date')
        payments_amount = payments_data.get('Amount')
        payments_admin = payments_data.get('Admin_fee')

        n_ID = member_data.get('National_ID')
        m_name = member_data.get('Name')
        m_email = member_data.get('Email')
        m_phone = member_data.get('Phone')
        m_adress = member_data.get('Address')
        m_enrollment = member_data.get('Enrollment')
        m_company = member_data.get('Company')
        m_age = member_data.get('Age')
        m_gender = member_data.get('Gender')

        if Members.objects.filter(Email = m_email).exists():
            return JsonResponse({'success': True, 'response': 'field already exists'}, status = 400)
        elif not n_ID or not m_name or not m_email or not m_phone or not m_adress or not m_enrollment \
        or not m_company or not m_age or not m_gender:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
        
        with transaction.atomic():
            try: 
                # query service
                # service = Services.objects.get(service_data.get('Name'))
                # member = Member_accounts.objects.get(member_acc_data.get('Balance'))
                # office = Office_spaces.objects.get(office_data.get('Name'))
                # payments = Payments.objects.get(payments_data.get('Date','Amount'))

                """"
                    1. we are going to receive a total amount which consists of admin if its a first payment,
                    2. we are going to seperate it into 2 thus admin and service amount, 
                    3. we are going to check if they is an balance
                """
                if not Members.objects.filter(Phone=m_phone).exists():
                    admin_amount = 0
                    #service_amount_owing = 0
                    bal = 0
                    if payments_amount > service_amount:
                        bal = (payments_amount - service_amount) - payments_admin
                        if bal < 0:
                            admin_amount = bal
                    elif payments_amount == service_amount:
                        admin_amount = -20
                        bal = admin_amount
                    else:
                        admin_amount = 20
                        bal = (service_amount - payments_amount) + admin_amount
                
                #types add 1
                types_add = Types.objects.create(
                    Name = s_type_name,
                    Price = service_amount,
                    Duration = service_duration,
                    Promotion = promotion
                )

                # payment add 2
                payment_add = Payments.objects.create(
                    #Date
                    Amount = payments_amount,
                    Admin_fee = admin_amount,
                    Description = f'payment for {m_name}'
                )
                #service add 3
                service_add = Services.objects.create(
                    Name = s_name,
                    Types = types_add,
                    delete = s_del
                )

                #member account add 4
                member_acc_add = Member_accounts.objects.create(
                    Balance  = bal,
                    Payments = payment_add,
                    delete = False
                )

                #office add 5
                office_add = Office_spaces.objects.create(
                    Name = office_name
                )
                
                #member add 6
                member_add = Members.objects.create(
                    National_ID = n_ID,
                    Name = m_name,
                    Email = m_email,
                    Phone = m_phone,
                    Address = m_adress,
                    Enrollment = m_enrollment,
                    Company = m_company,
                    Age = m_age,
                    Gender = m_gender,
                    delete = False,
                    Services=service_add,
                    Member_accounts = member_acc_add,
                    Office_spaces = office_add,
                    Payments = payment_add
                )
                Logs.objects.create(
                    action = 'create'
                )
                #member.save() unneccessary
                return JsonResponse({'success': True, 'response': 'Data saved'}, status = 200)
            except Exception as e:
                pass
    from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import json
from .models import Services, Types

# Service CRUD View
@csrf_exempt
def service_crud(request):
    if request.method == "GET":
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            services = Services.objects.filter(
                Q(Name__icontains=search_query) |
                Q(Types__Name__icontains=search_query)
            ).select_related('Types')
        else:
            services = Services.objects.all().select_related('Types')

        # Serialize data for the response
        data = [
            {
                'id': service.id,
                'Name': service.Name,
                'Types__Name': service.Types.Name,
                'Types__Price': service.Types.Price,
                'Types__Duration': service.Types.Duration,
                'Types__Promotion': service.Types.Promotion
            }
            for service in services
        ]
        return JsonResponse({'success': True, 'data': data}, status=200)

    elif request.method == "POST":
        try:
            # Parse JSON data
            data = json.loads(request.body)

            # Create Type object
            type_data = data.get('type_data', {})
            type_obj = Types.objects.create(
                Name=type_data['Name'],
                Price=type_data['Price'],
                Duration=type_data['Duration'],
                Promotion=type_data.get('Promotion', '')
            )

            # Create Service object
            Services.objects.create(
                Name=data['service_name'],
                Types=type_obj
            )
            return JsonResponse({'success': True, 'message': 'Service added successfully!'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    elif request.method == "PUT":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            service_id = data.get('id')

            # Fetch service and type objects
            service = Services.objects.get(id=service_id)
            type_data = data.get('type_data', {})
            type_obj = service.Types

            # Update Type object
            type_obj.Name = type_data['Name']
            type_obj.Price = type_data['Price']
            type_obj.Duration = type_data['Duration']
            type_obj.Promotion = type_data.get('Promotion', '')
            type_obj.save()

            # Update Service object
            service.Name = data['service_name']
            service.save()

            return JsonResponse({'success': True, 'message': 'Service updated successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    elif request.method == "DELETE":
        try:
            # Parse JSON data
            data = json.loads(request.body)
            service_id = data.get('id')

            # Delete service
            service = Services.objects.get(id=service_id)
            service.delete()

            return JsonResponse({'success': True, 'message': 'Service deleted successfully!'}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
