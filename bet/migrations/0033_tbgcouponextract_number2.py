# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0032_drawpreprinted_tbg_state'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tbgcouponextract',
            old_name='number',
            new_name='number_old',
        ),
    ]
