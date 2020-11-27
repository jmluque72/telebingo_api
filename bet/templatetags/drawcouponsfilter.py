#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django import template

from bet import models
from bet.views import is_admin

register = template.Library()

@register.filter
def has_coupons(draw, user):

    if draw.game.type != models.Game.TYPE.PREPRINTED:
        return False
    if is_admin(user):
        return draw.parent.coupon_set.exists()
    else:
        return draw.parent.coupon_set.filter(agency__user=user).exists()
