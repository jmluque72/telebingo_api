# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0027_auto_20160919_0906'),
    ]

    operations = [
        migrations.CreateModel(
            name='TbgRowExtract',
            fields=[
                ('rowextract_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.RowExtract')),
                ('coupon', models.ForeignKey(to='bet.Coupon')),
            ],
            bases=('bet.rowextract',),
        ),
        migrations.CreateModel(
            name='TbgWinnerExtract',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('extract', models.OneToOneField(related_name='winner_extract', verbose_name='Fila Extracto', to='bet.TbgRowExtract')),
            ],
            bases=('bet.winner',),
        ),
    ]
