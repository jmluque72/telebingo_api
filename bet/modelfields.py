# -*- coding: utf-8 -*-
from decimal import Decimal

from django.db import models

class RoundedDecimalField(models.DecimalField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        places = kwargs.get('decimal_places', 2)
        self.q = Decimal(10) ** -places

    def to_python(self, value):
        value = super(self.__class__, self).to_python(value)

        if isinstance(value, Decimal):
            return value.quantize(self.q)
        else:
            return value

"""
import decimal

from django.db import models

class RoundedDecimalField(models.DecimalField):
    ""
    Usage: my_field = RoundedDecimalField("my field", max_digits = 6, decimal_places = 2)
    ""
    def __init__(self, *args, **kwargs):
        super(RoundedDecimalField, self).__init__(*args, **kwargs)
        self.decimal_ctx = decimal.Context(prec = self.max_digits, rounding = decimal.ROUND_HALF_UP)

    def to_python(self, value):
        res = super(RoundedDecimalField, self).to_python(value)

        if res is None:
            return res

        return self.decimal_ctx.create_decimal(res).quantize(decimal.Decimal(10) ** - self.decimal_places)  """