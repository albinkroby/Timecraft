from django.db import models
from django.conf import settings
from django.utils import timezone
import random
import string
import math
import json

class DeliveryProfile(models.Model):
    VEHICLE_CHOICES = [
        ('motorcycle', 'Motorcycle'),
        ('bicycle', 'Bicycle'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    
    ZONE_CHOICES = [
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    phone = models.CharField(max_length=15)
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_CHOICES, blank=True, null=True)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='delivery_profile/', null=True, blank=True)
    
    # New fields for improved assignment - using CharField instead of JSONField for SQLite compatibility
    preferred_zones_text = models.TextField(default='', blank=True, help_text="Comma-separated list of preferred delivery zones")
    max_distance = models.PositiveIntegerField(default=15, help_text="Maximum delivery distance in kilometers")
    max_workload = models.PositiveSmallIntegerField(default=5, help_text="Maximum number of concurrent deliveries")
    availability_start = models.TimeField(null=True, blank=True, help_text="Daily availability start time")
    availability_end = models.TimeField(null=True, blank=True, help_text="Daily availability end time")
    weekday_availability_text = models.CharField(max_length=20, default='0,1,2,3,4', blank=True, help_text="Comma-separated list of available weekdays (0-6, where 0 is Monday)")
    
    # Onboarding status
    onboarding_completed = models.BooleanField(default=False, help_text="Whether the user has completed the onboarding process")
    onboarding_completed_at = models.DateTimeField(null=True, blank=True, help_text="When the user completed onboarding")
    
    def __str__(self):
        return f"Delivery Profile: {self.user.get_full_name()}"
    
    @property
    def preferred_zones(self):
        """Get preferred zones as a list"""
        if not self.preferred_zones_text:
            return []
        return [zone.strip() for zone in self.preferred_zones_text.split(',') if zone.strip()]
    
    @preferred_zones.setter
    def preferred_zones(self, zones_list):
        """Set preferred zones from a list"""
        if isinstance(zones_list, list):
            self.preferred_zones_text = ','.join(zones_list)
        else:
            self.preferred_zones_text = str(zones_list)
    
    @property
    def weekday_availability(self):
        """Get weekday availability as a list of integers"""
        if not self.weekday_availability_text:
            return []
        try:
            return [int(day.strip()) for day in self.weekday_availability_text.split(',') if day.strip()]
        except ValueError:
            return []
    
    @weekday_availability.setter
    def weekday_availability(self, days_list):
        """Set weekday availability from a list of integers"""
        if isinstance(days_list, list):
            self.weekday_availability_text = ','.join(str(day) for day in days_list)
        else:
            self.weekday_availability_text = str(days_list)
    
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
        
        # Check if current time is within availability window
        now = timezone.now()
        is_in_time_window = True
        
        if self.availability_start and self.availability_end:
            current_time = now.time()
            is_in_time_window = (current_time >= self.availability_start and 
                                current_time <= self.availability_end)
        
        # Check if current day is in available weekdays
        is_available_day = True
        weekday_avail = self.weekday_availability
        if weekday_avail:
            current_weekday = now.weekday()  # 0 is Monday, 6 is Sunday
            is_available_day = current_weekday in weekday_avail
        
        # Delivery person is available if they meet all criteria
        return (active_deliveries < self.max_workload and 
                self.is_active and 
                is_in_time_window and 
                is_available_day)

    def can_deliver_to_zone(self, zone_name):
        """Check if delivery person can deliver to a specific zone"""
        # If no preferred zones are set, assume they can deliver anywhere
        pref_zones = self.preferred_zones
        if not pref_zones:
            return True
        
        return zone_name in pref_zones
    
    def can_deliver_to_distance(self, destination_lat, destination_lng):
        """Check if destination is within the maximum delivery distance"""
        if not self.max_distance:
            return True
        
        distance = self.calculate_distance(destination_lat, destination_lng)
        if not distance:
            return True  # If distance can't be calculated, don't restrict
        
        return distance <= self.max_distance

    def is_profile_complete(self):
        """Check if all required profile fields are completed"""
        required_fields = ['phone', 'vehicle_type', 'vehicle_number']
        return all(getattr(self, field) for field in required_fields)
    
    def mark_onboarding_complete(self):
        """Mark the onboarding process as complete"""
        self.onboarding_completed = True
        self.onboarding_completed_at = timezone.now()
        self.save(update_fields=['onboarding_completed', 'onboarding_completed_at'])

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
