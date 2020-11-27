# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0014_auto_20160714_0946'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='requested',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, 'No Solicitado'), (1, 'Solicitado'), (2, 'Cargado')]),
        ),
    ]
