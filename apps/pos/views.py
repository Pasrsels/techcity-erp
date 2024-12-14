import os
import datetime
from django.http import JsonResponse
from django.db import transaction
from apps.finance.forms import CashWithdrawForm
from django.utils import timezone
from apps.finance.models import Invoice
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from loguru import logger
from apps.settings.models import TaxSettings
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from apps.inventory.models import Inventory


@login_required
@transaction.atomic
def pos(request):
    form = CashWithdrawForm()
    invoice_count = Invoice.objects.filter(issue_date=timezone.now(), branch=request.user.branch).count()
    held_invoices_count = Invoice.objects.filter(hold_status=True, branch=request.user.branch).count()
            
    return render(request, 'pos.html', {
        'invoice_count':invoice_count, 
        'form':form, 
        'count':held_invoices_count,
    })

@login_required
def process_receipt(request):
    pass    

@login_required
def last_due_invoice(request, customer_id):
    invoice = Invoice.objects.filter(customer__id=customer_id, payment_status=Invoice.PaymentStatus.PARTIAL)\
            .order_by('-issue_date').values('invoice_number')
    logger.info(invoice)
    return JsonResponse(list(invoice), safe=False)


def upload_file():
    file = request.files['file']
    file_path = os.path.join('uploads', file.filename)
    file.save(file_path)
    return JsonResponse({"status": "success", "file_path": file_path}), 200


#################################################################################################################################################################################################
""" Pos API end points mainly for:
    customers crud: check finance api views, 
    products
    processing the sale 
"""

class productsAPIView(APIView):
    """ Api view which returns products """
    def get(self, request):
        products = Inventory.objects.all().values(
            'id',
            'name',
            'price',
            'dealer_price',
            'category__name'
        )
        return Response({'success':True, 'data':products})
    

