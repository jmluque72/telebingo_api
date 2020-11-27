# -*- coding: utf-8 *-*

import json, traceback, sys

from django.http import HttpResponse, HttpResponseForbidden  # , Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from simple_webservice import calls

reload(sys)
sys.setdefaultencoding('utf8')


@csrf_exempt
@require_POST
def call(request):
    """
    query = {
        "id": arbitrario
        "name": nombre de funcion a ejecutar
        "args": argumen tos de la funcion
        "session": token de la funcion
    }

    return = {
        "id": igual que el id que fue
        "error": bool
        "error_msg": si error es true
        "stacktrace": string
        "response": puede ser none o el resultado
    }

    """
    qid, qname, args = None, None, None
    error, response, error_msg, stacktrace = False, None, "", ""
    try:
        #print request.POST["query"]

        data = None
        if "query" in request.POST:
            data = json.loads(request.POST["query"])
        else:
            data = json.loads(request.body)

        qid = data["id"]
        qname = data["name"]
        qargs = data["args"]
        session_id = data.get("session")
        response = calls.execute(request, qname, qargs, session_id)
    except Exception as err:
        error = True
        error_msg = unicode(err)
        if settings.DEBUG:
            stacktrace = u"".join(
                traceback.format_exception(*sys.exc_info())
            )
            print stacktrace

    if response is not None and 'error' in response:
        data = response
    elif isinstance(response, HttpResponseForbidden):
        return response
    else:
        data = {"id": qid, "error": error, "error_msg": error_msg,
            "stacktrace": stacktrace, "response": response}
    #if settings.DEBUG:
    #    print data
    return HttpResponse(json.dumps(data), content_type='application/json')


#===============================================================================
# MAIN
#===============================================================================

if __name__ == "__main__":
    print(__doc__)
