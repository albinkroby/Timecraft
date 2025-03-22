import random
import string
from django.utils import timezone
from datetime import timedelta
from mainapp.models import Order
from django.db.models import F
from django.db.models.functions import ACos, Cos, Sin, Radians
import math

def generate_otp(length=6):
    """Generate a random OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))

def assign_delivery_otp(order):
    """Generate and assign OTP to an order"""
    otp = generate_otp()
    order.delivery_otp = otp
    order.otp_created_at = timezone.now()
    order.save(update_fields=['delivery_otp', 'otp_created_at'])
    return otp

def verify_delivery_otp(order, otp):
    """Verify if the provided OTP matches the order's OTP and is valid"""
    # Check if OTP exists and matches
    if not order.delivery_otp or order.delivery_otp != otp:
        return False
    
    # Check if OTP has expired (valid for 24 hours)
    if not order.otp_created_at or timezone.now() > order.otp_created_at + timedelta(hours=24):
        return False
    
    return True

def get_available_delivery_personnel():
    """Get a list of available delivery personnel"""
    from .models import DeliveryProfile
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    delivery_users = User.objects.filter(role='delivery', is_active=True)
    
    available_personnel = []
    for user in delivery_users:
        try:
            profile = DeliveryProfile.objects.get(user=user)
            if profile.is_available():
                available_personnel.append(user)
        except DeliveryProfile.DoesNotExist:
            continue
    
    return available_personnel

def assign_order_to_delivery(order, delivery_person=None):
    """Assign an order to a delivery person"""
    if not delivery_person:
        # Auto-assign to an available delivery person based on location proximity
        available_personnel = get_available_delivery_personnel()
        if not available_personnel:
            return False, "No delivery personnel available"
        
        # Get the shipping address coordinates
        shipping_address = order.address
        if shipping_address and shipping_address.latitude and shipping_address.longitude:
            # Calculate distance between each delivery agent and the shipping address
            from .models import DeliveryProfile
            
            # Filter delivery profiles that have location data
            delivery_profiles = DeliveryProfile.objects.filter(
                user__in=[p.id for p in available_personnel],
                current_latitude__isnull=False,
                current_longitude__isnull=False
            )
            
            if delivery_profiles.exists():
                # Calculate distance using the Haversine formula
                # Convert lat/lon from degrees to radians
                lat1 = math.radians(float(shipping_address.latitude))
                lon1 = math.radians(float(shipping_address.longitude))
                
                closest_agent = None
                min_distance = float('inf')
                
                for profile in delivery_profiles:
                    lat2 = math.radians(float(profile.current_latitude))
                    lon2 = math.radians(float(profile.current_longitude))
                    
                    # Haversine formula
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    distance = 6371 * c  # Earth radius in km
                    
                    if distance < min_distance:
                        min_distance = distance
                        closest_agent = profile.user
                
                if closest_agent:
                    delivery_person = closest_agent
                    # Log the assignment decision
                    print(f"Assigning order {order.order_id} to agent {delivery_person.fullname} " 
                          f"based on proximity ({min_distance:.2f} km)")
                else:
                    # If no agent with location data, fall back to first available
                    delivery_person = available_personnel[0]
            else:
                # If no agent has location data, fall back to first available
                delivery_person = available_personnel[0]
        else:
            # If no shipping address location, use simple assignment
            delivery_person = available_personnel[0]
    
    # Assign the order
    order.assigned_to = delivery_person
    order.status = 'assigned_to_delivery'
    order.save(update_fields=['assigned_to', 'status'])
    
    # Generate OTP for delivery verification
    assign_delivery_otp(order)
    
    # Create delivery history entry
    from .models import DeliveryHistory
    DeliveryHistory.objects.create(
        delivery_person=delivery_person,
        order=order,
        status='assigned'
    )
    
    return True, f"Order assigned to {delivery_person.get_full_name()}" 