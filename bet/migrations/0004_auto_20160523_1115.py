# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0003_auto_20160520_1502'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='agencycoupon',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='agencycoupon',
            name='agency',
        ),
        migrations.RemoveField(
            model_name='agencycoupon',
            name='game',
        ),
        migrations.DeleteModel(
            name='AgencyCoupon',
        ),
    ]
