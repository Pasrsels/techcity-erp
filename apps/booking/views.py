from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from .models import *
from django.shortcuts import get_object_or_404
from django.contrib import messages
import json
from django.http.response import HttpResponse, JsonResponse
from django.db import transaction
from utils import *
from .forms import *
from loguru import logger

#service view
@login_required
def services_view(request):
    service = Services.objects.all()
    form = ServiceForm()
    if service:
        return redirect('booking:service_product_crud')
    return render(request,'services1.html',{'form':form})

#service crud
@login_required
def service_crud(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'saved successfully')
            return redirect('booking:service_product_crud')
        return JsonResponse({'success': False, 'message': 'invalid form'}, status = 400)
    #update
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            service_id = data['service_id']
            service_name = data['service_name']
            
            if not Services.objects.filter(id = service_id).exists():
                return JsonResponse({'success': False, 'message': f'user with {service_id} does not exist'}, status = 400)
            else:
                service_edit = Services.objects.get(id = service_id)
                service_edit.name = service_name
                service_edit.save()
                return JsonResponse({'success':True},status = 200)
        except Exception as e:
            return JsonResponse({'success':False, 'response':f'{e}'}, status = 400)
    #delete
    elif request.method == "DELETE":
        data = json.loads(request.body)
        service_id = data('service_id')
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete = True
            service_del.save()
            return JsonResponse({'success':True}, status=200)
        return JsonResponse({'success': False, 'response': 'cannot delete none existing field'}, status = 400)
    return JsonResponse({'success':False, 'response': 'invalid request'}, status =  500)


#getting sercices data
def ServiceData(request):
    if request.method == 'GET':
        service_info = Services.objects.all().values()
        logger.info(service_info)
        return JsonResponse({'success': True, 'product': list(service_info)}, status = 200)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

#service_product CRUD
@login_required
def service_product_crud(request):
    if request.method == 'GET':
        form = ServiceForm()
        unit_form = UnitForm()
        range_form = RangeForm()
        service_product_form = Service_productForm()
        service_product = Service_product.objects.all()
        service = Services.objects.all()
        logger.info(service_product)
        return render(request, 'service_products.html',{
        'service_product':service_product_form,
        'service_product_data': service_product,
        'services': service,
        'service_range': range_form,
        'unit_measurement': unit_form,
        'service': form
        })
    #add
    if request.method == 'POST':
        data = json.load(request.body)
        service_product_name = data.get('name')
        service_name = data.get('service name')
        measurement_id = data.get('unit measurement')
        promotion = data.get('promotion')
        range_id = data.get('service range')
        price = data.get('price')

        if not service_product_name or not service_name or not measurement_id or not promotion or not range_id or not price:
            return JsonResponse({'success': False, 'message': 'There are empty fields'}, status = 400)
        elif Service_product.objects.filter(name = service_product_name).exists():
            return JsonResponse({'Success': False, 'message': f'{service_product_name} alreay exists'}, status = 400)
        try:
            with transaction.atomic():
                service = Services.objects.get(name = service_name)
                service_range = Service_range.get(id = range_id)
                unit_measure = Unit_Measurement.objects.get(id = measurement_id)
                Service_product.objects.create(
                    name = service_product_name,
                    service = service,
                    unit_measure = unit_measure,
                    service_range = service_range
                )
                return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'reason: {e}'}, status = 400)
        #elif Service_product.objects.filter()  
    elif request.method == 'PUT': #Update
        data = json.load(request.body)
        service_name = data.get('service_name')
        service_product_name = data.get('name')
        price = data.get('price')
        unit_measurement = data.get('u_measure')
        service_range = data.get('range')
        promotion = data.get('promotion')

        if not service_name or not service_product_name or not price or not unit_measurement or not service_range or not promotion:
            return JsonResponse({'success': False, 'message': 'empty json'}, status = 400)
        elif not Services.objects.filter(name = service_name).exists or not Service_product.objects.filter(name = service_product_name).exists:
            return JsonResponse({'success': False, 'message': 'does not exist'}, status = 400)
        else:     
            service = Services.objects.update(
                name = service_name
                )
            services_product = Service_product.objects.update(
                name = service_product_name,
                service = service
            )
            with transaction.atomic():
                Service_range.objects.create(
                    service_range = service_range,
                    promotion = promotion,
                    price = price,
                    service_product = services_product
                )

                Unit_Measurement.objects.create(
                    measurement = unit_measurement,
                    service_product = services_product
                )
                return JsonResponse({'success': True, 'message': 'saved successfully'}, status = 200)
    elif request.method == 'DELETE':
        data = json.load(request.body)
        service_product_id = data.get('id')
        if not Service_product.objects.filter(id = service_product_id).exists():
            return JsonResponse({'success':False, 'message': 'service product does not exist'}, status = 400)
        try:
            service_prod_del = Service_product.objects.get(id = service_product_id)
            service_prod_del.delete()
            return JsonResponse({'success':True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'response: {e}'}, status = 400)
    return JsonResponse({'success': False, 'response': 'invalid request'}, status = 500)


#Service range crud
@login_required
def service_range_crud(request):
    #ADD
    if request.method == 'POST':
        data = json.load(request.body)
        range = data.get('range')
        price = data.get('price')

        Service_range.objects.create(
            range = range,
            price = price
        )
        return JsonResponse({'success': True}, status = 200)
    #read
    elif request.method == 'GET':
        service_range = Service_range.objects.all()
        return JsonResponse({'success': True, 'service_range': service_range})
    #update
    elif request.method == 'UPDATE':
        data = json.load(request.body)
        range = data.get('range')
        price = data.get('price')
        id = data.get('id')

        if not Service_range.objects.filter(id = id).exists():
            return JsonResponse({'success': False, 'message': f'id :{id} doesnot exist'})
        try:
            service_range_update = Service_range.objects.get(id = id)
            service_range_update.service_range = range
            service_range_update.price = price
            service_range_update.save()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'reason :{e}'}, status = 400)
    #delete
    elif request.method == 'DELETE':
        data = json.load(request.body)
        id = data.get('id')
        try:
            service_range = Service_range.objects.get(id = id)
            service_range.delete()
        except Exception as e:
            return JsonResponse({'success': False, 'message':f'reason : {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
    
@login_required
def unit_measurement_crud(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        measure = data.get('measurement')
        promotion = data.get('promotion')
        if promotion == 'on':
            promotion = True
        else:
            promotion = False
        Unit_Measurement.objects.create(
            measurement = measure,
            promotion = promotion
        )
        return JsonResponse({'success': True}, status = 200)
    #read
    elif request.method == 'GET':
        unit_measure = Unit_Measurement.objects.all()
        return JsonResponse({'success': True, 'unit_measure': unit_measure})
    #update
    elif request.method == 'UPDATE':
        data = json.load(request.body)
        measure = data.get('unit_measure')
        promotion = data.get('promotion')
        id = data.get('id')

        if not Unit_Measurement.objects.filter(id = id).exists():
            return JsonResponse({'success': False, 'message': f'id :{id} doesnot exist'})
        try:
            unit_measure = Unit_Measurement.objects.get(id = id)
            unit_measure.measurement = measure
            unit_measure.promotion = promotion
            unit_measure.save()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'reason :{e}'}, status = 400)
    #delete
    elif request.method == 'DELETE':
        data = json.load(request.body)
        id = data.get('id')
        try:
            unit_measure_delete = Unit_Measurement.objects.get(id = id)
            unit_measure_delete.delete()
        except Exception as e:
            return JsonResponse({'success': False, 'message':f'reason : {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

#member view
@login_required
def members_view(request):
    member = Services.objects.filter(delete=False)
    return render(request, 'members.html')

@login_required
def offices_view(request):
    office = Services.objects.all()
    return render(request, 'service_products.html',office)

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