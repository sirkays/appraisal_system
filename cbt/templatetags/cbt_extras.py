from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Returns the value of a key from a dictionary.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
