# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0042_auto_20161024_0952'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tbgendingextract',
            name='coupon',
            field=models.OneToOneField(null=True, to='bet.Coupon'),
        ),
        migrations.AlterField(
            model_name='winnertelebingo',
            name='ending_extract',
            field=models.OneToOneField(related_name='winner', null=True, blank=True, to='bet.TbgEndingExtract'),
        ),
    ]
