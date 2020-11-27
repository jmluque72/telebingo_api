# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bet.modelfields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0019_auto_20160819_1416'),
    ]

    operations = [
        migrations.AlterField(
            model_name='betcommission',
            name='value',
            field=bet.modelfields.RoundedDecimalField(default=12.0, verbose_name='valor', max_digits=5, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)]),
        ),
    ]
