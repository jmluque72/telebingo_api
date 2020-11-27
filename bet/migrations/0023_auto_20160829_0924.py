# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0022_auto_20160829_0917'),
    ]

    operations = [
        migrations.AlterField(
            model_name='couponextract',
            name='prize',
            field=models.OneToOneField(to='bet.Prize'),
        )
    ]
