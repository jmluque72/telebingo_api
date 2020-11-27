from django import template
register = template.Library()

@register.filter(name='endings')
def ending_filter(value):
    value = str(value)
    return [value[i:] for i in range(1,len(value))]


@register.filter(name='location_prize')
def location_prize(obj, location):
    if int(location) < 0 or int(location) > 20:
        return ''

    return obj.location_prize(int(location))


@register.filter(name='approach_prize')
def approach_prize(obj, location):
    if int(location) < 0 or int(location) > 20:
        return ''

    try:
        return obj.approach_prize(int(location))
    except:
        return ''


@register.filter(name='ending_prize_1')
def ending_prize_1(obj, ending):

    return obj.ending_prize(len(ending), 1)

@register.filter(name='ending_prize_2')
def ending_prize_2(obj, ending):

    return obj.ending_prize(len(ending), 2)

@register.filter(name='ending_prize_3')
def ending_prize_3(obj, ending):

    return obj.ending_prize(len(ending), 3)
