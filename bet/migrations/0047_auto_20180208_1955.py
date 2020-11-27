# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0046_auto_20161215_1455'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='date_of_birth',
            field=models.DateField(null=True, verbose_name='Fecha nacimiento', blank=True),
        ),
        migrations.AlterField(
            model_name='withdrawalmovement',
            name='cbu',
            field=models.CharField(max_length=22, verbose_name='CBU'),
        ),
    ]
