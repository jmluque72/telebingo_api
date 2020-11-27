# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0009_auto_20160607_1206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chargemovement',
            name='external_url',
            field=models.URLField(null=True, blank=True),
        ),
    ]
