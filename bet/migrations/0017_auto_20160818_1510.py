# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0016_game_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abstractmovement',
            name='confirm_date',
            field=models.DateTimeField(null=True, verbose_name='Fecha de acreditaci\xf3n', blank=True),
        ),
        migrations.AlterField(
            model_name='betcommissionmov',
            name='draw',
            field=models.ForeignKey(to='bet.BaseDraw'),
        ),
        migrations.AlterField(
            model_name='chargemovement',
            name='number',
            field=models.CharField(max_length=40, verbose_name='N\xfamero de transacci\xf3n'),
        ),
        migrations.AlterField(
            model_name='couponextract',
            name='number',
            field=models.CharField(max_length=40, verbose_name='Nro. Cup\xf3n'),
        ),
        migrations.AlterField(
            model_name='detailcoupons',
            name='ticket',
            field=models.OneToOneField(null=True, blank=True, to='bet.Ticket', verbose_name='Cup\xf3n'),
        ),
        migrations.AlterField(
            model_name='detailquiniela',
            name='location',
            field=models.PositiveIntegerField(verbose_name='Ubicaci\xf3n', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)]),
        ),
        migrations.AlterField(
            model_name='detailquiniela',
            name='number',
            field=models.CharField(max_length=4, verbose_name='Numero', validators=[django.core.validators.RegexValidator('^[0-9]{1,4}$', message='Ingrese un n\xfamero de 1 a 4 cifras')]),
        ),
        migrations.AlterField(
            model_name='drawpreprinted',
            name='coupon_image',
            field=models.ImageField(upload_to=bet.models.picture_coupon, null=True, verbose_name='Cup\xf3n completo', blank=True),
        ),
        migrations.AlterField(
            model_name='drawpreprinted',
            name='coupon_thumbnail',
            field=models.ImageField(upload_to=bet.models.picture_coupon_th, null=True, verbose_name='Cup\xf3n miniatura', blank=True),
        ),
        migrations.AlterField(
            model_name='game',
            name='code',
            field=models.CharField(unique=True, max_length=40, verbose_name='C\xf3digo'),
        ),
        migrations.AlterField(
            model_name='withdrawalmovement',
            name='cbu',
            field=models.CharField(max_length=22, verbose_name='CBU', validators=[django.core.validators.RegexValidator('^[0-9]{22}$', message='N\xfamero de CBU no v\xe1lido.')]),
        ),
    ]
