from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, F
from apps.inventory.models import WriteOff, DefectiveItem, InventoryShrinkage, Inventory, ActivityLog
from apps.inventory.forms import AddDefectiveForm, AddShrinkageForm, AddWriteOffForm
from django.db import transaction
import json
from loguru import logger

@login_required
def loss_management(request):
    """
        to put caching later
    """
    write_off_totals = WriteOff.objects.aggregate(total=Sum(F('quantity') * F('inventory_item__cost')))['total'] or 0
    defective_totals = DefectiveItem.objects.aggregate(total=Sum(F('quantity') * F('inventory_item__cost')))['total'] or 0
    shrinkage_totals = InventoryShrinkage.objects.aggregate(total=Sum(F('quantity') * F('inventory_item__cost')))['total'] or 0

    context = {
        'defective_form':AddDefectiveForm(),
        'shrinkage_form':AddShrinkageForm(),
        'write_off_form':AddWriteOffForm(),
        'write_off':write_off_totals,
        'defective':defective_totals,
        'shrinkage':shrinkage_totals
    }

    return render(request, 'loss_management/loss_management.html', context)

@login_required
def loss_management_accounts(request, account_name):
    try:
        if account_name == 'shrinkage':
            shrinkage = InventoryShrinkage.objects.all().select_related(
                'inventory_item',
                'created_by'
            ).values(
                'id',
                'inventory_item__id',
                'inventory_item__name',
                'inventory_item__cost',
                'quantity',
                'reason',
                'recorded_by',
                'created_at'
            ).annotate(
                total_cost = Sum(F('quantity') * F('inventory_item__cost'))
            )
            return JsonResponse(list(shrinkage), safe=False)

        if account_name == 'defective':
            defective = DefectiveItem.objects.all().select_related(
                'inventory_item',
                'created_by'
            ).values(
                'id',
                'inventory_item__id',
                'inventory_item__name',
                'inventory_item__cost',
                'quantity',
                'defect_description',
                'action_taken',
                'created_by',
                'created_at'
            ).annotate(
                total_cost = Sum(F('quantity') * F('inventory_item__cost'))
            )

            return JsonResponse(list(defective), safe=False)

        if account_name == 'write-off':
            write_off_data = WriteOff.objects.all().select_related(
                'inventory_item',
                'created_by'
            ).values(
                'id',
                'inventory_item__id',
                'inventory_item__name',
                'inventory_item__cost',
                'quantity',
                'reason',
                'created_by',
                'created_at'
            ).annotate(
                total_cost = Sum(F('quantity') * F('inventory_item__cost'))
            )

            return JsonResponse(list(write_off_data), safe=False)

    except Exception as e:
        logger.info(e)
        return JsonResponse({'success':False, 'message':f'{e}'}, status=200)

@login_required
@transaction.atomic
def create_defective(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity')
            defect_description = data.get('defect_description')
            action_taken = data.get('action_taken')

            product = Inventory.objects.get(id=product_id, branch=request.user.branch)

            if quantity > product.quantity:
                return JsonResponse({'success': False, 'message': 'Defective quantity cannot be more than the product quantity'}, status=400)

            defective_item = DefectiveItem.objects.create(
                inventory_item=product,
                quantity=quantity,
                defect_description=defect_description,
                action_taken=action_taken,
                created_by=request.user
            )

            product.quantity -= quantity
            product.save()

            ActivityLog.objects.create(
                branch=request.user.branch,
                user=request.user,
                action='defective',
                inventory=product,
                quantity=quantity,
                total_quantity=product.quantity,
                description=f'Defective: {defect_description}'
            )

            return JsonResponse({'success': True, 'message': 'Defective item created successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@transaction.atomic
def create_shrinkage(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity')
            reason = data.get('reason')

            product = Inventory.objects.get(id=product_id, branch=request.user.branch)

            if quantity > product.quantity:
                return JsonResponse({'success': False, 'message': 'Shrinkage quantity cannot be more than the product quantity'}, status=400)

            shrinkage_item = InventoryShrinkage.objects.create(
                inventory_item=product,
                quantity=quantity,
                reason=reason,
                created_by=request.user
            )

            product.quantity -= quantity
            product.save()

            ActivityLog.objects.create(
                branch=request.user.branch,
                user=request.user,
                action='shrinkage',
                inventory=product,
                quantity=quantity,
                total_quantity=product.quantity,
                description=f'Shrinkage: {reason}'
            )

            return JsonResponse({'success': True, 'message': 'Shrinkage item created successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@transaction.atomic
def create_write_off(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = data.get('quantity')
            reason = data.get('reason')

            product = Inventory.objects.get(id=product_id, branch=request.user.branch)

            if quantity > product.quantity:
                return JsonResponse({'success': False, 'message': 'Write-off quantity cannot be more than the product quantity'}, status=400)

            write_off_item = WriteOff.objects.create(
                inventory_item=product,
                quantity=quantity,
                reason=reason,
                created_by=request.user
            )

            product.quantity -= quantity
            product.save()

            ActivityLog.objects.create(
                branch=request.user.branch,
                user=request.user,
                action='write-off',
                inventory=product,
                quantity=quantity,
                total_quantity=product.quantity,
                description=f'Write-off: {reason}'
            )

            return JsonResponse({'success': True, 'message': 'Write-off item created successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
