from django.db import models
from django.utils import timezone

class Members(models.Model):
    National_ID = models.CharField(max_length=15, blank=False)
    Name = models.CharField(max_legnth= 50, blank=False)
    Email = models.EmailField(max_length=255, blank=False)
    Phone = models.CharField(max_length=12, blank=False)
    Address = models.CharField(max_length= 255, blank= False)
    Enrollmnet = models.Choices("permanent","temporary")
    Company = models.CharField(max_length= 255, blank= True)
    Age = models.IntegerField(max_length=2, blank=False)
    Gender = models.Choices("M", "F")
    #ADD MEMBER ACCOUNT FOREGIN KEY
    #ADD SERVICES FOREIGN KEY
    #ADD OFFICE SPACES FOREIGN KEY
    #ADD PAYMENTS FOREIGN KEY

    #add def funtion to every class

class Member_accounts(models.Model):
    Balance = models.DecimalField(max_digits= 8, decimal_places= 2, default= 0)
    #ADD FOREIGN KEY PAYMENTS

class Payments(models.Model):
    Date = models.CharField(default= timezone.now)
    Amount = models.DecimalField(max_digits= 8, decimal_places= 2)

class Services(models.Model):
    Name = models.CharField(max_length= 255)
    Types = models.ForeignKey('types', max_length= 255, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.name}: {self.price}'

class Types(models.Model):
    Name = models.CharField(max_length= 255)
    Price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    Service_duration = models.DateTimeField()
    Promotion = models.BooleanField()
    
    def __str__(self):
        return self.name


class Logs(models.Model):
    ACTION_CHOICES = [
        ('sale','sale'),
        ('return','return'),
        ('cancel','cancel'),
        ('delete','delete'),
        ('update','update'),
    ]
    
    Services = models.ForeignKey('services', on_delete=models.CASCADE, related_name='logs_file')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.Services.name}, {self.timestamp}"

