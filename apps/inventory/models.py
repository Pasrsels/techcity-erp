from email.policy import default
import random, string, uuid
from django.db import models
from apps.company.models import Branch
from django.db.models import Sum
from django.utils import timezone
from django.db.models import F
from loguru import logger
from apps.finance.models import Currency


TAX_CHOICES = [
    ('exempted', 'Exempted'),
    ('standard', 'Standard'),
    ('zero rated', 'Zero Rated')
]

class BatchCode(models.Model):
    code = models.CharField(max_length=255)

    class meta:
        app_label ='batch_code'

    def __str__(self) -> str:
        return self.code
    

class ProductCategory(models.Model):
    """Model for product categories."""

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Supplier(models.Model):
    """Model for suppliers."""
    name = models.CharField(max_length=102)
    contact_person = models.CharField(max_length=254)
    phone = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    address = models.CharField(max_length=255, null= True)
    delete = models.BooleanField(default= False)

    def __str__(self):
        return self.name

class SupplierAccount(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)  
    balance = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    date = models.DateField(null= True)

    class Meta:
        unique_together = ('currency', 'supplier') 

    def __str__(self):
        return f'{self.supplier.name} balance -> {self.balance}'

class SupplierAccountsPayments(models.Model):
    account = models.ForeignKey(SupplierAccount, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=15, choices=[
        ('cash', 'cash'),
        ('bank', 'bank'),
        ('Ecocash', 'ecocash')
    ])
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE) 
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.account.supplier.name} amount paid {self.amount}'


class Product(models.Model):
    """Model for products."""
    
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    quantity = models.IntegerField(default=0, null=True)
    min_stock_level = models.IntegerField(default=0, null=True)
    description = models.TextField(max_length=255, default='')
    end_of_day = models.BooleanField(default=False, null=True)
    service = models.BooleanField(default=False, null=True)
    dealer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, default=0)
    suppliers = models.ManyToManyField('Supplier', related_name="products")
    image = models.ImageField(upload_to='product_images/', null=True)

    def __str__(self):
        return self.name 

class SerialNumber(models.Model):
    serial_number = models.CharField(max_length=255, unique=True)
    status = models.BooleanField(default=True)  # True for active/available, False for used/inactive
    added_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.serial_number

class Inventory(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True)
    cost =  models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    dealer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    quantity = models.IntegerField(null=True)
    status = models.BooleanField(default=True, null=True)
    stock_level_threshold = models.IntegerField(default=5, null=True)
    reorder = models.BooleanField(default=False, null=True)
    alert_notification = models.BooleanField(default=False, null=True, blank=True)
    batch = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey('ProductCategory', on_delete=models.SET_NULL, null=True)
    tax_type = models.CharField(max_length=50, choices=TAX_CHOICES, null=True)
    batch = models.TextField(blank=True, default='')
    suppliers = models.ManyToManyField('Supplier', related_name="products_suppliers")
    description = models.TextField(max_length=255, default='')
    end_of_day = models.BooleanField(default=False, null=True)
    service = models.BooleanField(default=False, null=True)
    image = models.ImageField(upload_to='product_images/', default='placeholder.png', null=True)
    disable = models.BooleanField(default=False)
    serial_numbers = models.ManyToManyField('SerialNumber', related_name='inventories') 

    class Meta:
        unique_together = ('id', 'branch') 

    def update_stock(self, added_quantity):
        self.quantity += added_quantity
        self.save()
    
    def __str__(self):
        return f'{self.branch.name} : ({self.name}) quantity ({self.quantity})'

class Accessory(models.Model):
    main_product = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='main_product')
    accessory_product = models.ManyToManyField(Inventory)
    quantity = models.IntegerField()

    def __str__(self):
        return self.main_product.name

class PurchaseOrder(models.Model):
    """Model for purchase orders."""

    status_choices = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('canceled', 'Canceled')
    ]

    order_number = models.CharField(max_length=100, unique=True)
    order_date = models.DateTimeField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=status_choices, default='received')
    notes = models.CharField(max_length=255 ,null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    other_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    is_partial = models.BooleanField(default=False)  
    received = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=15, choices=[
        ('cash', 'cash'),
        ('bank', 'bank'),
        ('ecocash', 'ecocash')
    ]
    , default="cash")
    batch = models.CharField(max_length=20, null=True)
    hold = models.BooleanField(null=True, default=True)

    def generate_order_number():
        return f'PO-{uuid.uuid4().hex[:10].upper()}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super(PurchaseOrder, self).save(*args, **kwargs)

    def check_partial_status(self):
        partial_items = self.items.filter(received_quantity__lt=F('quantity'))
        self.is_partial = partial_items.exists()
        self.save()

    def __str__(self):
        return f"PO {self.order_number}"
    

class PurchaseOrderItem(models.Model):

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Inventory, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    actual_unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.IntegerField(default=0) 
    received = models.BooleanField(default=False, null=True)
    expected_profit = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    dealer_expected_profit = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True, default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)

    def receive_items(self, quantity):
    
        self.received_quantity += quantity
        if self.received_quantity >= self.quantity:
            self.received = True
        self.save()
        self.purchase_order.check_partial_status()  

    def check_received(self):
        """
        Checks if all related items in the purchase order with the same order_number are received and updates the purchase order's "received" flag.
        """
        order_number = self.purchase_order.order_number
        purchase_order_items = PurchaseOrderItem.objects.filter(purchase_order__order_number=order_number)

        all_received = True
        for item in purchase_order_items:
            if not item.received:
                all_received = False
            break

        logger.info(f'Received status ={all_received}')

        purchase_order = PurchaseOrder.objects.get(order_number=order_number)
        purchase_order.received = all_received
        purchase_order.save()

    # def __str__(self):
    #     return f"{self.product.name} x {self.quantity}"
    

class costAllocationPurchaseOrder(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    allocated = models.DecimalField(max_digits=10, decimal_places=2)
    allocationRate = models.DecimalField(max_digits=10, decimal_places=2)
    expense_cost = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    product = models.CharField(max_length=255)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    total_buying = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f'{self.purchase_order}: {self.product}'
    

class ProductDetail(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE) 


class otherExpenses(models.Model):

    """additional expenses for the purchase order"""

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f'{self.purchase_order} : {self.name} -> {self.amount}'
    
    
class Transfer(models.Model):
    transfer_ref = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='user_branch')
    transfer_to = models.ManyToManyField(Branch)
    description =  models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    time = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    quantity =  models.IntegerField(default=0, null=True)
    total_quantity_track = models.IntegerField(default=0, null=True)
    defective_status = models.BooleanField(default=False)
    delete = models.BooleanField(default=False, null=True)
    receive_status = models.BooleanField(default=False, null=True)
    hold = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['branch']),
            models.Index(fields=['transfer_ref']),
            models.Index(fields=['date']),
            models.Index(fields=['delete']),
            models.Index(fields=['hold']),
        ]
        

    @classmethod
    def generate_transfer_ref(self, branch, branches):

        """revisit on 03d"""
        
        formatted_branches = ', '.join([f"T{b[0].upper()}" for b in branches])

        last_transfer = Transfer.objects.filter(branch__name=branch, delete=False).order_by('-id').first()
        logger.info(f'last transfer reference: {last_transfer}')
        if last_transfer:
            last_reference = int(last_transfer.transfer_ref.split('#')[-1]) if '#' in last_transfer.transfer_ref else 1
            new_reference = f'{branch} - {formatted_branches} #{last_reference + 1:03d}'
            return new_reference
        else:
            return f'{branch}: {formatted_branches} #001'


    def __str__(self):
        return self.transfer_ref
    

class TransferItems(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    date_received = models.DateTimeField(auto_now_add=True)
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
    from_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='destination')
    to_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='source')
    product = models.ForeignKey(Inventory, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    over_less_quantity = models.IntegerField(null=True, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    dealer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    received = models.BooleanField(default=False)
    declined = models.BooleanField(default=False) 
    over_less = models.BooleanField(default=False)
    action_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='over_less_admin')
    quantity_track = models.IntegerField(default=0, null=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    over_less_description = models.CharField(max_length=255, null=True, blank=True)
    received_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    description = models.TextField(null=True)
    received_quantity = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    defect_quantity = models.IntegerField(default=0, null=True)
    received_back_quantity = models.IntegerField(default=0, null=True)
    done = models.BooleanField(default=False, null=True)

    # def __str__(self):
    #     return f'{self.product.name} to {self.to_branch}'
    
class Holdtransfer(models.Model):
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    from_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='hold_destination')
    to_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='hold_source')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(null=True)
    dealer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # def __str__(self):
    #     return f'{self.product.name} to {self.to_branch}'

class DefectiveProduct(models.Model):
    product = models.ForeignKey(Inventory, on_delete=models.SET_NULL, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    date = models.DateField(auto_now_add=True)
    branch_loss = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='loss')
    reason = models.TextField()
    status = models.CharField(max_length=50, choices=[
        ('lost in transit','Lost in transit'),
        ('stolen', 'stolen'),
        ('damaged', 'Damage'),
    ])
    
    def __str__(self):
        return self.product.name

class ActivityLog(models.Model):
    """Model for activity logs."""

    ACTION_CHOICES = [
        ('stock in', 'stock in'),
        ('Stock update', 'Stock update'),
        ('stock adjustment', 'stock adjustment'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('edit', 'Edit'),
        ('transfer in', 'transfer in'),
        ('transfer out', 'transfer out'),
        ('returns', 'returns'),
        ('sale return', 'sale return'),
        ('sale', 'Sale'), 
        ('declined', 'Declined'),
        ('write off', 'write off'),
        ('defective', 'defective'),
        ('activated', 'activated'),
        ('deactivated', 'deactivated'),
        ('removed', 'removed'),
        ('purchase edit +', 'purchase edit +'),
        ('purchase edit -', 'purchase edit -'),
        ('transfer cancel', 'transfer cancel')
    ]
    
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE) 
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    quantity = models.IntegerField()
    total_quantity = models.IntegerField()
    dealer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    system_quantity = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, null=True)
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL)
    invoice = models.ForeignKey('finance.invoice', null=True, blank=True, on_delete=models.SET_NULL) 
    product_transfer = models.ForeignKey(TransferItems, null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        get_latest_by = 'timestamp'

    def __str__(self):
        return f"{self.user} ({self.timestamp})"
    
class StockNotifications(models.Model):
    inventory = models.ForeignKey(Inventory, null=True, blank=True, on_delete=models.SET_NULL)
    transfer = models.ForeignKey(Transfer, null=True, blank=True, on_delete=models.SET_NULL)
    notification = models.CharField(max_length=255)
    status = models.BooleanField(default=False)
    type = models.CharField(max_length=30, choices=[
        ('stock level', 'Stock level'),
        ('stock take', 'stock take'),
        ('stock transfer', 'stock transfer')
    ])
    quantity = models.IntegerField(blank=True, null=True, default=0)
    
    def __str__(self):
        return f'{self.inventory}: {self.notification}'
    
class ReorderList(models.Model):
    date = models.DateField(auto_now_add=True)
    product = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    branch =  models.ForeignKey(Branch, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0 )
    
    def __str__(self):
        return f'{self.product.product.name}'

class ServiceCategory(models.Model):
    """Model for service categories."""
   
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Service(models.Model):
    
    tax_choices = [
        ('exempted', 'Exempted'),
        ('standard', 'Standard'),
        ('zero rated', 'Zero Rated')
    ]
    
    name = models.CharField(max_length=255)
    cost =  models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_type = models.CharField(max_length=50, choices=tax_choices)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True)
    # branch = models.ForeignKey(branch, on_delete=models.CASCADE)
    description = models.TextField(max_length=255, default= '')
    
    def __str__(self):
        return self.name
    
class reorderSettings(models.Model):
    supplier = models.CharField(max_length=255)
    quantity_suggestion = models.BooleanField(default=False)
    number_of_days_from = models.FloatField(null=True)
    number_of_days_to = models.FloatField(null=True)
    order_enough_stock = models.BooleanField(default=False)
    date_created = models.DateField(auto_now_add=True)


class StockTake(models.Model):
    date = models.DateField()
    s_t_number = models.CharField(max_length=255)
    result = models.CharField(max_length=255, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)

    def stocktake_number(self, branch):
        prv_stock_take = StockTake.objects.filter(branch__name=branch).order_by('-id').first()
        if prv_stock_take:
            last_stocktake_number = int(prv_stock_take.s_t_number)
            new_stocktake_number = last_stocktake_number + 1
        else:
            new_stocktake_number = 1

        return new_stocktake_number
    
    def __str__(self):
        return f'{self.date}: {self.s_t_number}'
        
class StocktakeItem(models.Model):
    stocktake = models.ForeignKey(StockTake, on_delete=models.CASCADE, null=True)
    product = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    quantity_difference = models.IntegerField()

    def __str__(self):
        return self.product.name


# Inventory loss models

class WriteOff(models.Model):
    inventory_item = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='write_offs')
    quantity = models.PositiveIntegerField()
    reason = models.TextField()
    created_by = models.ForeignKey('users.user', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Write-off: {self.inventory_item.name} ({self.quantity})"

class DefectiveItem(models.Model):
    inventory_item = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='defective_items')
    quantity = models.PositiveIntegerField()
    defect_description = models.TextField()
    action_taken = models.CharField(max_length=255, choices=[
        ('return_to_supplier', 'Return to Supplier'),
        ('write_off', 'Write Off'),
        ('repair', 'Repair'),
    ], default='write_off')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Defective: {self.inventory_item.name} ({self.quantity})"
    
class InventoryShrinkage(models.Model):
    inventory_item = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='shrinkages')
    quantity = models.PositiveIntegerField()
    date_discovered = models.DateTimeField()
    reason = models.CharField(max_length=255, choices=[
        ('theft', 'Theft'),
        ('damage', 'Damage'),
        ('miscount', 'Miscount'),
        ('other', 'Other'),
    ])
    additional_details = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Shrinkage: {self.inventory_item.name} ({self.quantity})"


