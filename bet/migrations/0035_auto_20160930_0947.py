# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def char_to_int(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    TbgCouponExtract = apps.get_model("bet", "TbgCouponExtract")
    for extract in TbgCouponExtract.objects.all():
        try:
            extract.number = int(extract.number_old)
        except ValueError:
            extract.number = 0
        extract.save()

def int_to_char(apps, schema_editor):
    TbgCouponExtract = apps.get_model("bet", "TbgCouponExtract")
    for extract in TbgCouponExtract.objects.all():
        extract.number_old = str(extract.number)
        extract.save()


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0034_auto_20160930_0947'),
    ]

    operations = [
        migrations.RunPython(char_to_int, int_to_char),
        migrations.RemoveField(model_name='tbgcouponextract', name='number_old')
    ]
