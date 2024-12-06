from django.db import models
from django.utils.translation import gettext_lazy as _

class voucherCategory(models.Model):
    name = models.CharField(max_length=50)
    
    class Meta:
        verbose_name = _("voucherCategory")
        verbose_name_plural = _("voucherCategorys")

    def __str__(self):
        return self.name


class voucherFile(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    file = models.FileField(upload_to='vouchers', max_length=100)
    category = models.ForeignKey("vouchers.voucherCategory", on_delete=models.CASCADE)
    date_created = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=50, default='not populated')

    class Meta:
        ordering = ['-date_created']
        verbose_name = _("voucherFile")
        verbose_name_plural = _("voucherFiles")

    def __str__(self):
        return self.name


class vouchers(models.Model):
    voucher_no = models.CharField(max_length=50)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    file = models.ForeignKey("vouchers.voucherFile", on_delete=models.CASCADE)
    date_created = models.DateField(auto_now_add=True)
    date_used = models.DateField(auto_now=True)
    status = models.CharField(max_length=50, default='unused')
    
    class Meta:
        ordering = ['-date_created']
        verbose_name = _("vouchers")
        verbose_name_plural = _("vouchers")

    def __str__(self):
        return self.voucher_no

    
class voucherLogs(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']
        verbose_name = _("voucherLogs")
        verbose_name_plural = _("voucherLogss")

    def __str__(self):
        return f'{self.user} : {self.action}'


class voucherUser(models.Model):
    voucher_no = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    phonenumber = models.CharField(max_length=50)    
    date_created = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = _("voucherUser")
        verbose_name_plural = _("voucherUsers")

    def __str__(self):
        return self.name







