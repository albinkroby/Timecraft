from django import template
from mainapp.models import CartItem

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    return value * arg

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