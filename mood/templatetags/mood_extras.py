from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Allow dict[key] lookups in Django templates: {{ my_dict|get_item:key }}"""
    return dictionary.get(key)
