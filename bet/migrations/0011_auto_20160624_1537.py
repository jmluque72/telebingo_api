# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, time, timedelta

from django.db import models, migrations


def set_draw_limit_agency(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    LotteryTime = apps.get_model("bet", "LotteryTime")
    for t in LotteryTime.objects.all():
        t.draw_limit_agency = (datetime.combine(datetime.today(), t.draw_time) - timedelta(minutes=15)).time()
        t.save()

class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0010_auto_20160621_0859'),
    ]

    operations = [
        migrations.AddField(
            model_name='lotterytime',
            name='draw_limit_agency',
            field=models.TimeField(default=time(0, 0), verbose_name=b'Cierre agencia'),
            preserve_default=False,
        ),
        migrations.RunPython(set_draw_limit_agency),
        migrations.AlterField(
            model_name='lotterytime',
            name='draw_limit',
            field=models.TimeField(verbose_name=b'Cierre usuario'),
        ),
    ]
