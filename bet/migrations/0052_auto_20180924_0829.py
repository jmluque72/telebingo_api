# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0051_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='basedraw',
            name='promotion_coupons',
            field=models.PositiveIntegerField(default=0, verbose_name='Promocion', choices=[(0, '2 x 1')]),
        ),
        migrations.AlterField(
            model_name='messages',
            name='date_entered',
            field=models.DateTimeField(default=datetime.datetime(2018, 9, 24, 11, 29, 28, 207105, tzinfo=utc), blank=True),
        ),
    ]
