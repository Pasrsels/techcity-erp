from django.db import models
from django.utils import timezone

class Members(models.Model):
    ENROLLMENT_CHOICES = [
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
    ]
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    National_ID = models.CharField(max_length=15, blank=False)
    Name = models.CharField(max_length=50, blank=False)
    Email = models.EmailField(max_length=255, blank=False)
    Phone = models.CharField(max_length=12, blank=False)
    Address = models.CharField(max_length=255, blank=False)
    Enrollment = models.CharField(choices=ENROLLMENT_CHOICES, max_length=20)
    Company = models.CharField(max_length=255, blank=True)
    Age = models.IntegerField(blank=False)
    Gender = models.CharField(choices=GENDER_CHOICES, max_length=1)
    Member_accounts = models.ForeignKey("Member_accounts", on_delete=models.CASCADE, null=True, blank=True)
    Services = models.ForeignKey("Services", on_delete=models.CASCADE, null=True, blank=True)
    Office_spaces = models.ForeignKey("Office_spaces", on_delete=models.CASCADE, null=True, blank=True)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE, null=True, blank=True)
    delete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.National_ID}, {self.Name}"


class Member_accounts(models.Model):
    Balance = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE)
    delete = models.BooleanField(default=False)

    def __str__(self):
        return f"Balance: {self.Balance}"


class Payments(models.Model):
    Date = models.DateField(default=timezone.now)
    Amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    Admin_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    Description = models.CharField(max_length=255, default='')

    def __str__(self):
        return f"Payment: {self.Amount}"


class Services(models.Model):
    Name = models.CharField(max_length=255)
    Types = models.ForeignKey('Types', on_delete=models.CASCADE, null=True, blank=True)
    delete = models.BooleanField(default=False)

    def __str__(self):
        return f"Service: {self.Name}"


class Types(models.Model):
    Name = models.CharField(max_length=255)
    Price = models.DecimalField(max_digits=10, decimal_places=2)
    Duration = models.CharField(max_length=50, default='')
    Promotion = models.BooleanField(default=False)

    def __str__(self):
        return f"Type: {self.Name}, Price: {self.Price}"


class Office_spaces(models.Model):
    Name = models.CharField(max_length=40, blank=False)

    def __str__(self):
        return f"Office: {self.Name}"


class Logs(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('read', 'Read'),
        ('delete', 'Delete'),
    ]
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    Services = models.ForeignKey('Services', on_delete=models.CASCADE, related_name='logs_file')
    Members = models.ForeignKey("Members", on_delete=models.CASCADE)
    Payments = models.ForeignKey("Payments", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log: {self.Services.Name}, {self.timestamp}"
