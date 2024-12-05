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
    service = Services.objects.filter(delete_s = False).values()
    items = ItemOfUse.objects.filter(delete_iou = False).values('id','service__id', 'description', 'name__item_of_use_name', 'cost', 'quantity')
    category = Category.objects.all().values()
    logger.info(items)
    return render(request,'services1.html',{
        'services': service,
        'items': items,
        'category_data': category,
        'serviceform': serviceform,   
    })

#2
@login_required
def services(request):
    serviceform = ServiceForm()
    inventoryform = InventoryForm()
    unit_measurement = UnitForm()
    services = Services.objects.filter(delete_s = False)
    iouForm = AddIouName()
    logger.info(services)
    categoryForm = AddCategory()
    names = ItemOfUse.objects.filter(delete_iou = False)
    category = Category.objects.all().values()
    measurements = UnitMeasurement.objects.all()
    return render(request, 'service_products.html',{
        'names':names,
        'iouForm':iouForm,
        'services': services,
        'service': serviceform,
        'category_data': category,
        'inventory': inventoryform,
        'measurements':measurements,
        'categoryForm':categoryForm,
        # 'unit_measure': unit_measure,
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

            if Services.objects.filter(service_name = name.lower()).exists():
                return JsonResponse({'success': False, 'message': f'{name} already exists'}, status = 400)
            
            logger.info(f'service name: {name}')
            with transaction.atomic():

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
            service_id = data.get('service_id')
            service_name = data.get('service_name')
            service_description = data.get('description')
            logger.info(service_name,service_description)
            if not Services.objects.filter(id = service_id).exists():
                return JsonResponse({'success': False, 'message': f'user with {service_id} does not exist'}, status = 400)
            else:
                service_edit = Services.objects.get(id = service_id)
                service_edit.service_name = service_name
                service_edit.description = service_description
                service_edit.save()
                return JsonResponse({'success':True},status = 200)
        except Exception as e:
            return JsonResponse({'success':False, 'response':f'{e}'}, status = 400)
    #delete
    elif request.method == "DELETE":
        data = json.loads(request.body)
        service_id = data.get('service_id')
        logger.info(data)
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete_s = True
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

            items = {
                name: str,
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
        
            if not service_name  or not items or not description:
                return JsonResponse({'success': False, 'message': 'please fill in the missing fields'}, status = 400)
            
            if not ServiceRange.objects.filter(name = items.get('service_range').lower()).exists():
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
                itemsofsue = [{
                    name,
                    quantity,
                    cost,
                    category,
                    description
                }]
            ]
        """
        try:
            data = json.loads(request.body)
            name = data.get('name')
            cost = data.get('cost')
            category = data.get('category')
            quantity = data.get('quantity')
            description = data.get('description')
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
                    name = item,
                    description = description,
                    cost=cost,
                    category=category,
                    quantity=quantity,
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
                service = Services.objects.filter(id=service_id).values('service_range')

                logger.info(f'name {iou}')
                items_iou = ItemOfUse.objects.filter(name=iou.id).values(
                    'name__item_of_use_name',
                    'quantity',
                    'cost',
                    'description',
                    'category__category_name',
                    'id',
                )
                logger.info(f'iou_items: {items_iou}')
                return JsonResponse({
                    'success': True, 
                    'items':list(items_iou),
                    'service_range':list(service),
                }, status = 200)
            except Exception as e:
                return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_of_use_id')
            logger.info(item_id)

            if ItemOfUse.objects.filter(id = item_id).exists():
                item_delete = ItemOfUse.objects.get(id = item_id)
                item_delete.delete_iou = True
                item_delete.save()
                return JsonResponse({'success':True}, status = 200)
            return JsonResponse({'success': False, 'message': 'item does not exist'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'error: {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
    
@login_required
def save_combined_service(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
            service_id = data.get('service_id')
            iout_items = data.get('iou')

            #get service 
            service = Services.objects.get(id=service_id)
            logger.info(service)
            # add service to iou
            for item in iout_items:
                iou = ItemOfUse.objects.get(id=item['id'])
                iou.service.add(service)
                iou.save()

                print(iou.service.all)

            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    
#member view
@login_required
def members_view(request):
    memberForm = AddMember()
    return render(request, 'members.html',{
        'memberForm ': memberForm
    })

#member
@login_required
def member_crud(request):
    #Add
    if request.method == "POST":

        data = json.loads(request.body)
 
        n_ID = data.get('National_ID')
        m_name = data.get('Name')
        m_email = data.get('Email')
        m_phone = data.get('Phone')
        m_adress = data.get('Address')
        m_enrollment = data.get('Enrollment')
        m_company = data.get('Company')
        m_age = data.get('Age')
        m_gender = data.get('Gender')

        if Members.objects.filter(National_ID = n_ID).exists():
            return JsonResponse({'success': True, 'message': 'Member already exists'}, status = 400)
        elif not n_ID or not m_name or not m_email or not m_phone or not m_adress or not m_enrollment \
        or not m_company or not m_age or not m_gender:
            return JsonResponse({'success': False, 'message': 'Pliz fill in empty fields'}, status = 400)
        with transaction.atomic():
            try: 
               
                """"
                    1. we are going to receive a total amount which consists of admin if its a first payment,
                    2. we are going to seperate it into 2 thus admin and service amount, 
                    3. we are going to check if they is an balance
                """

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
                    delete = False
                )

                MemberAccounts.objects.create(
                    Balance = 20,
                    Member = member_add,
                    delete = False
                )

                Logs.objects.create(
                    action = 'create'
                )
                return JsonResponse({'success': True, 'response': 'Data saved'}, status = 200)
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'error: {e}'}, status = 400)
    #Update
    elif request.method == "PUT":
        #get data part of file
        try:
            data = json.loads(request.body)

            n_ID = data.get('National_ID')
            m_id = data.get('member_id')
            m_name = data.get('Name')
            m_email = data.get('Email')
            m_phone = data.get('Phone')
            m_adress = data.get('Address')
            m_enrollment = data.get('Enrollment')
            m_company = data.get('Company')
            m_age = data.get('Age')
            m_gender = data.get('Gender')

            if Members.objects.filter(National_ID = n_ID).exists():
                with transaction.Atomic():
                    Member_update = Members.objects.get(id = m_id)
                    Member_update.National_ID = n_ID,
                    Member_update.Name = m_name,
                    Member_update.Email = m_email,
                    Member_update.Phone = m_phone,
                    Member_update.Address = m_adress,
                    Member_update.Enrollment = m_enrollment,
                    Member_update.Company = m_company,
                    Member_update.Age = m_age,
                    Member_update.Gender = m_gender,
                    Member_update.delete = False,
                    Member_update.save()

                    Logs.objects.create(
                        action = 'update'
                    )
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)
            id = data.get('id')

            if Members.objects.filter(id = id).exists():
                Members.objects.get(id = id)
                member = Members.objects.get(id = id)
                member.delete = True
                member.save()
                Logs.objects.create(
                    action = 'delete'
                )
                return JsonResponse({'success': True}, status = 200)
            return JsonResponse({'success':False, 'message': 'member doesnot exist'}, status = 400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'{e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
#member_acc    
@login_required
def member_acc_crud(request):
    #update
    if request.method == "PUT":
        data = json.loads(request.body)
        member_id = data.get('id')
        member_balance = data('Balance')
        try:
            if MemberAccounts.objects.get(id = member_id).DoesNotExist():
                return JsonResponse({'success': False, 'message': 'cannot update none existing field'}, status = 400)
            elif not member_id or not member_balance:
                return JsonResponse({'success': False, 'message': 'empty fields'}, status = 400)
            
            with transaction():
                member_account = MemberAccounts.objects.get(id = member_id)
                member_account.Balance = member_balance
                member_account.save()
                return JsonResponse({'success': True, 'response': 'items updated'}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response':f'{e}'}, status = 200)
    #delete
    elif request.method == "DELETE":
        try:
            data = json.loads(request.body)

            member_id = data('id')

            if MemberAccounts.objects.filter(id = member_id).exists():
                return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
            elif not member_id:
                return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
            member_acc_del = MemberAccounts.objects.get(id = member_id)
            member_acc_del.delete = True
            member_acc_del.save()
            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'error: {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)

#Payments
@login_required
def payments_crud(request):
    #add
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            payments_fee = data.get('fee')
            payments_amount = data.get('Amount')
            member_id = data.get('member_id')
            account_id = data.get('account_id')
    
            if not payments_amount or not member_id or not account_id:
                return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
            with transaction.atomic():
                member_details = Members.objects.get(id = member_id)
                account_details = MemberAccounts.objects.get(id = account_id)        
                Payments.objects.create(
                    Amount = payments_amount,
                    Member = member_details,
                    Account = account_details
                )
                old_balance = account_details.Balance
                account_details.Balance =  old_balance - payments_amount
                account_details.save()
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'error: {e}'}, status = 400)
    #update
    elif request.method == "PUT":

        data = json.loads(request.body)

        payments_id = data.get('id')
        payments_amount = data.get('Amount')
        member_account = data.get('account_id')
        
        try:
            if not payments_id or not payments_amount or not member_account:
                return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
            with transaction.atomic():
                payments = Payments.objects.get(id = payments_id)
                old_amount = payments.Amount
                payments.Amount = payments_amount
                
                member_acc = MemberAccounts.objects.get(id = member_account)
                current_balance = member_acc.Balance
                member_acc.Balance = (current_balance + old_amount) - payments_amount

                payments.save()
                member_acc.save()
                return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response':f'{e}'}, status = 200)
    # #delete
    # if request.method == "DELETE":
    #     data = json.loads(request.body)

    #     payments_id = data.get('id')

    #     if MemberAccounts.objects.get(id = payments_id).DoesNotExist():
    #         return JsonResponse({'success': False, 'response':'cannot delete no existing field'}, status = 400)
    #     if not payments_id:
    #         return JsonResponse({'success': False, 'response': 'empty field please fill'}, status = 400)
        
    #     payments_del = MemberAccounts.objects.filter(id = payments_id)
    #     payments_del.delete()
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
