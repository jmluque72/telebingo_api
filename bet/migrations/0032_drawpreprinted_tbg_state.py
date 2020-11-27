# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0031_auto_20160927_0937'),
    ]

    operations = [
        migrations.AddField(
            model_name='drawpreprinted',
            name='tbg_state',
            field=models.PositiveIntegerField(default=0, blank=True, verbose_name='Estado (Tbg)', choices=[(0, 'Pendiente'), (1, 'Notificado')]),
        ),
    ]
