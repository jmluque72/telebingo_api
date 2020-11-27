from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import password_reset_confirm, password_reset_complete
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from bet.views import is_agenciero


def handler404(request):
    response = render_to_response('errors/404custom.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response


def handler500(request):
    response = render_to_response('errors/500custom.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response


def generic_password_reset_confirm(request, uidb64=None, token=None,
                           template_name='registration/password_reset_confirm.html',
                           token_generator=default_token_generator,
                           set_password_form=SetPasswordForm,
                           post_reset_redirect=None,
                           current_app=None, extra_context=None):

    post_reset_redirect = reverse_lazy('auth_password_reset_complete')
    UserModel = get_user_model()
    try:
        # urlsafe_base64_decode() decodes to bytestring on Python 3
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = UserModel._default_manager.get(pk=uid)
        if is_agenciero(user):
            post_reset_redirect = 'agency_password_reset_complete'
    except (TypeError, ValueError, OverflowError, UserModel().DoesNotExist):
        pass

    return password_reset_confirm(request, uidb64, token, template_name,
                           token_generator, set_password_form, post_reset_redirect,
                           current_app, extra_context)


def agency_password_reset_complete(request,
                            template_name='registration/password_reset_complete.html',
                            current_app=None, extra_context=None):

    extra_context = extra_context or {}
    extra_context.update({'agenciero': True})

    return password_reset_complete(request, template_name, current_app, extra_context)