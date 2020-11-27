# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0012_auto_20160630_1221'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bet',
            name='code_trx',
            field=models.CharField(default=uuid.uuid4, unique=True, max_length=80, verbose_name=b'Transaccion'),
        ),
    ]
