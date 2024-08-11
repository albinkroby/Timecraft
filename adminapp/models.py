from django.db import models
from vendorapp.models import VendorProfile
# Create your models here.
from django.db import models
import os
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.db.models import Min, Max

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

    @classmethod
    def category_exists(cls, name):
        return cls.objects.filter(name__iexact=name).exists()

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Categories"
        
class BaseWatch(models.Model):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    total_stock = models.IntegerField(default=0)
    available_stock = models.IntegerField(default=0)
    sold_stock = models.IntegerField(default=0)
    is_in_stock = models.BooleanField(default=False)
    color = models.CharField(max_length=50)
    strap_material = models.CharField(max_length=50)
    case_size = models.DecimalField(max_digits=5, decimal_places=2)
    movement_type = models.CharField(max_length=50)
    water_resistance = models.CharField(max_length=50)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    display_type = models.CharField(max_length=50, default="Analog")
    style_code = models.CharField(max_length=100, blank=True, null=True)
    series = models.CharField(max_length=200, blank=True, null=True)
    occasion = models.CharField(max_length=200, blank=True, null=True)
    pack_of = models.IntegerField(default=1)
    strap_color = models.CharField(max_length=50, blank=True, null=True)
    net_quantity = models.IntegerField(default=1)
    strap_type = models.CharField(max_length=50, default="Band")
    case_material = models.CharField(max_length=100, default="Stainless Steel Back Case")
    water_resistance_depth = models.IntegerField(help_text="Water resistance depth in meters",blank=True, null=True)
    dial_color = models.CharField(max_length=50,blank=True, null=True)
    width = models.DecimalField(max_digits=5, decimal_places=2, help_text="Width in mm",blank=True, null=True)
    diameter = models.DecimalField(max_digits=5, decimal_places=2, help_text="Diameter in mm",blank=True, null=True)
    warranty_period = models.IntegerField(help_text="Warranty period in months",blank=True, null=True)

    primary_image = models.ImageField(upload_to='Watch/primary/', null=True, blank=True)

    def __str__(self):
        return self.model_name

    def save(self, *args, **kwargs):
        if self.primary_image and not self.primary_image.name.startswith('Watch/primary/'):
            extension = os.path.splitext(self.primary_image.name)[1]
            new_filename = f"{slugify(self.model_name)}_primary{extension}"
            self.primary_image.name = new_filename
        self.is_in_stock = self.available_stock > 0 
        super().save(*args, **kwargs)

    def get_primary_image(self):
        return self.primary_image

    @classmethod
    def get_price_range(cls):
        price_range = cls.objects.aggregate(min_price=Min('base_price'), max_price=Max('base_price'))
        return price_range

    @classmethod
    def get_unique_values(cls, field_name):
        return cls.objects.values_list(field_name, flat=True).distinct()

    def update_stock(self, new_stock):
        if new_stock > self.total_stock:
            self.total_stock = new_stock
        self.available_stock = new_stock
        self.sold_stock = self.total_stock - self.available_stock
        self.save()

def pre_save_base_watch_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.model_name)

pre_save.connect(pre_save_base_watch_receiver, sender=BaseWatch)

class WatchImage(models.Model):
    base_watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='Watch/additional/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.image:
            # Set the image name based on the model name and a unique identifier
            extension = os.path.splitext(self.image.name)[1]
            new_filename = f"{slugify(self.base_watch.model_name)}_additional_{self.base_watch.additional_images.count() + 1}{extension}"
            self.image.name = new_filename
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Additional image for {self.base_watch.model_name}"