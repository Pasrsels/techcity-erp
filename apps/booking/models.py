from django.db import models
from django.utils import timezone

class Types(models.Model):
    name = models.CharField(max_length= 255)

    def __str__(self):
        return self.name

class Services(models.Model):
    name = models.CharField(max_length= 255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True)
    measurement = models.CharField(max_length= 255)
    recorded = models.DecimalField(max_digits=10, decimal_places=4)
    date = models.DateField()
    Types = models.ForeignKey('types', max_length= 255, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.name}: {self.price}'

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
