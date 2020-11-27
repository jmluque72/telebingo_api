# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations



class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0020_auto_20160822_1016'),
    ]

    operations = [
        migrations.RenameModel(old_name='TelebingoResults', new_name='TelebingoOldResults'),
        migrations.AlterField(
            model_name='telebingooldresults',
            name='draw',
            field=models.OneToOneField(related_name='telebingoold_results', verbose_name='Sorteo',
                                       to='bet.DrawPreprinted'),
        ),
        migrations.CreateModel(
            name='TelebingoResults',
            fields=[
                ('preprintedresults_ptr',
                 models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False,
                                      to='bet.PreprintedResults')),
                ('bingo', models.OneToOneField(related_name='tbg_bingo_result', to='bet.VariableResultsSet')),
                ('line', models.OneToOneField(related_name='tbg_line_result', to='bet.VariableResultsSet')),
                ('round', models.OneToOneField(related_name='results', to='bet.Round')),
            ],
            bases=('bet.preprintedresults',),
        ),
        migrations.CreateModel(
            name='TbgCouponExtract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.CharField(max_length=40, verbose_name='Nro. Cup\xf3n')),
                ('draw', models.ForeignKey(related_name='winners_coupons_set', to='bet.DrawPreprinted')),
                ('prize', models.OneToOneField(to='bet.Prize')),
            ],
        ),
        migrations.AlterField(
            model_name='couponextract',
            name='prize',
            field=models.OneToOneField(null=True, to='bet.Prize'),
        )
    ]
