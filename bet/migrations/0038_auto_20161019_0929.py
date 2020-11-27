# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0037_auto_20161003_1545'),
    ]

    operations = [
        migrations.AddField(
            model_name='bet',
            name='date_played',
            field=models.DateTimeField(null=True, verbose_name='Fecha jugada'),
        ),
        migrations.DeleteModel(
            name='TelebingoOldResults',
        ),
    ]
