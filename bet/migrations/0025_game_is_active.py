# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0024_game_provinces'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
