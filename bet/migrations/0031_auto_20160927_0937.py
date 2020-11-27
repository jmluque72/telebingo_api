# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0030_auto_20160927_0821'),
    ]

    operations = [
        migrations.CreateModel(
            name='WinnerTelebingo',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('type', models.PositiveSmallIntegerField(choices=[(0, 'Linea'), (1, 'Bingo'), (2, 'Billete'), (3, 'Terminaci\xf3n')])),
                ('coupon_extract', models.OneToOneField(related_name='winner', null=True, blank=True, to='bet.TbgCouponExtract')),
                ('ending_extract', models.ForeignKey(related_name='winner_set', blank=True, to='bet.TbgEndingExtract', null=True)),
                ('row_extract', models.OneToOneField(related_name='winner', null=True, blank=True, to='bet.TbgRowExtract')),
            ],
            bases=('bet.winner',),
        ),
        migrations.DeleteModel(
            name='TbgWinnerEnding',
        ),
        migrations.DeleteModel(
            name='TbgWinnerExtract',
        ),
    ]
