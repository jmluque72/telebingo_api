# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0057_auto_20181128_0834'),
    ]

    operations = [
        migrations.AddField(
            model_name='brincoresults',
            name='tra2',
            field=models.OneToOneField(related_name='brinco_results_2', null=True, blank=True, to='bet.ResultsSet6', verbose_name='Tradicional 2'),
        ),
        migrations.AlterField(
            model_name='messages',
            name='date_entered',
            field=models.DateTimeField(default=datetime.datetime(2019, 5, 15, 7, 2, 31, 940415, tzinfo=utc), blank=True),
        ),
    ]
