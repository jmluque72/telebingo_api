#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytz

#==============================================================================
# IMPORTS
#==============================================================================

import logging, datetime, functools

from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import models
from importlib import import_module

log = logging.getLogger('simplewebservice')

#==============================================================================
# CONF
#==============================================================================

class InvalidSessionKey(Exception):
    pass

LOADING_SIMPLE_WEBSERVICE = False

REGISTERED_MODELS = {"select": {}, "insert": {}, "delete": {}, "update": {}}

PARSERS = {
    models.DateTimeField:
        lambda x, f: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") if isinstance(x, basestring) else x,
    models.TimeField:
        lambda x, f: datetime.datetime.strptime(x, "%H:%M:%S.%f").time() if isinstance(x, basestring) else x,
    models.DateField:
        lambda x, f: datetime.datetime.strptime(x, "%Y-%m-%d").date() if isinstance(x, basestring) else x,
    models.ForeignKey:
        lambda x, f: f.related_field.model.objects.get(pk=x)
}


DEFAULT_PARSER = lambda x, f: x


#==============================================================================
# FUNCTIONS
#==============================================================================

def webservice_autodiscover():
    """
    Auto-discover INSTALLED_APPS webservices.py modules and fail silently when
    not present. NOTE: autodiscover was inspired/copied from
    django.contrib.admin autodiscover

    """
    global LOADING_SIMPLE_WEBSERVICE
    if LOADING_SIMPLE_WEBSERVICE:
        return
    LOADING_SIMPLE_WEBSERVICE = True

    import imp
    from django.conf import settings

    for app in settings.INSTALLED_APPS:

        try:
            app_path = import_module(app).__path__
        except AttributeError:
            continue

        try:
            imp.find_module('webservices', app_path)
        except ImportError:
            continue

        import_module("%s.webservices" % app)

    LOADING_ADVCONF = False

def user_by_session_id(session_id):
    session = Session.objects.get(pk=session_id)
    user_id = session.get_decoded()['_auth_user_id']
    return User.objects.get(pk=user_id)

def profile_by_session_id(session_id):
    try:
        user = user_by_session_id(session_id)
    except (KeyError, User.DoesNotExist, Session.DoesNotExist):
        raise InvalidSessionKey("Invalid session")
    else:
        return user.profile


def register_model(Model, select=False, insert=False,
                   update=False, delete=False, login=False):
    name = "{}.{}".format(Model._meta.app_label, Model.__name__)
    if select:
        REGISTERED_MODELS["select"][name] = Model, login
    if insert:
        REGISTERED_MODELS["insert"][name] = Model, login
    if delete:
        REGISTERED_MODELS["delete"][name] = Model, login
    if update:
        REGISTERED_MODELS["update"][name] = Model, login
    #print "dddd"

def model_by_op(model_name, op):
    try:
        return REGISTERED_MODELS[op][model_name]
    except:
        raise ValueError("Model '{}' do not allowed for {}".format(model_name, op))


def parse_data(data, mdl):
    fields = dict((f.name, f) for f in mdl._meta.fields)
    parsed = {}
    for k, v in data.items():
        field = fields.get(k)
        if not field:
            field = fields[k.rsplit("__", 1)[0]]
        parsed[k] = PARSERS.get(type(field), DEFAULT_PARSER)(v, field)
    return parsed


def crud_function(op):
    def _inner(fnc):
        @functools.wraps(fnc)
        def _wrap(modelname, *a, **kw):
            Model, login = model_by_op(modelname, op)
            if login:
                user_by_session_id(kw["session"])
            return fnc(Model, modelname, *a, **kw)
        return _wrap
    return _inner



#==============================================================================
# MAIN
#==============================================================================

if __name__ == "__main__":
    print(__doc__)
