# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0018_agency_balance'),
    ]

    operations = [
        migrations.CreateModel(
            name='Chance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('letter', models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])),
                ('line1', models.CommaSeparatedIntegerField(max_length=22)),
                ('line2', models.CommaSeparatedIntegerField(max_length=22)),
                ('line3', models.CommaSeparatedIntegerField(max_length=22)),
            ],
        ),
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
            ],
        ),
        migrations.RenameField(
            model_name='agency',
            old_name='timestamp',
            new_name='date_joined',
        ),
        migrations.AddField(
            model_name='coupon',
            name='control',
            field=models.CharField(max_length=13, blank=True),
        ),
        migrations.AddField(
            model_name='drawpreprinted',
            name='chances',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Chances',
                                                   validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AddField(
            model_name='drawpreprinted',
            name='rounds',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Rondas',
                                                   validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='fraction_saldo',
            field=models.PositiveIntegerField(default=0, verbose_name='Fracciones disponibles', blank=True),
        ),
        migrations.AlterField(
            model_name='coupon',
            name='fraction_sales',
            field=models.PositiveIntegerField(default=0, verbose_name='Fracciones compradas', blank=True),
        ),
        migrations.AddField(
            model_name='round',
            name='draw',
            field=models.ForeignKey(related_name='round_set', to='bet.DrawPreprinted'),
        ),
        migrations.AddField(
            model_name='chance',
            name='coupon',
            field=models.ForeignKey(related_name='chance_set', to='bet.Coupon'),
        ),
        migrations.AddField(
            model_name='chance',
            name='round',
            field=models.ForeignKey(related_name='chance_set', to='bet.Round'),
        ),
    ]