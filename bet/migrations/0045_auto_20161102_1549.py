# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0044_auto_20161027_1142'),
    ]

    operations = [
        migrations.CreateModel(
            name='WinnerTelebingoCoupon',
            fields=[
                ('basewinner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseWinner')),
            ],
            bases=('bet.basewinner',),
        ),
        migrations.RemoveField(
            model_name='winnertelebingo',
            name='coupon_extract',
        ),
        migrations.AlterField(
            model_name='couponextract',
            name='results',
            field=models.ForeignKey(related_name='coupon_extract_set', to='bet.PreprintedResults'),
        ),
        migrations.AlterField(
            model_name='tbgcouponextract',
            name='draw',
            field=models.ForeignKey(related_name='coupon_extract_set', to='bet.DrawPreprinted'),
        ),
        migrations.AlterField(
            model_name='winnertelebingo',
            name='type',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Linea'), (1, 'Bingo'), (3, 'Terminaci\xf3n')]),
        ),
        migrations.AddField(
            model_name='winnertelebingocoupon',
            name='extract',
            field=models.OneToOneField(related_name='winner', to='bet.TbgCouponExtract'),
        ),
    ]
