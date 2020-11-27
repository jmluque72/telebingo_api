# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0045_auto_20161102_1549'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detailbrinco',
            name='number1',
            field=models.PositiveIntegerField(verbose_name='Numero 1', validators=[django.core.validators.MaxValueValidator(39)]),
        ),
        migrations.AlterField(
            model_name='detailbrinco',
            name='number2',
            field=models.PositiveIntegerField(verbose_name='Numero 2', validators=[django.core.validators.MaxValueValidator(39)]),
        ),
        migrations.AlterField(
            model_name='detailbrinco',
            name='number3',
            field=models.PositiveIntegerField(verbose_name='Numero 3', validators=[django.core.validators.MaxValueValidator(39)]),
        ),
        migrations.AlterField(
            model_name='detailbrinco',
            name='number4',
            field=models.PositiveIntegerField(verbose_name='Numero 4', validators=[django.core.validators.MaxValueValidator(39)]),
        ),
        migrations.AlterField(
            model_name='detailbrinco',
            name='number5',
            field=models.PositiveIntegerField(verbose_name='Numero 5', validators=[django.core.validators.MaxValueValidator(39)]),
        ),
        migrations.AlterField(
            model_name='detailbrinco',
            name='number6',
            field=models.PositiveIntegerField(verbose_name='Numero 6', validators=[django.core.validators.MaxValueValidator(39)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='extra1',
            field=models.PositiveIntegerField(verbose_name='Extra 1', validators=[django.core.validators.MaxValueValidator(9)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='extra2',
            field=models.PositiveIntegerField(verbose_name='Extra 2', validators=[django.core.validators.MaxValueValidator(9)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='number1',
            field=models.PositiveIntegerField(verbose_name='Numero 1', validators=[django.core.validators.MaxValueValidator(41)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='number2',
            field=models.PositiveIntegerField(verbose_name='Numero 2', validators=[django.core.validators.MaxValueValidator(41)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='number3',
            field=models.PositiveIntegerField(verbose_name='Numero 3', validators=[django.core.validators.MaxValueValidator(41)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='number4',
            field=models.PositiveIntegerField(verbose_name='Numero 4', validators=[django.core.validators.MaxValueValidator(41)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='number5',
            field=models.PositiveIntegerField(verbose_name='Numero 5', validators=[django.core.validators.MaxValueValidator(41)]),
        ),
        migrations.AlterField(
            model_name='detailloto',
            name='number6',
            field=models.PositiveIntegerField(verbose_name='Numero 6', validators=[django.core.validators.MaxValueValidator(41)]),
        ),
        migrations.AlterField(
            model_name='detailloto5',
            name='number1',
            field=models.PositiveIntegerField(verbose_name='Numero 1', validators=[django.core.validators.MaxValueValidator(36)]),
        ),
        migrations.AlterField(
            model_name='detailloto5',
            name='number2',
            field=models.PositiveIntegerField(verbose_name='Numero 2', validators=[django.core.validators.MaxValueValidator(36)]),
        ),
        migrations.AlterField(
            model_name='detailloto5',
            name='number3',
            field=models.PositiveIntegerField(verbose_name='Numero 3', validators=[django.core.validators.MaxValueValidator(36)]),
        ),
        migrations.AlterField(
            model_name='detailloto5',
            name='number4',
            field=models.PositiveIntegerField(verbose_name='Numero 4', validators=[django.core.validators.MaxValueValidator(36)]),
        ),
        migrations.AlterField(
            model_name='detailloto5',
            name='number5',
            field=models.PositiveIntegerField(verbose_name='Numero 5', validators=[django.core.validators.MaxValueValidator(36)]),
        ),
        migrations.AlterField(
            model_name='detailquiniseis',
            name='number1',
            field=models.PositiveIntegerField(verbose_name='Numero 1', validators=[django.core.validators.MaxValueValidator(45)]),
        ),
        migrations.AlterField(
            model_name='detailquiniseis',
            name='number2',
            field=models.PositiveIntegerField(verbose_name='Numero 2', validators=[django.core.validators.MaxValueValidator(45)]),
        ),
        migrations.AlterField(
            model_name='detailquiniseis',
            name='number3',
            field=models.PositiveIntegerField(verbose_name='Numero 3', validators=[django.core.validators.MaxValueValidator(45)]),
        ),
        migrations.AlterField(
            model_name='detailquiniseis',
            name='number4',
            field=models.PositiveIntegerField(verbose_name='Numero 4', validators=[django.core.validators.MaxValueValidator(45)]),
        ),
        migrations.AlterField(
            model_name='detailquiniseis',
            name='number5',
            field=models.PositiveIntegerField(verbose_name='Numero 5', validators=[django.core.validators.MaxValueValidator(45)]),
        ),
        migrations.AlterField(
            model_name='detailquiniseis',
            name='number6',
            field=models.PositiveIntegerField(verbose_name='Numero 6', validators=[django.core.validators.MaxValueValidator(45)]),
        ),
    ]
