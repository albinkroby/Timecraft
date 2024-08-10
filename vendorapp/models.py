from django.db import models
from mainapp.models import User
# Create your models here.

#Vendor Profiles
class VendorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    company_name = models.CharField(max_length=100,unique=True)
    description = models.TextField(null=True, blank=True)
    gst_number = models.CharField(max_length=20, null=False, blank=False)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    approval_status = models.CharField(max_length=10, choices=[
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name