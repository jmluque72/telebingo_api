# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0036_auto_20160930_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='basedetail',
            name='was_canceled',
            field=models.BooleanField(default=False, verbose_name='Fue cancelada'),
        )
    ]
