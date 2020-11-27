# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0053_auto_20181108_1431'),
    ]

    operations = [
        migrations.AddField(
            model_name='bet',
            name='won_notify',
            field=models.BooleanField(default=False, verbose_name='Notificado que gano'),
        ),
    ]
