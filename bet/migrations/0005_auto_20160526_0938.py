# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0004_auto_20160523_1115'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agency',
            name='province',
            field=models.ForeignKey(related_name='agency_set', verbose_name=b'Provincia', to='bet.Province'),
        ),
    ]
