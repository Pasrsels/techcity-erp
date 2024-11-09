from django.shortcuts import render, redirect
# from .data_utils import get_services_with_details
from .models import *
from django.shortcuts import get_object_or_404
import json
from django.http.response import HttpResponse, JsonResponse

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







