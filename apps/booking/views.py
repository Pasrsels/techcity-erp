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
    return render(request, 'services/service.html')
#services
@login_required
def service_crud(request):
    if request.method == "GET":#View
        service = Services.objects.all()
        return JsonResponse({'success':True, 'data':list(service), 'status': 200})
    elif request.method == "POST":#ADD
        data = json.loads(request.body)

        try:
            service_name = data.get([0]['service_name'])

            type_name = data.get([1]['type_name'])
            type_price = data.get([1]['type_price'])
            type_service_duration = data.get([1]['type_service_duration'])
            type_promotion = data.get([1]['type_promotion'])

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
            service_id = data.get([0]['service_id'])
            service = Services.objects.get(id=service_id)

            service_name = data.get([0]['service_name'])

            type_id = data.get([1]['type_id'])
            type_name = data.get([1]['type_name'])
            type_price = data.get([1]['type_price'])
            type_service_duration = data.get([1]['type_service_duration'])
            type_promotion = data.get([1]['type_promotion'])
            
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
        service_id = data.get([0]['service_id'])
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

        data = json(request.body)
        member_data = data.get('member_data', {})
        service_data = data.get('service_data', {})
        member_acc_data = data.get('member_acc_data',{})
        office_data = data.get('office_data',{})
        payments_data = data.get('payments_data',{})

        s_name = service_data.get('name')
        member_balance = member_acc_data.get('Balance')
        office_name = office_data.get('Name')
        total_service_amount = service_data.get('service_amount')

        payments_date = payments_data.get('Date')
        payments_amount = payments_data.get('Amount')

        n_ID = member_data.get('National_ID')
        m_name = member_data.get('Name')
        m_email = member_data.get('Email')
        m_phone = member_data.get('Phone')
        m_adress = member_data.get('Address')
        m_enrollment = member_data.get('Enrollment')
        m_company = member_data.get('Company')
        m_age = member_data.get('Age')
        m_gender = member_data.get('Gender')
        m_delete = member_data.get('delete')

        if Members.objects.filter(Email = m_email).exists():
            return JsonResponse({'success': True, 'response': 'field already exists'}, status = 400)
        elif not n_ID or not m_name or not m_email or not m_phone or not m_adress or not m_enrollment \
        or not m_company or not m_age or not m_gender:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
        
        with transaction.atomic():
            try: 
                # query service
                service = Services.objects.get(service_data.get('Name'))
                member = Member_accounts.objects.get(member_acc_data.get('Balance'))
                office = Office_spaces.objects.get(office_data.get('Name'))
                payments = Payments.objects.get(payments_data.get('Date','Amount'))

                """"
                    1. we are going to receive a total amount which consists of admin if its a first payment,
                    2. we are going to seperate it into 2 thus admin and service amount, 
                    3. we are going to check if they is an balance
                """

                if not Members.objects.filter(Phone=m_phone).exists():
                    admin_amount = 0
                    service_amount_owing = 0
                    bal = 0
                    if total_service_amount > service.Types.price:
                        amount_amount = total_service_amount - service.Types.price
                        bal = amount_amount
                    elif total_service_amount == service.Types.price:
                        admin_amount = 20
                        bal = admin_amount
                    else:
                        admin_amount = 20
                        service_amount_owing = service.Types.price - total_service_amount
                        bal = admin_amount + service_amount_owing
                else:
                    """ ndepenyu """

                

                # payment
                payment = Payments.objects.create(
                    Amount = total_service_amount,
                    Admin_fee = admin_amount
                )
                #balance
                balance = Member_accounts.objects.create(
                    Balance  = bal,
                )



                member = Members(
                    National_ID = n_ID,
                    Name = m_name,
                    Email = m_email,
                    Phone = m_phone,
                    Address = m_adress,
                    Enrollment = m_enrollment,
                    Company = m_company,
                    Age = m_age,
                    Gender = m_gender,
                    delete = m_delete,
                    Services=service,
                    Member_accounts = member,
                    Office_spaces = office,
                    Payments = payments
                )

                member.save()
                return JsonResponse({'success': True, 'response': 'Data saved'}, status = 200)
            except Exception as e:
                pass
        
    #Update
    elif request.method == "PUT":
        data = json(request.body)

        s_id = service_data.get('id')
        s_name = service_data.get('name')

        m_a_id = member_acc_data.get('id')
        member_balance = member_acc_data.get('Balance')

        o_id = office_data.get('id')
        office_name = office_data.get('Name')

        p_id = payments_data.get('id')
        payments_date = payments_data.get('Date')
        payments_amount = payments_data.get('Amount')

        m_id = member_data.get('id')
        n_ID = member_data.get('National_ID')
        m_name = member_data.get('Name')
        m_email = member_data.get('Email')
        m_phone = member_data.get('Phone')
        m_adress = member_data.get('Address')
        m_enrollment = member_data.get('Enrollment')
        m_company = member_data.get('Company')
        m_age = member_data.get('Age')
        m_gender = member_data.get('Gender')
        m_delete = member_data.get('delete')
       

        try:
            Members.objects.get(id = m_id)
            
            service = Services.objects.get(service_data.get('Name'))
            member_a = Member_accounts.objects.get(member_acc_data.get('Balance'))
            office = Office_spaces.objects.get(office_data.get('Name'))
            payments = Payments.objects.get(payments_data.get('Date','Amount'))

            member = Members(
                id = m_id,
                National_ID = n_ID,
                Name = m_name,
                Email = m_email,
                Phone = m_phone,
                Address = m_adress,
                Enrollment = m_enrollment,
                Company = m_company,
                Age = m_age,
                Gender = m_gender,
                Services = service,
                Member_accounts = member_a,
                Office_spaces  = office,
                Payments = payments
            )
            member.save() 

        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    elif request.method == "DELETE":
        data = json(request.body)

        id = member_data.get('id')

        try:
            Members.objects.get(id = id)
                # return JsonResponse({'success': False, 'response': 'field doesnot exist in database'}, status = 400)
            member = Members.objects.get(id = id)
            member.delete = True
            member.save()
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)

#member_acc    
@login_required
def member_acc_crud(request):
    #read
    if request.method == "GET":
        member_acc = Member_accounts.objects.all()
        return JsonResponse({'success': True, 'data': member_crud}, status = 200)
    #add
    elif request.method == "POST":
        data = json.loads(request.body)

        member_balance = data.get([0]['Balance'])
        payments_date = data.get([1]['Date'])
        payments_amount = data.get([1]['Amount'])

        # if Member_accounts.objects.filter(id = member_id).exists():
        #     return JsonResponse({'success': False, 'response': 'cannot add existing field'}, status = 400)
        if not member_id or not member_balance or not payments_id or not payments_date or not payments_amount:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
        
        with transaction():
            member_acc = Member_accounts(
                Balance = member_balance,
            )            
            payments = Payments(
               Date = payments_date,
               Amount = payments_amount
            )
            member_acc.save() 
            payments.save()
    #update
    elif request.method == "PUT":

        data = json.loads(request.body)

        member_id = data.get([0]['id'])
        member_balance = data.get([0]['Balance'])
        payments_id = data.get([1]['id'])
        payments_date = data.get([1]['Date'])
        payments_amount = data.get([1]['Amount'])
        
        try:
            if Member_accounts.objects.get(id = member_id).DoesNotExist():
                return JsonResponse({'success': False, 'response': 'cannot update none existing field'}, status = 400)
            elif not member_id or not member_balance or not payments_id or not payments_date or not payments_amount:
                return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
            
            with transaction():
                member_acc = Member_accounts(
                    id = member_id,
                    Balance = member_balance,
                )            
                payments = Payments(
                id = payments_id,
                Date = payments_date,
                Amount = payments_amount
                )
                member_acc.save() 
                payments.save()
                return JsonResponse({'success': True, 'response': 'items updated'}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response':f'{e}'}, status = 200)
    #delete
    if request.method == "DELETE":
        data = json.loads(request.body)

        member_id = data.get([0]['id'])

        if Member_accounts.objects.get(id = member_id).DoesNotExist():
            return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
        if not member_id:
            return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
        
        member_acc_del = Member_accounts.objects.filter(id = member_id)
        member_acc_del.delete = True
        member_acc_del.save()

#Payments
@login_required
def payments_crud(request):
    #read
    if request.method == "GET":
        payments_ = Member_accounts.objects.all()
        return JsonResponse({'success': True, 'data':list(payments_)}, status = 200)
    #add
    elif request.method == "POST":
        data = json.loads(request.body)

        payments_date = data.get('Date')
        payments_amount = data.get('Amount')

        if Member_accounts.objects.filter().exists():
            return JsonResponse({'success': False, 'response': 'cannot add existing field'}, status = 400)
        elif not payments_id or not payments_date or not payments_amount:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
                   
        payments = Payments(
            id = payments_id,
            Date = payments_date,
            Amount = payments_amount
        ) 
        payments.save()
    #update
    elif request.method == "PUT":

        data = json.loads(request.body)

        payments_id = data.get('id')
        payments_date = data.get('Date')
        payments_amount = data.get('Amount')
        
        try:
            if Member_accounts.objects.get(id = payments_id).DoesNotExist():
                return JsonResponse({'success': False, 'response': 'cannot update none existing field'}, status = 400)
            elif not payments_id or not payments_date or not payments_amount:
                return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
                    
            payments = Payments(
            id = payments_id,
            Date = payments_date,
            Amount = payments_amount
            ) 
            payments.save()
            return JsonResponse({'success': True, 'response': 'items updated'}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response':f'{e}'}, status = 200)
    #delete
    if request.method == "DELETE":
        data = json.loads(request.body)

        payments_id = data.get('id')

        if Member_accounts.objects.get(id = payments_id).DoesNotExist():
            return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
        if not payments_id:
            return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
        
        payments_del = Member_accounts.objects.filter(id = payments_id)
        payments_del.delete()

#office
@login_required
def office_crud(request):
    #read
    if request.method == "GET":
        office_view = Office_spaces.objects.all()
        return JsonResponse({'success': True, 'data': list(office_view)}, status = 200)
    #add
    elif request.method == "POST":
        data = json.loads(request.body)

        office_name = data.get([0]['Name'])
    
        if Member_accounts.objects.filter(Name = office_name).exists():
            return JsonResponse({'success': False, 'response': 'cannot add existing field'}, status = 400)
        elif not office_name:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
        
        
        office_space = Office_spaces(
            Name = office_name,
        )            
        office_space.save() 
    #update
    elif request.method == "PUT":

        data = json.loads(request.body)

        office_id = data.get([0]['id'])
        office_name = data.get([0]['Balance'])
        
        try:
            if Member_accounts.objects.get(id = office_id).DoesNotExist():
                return JsonResponse({'success': False, 'response': 'cannot update none existing field'}, status = 400)
            elif not office_id or not office_name:
                return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
            
            office_space = Office_spaces(
                id = office_id,
                Balance = office_name,
            )            
            
            office_space.save() 
            return JsonResponse({'success': True, 'response': 'items updated'}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response':f'{e}'}, status = 200)
    #delete
    if request.method == "DELETE":
        data = json.loads(request.body)

        office_id = data.get([0]['id'])

        try:
            if Member_accounts.objects.get(id = office_id).DoesNotExist():
                return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
            if not office_id:
                return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
            
            office_del = Member_accounts.objects.filter(id = office_id)
            office_del.delete()
            return JsonResponse({'success': True, 'response': 'item deleted'})
        except Exception as e:
            return JsonResponse({'success':False, 'response': f'{e}'}, status = 400)
        
