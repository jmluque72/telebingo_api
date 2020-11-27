# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.core.validators
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0052_auto_20180924_0829'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basedraw',
            name='promotion_coupons',
            field=models.PositiveIntegerField(default=99, verbose_name='Promocion', choices=[(99, 'Ninguna'), (0, '2 x 1')]),
        ),
        migrations.AlterField(
            model_name='detailquiniela',
            name='number',
            field=models.CharField(max_length=5, verbose_name='Numero', validators=[django.core.validators.RegexValidator('^[0-9]{1,5}$', message='Ingrese un n\xfamero de 1 a 5 cifras')]),
        ),
        migrations.AlterField(
            model_name='messages',
            name='date_entered',
            field=models.DateTimeField(default=datetime.datetime(2018, 11, 8, 17, 30, 51, 414108, tzinfo=utc), blank=True),
        ),
    ]
