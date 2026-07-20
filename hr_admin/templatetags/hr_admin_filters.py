from django import template
import json as _json

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    """Get a value from a dictionary using a variable key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def get_item(lst, index):
    """Get an item from a list by index."""
    try:
        return lst[index]
    except (IndexError, TypeError, KeyError):
        return None


@register.filter
def sub(value, arg):
    """Subtract arg from value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def mul(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage."""
    try:
        if float(total) == 0:
            return 0
        return int((float(value) / float(total)) * 100)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def tojson(value):
    """Serialize a Python value to a JSON string safe for inline JS."""
    return _json.dumps(value)

