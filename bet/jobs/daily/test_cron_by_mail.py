#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.mail import send_mail
from django_extensions.management.jobs import DailyJob

from bet import models

class Job(DailyJob):
    help = "Test cron execution"

    def execute(self):
        return

        try:
            p = models.UserProfile.objects.get(user__username='luciano')
            message = 'Cron executed at {} localtime - {} utctime. '.format(
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            )

            send_mail('Test Cron', message, 'from@example.com',
                [p.user.email], fail_silently=True)
        except models.UserProfile.DoesNotExist:
            pass
