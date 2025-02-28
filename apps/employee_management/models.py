from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid

class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Position(models.Model):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    pay_grade = models.CharField(max_length=50)
    is_manager = models.BooleanField(default=False)
    responsibilities = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.department}"

class Employee(models.Model):
    EMPLOYMENT_STATUS = [
        ('FT', 'Full Time'),
        ('PT', 'Part Time'),
        ('CT', 'Contract'),
        ('INT', 'Intern'),
    ]

    EMPLOYMENT_TYPE = [
        ('REM', 'Remote'),
        ('HYB', 'Hybrid'),
        ('ONS', 'On-site'),
    ]

    # Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    position = models.ForeignKey(Position, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    reports_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Personal Information
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20)
    emergency_contact = models.CharField(max_length=100)
    emergency_phone = models.CharField(max_length=20)
    address = models.TextField()
    
    # Employment Details
    hire_date = models.DateField()
    employment_status = models.CharField(max_length=3, choices=EMPLOYMENT_STATUS)
    employment_type = models.CharField(max_length=3, choices=EMPLOYMENT_TYPE)
    probation_end_date = models.DateField(null=True, blank=True)
    current_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    
    # System Fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"

class EmployeeDocument(models.Model):
    DOCUMENT_TYPES = [
        ('ID', 'Identity Document'),
        ('QUAL', 'Qualification'),
        ('CERT', 'Certification'),
        ('CONT', 'Contract'),
        ('EVA', 'Evaluation'),
        ('OTH', 'Other'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=4, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='employee_documents/')
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Leave(models.Model):
    LEAVE_TYPES = [
        ('ANN', 'Annual Leave'),
        ('SIC', 'Sick Leave'),
        ('MAT', 'Maternity Leave'),
        ('PAT', 'Paternity Leave'),
        ('UNP', 'Unpaid Leave'),
        ('OTH', 'Other'),
    ]

    LEAVE_STATUS = [
        ('PEN', 'Pending'),
        ('APP', 'Approved'),
        ('REJ', 'Rejected'),
        ('CAN', 'Cancelled'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=3, choices=LEAVE_STATUS, default='PEN')
    approved_by = models.ForeignKey(Employee, related_name='approved_leaves', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    break_start = models.DateTimeField(null=True, blank=True)
    break_end = models.DateTimeField(null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'date']

class PerformanceReview(models.Model):
    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Above Average'),
        (5, 'Excellent'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(Employee, related_name='reviews_given', on_delete=models.PROTECT)
    review_period_start = models.DateField()
    review_period_end = models.DateField()
    performance_rating = models.IntegerField(choices=RATING_CHOICES)
    achievements = models.TextField()
    areas_for_improvement = models.TextField()
    goals_set = models.TextField()
    comments = models.TextField()
    reviewed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Training(models.Model):
    TRAINING_STATUS = [
        ('SCH', 'Scheduled'),
        ('ONG', 'Ongoing'),
        ('COM', 'Completed'),
        ('CAN', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    trainer = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=3, choices=TRAINING_STATUS)
    participants = models.ManyToManyField(Employee, through='TrainingParticipant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TrainingParticipant(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    completion_status = models.BooleanField(default=False)
    completion_date = models.DateField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'training']

# forms.py
from django import forms
from .models import Employee, Leave, PerformanceReview

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'probation_end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model = Leave
        exclude = ['status', 'approved_by', 'created_at', 'updated_at']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReview
        exclude = ['reviewed_at', 'updated_at']
        widgets = {
            'review_period_start': forms.DateInput(attrs={'type': 'date'}),
            'review_period_end': forms.DateInput(attrs={'type': 'date'}),
        }