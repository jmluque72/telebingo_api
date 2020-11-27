#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.template import Library

register = Library()

@register.filter(name='order_by')
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)
