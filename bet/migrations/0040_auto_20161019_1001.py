# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0039_auto_20161019_0930'),
    ]

    operations = [
        migrations.AlterField(
            model_name='betcommissionmov',
            name='bet',
            field=models.OneToOneField(related_name='commission', to='bet.Bet'),
        ),
    ]
