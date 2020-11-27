# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0055_auto_20181116_0840'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messages',
            name='date_entered',
            field=models.DateTimeField(default=datetime.datetime(2018, 11, 16, 11, 41, 26, 11624, tzinfo=utc), blank=True),
        ),
    ]
