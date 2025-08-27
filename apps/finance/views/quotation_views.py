from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from ..models import Qoutation, QoutationItems, Customer, Currency
from apps.inventory.models import Inventory
from ..tasks import send_quotation_email
from decimal import Decimal
import json
from django.template.loader import render_to_string
from loguru import logger

@login_required
@transaction.atomic
def create_quotation(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        qoute_data = data['data'][0]
        items_data = data['items']

        customer = Customer.objects.get(id=int(qoute_data['client_id']))
        currency = Currency.objects.get(id=qoute_data['currency'])

        qoute = Qoutation.objects.create(
            customer = customer,
            amount =  Decimal(qoute_data['subtotal']),
            branch = request.user.branch,
            currency = currency,
            qoute_reference = Qoutation.generate_qoute_number(request.user.branch.name),
            products = ', '.join([f'{item['product_name']} x {item['quantity']}' for item in items_data])
        )

        for item_data in items_data:
            item = Inventory.objects.get(pk=item_data['inventory_id'])

            QoutationItems.objects.create(
                qoute=qoute,
                product=item,
                unit_price=item.price,
                quantity=item_data['quantity'],
                total_amount= item.price * item_data['quantity'],
            )
        return JsonResponse({'success': True, 'qoute_id': qoute.id})
    return JsonResponse({'success': False})

@login_required
def qoutation_list(request):
    search_query = request.GET.get('q', '')
    qoutations = Qoutation.objects.filter(branch=request.user.branch).order_by('-date')

    if search_query:
        qoutations = qoutations.filter(
            Q(customer__name__icontains=search_query)|
            Q(products__icontains=search_query)|
            Q(date__icontains=search_query)|
            Q(qoute_reference__icontains=search_query)
        )

    return render(request, 'qoutations.html', {'qoutations':qoutations, 'search_query':search_query})

@login_required
def qoute_preview(request, qoutation_id):
    qoute = Qoutation.objects.get(id=qoutation_id)
    qoute_items = QoutationItems.objects.filter(qoute=qoute)
    return render(request, 'qoute.html', {'qoute':qoute, 'qoute_items':qoute_items})

@login_required
def qoute_preview_modal(request, qoutation_id):
    try:
        qoute = Qoutation.objects.get(id=qoutation_id)
        qoute_items = QoutationItems.objects.filter(qoute=qoute)
        html = render_to_string('qoutations/partial_preview.html', {
            'qoute': qoute,
            'qoute_items': qoute_items
        }, request=request)

        return JsonResponse({'success': True, 'html': html}, status=200)

    except Exception as e:
        return JsonResponse({'success': False, 'message':str(e)}, status=400)

@login_required
def delete_qoute(request, qoutation_id):
    qoute = get_object_or_404(Qoutation, id=qoutation_id)
    qoute.delete()
    return JsonResponse({'success':True, 'message':'Qoutation successfully deleted'}, status=200)

@login_required
def send_quote_email(request, quote_id):
    if request.method == 'POST':
        send_quotation_email.delay(quote_id)
        return JsonResponse({'success': True, 'message': 'Email sent successfully'})
    return JsonResponse({'success': False, 'error': 'Only POST method is allowed'})
