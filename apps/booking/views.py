from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from .models import *
import json


# Create your views here.
def services_view(request):
    return render(request, 'services/service.html')

def service_crud(request,service_id):
    if request.method == "GET":
        service = Services.objects.filter(id= service_id).values()
        return JsonResponse({'success':True, 'data':list(service), 'status': 200})
    elif request.method == "POST":#ADD
        
        data = json.loads(request.body)

        name = data.get('Name')
        
        service_add = Services(name = name,)
        service_add.save()

        