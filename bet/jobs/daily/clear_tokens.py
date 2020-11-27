#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from oauth2_provider.models import AccessToken, Grant, RefreshToken
from oauth2_provider.settings import oauth2_settings
from django_extensions.management.jobs import DailyJob

from bet import models


class Job(DailyJob):
    help = "Delete expired RefreshTokens and their corresponding AccessTokens."
    # Based on oauth2_provider.management.commands.cleartokens

    def execute(self):

        now = timezone.now()
        refresh_expire_at = None

        REFRESH_TOKEN_EXPIRE_SECONDS = oauth2_settings.REFRESH_TOKEN_EXPIRE_SECONDS
        if REFRESH_TOKEN_EXPIRE_SECONDS:
            if not isinstance(REFRESH_TOKEN_EXPIRE_SECONDS, timezone.timedelta):
                try:
                    REFRESH_TOKEN_EXPIRE_SECONDS = timezone.timedelta(seconds=REFRESH_TOKEN_EXPIRE_SECONDS)
                except TypeError:
                    e = "REFRESH_TOKEN_EXPIRE_SECONDS must be either a timedelta or seconds"
                    raise ImproperlyConfigured(e)
            refresh_expire_at = now - REFRESH_TOKEN_EXPIRE_SECONDS

        keep_logged = models.UserSetting.objects.filter(
            setting__code=models.USER_SETTINGS.STAY_LOGGED_IN,
            value=True).values_list('profile__user', flat=True)
        with transaction.atomic():
            if refresh_expire_at:
                RefreshToken.objects.filter(access_token__expires__lt=refresh_expire_at)\
                                            .exclude(user__in=keep_logged).delete()
            AccessToken.objects.filter(refresh_token__isnull=True, expires__lt=now)\
                                       .exclude(user__in=keep_logged).delete()
            Grant.objects.filter(expires__lt=now).exclude(user__in=keep_logged).delete()
