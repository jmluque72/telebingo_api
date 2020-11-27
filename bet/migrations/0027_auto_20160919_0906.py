# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0026_auto_20160914_1649'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='chance',
            unique_together=set([('coupon', 'round', 'letter')]),
        ),
    ]
