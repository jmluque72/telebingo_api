# -*- coding: utf-8 *-*
from django.conf.urls import patterns

urlpatterns = patterns(
    'simple_webservice.views',
    # Login, logout and session check
    (r'^call/$', 'call'),
)
