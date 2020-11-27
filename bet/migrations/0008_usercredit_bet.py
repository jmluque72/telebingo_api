# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0007_usercredit'),
    ]

    operations = [
        migrations.AddField(
            model_name='usercredit',
            name='bet',
            field=models.OneToOneField(null=True, blank=True, to='bet.Bet'),
        ),
    ]
