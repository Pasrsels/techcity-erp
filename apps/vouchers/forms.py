from django.forms import ModelForm
from apps.vouchers.models import voucherFile, vouchers, voucherCategory, voucherUser

class addVoucherFileForm(ModelForm):
    
    class Meta:
        model = voucherFile
        fields = ('name', 'file', 'category')

class voucherForm(ModelForm):
    
    class Meta:
        model = vouchers
        fields = ('status',)

class categoryForm(ModelForm):
    
    class Meta:
        model = voucherCategory
        fields = '__all__'

class voucherUserForm(ModelForm):
    
    class Meta:
        model =  voucherUser
        exclude = ('voucher_no',)



