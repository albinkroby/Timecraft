from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
        ('staff', 'Staff'),
    )
    
    fullname = models.CharField(max_length=255)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    # Use email as the unique identifier instead of username
    email = models.EmailField(unique=True)

    # If you want to use email for login instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'fullname']

    def __str__(self):
        return self.email

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    flat_house_no = models.CharField(max_length=255, verbose_name="Flat/House No:/Building/Company/Apartment")
    area_street = models.CharField(max_length=255, verbose_name="Area/Street/Sector/Village")
    landmark = models.CharField(max_length=255)
    pincode = models.CharField(max_length=10)
    town_city = models.CharField(max_length=100, verbose_name="Town/City")
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username}'s profile"
    

