#!/usr/bin/env python
# -*- coding: utf-8 -*-

from simple_webservice.core import webservice_autodiscover, register_model
from simple_webservice.core import InvalidSessionKey
from simple_webservice.calls import register_call
from simple_webservice.serializer import query_to_dict, model_to_dict, to_simple_types

