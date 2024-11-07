from django.db import models

class Types(models.Model):
    name = models.CharField(max_length= 255)

    def __str__(self):
        return self.name

class Services(models.Model):
    name = models.CharField(max_length= 255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    measurement = models.CharField(max_length= 255)
    recorded = models.DecimalField(max_digits=10, decimal_places=4)
    date = models.DateField()
    Types = models.ForeignKey('types', max_length= 255, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'{self.name}: {self.price}'