import random
import string
from django.utils import timezone
from datetime import timedelta
from mainapp.models import Order
from django.db.models import F, Count
from django.db.models.functions import ACos, Cos, Sin, Radians
import math
from collections import defaultdict
from mainapp.utils import verify_pincode, get_zone_from_pincode

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

def get_delivery_personnel_workload(delivery_personnel):
    """
    Get the current workload of each delivery person.
    Returns a dictionary with user_id as key and order count as value.
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get all active orders for delivery personnel
    order_counts = Order.objects.filter(
        assigned_to__in=delivery_personnel,
        status__in=['assigned_to_delivery', 'out_for_delivery']
    ).values('assigned_to').annotate(
        order_count=Count('id')
    ).order_by('order_count')
    
    # Create a dictionary mapping user_id to order count
    workload = {item['assigned_to']: item['order_count'] for item in order_counts}
    
    # Add users with zero orders
    for user in delivery_personnel:
        if user.id not in workload:
            workload[user.id] = 0
    
    return workload

def assign_order_based_on_workload(order, available_personnel):
    """
    Assign order to the delivery person with the lowest workload.
    Returns the chosen delivery person.
    """
    if not available_personnel:
        return None
    
    # Get current workload for each available person
    workload = get_delivery_personnel_workload(available_personnel)
    
    # Sort by workload (ascending)
    sorted_personnel = sorted(available_personnel, key=lambda user: workload[user.id])
    
    # Return the delivery person with the minimum workload
    return sorted_personnel[0] if sorted_personnel else None

def get_delivery_zones():
    """
    Define delivery zones by postal code prefixes.
    Returns a dictionary mapping zone names to postal code patterns.
    This is a placeholder implementation - customize for your actual service areas.
    """
    # Simple zone definition based on postal code prefixes
    # In a real implementation, this might come from a database
    return {
        'north': ['1', '2'],        # Postal codes starting with 1 or 2
        'south': ['3', '4'],        # Postal codes starting with 3 or 4
        'east': ['5', '6', '7'],    # Postal codes starting with 5, 6, or 7
        'west': ['8', '9', '0'],    # Postal codes starting with 8, 9, or 0
    }

def get_zone_for_address(address):
    """
    Determine the zone for a given address based on postal code.
    """
    # Enhanced debugging
    print(f"Analyzing address for zone determination: {address}")
    
    if not address:
        print("No address provided for zone determination")
        return 'Unknown'
    
    # Check for pincode field
    if hasattr(address, 'pincode') and address.pincode:
        pincode = address.pincode
        print(f"Using pincode: {pincode}")
        
        # Verify pincode and get data
        pincode_data = verify_pincode(pincode)
        if pincode_data:
            # Use the pincode data to determine zone
            zone = get_zone_from_pincode(pincode_data)
            print(f"Determined zone {zone} for pincode {pincode}")
            return zone
    
    # Fallback to traditional zone assignment
    print("Falling back to traditional zone assignment")
    zone = 'Other'
    
    # Normalize the zone name to ensure it's one of our standard zones
    if zone not in ['north', 'south', 'east', 'west', 'central', 'Unknown', 'Other']:
        print(f"Converting non-standard zone '{zone}' to 'Other'")
        zone = 'Other'
    
    return zone

def get_preferred_zones_for_personnel(delivery_person):
    """
    Get preferred delivery zones for a delivery person.
    Returns the delivery person's preferred zones or all zones if none are set.
    """
    from .models import DeliveryProfile
    
    try:
        profile = DeliveryProfile.objects.get(user=delivery_person)
        # Use the property accessor which handles the conversion from text to list
        preferred_zones = profile.preferred_zones
        
        # Return all zones if no preference is set
        if not preferred_zones:
            return list(get_delivery_zones().keys())
            
        return preferred_zones
    except DeliveryProfile.DoesNotExist:
        return []

def assign_order_based_on_zone(order, available_personnel):
    """
    Assign order to a delivery person who prefers the zone of the delivery address.
    Returns the chosen delivery person or None if no match is found.
    """
    if not available_personnel or not order.address:
        return None
    
    delivery_zone = get_zone_for_address(order.address)
    if not delivery_zone:
        return None
    
    # Find personnel who prefer this zone
    matching_personnel = []
    for person in available_personnel:
        preferred_zones = get_preferred_zones_for_personnel(person)
        if delivery_zone in preferred_zones:
            matching_personnel.append(person)
    
    if matching_personnel:
        # If multiple matching personnel, choose the one with the lowest workload
        return assign_order_based_on_workload(order, matching_personnel)
    
    return None

def assign_order_to_delivery(order, delivery_person=None):
    """Assign an order to a delivery person"""
    if not delivery_person:
        # Try to auto-assign in this order:
        # 1. Based on location proximity (if location data is available)
        # 2. Based on delivery zone (if location data is not available)
        # 3. Based on workload balancing (if zone matching fails)
        # 4. Fall back to any available delivery person
        
        available_personnel = get_available_delivery_personnel()
        if not available_personnel:
            return False, "No delivery personnel available"
        
        # Get the shipping address coordinates
        shipping_address = order.address
        
        # Priority 1: Location-based assignment
        if shipping_address and shipping_address.latitude and shipping_address.longitude:
            # Check if we have delivery personnel with location data
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
                    
        # If no delivery person assigned yet, try zone-based assignment
        if not delivery_person:
            delivery_person = assign_order_based_on_zone(order, available_personnel)
            if delivery_person:
                print(f"Assigning order {order.order_id} to agent {delivery_person.fullname} based on zone matching")
        
        # If still no delivery person, try workload balancing
        if not delivery_person:
            delivery_person = assign_order_based_on_workload(order, available_personnel)
            if delivery_person:
                print(f"Assigning order {order.order_id} to agent {delivery_person.fullname} based on workload balancing")
        
        # Last resort: use any available delivery person
        if not delivery_person and available_personnel:
            delivery_person = available_personnel[0]
            print(f"Assigning order {order.order_id} to agent {delivery_person.fullname} as fallback")
    
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