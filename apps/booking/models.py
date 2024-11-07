from django.db import models

# Create your models here.
class Types(models.Model):
    name = models.CharField(max_legnth= 255)

class Services(models.Model):
    name = models.CharField(max_length= 255)
    price = models.FloatField(max_length= 8)
    cost = models.FloatField(max_length= 8, blank=True)
    measurement = models.CharField(max_length= 255)
    recorded = models.FloatField(max_length= 8)
    date = models.DateField()
    Types = models.ForeignKey(max_length= 255, on_delete=models.CASCADE, null=True)