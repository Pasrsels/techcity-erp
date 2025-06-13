from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def trim(value):
    return value.strip()

@register.filter
def filter_received(orders):
    return orders.filter(status='received')