# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0041_basedraw_orig_extract'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tbgendingextract',
            name='draw',
        ),
        migrations.RemoveField(
            model_name='tbgendingextract',
            name='ending',
        ),
        migrations.AddField(
            model_name='tbgendingextract',
            name='coupon',
            field=models.ForeignKey(to='bet.Coupon', null=True),
        ),
    ]
