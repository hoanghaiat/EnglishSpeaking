from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Dict lookup by variable key: {{ mydict|get_item:mykey }}."""
    if mapping is None:
        return None
    return mapping.get(key)
