from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from mainapp.models import Address, User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
from datetime import timedelta

# Add these imports at the top of models.py
from eth_utils import keccak
import json
from django.conf import settings
from web3 import Web3

# Create your models here.

class WatchPartName(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class WatchPart(models.Model):
    part_name = models.ForeignKey(WatchPartName, on_delete=models.CASCADE,null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    model_path = models.CharField(max_length=255, help_text="Path to the part in the 3D model, e.g., 'Sketchfab_model>root>GLTF_SceneRootNode>STRAP_-_PARENT_29>Strap_Merged002_27>Object_64'")

    def __str__(self):
        return f"{self.part_name.name} - {self.description[:50]}"

class WatchPartOption(models.Model):
    part = models.ForeignKey(WatchPart, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)
    texture = models.ImageField(upload_to='watch_part_textures/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='watch_part_thumbnails/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, blank=True, null=True, help_text="Hex color code (e.g., #FF5733)")
    
    def __str__(self):
        return f"{self.part.part_name.name} - {self.name}"

class CustomizableWatch(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    model_file = models.FileField(upload_to='custom_watch_models/', help_text="ZIP file containing the 3D model (GLTF/GLB) and associated files")
    thumbnail = models.ImageField(upload_to='custom_watch_thumbnails/', null=True, blank=True)

    def __str__(self):
        return self.name

class CustomizableWatchPart(models.Model):
    customizable_watch = models.ForeignKey(CustomizableWatch, on_delete=models.CASCADE, related_name='customizable_parts')
    part = models.ForeignKey(WatchPart, on_delete=models.CASCADE)
    options = models.ManyToManyField(WatchPartOption)

    class Meta:
        unique_together = ('customizable_watch', 'part')

    def __str__(self):
        return f"{self.customizable_watch.name} - {self.part.part_name.name}"

class CustomWatchSavedDesign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customizable_watch = models.ForeignKey(CustomizableWatch, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    design_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    preview_image = models.ImageField(upload_to='design_previews/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s design: {self.name}"
    
class CustomWatchOrder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Order Approved'),
        ('manufacturing', 'Manufacturing'),
        ('ready_to_ship', 'Ready to Ship'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    customizable_watch = models.ForeignKey(CustomWatchSavedDesign, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_watch_orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_the_way')
    stripe_session_id = models.CharField(max_length=200, blank=True, null=True)
    order_id = models.CharField(max_length=50, unique=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=200, blank=True, null=True)
    return_reason = models.CharField(max_length=200, blank=True, null=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    shipping_started_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Custom Order for {self.customizable_watch.name}"

    def is_returnable(self):
        if self.status == 'delivered' and self.delivery_date:
            return (timezone.now().date() - self.delivery_date) <= timedelta(days=10)
        return False

    def cancel_order(self, reason):
        if self.status not in ['delivered', 'cancelled']:
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.save()
            return True
        return False

    def can_view_certificate(self):
        """Check if the certificate should be available"""
        return self.status == 'delivered' and hasattr(self, 'certificate')
    
    def certificate_status(self):
        """Get the current status of the certificate"""
        if self.status != 'delivered':
            return 'pending_delivery'
        elif not hasattr(self, 'certificate'):
            return 'generating'
        elif not self.certificate.is_verified:
            return 'pending_verification'
        return 'verified'

@receiver(pre_save, sender=CustomWatchOrder)
def create_order_id(sender, instance, **kwargs):
    if not instance.order_id:
        now = timezone.now()
        time_string = now.strftime("%d%m%Y%H%M%S%f")
        unique_id = str(uuid.uuid4().hex[:6])  # Add this for extra uniqueness
        instance.order_id = f"CWH{time_string}{unique_id}"

class CustomWatchOrderPart(models.Model):
    order = models.ForeignKey(CustomWatchOrder, on_delete=models.CASCADE, related_name='selected_parts')
    part = models.ForeignKey(WatchPart, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(WatchPartOption, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'part')

    def __str__(self):
        return f"{self.order} - {self.part.name}: {self.selected_option.name}"

class WatchCertificate(models.Model):
    order = models.OneToOneField('CustomWatchOrder', on_delete=models.CASCADE, related_name='certificate')
    certificate_hash = models.CharField(max_length=66)  # ethereum hash length
    issued_date = models.DateTimeField(auto_now_add=True)
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_metamask_verified = models.BooleanField(default=False)
    
    def generate_certificate_hash(self):
        """Generate a unique hash for the certificate"""
        certificate_data = {
            'order_id': self.order.order_id,
            'watch_name': self.order.customizable_watch.name,
            'customer': self.order.user.email,
            'date': self.issued_date.isoformat(),
            'customizations': [
                {
                    'part': part.part.part_name.name,
                    'option': part.selected_option.name
                } for part in self.order.selected_parts.all()
            ]
        }
        
        # Create a deterministic JSON string
        json_data = json.dumps(certificate_data, sort_keys=True)
        # Generate keccak256 hash
        return '0x' + keccak(text=json_data).hex()
