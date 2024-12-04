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
#1
@login_required
def services_view(request):
    serviceform = ServiceForm()
    service = Services.objects.all().values()
    items = inventory.objects.all().values()
    category = Category.objects.all().values()
    itemsofuse = ItemOfUse.objects.all().values()
    logger.info(items)
    return render(request,'services1.html',{
        'services': service,
        'items': items,
        'category_data': category,
        'serviceform': serviceform,
        'itemofuse_data': itemsofuse,   
    })

#2
@login_required
def services(request):
    serviceform = ServiceForm()
    inventoryform = InventoryForm()
    unit_measurement = UnitForm()
    services = Services.objects.all()
    iouForm = AddIouName()
    categoryForm = AddCategory()
    names = itemOfUseName.objects.all()
    return render(request, 'service_products.html',{
        'names':names,
        'iouForm':iouForm,
        'services': services,
        'service': serviceform,
        'inventory': inventoryform,
        'categoryForm':categoryForm,
        'unit_measurement':unit_measurement
    })

#3
#service crud
@login_required
def service_crud(request):
    """
        payload
            [{
                name: str,
                descrption: str,
                unit_measure: int (fk),
                service_range: str
            }]
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description')
            unit_measure = data.get('unit_measure')
            service_range = data.get('service_range')
            logger.info(name)

            if Services.objects.filter(service_name = name).exists():
                return JsonResponse({'success': False, 'message': f'{name} already exists'}, status = 400)
            
            um = UnitMeasurement.objects.get(id=unit_measure)
            
            Services.objects.create(
                service_name  = name,
                description = description,
                service_range = service_range,
                unit_measure = um
            )

            service_data = Services.objects.all().values(
                'id',
                'service_name'
            )
            return JsonResponse({'success': True, 'data': list(service_data)}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status = 400)
    #update
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            service_id = data('service_id')
            service_name = data('service_name')
            
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



#BIG item of use
@login_required
def ServiceCrud(request):
    """
        payload
        [
            service_name:str,
            items = {
                item_of_use_name: str,
                service_range: str,
                unit_of_measurement_id: int,
                cost:float,
                quantity:int 
            }
        ]
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service_name = data.get('service_name', '')
            description = data.get('description', '')
            items = data.get('items', [])
        
            if not service_name  or not items or not description :
                return JsonResponse({'success': False, 'message': 'please fill in the missing fields'}, status = 400)
            elif not ServiceRange.objects.filter(name = items.get('service_range')).exists():
                service_ranging = ServiceRange.objects.create(
                    service_range = items.get('service_range')
                )
            
            with transaction.atomic():
                service = Services.objects.get(name  = service_name)
                item_of_use_list = []
                for item in items:
                    item_of_use_list.append(
                        {
                            'service': service,
                            'name': items.get('item_of_use_name'),
                            'cost': items.get('cost'),
                            'quantity': items.get('quantity'),
                            'unit_measure': UnitMeasurement.objects.get(id=items.get('unit_of_measurement_id')),
                            'service_range': ServiceRange.objects.get(service_range = items.get('service_range'))
                        }
                    )
                    ItemOfUse.objects.bulk_create(item_of_use_list)
                    return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status = 400)
        
    elif request.method == 'UPDATE':
        try:
            data = json.loads(request.body)
            service_id = data.get('id')
            service_name = data.get('name')
            description = data.get('description')

            if not service_name  or not service_id or not description :
                return JsonResponse({'success': False, 'message': 'please fill in the missing fields'}, status = 400)
            elif not Services.objects.filter(name = service_name).exists():
                return JsonResponse({'success':False, 'message':'cannot update something that does not exist'}, status = 400)
            with transaction.atomic():
                service_update = Services.objects.get(id = service_id)
                service_update.name = service_name
                service_update.description = description
                return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status = 400)
        
    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            service_id = data.get('id')

            if not Services.objects.filter(name = service_name).exists():
                return JsonResponse({'success':False, 'message':'cannot delete something that does not exist'}, status = 400)
            elif service_id == '':
                return JsonResponse({'success':False, 'message':'empty id'}, status = 400)
            service_delete = Services.objects.get(id = service_id)
            service_delete.delete(),
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

#service_product CRUD
@login_required
def itemofuseCrud(request):
    #add
    if request.method == 'POST':
        data = json.load(request.body)
        itemofuse_name = data.get('name')
        cost = data.get('cost')
        category = data.get('category')
        quantity = data.get('quantity')

        with transaction.atomic():
            inventory.objects.create(
                name = itemofuse_name,
                cost = cost,
                category = category,
                quantity = quantity,
            )
            return JsonResponse({'success': True}, status = 200)
         
    elif request.method == 'PUT': #Update
        data = json.load(request.body)
        item_id = data.get('id')
        item_cost = data.get('cost')
        itemofuse_name = data.get('name')
        quantity = data.get('quantity')

        if not item_id or not item_cost or not itemofuse_name:
            return JsonResponse({'success': False, 'message': 'empty json'}, status = 400)
        elif not ItemOfUse.objects.filter(name = itemofuse_name).exists:
            return JsonResponse({'success': False, 'message': 'does not exist'}, status = 400)
        else:
            item_update = ItemOfUse.objects.get(id = item_id)
            item_update.name = itemofuse_name
            item_update.cost = item_cost
            item_update.quantity = quantity
            item_update.save()
            return JsonResponse({'success': True, 'message': 'saved successfully'}, status = 200)
    elif request.method == 'DELETE':
        data = json.load(request.body)
        item_id = data.get('id')
        if not ItemOfUse.objects.filter(id = item_id).exists():
            return JsonResponse({'success':False, 'message': 'service product does not exist'}, status = 400)
        try:
            item_del = ItemOfUse.objects.get(id = item_id)
            item_del.delete()
            return JsonResponse({'success':True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'response: {e}'}, status = 400)
    return JsonResponse({'success': False, 'response': 'invalid request'}, status = 500)

    
@login_required
def unit_measurement_crud(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            measure = data.get('measurement')

            # to change to lower case
            measure = measure

            # validation for existance
            if UnitMeasurement.objects.filter(measurement=measure).exists():
                return JsonResponse({'success': False, 'message':f'{measure} measurement exists.' }, status = 400) 

            logger.info('Creating measurement .....')

            # creation 
            unit = UnitMeasurement.objects.create(
                measurement = measure,
            )

            logger.info(f'Measurement created: {unit}')

            measurements = UnitMeasurement.objects.all().values()

            logger.info(f'Measurements: {measurements}')

            return JsonResponse({'success': True, 'data':list(measurements)}, status = 200)
        except Exception as e:
           return JsonResponse({'success': False, 'message':f'{e}' }, status = 400) 
        
    
    #read
    elif request.method == 'GET':
        unit_measure = UnitMeasurement.objects.all()
        return JsonResponse({'success': True, 'unit_measure': unit_measure})
    
    #update
    elif request.method == 'UPDATE':
        data = json.load(request.body)
        measure = data.get('unit_measure')
        promotion = data.get('promotion')
        id = data.get('id')

        if not UnitMeasurement.objects.filter(id = id).exists():
            return JsonResponse({'success': False, 'message': f'id :{id} doesnot exist'})
        try:
            unit_measure = UnitMeasurement.objects.get(id = id)
            unit_measure.measurement = measure
            unit_measure.save()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'reason :{e}'}, status = 400)
        
    #delete
    elif request.method == 'DELETE':
        data = json.load(request.body)
        id = data.get('id')
        try:
            unit_measure_delete = UnitMeasurement.objects.get(id = id)
            unit_measure_delete.delete()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message':f'reason : {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

#member view
@login_required
def members_view(request):
    member = Services.objects.filter(delete=False)
    return render(request, 'members.html',{'formMemberData': member})

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
                    delete = s_del
                )

                #member account add 4
                member_acc_add = MemberAccounts.objects.create(
                    Balance  = bal,
                    Payments = payment_add,
                    delete = False
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
                    delete = s_del
                )

                #member account add 4
                member_acc_add = MemberAccounts.objects.update(
                    Balance  = bal,
                    Payments = payment_add,
                    delete = False
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
        member_acc = MemberAccounts.objects.all()
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
            member_acc = MemberAccounts(
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
            if MemberAccounts.objects.get(id = member_id).DoesNotExist():
                return JsonResponse({'success': False, 'response': 'cannot update none existing field'}, status = 400)
            elif not member_id or not member_balance or not payments_id or not payments_date or not payments_amount:
                return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
            
            with transaction():
                member_acc = MemberAccounts(
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

        if MemberAccounts.objects.get(id = member_id).DoesNotExist():
            return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
        if not member_id:
            return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
        
        member_acc_del = MemberAccounts.objects.filter(id = member_id)
        member_acc_del.delete = True
        member_acc_del.save()

#Payments
@login_required
def payments_crud(request):
    #read
    if request.method == "GET":
        payments_ = MemberAccounts.objects.all()
        return JsonResponse({'success': True, 'data':list(payments_)}, status = 200)
    #add
    elif request.method == "POST":
        data = json.loads(request.body)

        payments_date = data.get('Date')
        payments_amount = data.get('Amount')

        if MemberAccounts.objects.filter().exists():
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
            if MemberAccounts.objects.get(id = payments_id).DoesNotExist():
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

        if MemberAccounts.objects.get(id = payments_id).DoesNotExist():
            return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
        if not payments_id:
            return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
        
        payments_del = MemberAccounts.objects.filter(id = payments_id)
        payments_del.delete()

@login_required
def category_crud(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            name = name.lower()

            # validation for existance
            if Category.objects.filter(category_name=name).exists():
                return JsonResponse({'success': False, 'message':f'{name} category exists.' }, status = 400) 

            logger.info('Creating category .....')

            # creation 
            cat = Category.objects.create(
                category_name = name
            )

            logger.info(f'Category created: {cat}')

            categories = Category.objects.all().values()

            logger.info(f'Categories: {categories}')
            return JsonResponse({'success': True, 'data':list(categories)}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
        
@login_required
def item_of_use_crud(request):
    if request.method == 'POST':
        """
            payload
            data = [
                servivce:int (id)
                itemsofsue = [{
                    quantity,
                    cost,
                    category
                }]
            ]
        """
        try:
            data = json.loads(request.body)
            name = data.get('name')
            service = data.get('service')
            name = name.lower()

            logger.info(f'name: {name}')

            # validation for existance
            if itemOfUseName.objects.filter(item_of_use_name=name).exists():
                return JsonResponse({'success': False, 'message':f'{name} Item of use exists.' }, status = 400) 

            with transaction.atomic():
                # creation 
                item = itemOfUseName.objects.create(
                    item_of_use_name = name
                )

                category = Category.objects.get(id=data.get('category'))

                ItemOfUse.objects.create(
                    name=item,
                    service=service,
                    cost=data.get('cost'),
                    category=category,
                    quantity=data.get('quantity')
                )

                items = itemOfUseName.objects.all().values()

                logger.info(f'items: {items}')
                return JsonResponse({'success': True, 'data':list(items)}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    
    if request.method == 'GET':
        iou_id = request.GET.get('id', '')
        service_id = request.GET.get('service_id', '')

        logger.info(f'id: {iou_id}')
        logger.info(f'service: {service_id}')

        if iou_id and service_id:
            try:
                iou = itemOfUseName.objects.get(id=iou_id)
                service = Services.objects.get(id=service_id)
                items_iou = ItemOfUse.objects.filter(name=iou).values(
                    'name__item_of_use_name',
                    'quantity',
                    'cost',
                    'description',
                    'category__category_name'
                )
                logger.info(f'iou_items: {items_iou}')
                return JsonResponse({'success': True, 'date':list(items_iou)}, status = 400)
            except Exception as e:
                return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    
    
