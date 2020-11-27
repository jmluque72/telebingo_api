# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0008_usercredit_bet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usercredit',
            name='winner',
            field=models.OneToOneField(to='bet.Winner'),
        ),
    ]
