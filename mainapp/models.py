from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
import random
from datetime import timedelta
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
        ('staff', 'Staff'),
        ('vendor', 'Vendor'),
    )
    
    fullname = models.CharField(max_length=255)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False, blank=True,null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'fullname']

    def __str__(self):
        return self.email

from adminapp.models import BaseWatch, Brand, Category

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=10)

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('home', 'Home'),
        ('office', 'Office'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address')
    flat_house_no = models.CharField(max_length=255, verbose_name="Flat/House No:/Building/Company/Apartment")
    area_street = models.CharField(max_length=255, verbose_name="Area/Street/Sector/Village")
    landmark = models.CharField(max_length=255)
    pincode = models.CharField(max_length=10)
    town_city = models.CharField(max_length=100, verbose_name="Town/City")
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='home')
    is_primary = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Set all other addresses of this user to non-primary
            Address.objects.filter(user=self.user).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.flat_house_no}, {self.area_street}, {self.town_city}, {self.state}, {self.pincode}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.watch.model_name} in cart for {self.cart.user.username}"

    @property
    def total_price(self):
        return self.watch.base_price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = (
        ('on_the_way', 'On the way'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_the_way')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    stripe_session_id = models.CharField(max_length=200, blank=True, null=True)
    order_id = models.CharField(max_length=50, unique=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.order_id} by {self.user.email}"

    def get_vendor_total(self, vendor):
        return sum(
            item.price * item.quantity 
            for item in self.items.filter(watch__vendor=vendor)
        )

    def cancel_order(self, reason):
        if self.status not in ['delivered', 'cancelled']:
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.save()
            return True
        return False
    
    from datetime import timedelta

    def is_returnable(self):
        if self.status == 'delivered' and self.delivery_date:
            return (timezone.now().date() - self.delivery_date) <= timedelta(days=10)
        return False

@receiver(pre_save, sender=Order)
def create_order_id(sender, instance, **kwargs):
    if not instance.order_id:
        now = timezone.now()
        time_string = now.strftime("%d%m%Y%H%M%S%f")
        unique_id = str(uuid.uuid4().hex[:6])  # Add this for extra uniqueness
        instance.order_id = f"WH{time_string}{unique_id}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.watch.model_name} in Order {self.order.id}"

    @property
    def total_price(self):
        return self.price * self.quantity

class WatchNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'watch')

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Chat with {self.user.username if self.user else self.guest_name}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages',default=True)
    is_user = models.BooleanField(default=True) 
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


class SupportTicket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending Customer Response'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ]
    
    TICKET_TYPES = [
        ('order_issue', 'Order Related'),
        ('payment_issue', 'Payment Related'),
        ('product_inquiry', 'Product Inquiry'),
        ('return_refund', 'Return/Refund'),
        ('vendor_support', 'Vendor Support'),
        ('technical_issue', 'Technical Issue'),
        ('other', 'Other')
    ]

    ticket_id = models.CharField(max_length=10, unique=True, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPES,null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        'adminapp.StaffMember',  # Use string reference instead of direct model
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolution = models.TextField(blank=True, null=True)
    customer_feedback = models.IntegerField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = f"TKT{timezone.now().strftime('%y%m%d')}{random.randint(1000,9999)}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']

class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_staff_reply = models.BooleanField(default=False)

class ProductView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(BaseWatch, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-timestamp']),
        ]

class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    favorite_brands = models.ManyToManyField(Brand, blank=True)
    favorite_categories = models.ManyToManyField(Category, blank=True)
    preferred_price_range = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
