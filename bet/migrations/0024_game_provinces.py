# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0023_auto_20160829_0924'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='provinces',
            field=models.ManyToManyField(to='bet.Province', blank=True),
        ),
    ]
