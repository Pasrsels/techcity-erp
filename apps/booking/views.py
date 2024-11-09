<<<<<<< HEAD
from django.shortcuts import render, redirect
# from .data_utils import get_services_with_details
=======
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
>>>>>>> 41f8753387e45acff57e2e8143c59fdcd7559057
from .models import *
from django.shortcuts import get_object_or_404
import json
from django.http.response import HttpResponse, JsonResponse

<<<<<<< HEAD
def services_page(request):
    if request.method == 'GET':
        services = Services.objects.all()
        return render(request, 'services.html', {'services': services})

    elif request.method == "POST":
        # Handle service edit requests (requires form data in request)
        service_id = request.POST.get('service_id')
        service = get_object_or_404(Services, id=service_id)
        # Update service fields from POST data
        service.name = request.POST.get('name', service.name)
        service.type.promotion = request.POST.get('promotion', service.type.promotion)
        service.type.price = request.POST.get('price', service.type.price)
        service.type.duration = request.POST.get('duration', service.type.duration)
        service.type.save()  # Save the type if any fields were updated
        service.save()       # Save the service
        return redirect('services_page')

    elif request.method == "DELETE":
        # Handle service deletion
        data = json.loads(request.body)
        service_id = data.get('service_id')
        service = get_object_or_404(Services, id=service_id)
        service.delete()
        return HttpResponse(status=204)

    elif request.method == "GET" and 'service_id' in request.GET:
        # Handle AJAX request to get service details
        service_id = request.GET.get('service_id')
        service = get_object_or_404(Services, id=service_id)
        data = {
            "name": service.name,
            "type_name": service.type.name,
            "promotion": service.type.promotion,
            "price": service.type.price,
            "duration": service.type.duration,
        }
        return JsonResponse(data)

    return HttpResponse(status=405)  # Method not allowed for other cases







=======

# Create your views here.
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
        elif not service_id or  not service_name or not service_type or not type_id or not type_name or not type_price or not type_service_duration or not type_promotion:
            return JsonResponse({'success': True, 'response': 'please fill in missing fields', 'status': 400})
        type_add = Types(t_id = type_id, t_name = type_name, t_price = type_price, t_sduration = type_service_duration, t_promo = type_promotion)
        type_add.save()
        #not sure on addind type id
        service_add = Services(s_id = service_id, s_name = service_name, s_type = service_type)
        service_add.save()
        return JsonResponse({'success':True, 'status': 200})
    #update
    elif request.method == "PUT":

        data = json.loads(request.body)

        service_id = data.get([0]['service_id'])
        service_name = data.get([0]['service_name'])
        service_type = data.get([0]['service_type_id'])

        type_id = data.get([1]['type_id'])
        type_name = data.get([1]['type_name'])
        type_price = data.get([1]['type_price'])
        type_service_duration = data.get([1]['type_service_duration'])
        type_promotion = data.get([1]['type_promotion'])
        
        if Services.objects.filter(id = service_id).exists:
            return JsonResponse({'success': False, 'response': 'this update already exists', 'status': 400})
        service_update = Services(name = service_name)
        service_update.save()
        return JsonResponse({'success':True, 'status':200})
    
    elif request.method == "DELETE":

        data = json.loads(request.body)
        service_id = data.get([0]['service_id'])
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete()
            return JsonResponse({'success':True, 'status':200})
        return JsonResponse({'success': False, 'response': 'cannot delete none existing field', 'status': 400})
    return JsonResponse({'success':False, 'response': 'invalid request', 'status': 400})
>>>>>>> 41f8753387e45acff57e2e8143c59fdcd7559057
