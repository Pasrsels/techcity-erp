from pickle import FALSE
import uuid
# from apps.inventory.models import Supplier
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.company.models import Branch
from apps.users.models import User
from django.db.models import Sum
from django.utils.timezone import localdate
from django.db import transaction
import os

today = localdate()


class PaymentMethod(models.Model):
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name
    
class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)  
    name = models.CharField(max_length=50)  
    symbol = models.CharField(max_length=5)  
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    default = models.BooleanField(default=False)
   
    def __str__(self):
        return f"{self.name}"

# class Creditors(models.Model):
#     supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True)
#     amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

#     def __str__(self):
#         return f'{self.supplier.name}: {self.amount}'

class ChartOfAccounts(models.Model):
    class AccountType(models.TextChoices):
        ASSET = 'Asset', _('Asset')
        LIABILITY = 'Liability', _('Liability')
        EQUITY = 'Equity', _('Equity')
        REVENUE = 'Revenue', _('Revenue')
        EXPENSE = 'Expense', _('Expense')

    class NormalBalance(models.TextChoices):
        DEBIT = 'Debit', _('Debit')
        CREDIT = 'Credit', _('Credit')
        
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=AccountType.choices)
    normal_balance = models.CharField(max_length=6, choices=NormalBalance.choices)
    
    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=100)
    id_number = models.CharField(max_length=100)
    date = models.DateField(auto_now_add=True)
    branch = models.ForeignKey('company.branch', on_delete=models.PROTECT)              
    
    def __str__(self):
        return self.name

class CustomerAccount(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.customer.name})'
    
class CustomerAccountBalances(models.Model):
    # Customer has two accounts i.e. USD and ZIG account
    account = models.ForeignKey(CustomerAccount, on_delete=models.CASCADE, related_name='balances')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)  
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)   

    class Meta:
        unique_together = ('account', 'currency') 

    def __str__(self):
        return f'{self.account} - {self.currency}: {self.balance}'
    
class CustomerDeposits(models.Model):
    customer_account = models.ForeignKey("finance.CustomerAccountBalances", on_delete=models.CASCADE, related_name="customer_deposits")
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0) 
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)  
    payment_method = models.CharField(max_length=15, choices=[
        ('cash', 'cash'),
        ('bank', 'bank'),
        ('ecocash', 'ecocash')
    ]
    , default="cash")
    reason = models.CharField(max_length=255, null=False, blank=False)
    payment_reference = models.CharField(max_length=255, default="")
    cashier = models.ForeignKey("users.User", on_delete=models.DO_NOTHING, related_name="cashier")
    date_created = models.DateField(auto_now_add=True)
    branch = models.ForeignKey('company.branch', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self) -> str:
        return f'{self.customer_account.account}'


class Transaction(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=200, blank=True)
    account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reference_number = models.CharField(max_length=50, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey('company.branch', on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.reference_number:  
            while True:  
                ref_number = uuid.uuid4().hex[:10].upper()  
                if not Transaction.objects.filter(reference_number=ref_number).exists():  
                    self.reference_number = ref_number
                    break  
        super(Transaction, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} - {self.description} - Ref: {self.reference_number}"

class VATRate(models.Model):
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=50, blank=True)
    status = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.rate}% - {self.description}"

class VATTransaction(models.Model):
    class VATType(models.TextChoices):             
        INPUT = 'Input', _('Input')
        OUTPUT = 'Output', _('Output')

    invoice = models.OneToOneField('finance.invoice', on_delete=models.CASCADE, null=True)
    purchase_order = models.OneToOneField('inventory.Purchaseorder', on_delete=models.CASCADE, null=True)
    vat_type = models.CharField(max_length=6, choices=VATType.choices)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"VAT Transaction for {self.invoice}"

class Account(models.Model):

    class AccountType(models.TextChoices):
        CASH = 'CA', 'Cash'
        BANK = 'BA', 'Bank'
        ECOCASH = 'EC', 'Ecocash'
        
    name = models.CharField(max_length=50)
    type = models.CharField(
        max_length=2,
        choices=AccountType.choices,
        default=AccountType.CASH
    )
    
    def __str__(self):
        return f'{self.name} ({self.type})'
    
class AccountBalance(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='balances')
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    branch = models.ForeignKey('company.branch', on_delete=models.CASCADE)

    #class Meta:
    #    unique_together = ('account', 'currency')

    def __str__(self):
        return f'{self.account.name} ({self.account.type}):{self.currency}{self.balance}'


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        PURCHASE = 'Purchase', _('Purchase')
        SALE = 'Sale', _('Sale')
        ADJUSTMENT = 'Adjustment', _('Adjustment')

    item = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    invoice = models.ForeignKey('finance.invoice', on_delete=models.PROTECT)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    payment_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_stock_transactions')
    payment_object_id = models.PositiveIntegerField(null=True, blank=True)
    payment_object = GenericForeignKey('payment_content_type', 'payment_object_id') 

    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()


def expense_receipt_upload_path(instance, filename):
    """Generates a unique file path for uploaded receipts."""
    return os.path.join('receipts/', f"expense_{instance.id}_{filename}")

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )

    def __str__(self):
        return f"{self.parent.name} → {self.name}" if self.parent else self.name

class Expense(models.Model):
    issue_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=15, choices=[
        ('cash', 'cash'),
        ('bank', 'bank'),
        ('ecocash', 'ecocash')
    ])
    currency = models.ForeignKey('Currency', on_delete=models.CASCADE)
    category = models.ForeignKey('ExpenseCategory', on_delete=models.PROTECT)
    description = models.CharField(max_length=200)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    branch = models.ForeignKey('company.Branch', on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    purchase_order = models.ForeignKey("inventory.PurchaseOrder", on_delete=models.CASCADE, null=True, blank=True)

    receipt = models.FileField(upload_to=expense_receipt_upload_path, null=True, blank=True)

    is_recurring = models.BooleanField(default=False)
    recurrence_value = models.PositiveIntegerField(null=True, blank=True, help_text="Repeat every X units")
    recurrence_unit = models.CharField(
        max_length=10,
        choices=[
            ('day', 'Day(s)'),
            ('week', 'Week(s)'),
            ('month', 'Month(s)'),
            ('year', 'Year(s)')
        ],
        null=True,
        blank=True
    )
    cash_up_status = models.BooleanField(default=False, null=True)

    def __str__(self):
        return f"{self.issue_date} - {self.category} - {self.description} - ${self.amount}"

    
class Sale(models.Model):
    """
    Represents a sale transaction.
    """
    date = models.DateField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction = models.ForeignKey('finance.Invoice', on_delete=models.PROTECT)
    

    def __str__(self):
        return f"Sale to {self.transaction.customer} on {self.date} ({self.total_amount})"

class Invoice(models.Model):
    """
    Model representing an invoice.
    """
    class PaymentStatus(models.TextChoices):
        DRAFT = 'Draft', _('Draft')
        PENDING = 'Pending', _('Pending')
        PARTIAL = 'Partial', _('Partial')
        PAID = 'Paid', _('Paid')
        OVERDUE = 'Overdue', _('Overdue')

    invoice_number = models.CharField(max_length=50, unique=True, null=True)       
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)  
    issue_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0) 
    vat = models.DecimalField(max_digits=15, decimal_places=2, default=0)     
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)  
    amount_due = models.DecimalField(max_digits=15, decimal_places=2, default=0) 
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True) 
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True)
    branch = models.ForeignKey('company.branch', on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT, null=True)
    reocurring = models.BooleanField(default=False)
    subtotal =  models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    note = models.TextField(null=True)
    cancelled = models.BooleanField(default=False)
    products_purchased = models.TextField()
    invoice_return = models.BooleanField(default=False)
    payment_terms = models.CharField(choices=(
        ('cash', 'cash'),
        ('layby', 'layby'),
        ('installment', 'installment')
    ))
    hold_status = models.BooleanField(default=False)
    amount_received = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    receiptServerSignature = models.TextField(null=True, blank=True)
    receipt_hash = models.TextField(null=True, blank=True) 
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    signature_data = models.CharField(max_length=50, null=True)
    code = models.CharField(max_length=50, null=True)
    fiscal_day = models.CharField(max_length=50, null=True)
    cash_up_status = models.BooleanField(default=False, null=True)
    
    def generate_invoice_number(branch):
        last_invoice = Invoice.objects.filter(branch__name=branch).order_by('-id').first()
        if last_invoice:
            return f"INV{branch}-{int(last_invoice.invoice_number ) + 1}"
        else:
            new_invoice_number = 1
            return f"INV{branch}-{new_invoice_number}"  

    def __str__(self):
        return f"Invoice #{self.invoice_number} - {self.customer.name}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='invoice_items')
    item = models.ForeignKey('inventory.Inventory', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    vat_rate = models.ForeignKey(VATRate, on_delete=models.PROTECT)
    vat_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)  
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    cash_up_status = models.BooleanField(default=False, null=True)
    
    @property
    def subtotal(self):
        return Decimal(self.unit_price )* int(self.quantity)

    @property
    def total(self):
        return self.subtotal

    def save(self, *args, **kwargs):
        # Calculate and set the VAT amount automatically
        vat_rate_percentage = self.vat_rate.rate
        vat_rate = Decimal(vat_rate_percentage) / Decimal('100')  
        self.vat_amount = self.subtotal * vat_rate
        self.total_amount = self.total
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.item.description} for Invoice #{self.invoice.invoice_number}"
    

class layby(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='layby')
    branch = models.ForeignKey('company.branch', on_delete=models.CASCADE)
    fully_paid = models.BooleanField(default=False)

    def check_payment_status(self):
        """
            Checks if all related layby dates are paid and updates the invoice status.
        """
        related_dates = laybyDates.objects.filter(layby=self)
        
        unpaid_dates = related_dates.filter(is_paid=False)
        
        if not unpaid_dates.exists() and related_dates.exists():
            with transaction.atomic():
                self.invoice.payment_status = Invoice.PaymentStatus.PAID
                self.invoice.amount_paid = self.invoice.amount
                self.invoice.amount_due = Decimal('0.00')
                self.invoice.save()
                
                Payment.objects.create(
                    invoice=self.invoice,
                    amount_paid=self.invoice.amount,
                    payment_method=Payment.objects.filter(invoice=self.invoice).first().payment_method 
                        if Payment.objects.filter(invoice=self.invoice).exists() else 'cash',
                    amount_due=Decimal('0.00'),
                    user=self.invoice.user
                )
                s
                self.fully_paid = True
                self.save()
                # Log the activity
                # ActivityLog.objects.create(
                #     branch=self.invoice.branch,
                #     user=self.invoice.user,
                #     action='Layby Complete',
                #     invoice=self.invoice
                # )
                
                return True
        
        return False

    def __str__(self):
        return f'{self.invoice} : {self.branch}'

class laybyDates(models.Model):
    layby = models.ForeignKey(layby, on_delete=models.CASCADE)
    amount_to_be_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    due_date = models.DateField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('ecocash', 'EcoCash'),
    ], null=True)

    def __str__(self):
        return f'{self.invoice}: {self.due_date}'

class Paylater(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='paylater')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    due_date = models.DateField()   
    paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('ecocash', 'EcoCash'),
    ], null=True)

    def __str__(self):
        return f'{self.invoice}: {self.due_date}'
    
class MonthlyInstallment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    due_date = models.DateField()  
    paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('ecocash', 'EcoCash'),
    ], null=True)

    def __str__(self):
        return f'{self.invoice}: {self.due_date}'
    
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True) 
    # balance =  models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('credit card', 'Credit Card'),
        ('pay later', 'pay later'),
        ('Ecocash','Ecocash')
    ])
    user = models.ForeignKey('users.user', on_delete=models.PROTECT)
    
    def __str__(self):
        return f'{self.invoice.invoice_number} {self.amount_paid}'


class Cashbook(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    issue_date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255)
    debit = models.BooleanField(default=False)
    credit = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    branch = models.ForeignKey('company.branch', on_delete=models.CASCADE)
    manager = models.BooleanField(default=False)
    accountant = models.BooleanField(default=False, null=True)
    director = models.BooleanField(default=False, null=True)
    cancelled = models.BooleanField(default=False, null=True)
    note = models.TextField(default='', null=True)

    def __str__(self):
        return f'{self.issue_date}'

class CashBookNote(models.Model):
    entry = models.ForeignKey(Cashbook, related_name="notes", on_delete=models.CASCADE)
    user = models.ForeignKey('users.user', on_delete=models.CASCADE)
    note = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.user.username} on {self.timestamp}"
    

class CashTransfers(models.Model):
    class TransferMethod(models.TextChoices):
        BANK = ('Bank'), _('Bank')
        CASH = ('Cash'), _('Cash')
        ECOCASH =('Ecocash'), _('Ecocash')
   
    date = models.DateField(auto_now_add=True)    
    from_branch = models.ForeignKey('company.Branch', on_delete=models.CASCADE, related_name='kwarikuenda')
    to = models.ForeignKey('company.Branch', on_delete=models.CASCADE, related_name='to')
    branch = models.ForeignKey('company.branch', on_delete=models.CASCADE, related_name='parent')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    reason = models.CharField(max_length=255)
    transfer_method = models.CharField(max_length=10, choices=TransferMethod.choices, default=TransferMethod.CASH)
    received_status = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.to}: {self.amount}'
    
class FinanceNotifications(models.Model):
    expense = models.OneToOneField(Expense, on_delete=models.CASCADE, null=True)
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, null=True)
    transfer = models.OneToOneField(CashTransfers, on_delete=models.CASCADE, null=True)
    notification = models.CharField(max_length=255)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=20, choices=[
        ('Expense', 'Expense'),
        ('Invoice', 'Invoice'),
        ('Transfer', 'Transfer')
    ])

    def __str__(self):
        return self.notification
    
class Qoutation(models.Model):
    qoute_reference = models.CharField(max_length=255)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True) 
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.BooleanField(default=False)
    date = models.DateField(auto_now_add=True)
    branch = models.ForeignKey('company.branch', on_delete=models.CASCADE)
    products = models.CharField(max_length=255)
    
    def generate_qoute_number(branch):
        last_qoute = Qoutation.objects.filter(branch__name=branch).order_by('-id').first()
        if last_qoute:
            if str(last_qoute.qoute_reference.split('-')[0])[-1] == branch[0]:
                last_qoute_number = int(last_qoute.qoute_reference.split('-')[1]) 
                new_qoute_number = last_qoute_number + 1   
            else:
                new_qoute_number = 1
            return f"Q{branch[:1]}-{new_qoute_number :04d}"  
        else:
            new_qoute_number  = 1
            return f"Q{branch[:1]}-{new_qoute_number :04d}"  
    
    def __str__(self):
        return f'{self.qoute_reference} {self.customer.name}'
    
class QoutationItems(models.Model):
    qoute = models.ForeignKey(Qoutation, on_delete=models.CASCADE, related_name='qoute_items')
    product = models.ForeignKey('inventory.Inventory', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        return f'{self.qoute.qoute_reference} {self.product.product.name}'

class CashWithdraw(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    password = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.BooleanField(default=False)
    reason = models.CharField(max_length=10)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.date} {self.user.username} {self.amount}'
    
class PurchaseOrderAccount(models.Model):
    purchase_order = models.ForeignKey('inventory.PurchaseOrder', on_delete=models.CASCADE, related_name='purchase_order')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    expensed = models.BooleanField(default=False)
    
    def __str__(self) -> str:
        return self.purchase_order.order_number

class PurchasesAccount(models.Model):
    purchase_order = models.ForeignKey('inventory.PurchaseOrder', on_delete=models.CASCADE, related_name='purchases')
    debit = models.BooleanField(default=False)
    credit = models.BooleanField(default=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)

class COGS(models.Model):
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 

class COGSItems(models.Model):
    cogs = models.ForeignKey(COGS, on_delete=models.CASCADE, null=True)
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey('inventory.Inventory', on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)


class SalesReturns(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey("users.user", on_delete=models.CASCADE)
    
    def __str__(self) -> str:
        return self.invoice

class CashWithdrawals(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=False)
    description = models.CharField(max_length=255)
    user = models.ForeignKey("users.user", on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE) 

class CashDeposit(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    timestamp = models.DateTimeField(auto_now=False, auto_now_add=False)
    description = models.CharField(max_length=255)
    user = models.ForeignKey("users.user", on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE) 

    def __str__(self) -> str:
        return self.account.name 
    
class AccountTransaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    cash_withdrawal = models.ForeignKey(CashWithdraw, on_delete=models.CASCADE, null=True)
    cash_deposit = models.ForeignKey(CashDeposit, on_delete=models.CASCADE, null=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    sales_returns = models.ForeignKey(SalesReturns, on_delete=models.CASCADE, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class ExpenseSubCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Expenses Sub Categories"
    
    def __str__(self):
        return self.name

class IncomeSubCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Income Sub Categories"
    
    def __str__(self):
        return self.name

class MainIncomeCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sub_income_category = models.ForeignKey(IncomeSubCategory, on_delete=models.CASCADE, null=True)
    
    class Meta:
        verbose_name_plural = "Income Main Categories"
    
    def __str__(self):
        return self.name

class MainExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sub_expense = models.ForeignKey(ExpenseSubCategory, on_delete=models.CASCADE, null=True)
    
    class Meta:
        verbose_name_plural = "Expenses Main Categories"
    
    def __str__(self):
        return self.name

class CashFlowName(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        verbose_name_plural = "cashflow_name"
    
    def __str__(self):
        return self.name

class Cashflow(models.Model):
    name = models.ForeignKey(CashFlowName, on_delete=models.CASCADE, null=True)
    date = models.DateField()
    income_category = models.ForeignKey(MainIncomeCategory, on_delete=models.CASCADE, null=True)
    expense_category = models.ForeignKey(MainExpenseCategory, on_delete=models.CASCADE, null=True, blank=True)
    income = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    expense = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    # sales = models.ManyToManyField(Sale, blank=True)
    status = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_cashflows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cash_up = models.ForeignKey('finance.CashUp', on_delete=models.CASCADE, null=True)

    def save(self, *args, **kwargs):
        # Calculate total (income - expense)
        self.total = self.income - self.expense
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.branch} - {self.date} - {self.total}"

class CashUp(models.Model):
    date = models.DateField()
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2)
    received_amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    sales = models.ManyToManyField(Invoice, related_name='cashup_sales')
    expenses = models.ManyToManyField(Expense, related_name='cashup_expenses')
    status = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_cashups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sales_status = models.BooleanField(default=False)
    expenses_status = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Calculate balance (received_amount - expected_cash)
        self.balance = self.received_amount - self.expected_cash
        super().save(*args, **kwargs)
    
    def get_total_sales(self):
        return self.sales.filter(invoice__issue_date=today) \
            .aggregate(total=Sum('total_amount'))['total'] or 0
    
    def get_total_expenses(self):
        return self.expenses.filter(issue_date=today).aggregate(total=models.Sum('amount'))['total'] or 0
    
    def get_net_cash(self):
        return self.get_total_sales() - self.get_total_expenses()

    def __str__(self):
        return f"{self.branch} - {self.date} - Balance: {self.balance}"

    class Meta:
        verbose_name_plural = "Cash Ups"


class UserAccount(models.Model):
    user = models.ForeignKey(User, related_name='accounts', on_delete=models.CASCADE)
    account_type = models.CharField(max_length=50)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_credits = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_debits = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_transaction_date = models.DateTimeField(null=True, blank=True)

class UserTransaction(models.Model):
    account = models.ForeignKey(UserAccount, related_name='transactions', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10) 
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    debit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    received_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_transactions', null=True)

class IncomeCategory(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='incomes'
    )

    def __str__(self):
        return f"{self.parent.name} → {self.name}" if self.parent else self.name


class Income(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey('Currency', on_delete=models.CASCADE)
    category = models.ForeignKey('IncomeCategory', on_delete=models.PROTECT)
    note = models.CharField(max_length=200)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    branch = models.ForeignKey('company.Branch', on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    sale = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True)
    expenses = models.ForeignKey(Expense, on_delete=models.CASCADE, null=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_value = models.PositiveIntegerField(null=True, blank=True)
    recurrence_unit = models.CharField(
        max_length=10,
        choices=[
            ('day', 'Day(s)'),
            ('week', 'Week(s)'),
            ('month', 'Month(s)'),
            ('year', 'Year(s)')
        ],
        null=True,
        blank=True
    )    
    def __str__(self):
        return f"{self.created_at} - {self.category} - {self.note} - ${self.amount}"

class FinanceLog(models.Model):
    TRANSACTION_TYPES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_type_display()} | {self.category} | ${self.amount}"
