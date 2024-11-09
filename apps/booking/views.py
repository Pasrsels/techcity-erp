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
        service = Services.objects.filter(id=id).values()
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
