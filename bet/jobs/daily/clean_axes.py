#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.timezone import timedelta, now

from django_extensions.management.jobs import DailyJob
from axes.models import AccessAttempt, AccessLog

class Job(DailyJob):
    help = "Delete old AccessAttemps and their corresponding AccessLogs."

    def execute(self):
        cooloff_time = getattr(settings, 'AXES_COOLOFF_TIME', None)
        if isinstance(cooloff_time, int) or isinstance(cooloff_time, float):
            cooloff_time = timedelta(hours=cooloff_time)

        AccessAttempt.objects.filter(attempt_time__lte=now()-cooloff_time).delete()
        AccessLog.objects.filter(attempt_time__lte=now()-cooloff_time).delete()
