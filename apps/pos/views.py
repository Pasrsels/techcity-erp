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

# import json
# import base64
# from .models import OfflineReceipt

# def submit_offline_receipts():
#     receipts = OfflineReceipt.objects.filter(submitted=False)

#     if not receipts.exists():
#         print("No receipts to submit.")
#         return

#     receipt_list = [receipt.receipt_data for receipt in receipts]
#     file_data = {
#         "header": {
#             "deviceID": 123456,
#             "fiscalDayNo": 1,
#             "fiscalDayOpened": "2025-01-06T08:00:00",
#             "fileSequence": 1
#         },
#         "content": {"receipts": receipt_list},
#         "footer": {
#             "fiscalDayClosed": "2025-01-06T20:00:00",
#             "fiscalCounters": [
#                 {
#                     "fiscalCounterType": "SaleByTax",
#                     "fiscalCounterCurrency": "USD",
#                     "fiscalCounterValue": sum(r["receiptTotal"] for r in receipt_list)
#                 }
#             ]
#         }
#     }

#     encoded_file = base64.b64encode(json.dumps(file_data).encode()).decode()

#     try:
#         response = submit_file_to_zimra(encoded_file)
#         if response.get("status") == "success":
#             receipts.update(submitted=True)
#             logger.info("Receipts submitted successfully.")
#         else:
#             logger.info(f"Submission failed: {response}")
#     except Exception as e:
#         logger.info(f"Error submitting receipts: {e}")


# def submit_file_to_zimra(encoded_file):
#     # url = "https://fdmsapi.zimra.co.zw/submitFile"
#     # headers = {"Authorization": f"Bearer {api_key}"}
#     # payload = {"deviceID": 123456, "file": encoded_file}

#     # response = requests.post(url, json=payload, cert=(cert_path, key_path), headers=headers)
#     pass
#     # return response.json()


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