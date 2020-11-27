from django import template
register = template.Library()

@register.filter(name='negate')
def negate_filter(value):
    if type(value) == str:
        return '-' + value
    return -value
