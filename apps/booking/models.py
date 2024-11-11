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
    Member_accounts = models.ForeignKey("Member_accounts", on_delete=models.CASCADE, null = True)
    Services = models.ForeignKey("Services", on_delete=models.CASCADE, null = True)
    Office_spaces = models.ForeignKey("Office_spaces", on_delete=models.CASCADE, null = True)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE, null = True)

    #add def funtion to every class
    def __str__(self) -> str:
        return f"{self.National_ID}", f"{self.Name}"

class Member_accounts(models.Model):
    Balance = models.DecimalField(max_digits= 8, decimal_places= 2, default= 0.00)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.Balance}"

class Payments(models.Model):
    Date = models.CharField(default= timezone.now)
    Amount = models.DecimalField(max_digits= 8, decimal_places= 2)

    def __str__(self) -> str:
        return f"{self.Amount}"

class Services(models.Model):
    Name = models.CharField(max_length= 255)
    Types = models.ForeignKey('Types', max_length= 255, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.name}, {self.Types.Price}'

class Types(models.Model):
    Name = models.CharField(max_length= 255)
    Price = models.DecimalField(max_digits=10, decimal_places=2)
    Service_duration = models.CharField(max_length=50)
    Promotion = models.BooleanField()

    def __str__(self):
        return f"{self.Name}"

class Office_spaces(models.Model):
    Name = models.CharField(max_length= 40, blank=False)

    def __str__(self):
        return f"{self.Name}"


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

