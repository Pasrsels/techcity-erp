from django.db import models


def company_logo_path(instance, filename):
    return f"{instance.name}/logos/{filename}"


class Company(models.Model): 
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    domain = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to=company_logo_path, blank=True)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'company'

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # change logo name before saving and folder location
        if self.logo:
            self.logo.name = f"{self.name}_logo.png"
        super(Company, self).save(*args, **kwargs)


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    phonenumber = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    disable = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name
    

class BranchBSession(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        db_table = 'branch_b_session'  
        managed = False  