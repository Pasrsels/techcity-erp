from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from .models import *
from django.shortcuts import get_object_or_404
import json
from django.http.response import HttpResponse, JsonResponse
from django.db import transaction
from utils import *
from forms import *

@login_required
def services_view(request):
    services = Services.objects.filter(delete=False)
    form = ServiceForm
    return render(request, 'services.html',{'form': form,'data': services})

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
        service = Services.objects.filter(delete = False)
        return JsonResponse({'success':True, 'data':list(service), 'status': 200})
    elif request.method == "POST":#ADD
        data = json.loads(request.body)
        try:
            service_name = data['service_name']

            s_p_name = data['name']

            s_p_d_price = data['price']
            unit_measurement = data['type_service_duration']
            range = data['range']
            promo = data['promotion']

            if not Services.objects.filter(name = service_name).exists():
                with transaction.atomic():
                    service_info = Services.objects.create(
                        name = service_name,
                        service_product = service_product_info
                    )

                    service_product_info = Service_product.objects.create(
                        name = s_p_name,
                        service = service_info
                    )

                    Service_product_details.objects.create(
                        price = s_p_d_price,
                        unit_of_measurement = unit_measurement,
                        service_range = range,
                        promotion = promo,
                        service_product = service_product_info
                    )
            elif not Service_product_details.objects.filter(name = s_p_name).exists():
                service_info = Services.objects.get(name = service_name)
                with transaction.atomic():
                    service_product_info = Service_product.objects.create(
                        name = s_p_name,
                        service = service_info
                    )

                    Service_product_details.objects.create(
                        price = s_p_d_price,
                        unit_of_measurement = unit_measurement,
                        service_range = range,
                        promotion = promo,
                        service_product = service_product_info
                    )
            else:
                service_product_info = Service_product.objects.get(service__name = s_p_name)
                with transaction.atomic():
                    service_product_details_info = Service_product_details.objects.create(
                        price = s_p_d_price,
                        unit_of_measurement = unit_measurement,
                        service_range = range,
                        promotion = promo,
                        service_product = service_product_info
                    )
        except Exception as e:
            return JsonResponse({'succes':False, 'response': f'{e}'}, status = 400)
    #update
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            service_id = data[0]['service_id']
            service = Services.objects.get(id=service_id)

            s_p_id = data['type_id']
            
            service_name = data['service_name']

            s_p_name = data['name']

            s_p_d_price = data['price']
            unit_measurement = data['type_service_duration']
            range = data['range']
            promo = data['promotion']

            if not Services.objects.filter(id = service_id).exists():
                return JsonResponse({'success': False, 'message': f'user with {service_id} does not exist'}, status = 400)
            else:
                with transaction.atomic():
                    service_product_details_info = Service_product_details.objects.get(id = id)
                    service_product_details_info.price = s_p_d_price,
                    service_product_details_info.unit_of_measurement = unit_measurement,
                    service_product_details_info.service_range = range,
                    service_product_details_info.promotion = promo
                    
                    service_product_details_info.save()

                    service_product_info = Service_product.objects.get(id = id)
                    service_product_info.name = s_p_name,
                    service_product_info.service_product_details = service_product_details_info

                    service_product_info.save()

                    service_info = Services.objects.get(id = id)
                    service_info.name = service_name,
                    service_info.service_product = service_product_info

                    service_info.save()
                    return JsonResponse({'success':True},status = 200)
        except Exception as e:
            return JsonResponse({'success':False, 'response':f'{e}'})
    
    elif request.method == "DELETE":

        data = json.loads(request.body)
        service_id = data['service_id']
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete = True
            service_del.save()
            return JsonResponse({'success':True}, status=200)
        return JsonResponse({'success': False, 'response': 'cannot delete none existing field'}, status = 400)
    return JsonResponse({'success':False, 'response': 'invalid request'}, status =  400)

#types
@login_required
def type_crud(request):
    if request.method == "GET":#View
        view = Service_product.objects.all()
        return JsonResponse({'success':True, 'data':list(view), 'status': 200})
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            type_id = data.get('service_id')
            if Services.objects.filter(id = type_id).exists():
                service_del = Service_product.objects.get(id= type_id)
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
    #Update
    elif request.method == "PUT":
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
        office_id = office_data.get('id')
        office_name = office_data.get('Name')

        s_id = service_data.get('id')
        s_name = service_data.get('Name')
        s_del = service_data.get('delete')
        s_type_id = type_data.get('id')
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

        try:
            Members.objects.get(Phone = m_phone)
            
            with transaction.Atomic():
                #type add 1
                types_add = Types.objects.update(
                        Name = s_type_name,
                        Price = service_amount,
                        Duration = service_duration,
                        Promotion = promotion
                    )

                # payment add 2
                payment_add = Payments.objects.update(
                    #Date
                    Amount = payments_amount,
                    Admin_fee = admin_amount,
                    Description = f'payment for {m_name}'
                )
                #service add 3
                service_add = Services.objects.update(
                    Name = s_name,
                    Types = types_add,
                    delete = s_del
                )

                #member account add 4
                member_acc_add = Member_accounts.objects.update(
                    Balance  = bal,
                    Payments = payment_add,
                    delete = False
                )

                #office add 5
                office_add = Office_spaces.objects.update(
                    Name = office_name
                )
                
                #member add 6
                member_add = Members.objects.update(
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
                Logs.objects.update(
                    action = 'update'
                )
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    elif request.method == "DELETE":
        data = json(request.body)

        id = member_data.get('id')

        try:
            Members.objects.get(id = id)
            member = Members.objects.get(id = id)
            member.delete = True
            member.save()
            Logs.objects.delete(
                action = 'delete'
            )
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

        member_balance = data[0]['Balance']
        payments_date = data[1]['Date']
        payments_amount = data[1]['Amount']

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

        member_id = data[0]['id']
        member_balance = data[0]['Balance']
        payments_id = data[1]['id']
        payments_date = data[1]['Date']
        payments_amount = data[1]['Amount']
        
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

        member_id = data[0]['id']

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

        office_name = data[0]['Name']
    
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

        office_id = data[0]['id']
        office_name = data[0]['Balance']
        
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

        office_id = data[0]['id']

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