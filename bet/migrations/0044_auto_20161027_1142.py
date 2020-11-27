# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0043_auto_20161024_1435'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coupon',
            name='number',
            field=models.CharField(max_length=40, verbose_name='Billete'),
        ),
        migrations.AlterField(
            model_name='couponextract',
            name='number',
            field=models.CharField(max_length=40, verbose_name='Nro. Billete'),
        ),
        migrations.AlterField(
            model_name='detailcoupons',
            name='ticket',
            field=models.OneToOneField(null=True, blank=True, to='bet.Ticket', verbose_name='Billete'),
        ),
        migrations.AlterField(
            model_name='drawpreprinted',
            name='coupon_image',
            field=models.ImageField(upload_to=bet.models.picture_coupon, null=True, verbose_name='Billete completo', blank=True),
        ),
        migrations.AlterField(
            model_name='drawpreprinted',
            name='coupon_thumbnail',
            field=models.ImageField(upload_to=bet.models.picture_coupon_th, null=True, verbose_name='Billete miniatura', blank=True),
        ),
        migrations.AlterField(
            model_name='prize',
            name='type',
            field=models.SmallIntegerField(default=0, choices=[(0, 'Dinero'), (1, 'Otro Billete'), (2, 'Otro Premio')]),
        ),
    ]
