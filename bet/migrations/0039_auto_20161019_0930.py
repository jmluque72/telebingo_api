# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def fill_date_played(apps, schema_editor):
    Bet = apps.get_model('bet', 'Bet')
    for bet in Bet.objects.filter(movement__confirm_date__isnull=False):
        bet.date_played = bet.movement.confirm_date
        bet.save(update_fields=('date_played',))


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0038_auto_20161019_0929'),
    ]

    operations = [
        migrations.RunPython(fill_date_played)
    ]
