# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0006_tcargodetail_id_trx'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserCredit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('expiration', models.DateTimeField()),
                ('accredited', models.BooleanField(default=False)),
                ('agency', models.ForeignKey(to='bet.Agency')),
                ('game', models.ForeignKey(to='bet.Game')),
                ('user', models.ForeignKey(to='bet.UserProfile')),
                ('winner', models.ForeignKey(to='bet.Winner')),
            ],
        ),
    ]
