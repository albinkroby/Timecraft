from django import template
from django.db.models import Count

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key
    Usage: {{ dictionary|get_item:key }}
    """
    if not dictionary:
        return None
    
    try:
        return dictionary.get(key)
    except (KeyError, AttributeError, TypeError):
        return None

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