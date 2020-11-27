# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0002_auto_20160520_1017'),
    ]

    operations = [
        migrations.CreateModel(
            name='TCargoDetail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('successful', models.BooleanField()),
                ('message', models.CharField(max_length=255)),
                ('trx', models.CharField(unique=True, max_length=20, verbose_name=b'IDUnicoTrx')),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='bet.TCargo', null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='setting',
            name='code',
            field=models.SmallIntegerField(unique=True, choices=[(0, 'MAIL extracto enviado'), (1, 'MAIL ticket enviado'), (2, 'PUSH ticket enviado'), (3, 'MAIL apuesta jugada'), (4, 'MAIL notificacion ganador'), (5, 'PUSH notificacion ganador'), (6, 'MAIL retiro aprobado'), (7, 'PUSH retiro aprobado'), (8, 'MAIL solicitud de retiro'), (9, 'MAIL saldo acreditado'), (10, 'PUSH saldo acreditado'), (11, 'MAIL saldo rechazado'), (12, 'PUSH saldo rechazado'), (13, 'MAIL solicitud premio rechazada'), (14, 'PUSH solicitud premio rechazada'), (15, 'MAIL activacion de cuenta')]),
        ),
    ]
