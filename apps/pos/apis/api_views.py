from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.finance.models import Invoice
from loguru import logger

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
