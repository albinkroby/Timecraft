from django.contrib import admin
from .models import VendorProfile,VendorAddress
# Register your models here.

admin.site.register(VendorProfile)
admin.site.register(VendorAddress)
