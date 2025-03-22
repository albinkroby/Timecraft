from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string
import math

class DeliveryProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    phone = models.CharField(max_length=15)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='delivery_profile/', null=True, blank=True)
    
    def __str__(self):
        return f"Delivery Profile: {self.user.get_full_name()}"
    
    def update_location(self, latitude, longitude):
        self.current_latitude = latitude
        self.current_longitude = longitude
        self.last_location_update = timezone.now()
        self.save()
    
    def calculate_distance(self, destination_lat, destination_lng):
        """Calculate distance in kilometers between delivery agent and destination using Haversine formula"""
        if not (self.current_latitude and self.current_longitude and destination_lat and destination_lng):
            return None
            
        # Earth radius in kilometers
        R = 6371
        
        # Convert decimal degrees to radians
        def deg2rad(deg):
            return deg * (math.pi/180)
            
        # Current location coordinates
        lat1 = float(self.current_latitude)
        lon1 = float(self.current_longitude)
        
        # Destination coordinates
        lat2 = float(destination_lat)
        lon2 = float(destination_lng)
        
        # Haversine formula
        dLat = deg2rad(lat2 - lat1)
        dLon = deg2rad(lon2 - lon1)
        
        a = math.sin(dLat/2) * math.sin(dLat/2) + \
            math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * \
            math.sin(dLon/2) * math.sin(dLon/2)
            
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return round(distance, 2)
    
    def is_available(self):
        """Check if delivery person is available for new assignments"""
        # Count active deliveries that are not completed
        from mainapp.models import Order
        active_deliveries = Order.objects.filter(
            assigned_to=self.user,
            status__in=['assigned_to_delivery', 'out_for_delivery']
        ).count()
        
        # Delivery person is available if they have less than 5 active deliveries
        return active_deliveries < 5 and self.is_active

class DeliveryHistory(models.Model):
    delivery_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_history')
    order = models.ForeignKey('mainapp.Order', on_delete=models.CASCADE, related_name='delivery_updates')
    status = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Delivery update for order {self.order.order_id}: {self.status}"

class DeliveryMetrics(models.Model):
    delivery_person = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_metrics')
    total_deliveries = models.PositiveIntegerField(default=0)
    completed_deliveries = models.PositiveIntegerField(default=0)
    cancelled_deliveries = models.PositiveIntegerField(default=0)
    avg_delivery_time = models.DurationField(null=True, blank=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Metrics for {self.delivery_person.get_full_name()}"
    
    def update_avg_rating(self, new_rating):
        """Update average rating when a new rating is received"""
        if self.total_ratings == 0:
            self.avg_rating = new_rating
        else:
            total = self.avg_rating * self.total_ratings
            self.avg_rating = (total + new_rating) / (self.total_ratings + 1)
        
        self.total_ratings += 1
        self.save()

class DeliveryRating(models.Model):
    order = models.OneToOneField('mainapp.Order', on_delete=models.CASCADE, related_name='delivery_rating')
    delivery_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField()  # 1-5 stars
    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Rating for order {self.order.order_id}: {self.rating}/5"
    
    def save(self, *args, **kwargs):
        """Update metrics when a new rating is saved"""
        super().save(*args, **kwargs)
        
        # Update delivery metrics
        metrics, created = DeliveryMetrics.objects.get_or_create(delivery_person=self.delivery_person)
        metrics.update_avg_rating(self.rating)
