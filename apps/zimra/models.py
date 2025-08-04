from django.db import models

class Receipt(models.Model):
    RECEIPT_TYPE_CHOICES = [
        ('FiscalInvoice', 'Fiscal Invoice'),
        ('CreditNote', 'Credit Note'),
        ('DebitNote', 'Debit Note'),
    ]
    receipt_type = models.CharField(max_length=20, choices=RECEIPT_TYPE_CHOICES)
    receipt_currency = models.CharField(max_length=10)
    receipt_date = models.DateField()
    receipt_number = models.CharField(max_length=20)

class ReceiptTaxes(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    tax_id = models.CharField(max_length=20)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2)
    sales_amount_with_tax = models.DecimalField(max_digits=12, decimal_places=2)


class ReceiptPayment(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    money_type_code = models.CharField(max_length=20)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
