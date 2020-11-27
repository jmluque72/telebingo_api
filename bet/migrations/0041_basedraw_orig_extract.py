# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bet.storage
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0040_auto_20161019_1001'),
    ]

    operations = [
        migrations.AddField(
            model_name='basedraw',
            name='orig_extract',
            field=models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.save_orig_extract_file, null=True, verbose_name='Extracto original', blank=True),
        ),
    ]
