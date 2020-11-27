# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0005_auto_20160526_0938'),
    ]

    operations = [
        migrations.AddField(
            model_name='tcargodetail',
            name='id_trx',
            field=models.CharField(max_length=20, null=True, verbose_name=b'IDTrx'),
        ),
    ]
