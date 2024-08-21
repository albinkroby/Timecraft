from django.db import models
from vendorapp.models import VendorProfile
import os
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.db.models import Min, Max
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import imagehash
from PIL import Image
from django.conf import settings
import numpy as np

class Brand(models.Model):
    brand_name = models.CharField(max_length=100, unique=True)
    brand_image = models.ImageField(upload_to='brands/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    brand_parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_brands')

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

class Collection(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Material(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Feature(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

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

class WatchType(models.Model):
    type_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.type_name

class BaseWatch(models.Model):
    GENDER_CHOICES = [
        ('Men', 'Men'),
        ('Women', 'Women'),
        ('Unisex', 'Unisex'),
    ]

    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.SET_NULL, null=True, blank=True)
    watch_type = models.ForeignKey(WatchType, on_delete=models.SET_NULL, null=True, blank=True)
    
    model_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='Unisex')
    slug = models.SlugField(unique=True, blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    total_stock = models.IntegerField(default=0)
    available_stock = models.IntegerField(default=0)
    sold_stock = models.IntegerField(default=0)
    is_in_stock = models.BooleanField(default=False)
    color = models.CharField(max_length=50)
    style_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Materials
    strap_material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, related_name='strap_watches')
    glass_material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, related_name='glass_watches')
    case_material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, related_name='case_watches')
    
    case_size = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\d+(\.\d+)?\s*X\s*\d+(\.\d+)?\s*X\s*\d+(\.\d+)?$',
                message="Case size must be in the format '23 X 34 X 45' or '23.5 X 34.5 X 45.5'",
                code='invalid_case_size'
            )
        ],
        help_text="Enter case size in the format '23 X 34 X 45' (length X width X height in mm)"
    )
    water_resistance = models.CharField(max_length=50,choices=[('yes','yes'),('no','no')],blank=True,null=True)
    water_resistance_depth = models.IntegerField(help_text="Water resistance depth in meters", blank=True, null=True)
    
    net_quantity = models.IntegerField(default=1)
    alarms = models.IntegerField(default=0)
    function_display = models.CharField(max_length=100, blank=True, null=True)
    
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    
    series = models.CharField(max_length=200, blank=True, null=True)
    occasion = models.CharField(max_length=200, blank=True, null=True)
    strap_color = models.CharField(max_length=50, blank=True, null=True)
    strap_type = models.CharField(max_length=50, default="Band")
    dial_color = models.CharField(max_length=50, blank=True, null=True)
    warranty_period = models.IntegerField(help_text="Warranty period in months", blank=True, null=True)

    primary_image = models.ImageField(upload_to='Watch/primary/', null=True, blank=True)
    features = models.ManyToManyField(Feature, related_name='watches')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    image_hash = models.CharField(max_length=512, blank=True, null=True)  # Increased max_length to accommodate larger hash

    def __str__(self):
        return self.model_name
    
    def clean(self):
        super().clean()
        # Additional validation if needed
        if self.case_size:
            try:
                dimensions = [float(dim.strip()) for dim in self.case_size.split('X')]
                if len(dimensions) != 3:
                    raise ValidationError({'case_size': "Case size must have exactly three dimensions."})
            except ValueError:
                raise ValidationError({'case_size': "Invalid format. Use numbers separated by 'X'."})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.primary_image and not self.primary_image.name.startswith('Watch/primary/'):
            extension = os.path.splitext(self.primary_image.name)[1]
            new_filename = f"{slugify(self.model_name)}_primary{extension}"
            self.primary_image.name = new_filename
        self.is_in_stock = self.available_stock > 0 
        super().save(*args, **kwargs)
        if self.primary_image and not self.image_hash:
            self.generate_image_hash()

    def generate_image_hash(self):
        if self.primary_image:
            image_path = self.primary_image.path
            with Image.open(image_path) as img:
                img = img.convert('RGB')
                img = img.resize((256, 256))
                phash = imagehash.phash(img)
                dhash = imagehash.dhash(img)
                whash = imagehash.whash(img)
                self.image_hash = f"{phash},{dhash},{whash}"

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

    def update_stock_after_order(self, quantity):
        if self.available_stock >= quantity:
            self.available_stock -= quantity
            self.sold_stock += quantity
            self.is_in_stock = self.available_stock > 0
            self.save()
        else:
            raise ValueError(f"Not enough stock for {self.model_name}")

def pre_save_base_watch_receiver(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.model_name)

pre_save.connect(pre_save_base_watch_receiver, sender=BaseWatch)

class WatchImage(models.Model):
    base_watch = models.ForeignKey(BaseWatch, on_delete=models.CASCADE, related_name='additional_images')
    image = models.ImageField(upload_to='Watch/additional/', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.image:
            extension = os.path.splitext(self.image.name)[1]
            new_filename = f"{slugify(self.base_watch.model_name)}_additional_{self.base_watch.additional_images.count() + 1}{extension}"
            self.image.name = new_filename
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Additional image for {self.base_watch.model_name}"

class SmartWatchFeature(models.Model):
    base_watch = models.OneToOneField(BaseWatch, on_delete=models.CASCADE, related_name='smartwatch_features')
    heart_rate_monitor = models.BooleanField(default=False)
    gps = models.BooleanField(default=False)
    step_counter = models.BooleanField(default=False)
    sleep_tracker = models.BooleanField(default=False)

    def __str__(self):
        return f"Smartwatch features for {self.base_watch.model_name}"

class PremiumWatchFeature(models.Model):
    base_watch = models.OneToOneField(BaseWatch, on_delete=models.CASCADE, related_name='premium_features')
    sapphire_glass = models.BooleanField(default=False)
    automatic_movement = models.BooleanField(default=False)
    chronograph = models.BooleanField(default=False)

    def __str__(self):
        return f"Premium features for {self.base_watch.model_name}"