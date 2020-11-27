# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bet.storage
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0048_auto_20180409_1303'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basedraw',
            name='winner_to_provider',
            field=models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.save_winner_file, null=True, verbose_name='Winner to provider', blank=True),
        ),
    ]
