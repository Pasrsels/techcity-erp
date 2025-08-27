from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings

class OfflineReceipt(models.Model):
    receipt_data = models.JSONField()  
    created_at = models.DateTimeField(auto_now_add=True) 
    submitted = models.BooleanField(default=False)  

    def __str__(self):
        return f"Receipt {self.id} - Submitted: {self.submitted}"
    

class FiscalDay(models.Model):
    day_no = models.IntegerField(default=1)
    is_open = models.BooleanField(default=False)
    global_count = models.IntegerField(default=0)
    receipt_count = models.IntegerField(default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

class FiscalCounter(models.Model):
    SALE_BY_TAX = "SaleByTax"
    SALE_BY_VAT = "SaleByVAT"
    SALE_TAX_BY_TAX = "SaleTaxByTax"
    Balancebymoneytype = "Balancebymoneytype"
    OTHER = "Other"

    COUNTER_TYPE_CHOICES = [
        (SALE_BY_TAX, "SaleByTax"),
        (SALE_BY_VAT, "SaleByVAT"),
        (SALE_TAX_BY_TAX, "SaleTaxByTax"),
        (Balancebymoneytype, "Balancebymoneytype"),
        (OTHER, "Other"),
    ]

    CASH = "Cash"
    CARD = "Card"
    BANK_TRANSFER = "BankTransfer"
    MOBILE_MONEY = "MobileMoney"

    MONEY_TYPE_CHOICES = [
        (CASH, "Cash"),
        (CARD, "Card"),
        (BANK_TRANSFER, "Bank Transfer"),
        (MOBILE_MONEY, "Mobile Money"),
    ]

    fiscal_counter_type = models.CharField(max_length=30, choices=COUNTER_TYPE_CHOICES, default=SALE_BY_TAX)
    fiscal_counter_currency = models.CharField(max_length=10, choices=[
        ('USD', 'usd'),
        ('ZWG', 'zwg')
    ], default='USD')
    fiscal_counter_tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    fiscal_counter_tax_id = models.IntegerField(default=3)
    fiscal_counter_money_type = models.CharField(max_length=20, choices=MONEY_TYPE_CHOICES, default=CASH, null=True)
    fiscal_counter_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.fiscal_counter_type} - {self.fiscal_counter_currency} - {self.fiscal_counter_value}"



class NotificationsSettings(models.Model):
    # products settings
    product_creation = models.BooleanField(default=True)
    product_update = models.BooleanField(default=True)
    product_deletion = models.BooleanField(default=True)
    invoice_on_sale = models.BooleanField(default=True)
    low_stock = models.BooleanField(default=False)

    service_creation = models.BooleanField(default=True)
    service_update = models.BooleanField(default=True)
    service_deletion = models.BooleanField(default=True)

    # transfers settings
    transfer_creation = models.BooleanField(default=True)
    transfer_approval = models.BooleanField(default=True)
    transfer_receiving = models.BooleanField(default=True)

    # finance settings
    expense_creation = models.BooleanField(default=True)
    expense_approval = models.BooleanField(default=True)
    recurring_invoices = models.BooleanField(default=True)
    money_transfer = models.BooleanField(default=True)
    cash_withdrawal = models.BooleanField(default=True)
    cash_deposits = models.BooleanField(default=True)

    # users settings
    user_creation = models.BooleanField(default=True)
    user_approval = models.BooleanField(default=True)
    user_deletion = models.BooleanField(default=True)
    user_login = models.BooleanField(default=True)

    user = models.ForeignKey("users.User", on_delete=models.CASCADE)

    def __str__(self):
        return self.user.email

# system printer settings
class Printer(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    printer_type = models.CharField(max_length=255, choices=(('bluetooth', 'Bluetooth'), ('system', 'System')))
    port = models.CharField(max_length=255)
    driver_name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    pc_identifier = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255, blank=True, null=True)
    mac_address = models.CharField(max_length=255, blank=True, null=True)
    system_uuid = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class TaxSettings(models.Model):
    name = models.CharField(max_length=55)
    selected = models.BooleanField(default=False)

    def __str__(self):
        return self.name
