# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid

def gen_uuid(apps, schema_editor):
    Bet = apps.get_model('bet', 'Bet')
    for row in Bet.objects.all():
        row.code_trx = uuid.uuid4()
        row.save()

class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0011_auto_20160624_1537'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]
