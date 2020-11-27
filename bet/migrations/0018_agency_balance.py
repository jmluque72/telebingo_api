# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations
from django.db.models import F, Sum

import bet.modelfields


def update_balance(apps, schema_editor):
    Agency = apps.get_model('bet', 'Agency')
    for agency in Agency.objects.all():
        agency.balance = agency.movement_set.filter(state=0).aggregate(total=Sum(F('amount'))).get('total') or 0
        agency.save(update_fields=('balance',))


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0017_auto_20160818_1510'),
    ]

    operations = [
        migrations.AddField(
            model_name='agency',
            name='balance',
            field=bet.modelfields.RoundedDecimalField(default=0, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.RunPython(update_balance, reverse_code=migrations.RunPython.noop),
    ]
