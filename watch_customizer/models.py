from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from mainapp.models import Address, User

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
    roughness = models.FloatField(default=0.5, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    metalness = models.FloatField(default=0.5, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    
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

class CustomWatchOrder(models.Model):
    STATUS_CHOICES = (
        ('on_the_way', 'On the way'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    )
    customizable_watch = models.ForeignKey(CustomizableWatch, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_watch_orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_the_way')
    stripe_session_id = models.CharField(max_length=200, blank=True, null=True)
    order_id = models.CharField(max_length=50, unique=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Custom Order for {self.customizable_watch.name}"

class CustomWatchOrderPart(models.Model):
    order = models.ForeignKey(CustomWatchOrder, on_delete=models.CASCADE, related_name='selected_parts')
    part = models.ForeignKey(WatchPart, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(WatchPartOption, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'part')

    def __str__(self):
        return f"{self.order} - {self.part.name}: {self.selected_option.name}"

class CustomWatchSavedDesign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customizable_watch = models.ForeignKey(CustomizableWatch, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    design_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s design: {self.name}"