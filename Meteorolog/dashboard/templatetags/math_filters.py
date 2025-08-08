from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Şablonda bir değeri başka bir değerle çarpar."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''