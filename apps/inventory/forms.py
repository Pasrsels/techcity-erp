from django import forms
from . models import (
    Product,
    ProductCategory, 
    Inventory, Transfer, 
    DefectiveProduct, 
    Service, 
    Supplier, 
    PurchaseOrder,
    BatchCode, 
    reorderSettings,
    StockTake,
    DefectiveItem,
    InventoryShrinkage,
    WriteOff
)
from datetime import date
from loguru import logger

class BatchForm(forms.ModelForm):
    class Meta:
        model = BatchCode
        fields = '__all__'

class AddProductForm(forms.ModelForm):
    class Meta:
        model = Inventory
        exclude = ['supplier']

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        exclude = ['branch', 'name']
        
class addCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = '__all__'
        
class addTransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        exclude = ['transfer_ref', 'branch', 'user', 'quantity', 'defective_status', 'total_quantity_track']
        

class DefectiveForm(forms.ModelForm):
    class Meta:
        model = DefectiveProduct
        fields = ['id', 'quantity', 'reason', 'status', 'branch_loss']

        
class RestockForm(forms.ModelForm):
    class Meta:
        model = DefectiveProduct
        fields = ['quantity']
        
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['name', 'price']

class AddSupplierForm(forms.ModelForm):   
    class Meta :
        model = Supplier
        fields = '__all__'

#testing supplier edit form
class EditSupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'

class CreateOrderForm(forms.ModelForm):
    class Meta:
        model =  PurchaseOrder
        exclude = ['order_number', 'branch', 'payment_method']
      

class noteStatusForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['batch', 'status', 'delivery_date', 'payment_method', 'notes']
        
        widgets = {
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(noteStatusForm, self).__init__(*args, **kwargs)
        
        if not self.initial.get('delivery_date'):
            self.initial['delivery_date'] = date.today()

        # set the batch incrementing from the previous 
        latest_order = PurchaseOrder.objects.filter().order_by('-order_date').first()
    
        if latest_order and latest_order.batch:
            try:
                # Ensure the batch follows the expected format "Batch X"
                batch_parts = latest_order.batch.split(' ')
                if len(batch_parts) == 2 and batch_parts[1].isdigit():
                    batch_number = int(batch_parts[1]) + 1
                else:
                    batch_number = 1  
            except (IndexError, ValueError):
                batch_number = 1  
        else:
            batch_number = 1  
        self.initial['batch'] = f'Batch {batch_number}'


class PurchaseOrderStatusForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['status']

class ReorderSettingsForm(forms.ModelForm):
    class Meta:
        model = reorderSettings
        fields = ['supplier', 'quantity_suggestion', 'number_of_days_from', 'number_of_days_to', 'order_enough_stock']
       

class StockTakeForm(forms.ModelForm):
    class Meta:
        model = StockTake
        exclude = ['branch', 's_t_number']


class AddDefectiveForm(forms.ModelForm):
    class Meta:
        model = DefectiveItem
        fields = ['inventory_item', 'quantity', 'action_taken', 'defect_description']
        widgets = {
            'inventory_item': forms.Select(attrs={'class': 'form-control product'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(AddDefectiveForm, self).__init__(*args, **kwargs)
        if self.request:
            self.fields['inventory_item'].queryset = Inventory.objects.filter(branch=self.request.user.branch)

class AddWriteOffForm(forms.ModelForm):
    class Meta:
        model = WriteOff
        fields = ['inventory_item', 'quantity', 'reason']
        widgets = {
            'inventory_item': forms.Select(attrs={'class': 'form-control product'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(AddWriteOffForm, self).__init__(*args, **kwargs)
        if self.request:
            self.fields['inventory_item'].queryset = Inventory.objects.filter(branch=self.request.user.branch)


class AddShrinkageForm(forms.ModelForm):
    class Meta:
        model = InventoryShrinkage
        fields = ['inventory_item', 'quantity', 'reason', 'additional_details']
        widgets = {
            'inventory_item': forms.Select(attrs={'class': 'form-control product'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(AddShrinkageForm, self).__init__(*args, **kwargs)
        if self.request:
            self.fields['inventory_item'].queryset = Inventory.objects.filter(branch=self.request.user.branch)
