# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.auth.views import password_reset
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseForbidden
from django.views.generic.base import TemplateView

from django.contrib import admin
admin.autodiscover()

from simple_webservice import webservice_autodiscover
webservice_autodiscover()

from agencia24 import views
from bet.forms import PasswordResetForm, SetPasswordForm

handler404 = views.handler404
handler500 = views.handler500

urlpatterns = patterns('',
    url(r'^ws/', include('simple_webservice.urls', namespace='ws')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'', include('bet.urls', namespace='bet')),

    url(r'^accounts/register/', lambda request: HttpResponseForbidden()),
    url(r'^accounts/password/change/', lambda request: HttpResponseForbidden()),

    url(r'^accounts/password/reset/$', password_reset,
                           {'post_reset_redirect': reverse_lazy('auth_password_reset_done'),
                            'password_reset_form': PasswordResetForm},
                           name='auth_password_reset'),
    url(r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$',
                                views.generic_password_reset_confirm,
                                name='auth_password_reset_confirm'),
    url(r'^accounts/password/reset/complete/agency/$',
                           views.agency_password_reset_complete,
                           name='agency_password_reset_complete'),

    (r'^accounts/', include('registration.backends.default.urls')),

    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^denied/$', TemplateView.as_view(template_name='errors/403custom.html')),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^site_media/media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
            }),
        url(r'^site_media/static/(?P<path>.*)$', 'django.views.static.serve', {
                'document_root': settings.STATIC_ROOT,
            }),
    )
else:
    urlpatterns += patterns('',
        url(r'^site_media/media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
            }),
        url(r'^site_media/static/(?P<path>.*)$', 'django.views.static.serve', {
                'document_root': settings.STATIC_ROOT,
            }),
    )

