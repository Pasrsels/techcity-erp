from django.db import models
from django.utils import timezone

class Members(models.Model):
    National_ID = models.CharField(max_length=15, blank=False)
    Name = models.CharField(max_length= 50, blank=False)
    Email = models.EmailField(max_length=255, blank=False)
    Phone = models.CharField(max_length=12, blank=False)
    Address = models.CharField(max_length= 255, blank= False)
    Enrollmnet = models.Choices("permanent","temporary")
    Company = models.CharField(max_length= 255, blank= True)
    Age = models.IntegerField(blank=False)
    Gender = models.Choices("M", "F")
    Member_accounts = models.ForeignKey("MemberAccounts", on_delete=models.CASCADE, null = True)
    Services = models.ForeignKey("Services", on_delete=models.CASCADE, null = True)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE, null = True)
    delete = models.BooleanField(default=False)
    #add def funtion to every class
    def __str__(self) -> str:
        return f"{self.National_ID}", f"{self.Name}"

class MemberAccounts(models.Model):
    Balance = models.DecimalField(max_digits= 8, decimal_places= 2, default= 0.00)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE)
    delete = models.BooleanField(default= False)
    def __str__(self) -> str:
        return f"{self.Balance}"

class Payments(models.Model):
    Date = models.CharField(default= timezone.now)
    Amount = models.DecimalField(max_digits= 8, decimal_places= 2, default= 0.00)
    Admin_fee = models.DecimalField(max_digits=8 , decimal_places=2, default= 0.00)
    Description = models.CharField(max_length= 255, default='')
    def __str__(self) -> str:
        return f"{self.Amount}"

class Services(models.Model): # removed the foreign key to itemofuse 
    service_name = models.CharField(max_length= 255, default='')
    description = models.CharField(max_length=255, default= 'none')
    unit_measure = models.ForeignKey('UnitMeasurement', on_delete= models.CASCADE, null=True)
    service_range = models.CharField(max_length=255, default= 'none')

    def __str__(self):
        return f'{self.service_name}'

class Category(models.Model):
    category_name = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.category_name}'

class itemOfUseName(models.Model):
     item_of_use_name = models.CharField(max_length=255)

     def __str__(self):
         return self.item_of_use_name
     
class ItemOfUse(models.Model):
    service = models.ManyToManyField(Services)
    name = models.ForeignKey(itemOfUseName, on_delete=models.CASCADE)
    quantity = models.IntegerField( default= 0)
    cost = models.DecimalField(max_digits=4, decimal_places= 2, default= 0.00)
    description = models.CharField(max_length=255, default= 'none')
    category = models.ForeignKey('Category', on_delete= models.CASCADE)
    
    def __str__(self):
        return f"{self.name}"

class UnitMeasurement(models.Model):
    measurement = models.CharField(max_length=60, null = True)
    def __str__(self):
        return f'{self.measurement}'

class ServiceRange(models.Model): # removed to and from
    service_range = models.CharField(max_length=40, default= 'none')

    def __str__(self):
        return f'{self.service_range}'

class inventory(models.Model):
    name = models.CharField(max_length= 255)
    cost = models.DecimalField(max_digits=5, decimal_places=2 , default= 0.00)
    category = models.ForeignKey('Category', on_delete= models.CASCADE)
    quantity = models.IntegerField(default= 0)
    
    
 
class Logs(models.Model):
    ACTION_CHOICES = [
        ('create','create'),
        ('update','update'),
        ('read','read'),
        ('delete','delete'),
    ]
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    Services = models.ForeignKey('services', on_delete=models.CASCADE, related_name='logs_file')
    Members = models.ForeignKey("Members", on_delete=models.CASCADE)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.Services.name}, {self.timestamp}"

