# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bet.storage
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0047_auto_20180208_1955'),
    ]

    operations = [
        migrations.AddField(
            model_name='basedraw',
            name='result_to_provider',
            field=models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.save_result_file, null=True, verbose_name='Result to provider', blank=True),
        ),
        migrations.AddField(
            model_name='basedraw',
            name='winner_to_provider',
            field=models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.save_winner_file, null=True, verbose_name='Winner to provider', blank=True),
        ),
        migrations.AddField(
            model_name='tbgendingextract',
            name='chance',
            field=models.CharField(max_length=1, null=True, verbose_name='Chance', blank=True),
        ),
        migrations.AddField(
            model_name='tbgendingextract',
            name='description',
            field=models.CharField(max_length=40, null=True, verbose_name='Descripcion', blank=True),
        ),
        migrations.AddField(
            model_name='tbgendingextract',
            name='ending',
            field=models.BooleanField(default=True, verbose_name='Termination'),
        ),
        migrations.AddField(
            model_name='tbgendingextract',
            name='round',
            field=models.IntegerField(default=1, null=True, verbose_name='Ronda', blank=True),
        ),
        migrations.AlterField(
            model_name='abstractmovement',
            name='state',
            field=models.PositiveIntegerField(default=0, verbose_name='Estado', choices=[(0, 'Pendiente'), (1, 'Acreditado'), (2, 'Cancelado'), (99, 'Temporario')]),
        ),
        migrations.AlterField(
            model_name='lotoresults',
            name='des',
            field=models.OneToOneField(related_name='loto_des', verbose_name='Desquite', to='bet.ResultsSet6Extra'),
        ),
        migrations.AlterField(
            model_name='winnertelebingo',
            name='type',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Linea'), (1, 'Bingo'), (3, 'Extras'), (4, 'Chance Local')]),
        ),
    ]
