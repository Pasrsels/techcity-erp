from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import *
from django.views.decorators.csrf import csrf_exempt
import json


# Create your views here.
def services_view(request):
    services = Services.objects.filter(delete=False)
    return render(request, 'services/service.html')

def service_crud(request, service_id):
    if request.method == "GET":#View
        service = Services.objects.filter(id= service_id).values()
        return JsonResponse({'success':True, 'data':list(service), 'status': 200})
    elif request.method == "POST":#ADD
        
        data = json.loads(request.body)
        service_data = data.get('service', [])
        type_data = data.get('type_data', [])

        name = data.get('Name')
        
        service_add = Services(name = name,)
        service_add.save()

        Types.objects.create(
            name=type_data[0].name
        )
        return JsonResponse({'success':True, 'status': 200})
    elif request.method == "PUT":

        data = json.loads(request.body)

        name = data.get('name')

        service_edit = Services.objects.get(id= service_id)

        service_edit.Name = name
        service_edit.save()
        return JsonResponse({'success':True, 'status':200})
    
    elif request.method == "DELETE":

        data = json.loads(request.body)
        
        name = data.get('Name')

        service_del = Services.objects.get(id= service_id)
        service_del.delete()
        return JsonResponse({'success':True, 'status':200})
    return JsonResponse({'success':True, 'status': 200})
