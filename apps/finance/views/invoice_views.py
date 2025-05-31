from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from io import BytesIO
from xhtml2pdf import pisa
from ..models import Invoice, InvoiceItem
from ..forms import InvoiceForm
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from loguru import logger
from ..tasks import send_invoice_email_task
from apps.pos.utils.receipt_signature import generate_receipt_data
from apps.pos.utils.submit_receipt_data import submit_receipt_data

@login_required
def invoice(request):
    form = InvoiceForm()
    return render(request, 'invoice.html', {'form': form})

@login_required
@transaction.atomic
def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.save()
            return redirect('finance:invoice_details', invoice_id=invoice.id)
    else:
        form = InvoiceForm()
    return render(request, 'create_invoice.html', {'form': form})

@login_required
def invoice_details(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    items = InvoiceItem.objects.filter(invoice=invoice)
    return render(request, 'invoice_details.html', {'invoice': invoice, 'items': items})

@login_required
@transaction.atomic
def update_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            return redirect('finance:invoice_details', invoice_id=invoice.id)
    else:
        form = InvoiceForm(instance=invoice)
    return render(request, 'update_invoice.html', {'form': form, 'invoice': invoice})

@login_required
@transaction.atomic
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.delete()
    return redirect('finance:invoice')

@login_required
def invoice_pdf(request):
    invoice_id = request.GET.get('invoice_id')
    invoice = get_object_or_404(Invoice, id=invoice_id)
    items = InvoiceItem.objects.filter(invoice=invoice)
    
    html_string = render_to_string('invoice_pdf.html', {'invoice': invoice, 'items': items})
    buffer = BytesIO()
    pisa.CreatePDF(html_string, dest=buffer)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
    return response

@login_required
def send_invoice_email(request):
    invoice_id = request.GET.get('invoice_id')
    invoice = get_object_or_404(Invoice, id=invoice_id)
    items = InvoiceItem.objects.filter(invoice=invoice)
    
    html_string = render_to_string('invoice_email.html', {'invoice': invoice, 'items': items})
    buffer = BytesIO()
    pisa.CreatePDF(html_string, dest=buffer)
    
    email = EmailMessage(
        'Your Invoice',
        'Please find your invoice attached.',
        'your_email@example.com',
        [invoice.customer.email],
    )
    
    buffer.seek(0)
    email.attach(f'invoice_{invoice.invoice_number}.pdf', buffer.getvalue(), 'application/pdf')
    email.send()
    
    return JsonResponse({'success': True})

# API Views
class InvoiceList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.all()
        data = [{
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'customer': invoice.customer.name,
            'amount': invoice.amount,
            'date': invoice.issue_date
        } for invoice in invoices]
        return JsonResponse(data, safe=False)

class CreateInvoice(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = InvoiceForm(request.data)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.user = request.user
            invoice.save()
            return JsonResponse({'id': invoice.id}, status=201)
        return JsonResponse(form.errors, status=400)

class InvoiceDetails(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id=invoice_id)
        items = InvoiceItem.objects.filter(invoice=invoice)
        data = {
            'invoice': {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'customer': invoice.customer.name,
                'amount': invoice.amount,
                'date': invoice.issue_date
            },
            'items': [{
                'id': item.id,
                'product': item.product.name,
                'quantity': item.quantity,
                'price': item.price
            } for item in items]
        }
        return JsonResponse(data)

class InvoicePDF(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        invoice = get_object_or_404(Invoice, id=id)
        items = InvoiceItem.objects.filter(invoice=invoice)
        
        html_string = render_to_string('invoice_pdf.html', {'invoice': invoice, 'items': items})
        buffer = BytesIO()
        pisa.CreatePDF(html_string, dest=buffer)
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
        return response 