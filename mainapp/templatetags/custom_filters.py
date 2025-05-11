from django import template
from datetime import timedelta, date
from django.utils import timezone

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    return value * arg

@register.filter(name='div')
def div(value, arg):
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter(name='range')
def range_filter(value):
    return range(value)

@register.filter(name='get_list')
def get_list(dictionary, key):
    return dictionary.getlist(key) if hasattr(dictionary, 'getlist') else dictionary.get(key, [])

@register.filter
def multiplyfloat(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def map_watch(cart_items):
    return [item.watch for item in cart_items]

@register.filter
def subtract(value, arg):
    return value - arg

@register.filter
def days_until_expiry(delivery_date, days_limit):
    """Calculate days remaining until return eligibility expires."""
    if not delivery_date:
        return 0
    
    expiry_date = delivery_date + timedelta(days=int(days_limit))
    today = timezone.now().date()
    
    days_left = (expiry_date - today).days
    return max(0, days_left)

@register.filter
def add_days(value, days):
    """Add a number of days to a date."""
    if not value:
        return None
    
    if isinstance(value, date):
        return value + timedelta(days=int(days))
    
    return value 

@register.filter
def workload_count(user_id):
    """
    Count active orders assigned to a delivery person
    Usage: {{ user_id|workload_count }}
    """
    from mainapp.models import Order  # Import from mainapp instead of deliveryapp
    
    try:
        # Count orders in active delivery statuses
        return Order.objects.filter(
            return_assigned_to_id=user_id,
            status__in=['return_scheduled', 'return_in_transit']
        ).count()
    except Exception:
        return 0 
    
@register.filter(name='mul')
def multiply_onboard(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''