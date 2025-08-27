from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import Services, ItemOfUse, Category, UnitMeasurement, itemOfUseName
from ..forms import ServiceForm, AddIouName, AddCategory, UnitForm
from loguru import logger
import json
from django.db import transaction

@login_required
def services_view(request):
    serviceform = ServiceForm()
    service = Services.objects.all().values()
    items = ItemOfUse.objects.all().values('id','service__id', 'description', 'name__item_of_use_name', 'cost', 'quantity')
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

@login_required
def services(request):
    serviceform = ServiceForm()
    inventoryform = InventoryForm()
    unit_measurement = UnitForm()
    services = Services.objects.all()
    iouForm = AddIouName()
    categoryForm = AddCategory()
    names = itemOfUseName.objects.all()
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
        'unit_measurement':unit_measurement
    })

@login_required
def service_crud(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            description = data.get('description')
            unit_measure = data.get('unit_measure')
            service_range = data.get('service_range')

            if Services.objects.filter(service_name = name.lower()).exists():
                return JsonResponse({'success': False, 'message': f'{name} already exists'}, status = 400)

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
    if request.method == "PUT":
        try:
            data = json.loads(request.body)
            service_id = data.get('service_id')
            service_name = data.get('service_name')
            service_description = data.get('description')
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
    elif request.method == "DELETE":
        data = json.loads(request.body)
        service_id = data.get('service_id')
        if Services.objects.filter(id = service_id).exists():
            service_del = Services.objects.get(id= service_id)
            service_del.delete()
            return JsonResponse({'success':True}, status=200)
        return JsonResponse({'success': False, 'response': 'cannot delete none existing field'}, status = 400)
    return JsonResponse({'success':False, 'response': 'invalid request'}, status =  500)

@login_required
def save_combined_service(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service_id = data.get('service_id')
            iout_items = data.get('iou')

            service = Services.objects.get(id=service_id)

            for item in iout_items:
                iou = ItemOfUse.objects.get(id=item['id'])
                iou.service.add(service)
                iou.save()

            return JsonResponse({'success': True}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)
