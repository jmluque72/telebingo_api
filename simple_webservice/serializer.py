#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime, decimal, types

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.forms.models import model_to_dict as _model_to_dict



def get_url(field):
    # Sometimes FileField raises ValueError when accessing url attr.
    try:
        return field.url
        """url = field.url
        if url.startswith('/') and settings.SITE_ID:
            return '{}{}'.format(Site.objects.get_current().domain, url)
        return url"""
    except ValueError:
        return None
    except AttributeError:
        return field

TO_SIMPLE_TYPES = {
    datetime.datetime: lambda x: x.isoformat().replace("T", " "),
    datetime.time: lambda x: x.isoformat(),
    datetime.date: lambda x: x.isoformat(),
    bool: lambda x: x,
    int: lambda x: x,
    long: lambda x: x,
    float: lambda x: x,
    str: unicode,
    unicode: lambda x: x,
    decimal.Decimal: lambda x: float(x),
    type(None): lambda x: None,
    complex: lambda x: unicode(x),
    models.FileField: get_url,
    models.ImageField: get_url,
    types.MethodType: lambda x: TO_SIMPLE_TYPES.get(type(x()), DEFAULT_PARSER)(x()),
}

DEFAULT_PARSER = get_url

def to_simple_types(v):
    if v == "" or v is None:
        return None

    return TO_SIMPLE_TYPES.get(type(v), DEFAULT_PARSER)(v)

def query_to_dict(query, *a, **kw):
    return [model_to_dict(obj, *a, **kw) for obj in query]


def model_to_dict(obj, *a, **kw):
    extra_fields = kw.pop('extra_fields', ())

    as_dict = _model_to_dict(obj, *a, **kw)
    as_dict.update({extra: getattr(obj, extra) for extra in extra_fields if hasattr(obj, extra)})

    for k, v in as_dict.items():
        as_dict[k] = to_simple_types(v)

    return as_dict



