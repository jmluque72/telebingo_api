# -*- coding: utf-8 *-*

import logging

from django.contrib.auth import authenticate, login as login_user, logout as logout_user
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.conf import settings

from simple_webservice import core, serializer

# Get an instance of a logger
logger = logging.getLogger(__name__)


#===============================================================================
# REGISTER CALLS
#===============================================================================

_calls = {}

def register_call(login=False):
    def _wrap(fnc):
        _calls[fnc.__name__] = {"login": login, "function": fnc}
        return fnc
    return _wrap


def execute(request, fncname, args, session_id):
    fnc_data = _calls[fncname]
    if fnc_data["login"]:
        core.user_by_session_id(session_id)

    return fnc_data["function"](request=request, session=session_id, **args)


#===============================================================================
# CALLS
#===============================================================================

@register_call()
def ping(**kwargs):
    return {"ping": True}


@register_call()
def login(username, password, **kwargs):
    user = authenticate(username=username, password=password)
    request = kwargs.get("request")
    if user is not None:
        if user.is_active:
            login_user(request, user)
            session_id = request.session.session_key
            return {"session_id": session_id, "login": True}
    else:
        raise Exception("Invalid credentials")


@register_call(login=True)
def logout(request, session, **kwargs):
    session = Session.objects.get(pk=session)
    session.delete()
    logout_user(request)
    return {"session_id": None, "login": False}


@register_call()
def check_session(session, **kwargs):
    try:
        Session.objects.get(pk=session)
        return {"alive": True}
    except Session.DoesNotExist:
        return {"alive": False}


@register_call()
@core.crud_function("insert")
def insert(Model, modelname, data, **kw):
    mdl = Model.objects.create(**core.parse_data(data, Model))
    mdl.save()
    return {"pk": mdl.pk}


@register_call()
@core.crud_function("update")
def update(Model, modelname, pk, data, **kw):
    Model.objects.filter(pk=pk).update(**core.parse_data(data, Model))
    return {"pk": pk}


@register_call()
@core.crud_function("delete")
def delete(Model, modelname, pk, **kw):
    Model.objects.filter(pk=pk).delete()
    return {"pk": pk}


@register_call()
@core.crud_function("select")
def select(Model, modelname, data, **kw):
    #print "ddd"
    if data:
        query = Model.objects.filter(**core.parse_data(data, Model))
    else:
        query = Model.objects.all()
    return serializer.query_to_dict(query)


#===============================================================================
# MAIN
#===============================================================================

if __name__ == "__main__":
    print(__doc__)
