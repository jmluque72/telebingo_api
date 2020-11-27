# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0028_tbgrowextract_tbgwinnerextract'),
    ]

    operations = [
        migrations.CreateModel(
            name='TbgEndingExtract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ending', models.CharField(max_length='3', verbose_name='Terminaci\xf3n')),
                ('draw', models.ForeignKey(related_name='winners_ending_set', to='bet.DrawPreprinted')),
                ('prize', models.OneToOneField(to='bet.Prize')),
            ],
        ),
        migrations.CreateModel(
            name='TbgWinnerEnding',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('extract', models.ForeignKey(related_name='winner_set', to='bet.TbgEndingExtract')),
            ],
            bases=('bet.winner',),
        ),
        migrations.AlterField(
            model_name='tbgcouponextract',
            name='number',
            field=models.CharField(max_length=40, verbose_name='DNI'),
        ),
    ]
