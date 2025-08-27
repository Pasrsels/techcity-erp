from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import ItemOfUse, itemOfUseName, Category, Services
import json
from django.db import transaction
from loguru import logger

@login_required
def itemofuseCrud(request):
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
def item_of_use_crud(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            cost = data.get('cost')
            category = data.get('category')
            quantity = data.get('quantity')
            description = data.get('description')
            name = name.lower()

            if itemOfUseName.objects.filter(item_of_use_name=name).exists():
                return JsonResponse({'success': False, 'message':f'{name} Item of use exists.' }, status = 400)

            with transaction.atomic():
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

                return JsonResponse({'success': True, 'data':list(items)}, status = 200)
        except Exception as e:
            return JsonResponse({'success': False, 'response': f'{e}'}, status = 400)

    if request.method == 'GET':
        iou_id = request.GET.get('id', '')
        service_id = request.GET.get('service_id', '')

        if iou_id and service_id:
            try:
                iou = itemOfUseName.objects.get(id=iou_id)
                service = Services.objects.filter(id=service_id).values('service_range')

                items_iou = ItemOfUse.objects.filter(name=iou.id).values(
                    'name__item_of_use_name',
                    'quantity',
                    'cost',
                    'description',
                    'category__category_name',
                    'id',
                )
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

            if ItemOfUse.objects.filter(id = item_id).exists():
                item_delete = ItemOfUse.objects.get(id = item_id)
                item_delete.delete()
                return JsonResponse({'success':True}, status = 200)
            return JsonResponse({'success': False, 'message': 'item does not exist'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'error: {e}'}, status = 400)
    return JsonResponse({'success': False, 'message': 'invalid request'}, status = 500)
