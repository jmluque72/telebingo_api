# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0049_auto_20180409_1309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lotoresults',
            name='des',
            field=models.OneToOneField(related_name='loto_des', verbose_name='Desquite', to='bet.ResultsSet6Extra'),
        ),
    ]
