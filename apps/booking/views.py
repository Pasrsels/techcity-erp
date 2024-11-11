from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from .models import *
from django.shortcuts import get_object_or_404
import json
from django.http.response import HttpResponse, JsonResponse
from django.db import transaction



def services_view(request):
    services = Services.objects.filter(delete=False)
    return render(request, 'services/service.html')

@login_required
def service_crud(request):
    if request.method == "GET":#View
        service = Services.objects.all()
        return JsonResponse({'success':True, 'data':list(service), 'status': 200})
    elif request.method == "POST":#ADD
        
        data = json.loads(request.body)

        service_id = data.get([0]['service_id'])
        service_name = data.get([0]['service_name'])
        service_type = data.get([0]['service_type_id'])

        type_id = data.get([1]['type_id'])
        type_name = data.get([1]['type_name'])
        type_price = data.get([1]['type_price'])
        type_service_duration = data.get([1]['type_service_duration'])
        type_promotion = data.get([1]['type_promotion'])

        if Services.objects.filter(id = service_id).exists() or Services.objects.filter(id = type_id).exists():
            return JsonResponse({'success': False, 'reason': 'added item already exists', 'status': 400})
        elif not service_id or  not service_name or not service_type or not type_id or not type_name or \
              not type_price or not type_service_duration or not type_promotion:
            return JsonResponse({'success': True, 'response': 'please fill in missing fields', 'status': 400})
        
        with transaction.atomic():
            type_add = Types(
                t_name = type_name, 
                t_price = type_price, 
                t_sduration = type_service_duration, 
                t_promo = type_promotion
                )
            type_add.save()
            #not sure on addind type id
            service_add = Services(s_id = service_id, s_name = service_name, s_type = service_type)
            service_add.save()
            return JsonResponse({'success':True, 'status': 200})
    #update
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            service_id = data.get([0]['service_id'])

            service = Services.objects.get(id=service_id)

            service_name = data.get([0]['service_name'])
            service_type = data.get([0]['service_type_id'])

            type_id = data.get([1]['type_id'])
            type_name = data.get([1]['type_name'])
            type_price = data.get([1]['type_price'])
            type_service_duration = data.get([1]['type_service_duration'])
            type_promotion = data.get([1]['type_promotion'])
            
            service.Name = service_name
        
            service.save()
            return JsonResponse({'success':True, 'status':200})
        except Exception as e:
            return JsonResponse({'success':False, 'message':f'{e}'})
    
    elif request.method == "DELETE":

        data = json.loads(request.body)
        service_id = data.get([0]['service_id'])
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete()
            return JsonResponse({'success':True}, status=200)
        return JsonResponse({'success': False, 'response': 'cannot delete none existing field', 'status': 400})
    return JsonResponse({'success':False, 'response': 'invalid request', 'status': 400})

@login_required
def member_crud(request):
    #Read
    if request.method == "GET":
        member = Members.objects.all()
        return JsonResponse({'success': True, 'data': list(member)}, status = 200)
    #Add
    elif request.method == "POST":
        data = json(request.body)
        
        id = data.get([]['id'])
        n_ID = data.get([0]['National_ID'])
        name = data.get([0]['Name'])
        email = data.get([0]['Email'])
        phone = data.get([0]['Phone'])
        adress = data.get([0]['Address'])
        enrollment = data.get([0]['Enrollment'])
        company = data.get([0]['Company'])
        age = data.get([0]['Age'])
        gender = data.get([0]['Gender'])

        if Members.objects.filter(id = id).exists():
            return JsonResponse({'success': True, 'response': 'field already exists'}, status = 400)
        elif not id or not n_ID or not name or not email or not phone or not adress or not enrollment \
        or not company or not age or not gender:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
        
        member = Members(
            id = id,
            National_ID = n_ID,
            Name = name,
            Email = email,
            Phone = phone,
            Address = adress,
            Enrollment = enrollment,
            Company = company,
            Age = age,
            Gender = gender
        )
        member.save()
        return JsonResponse({'success': True, 'response': 'Data saved'}, status = 200)
    #Update
    elif request.method == "PUT":
        data = json(request.body)

        id = data.get([]['id'])
        n_ID = data.get([0]['National_ID'])
        name = data.get([0]['Name'])
        email = data.get([0]['Email'])
        phone = data.get([0]['Phone'])
        adress = data.get([0]['Address'])
        enrollment = data.get([0]['Enrollment'])
        company = data.get([0]['Company'])
        age = data.get([0]['Age'])
        gender = data.get([0]['Gender'])

        try:
            if Members.objects.get(id = id).DoesNotExist():
                return JsonResponse({'success': False, 'response': 'member doesnot exist in database'}, status = 400)
            member = Members(
                id = id,
                National_ID = n_ID,
                Name = name,
                Email = email,
                Phone = phone,
                Address = adress,
                Enrollment = enrollment,
                Company = company,
                Age = age,
                Gender = gender
            )
            member.save()
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
    elif request.method == "DELETE":
        data = json(request.body)

        id = data.get([]['id'])

        try:
            if Members.objects.get(id = id).DoesNotExist():
                return JsonResponse({'success': False, 'response': 'field doesnot exist in database'}, status = 400)
            member = Members.objects.get(id = id)
            member.delete()
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
        
@login_required
def member_acc_crud(request):
    #read
    if request.method == "GET":
        member_acc = Member_accounts.objects.all()
        return JsonResponse({'success': True,}, status = 200)
    #add
    elif request.method == "POST":
        data = json.loads(request.body)

        member_id = data.get([0]['id'])
        member_balance = data.get([0]['Balance'])
        payments_id = data.get([1]['id'])
        payments_date = data.get([1]['Date'])
        payments_amount = data.get([1]['Amount'])

        if Member_accounts.objects.filter(id = member_id).exists():
            return JsonResponse({'success': False, 'response': 'cannot add existing field'}, status = 400)
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
        member_acc_del.delete()

def office_crud(request):
    #read
    if request.method == "GET":
        office_view = Office_spaces.objects.all()
        return JsonResponse({'success': True, 'data': list(office_view)}, status = 200)
    #add
    elif request.method == "POST":
        data = json.loads(request.body)

        office_id = data.get([0]['id'])
        office_name = data.get([0]['Balance'])
    
        if Member_accounts.objects.filter(id = office_id).exists():
            return JsonResponse({'success': False, 'response': 'cannot add existing field'}, status = 400)
        elif not office_id or not office_name:
            return JsonResponse({'success': False, 'response': 'empty fields'}, status = 400)
        
        
        office_space = Office_spaces(
            id = office_id,
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
        
