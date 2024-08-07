from django.db import models
from vendorapp.models import VendorProfile
# Create your models here.
from django.db import models
import os
from django.utils.text import slugify
from django.db.models.signals import pre_save
# from .storage import WatchImageStorage

class Brand(models.Model):
    brand_name = models.CharField(max_length=100, unique=True)
    brand_image = models.ImageField(upload_to='brands/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def rename_image(instance, filename):
        ext = filename.split('.')[-1]
        slugified_name = slugify(instance.brand_name)
        return f'{slugified_name}.{ext}'

    def save(self, *args, **kwargs):
        if self.brand_image:
            self.brand_image.name = self.rename_image(self.brand_image.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.brand_name

    class Meta:
        ordering = ['brand_name']

class Category(models.Model):
    name = models.CharField(max_length=50)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')

    def __str__(self):
        return self.name
        
class BaseWatch(models.Model):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    stock_quantity = models.IntegerField()
    color = models.CharField(max_length=50)
    strap_material = models.CharField(max_length=50)
    case_size = models.DecimalField(max_digits=5, decimal_places=2)
    movement_type = models.CharField(max_length=50)
    water_resistance = models.CharField(max_length=50)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)

def pre_save_base_watch_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.model_name)

pre_save.connect(pre_save_base_watch_receiver, sender=BaseWatch)

class WatchImage(models.Model):
    base_watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='Watch/',null=True,blank=True)
    is_primary = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.image:
            # Set the image name based on the model name and a unique identifier
            extension = os.path.splitext(self.image.name)[1]
            new_filename = f"{slugify(self.base_watch.model_name)}_{self.base_watch.images.count() + 1}{extension}"
            self.image.name = new_filename
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.base_watch.model_name}"