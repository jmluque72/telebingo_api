# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tcargo',
            name='amount',
            field=models.PositiveIntegerField(verbose_name=b'Importe'),
        ),
        migrations.AlterField(
            model_name='tcargo',
            name='pos',
            field=models.IntegerField(null=True, verbose_name=b'idPtoVenta'),
        ),
        migrations.AlterField(
            model_name='tcargo',
            name='wholesaler',
            field=models.IntegerField(null=True, verbose_name=b'idMayorista'),
        ),
    ]
