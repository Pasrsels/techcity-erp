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


#API EndPoint
################################################################################################################
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class POS(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        invoice_count = Invoice.objects.filter(issue_date=timezone.now(), branch=request.user.branch).count()
        held_invoices_count = Invoice.objects.filter(hold_status=True, branch=request.user.branch).count()
        data = {
            'invoice count': invoice_count,
            'held invoice count': held_invoices_count
        }        
        return Response(data, status= status.HTTP_200_OK)

class LastDueInvoice(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, customer_id):
        invoice = Invoice.objects.filter(customer__id=customer_id, payment_status=Invoice.PaymentStatus.PARTIAL)\
        .order_by('-issue_date').values('invoice_number')
        logger.info(invoice)
        return Response(invoice, status= status.HTTP_200_OK)