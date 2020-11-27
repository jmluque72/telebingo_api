# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0033_tbgcouponextract_number2'),
    ]

    operations = [
        migrations.AddField(
            model_name='tbgcouponextract',
            name='number',
            field=models.PositiveIntegerField(default=1, verbose_name='DNI'),
            preserve_default=False,
        ),
    ]
