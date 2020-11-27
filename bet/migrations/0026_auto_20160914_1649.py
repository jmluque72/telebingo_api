# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0025_game_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chargemovement',
            name='number',
            field=models.CharField(max_length=40, verbose_name='N\xfamero de transacci\xf3n', db_index=True),
        ),
    ]
