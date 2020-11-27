# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0035_auto_20160930_0947'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tbgendingextract',
            name='draw',
            field=models.OneToOneField(related_name='winner_ending', to='bet.DrawPreprinted'),
        ),
    ]
