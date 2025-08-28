from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
import pandas as pd
from weasyprint import HTML
from .models import Cashbook

@login_required
def get_transactions_preview(request):
    """Get preview data for transactions based on filters"""
    transaction_type = request.GET.get('type', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Convert dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    
    # Base queryset
    transactions = Cashbook.objects.filter(branch=request.user.branch)
    
    # Apply date filters
    if start_date:
        transactions = transactions.filter(issue_date__gte=start_date)
    if end_date:
        transactions = transactions.filter(issue_date__lte=end_date)
    
    # Apply transaction type filter
    if transaction_type == 'cash_in':
        transactions = transactions.filter(credit=True)
    elif transaction_type == 'cash_out':
        transactions = transactions.filter(debit=True)
    
    # Prepare data for response
    data = []
    for transaction in transactions:
        data.append({
            'date': transaction.issue_date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'amount': float(transaction.amount),
            'type': 'Cash In' if transaction.credit else 'Cash Out',
            'currency': transaction.currency.code
        })
    
    return JsonResponse({'data': data})

@login_required
def export_transactions_pdf(request):
    """Export transactions to PDF"""
    transaction_type = request.GET.get('type', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Convert dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    
    # Get transactions using the same logic as preview
    transactions = Cashbook.objects.filter(branch=request.user.branch)
    
    if start_date:
        transactions = transactions.filter(issue_date__gte=start_date)
    if end_date:
        transactions = transactions.filter(issue_date__lte=end_date)
    
    if transaction_type == 'cash_in':
        transactions = transactions.filter(credit=True)
    elif transaction_type == 'cash_out':
        transactions = transactions.filter(debit=True)
    
    # Prepare context for template
    context = {
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'transaction_type': transaction_type,
        'branch': request.user.branch.name
    }
    
    # Render HTML template
    html_string = render_to_string('cashbook/reports/transactions_pdf.html', context)
    
    # Generate PDF
    html = HTML(string=html_string)
    pdf = html.write_pdf()
    
    # Create response
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="transactions_report_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    return response

@login_required
def export_transactions_excel(request):
    """Export transactions to Excel"""
    transaction_type = request.GET.get('type', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Convert dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
    
    # Get transactions using the same logic as preview
    transactions = Cashbook.objects.filter(branch=request.user.branch)
    
    if start_date:
        transactions = transactions.filter(issue_date__gte=start_date)
    if end_date:
        transactions = transactions.filter(issue_date__lte=end_date)
    
    if transaction_type == 'cash_in':
        transactions = transactions.filter(credit=True)
    elif transaction_type == 'cash_out':
        transactions = transactions.filter(debit=True)
    
    # Prepare data for Excel
    data = []
    for transaction in transactions:
        data.append({
            'Date': transaction.issue_date,
            'Description': transaction.description,
            'Amount': float(transaction.amount),
            'Type': 'Cash In' if transaction.credit else 'Cash Out',
            'Currency': transaction.currency.code
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel file
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="transactions_report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    
    # Write to Excel
    df.to_excel(response, index=False)
    
    return response 