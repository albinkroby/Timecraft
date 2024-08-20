from django import template

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