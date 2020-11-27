# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0054_auto_20181116_0839'),
    ]

    operations = [
        migrations.AlterField(
            model_name='messages',
            name='date_entered',
            field=models.DateTimeField(default=datetime.datetime(2018, 11, 16, 11, 40, 13, 579965, tzinfo=utc), blank=True),
        ),
    ]
