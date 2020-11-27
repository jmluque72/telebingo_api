# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0048_auto_20180612_1244'),
    ]

    operations = [
        migrations.CreateModel(
            name='Messages',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=255, null=True, blank=True)),
                ('users', models.CharField(max_length=2048, null=True, blank=True)),
                ('type', models.IntegerField(default=2, choices=[(0, 'ALL'), (1, 'APOSTARON_ULTIMO_QUINI')])),
                ('date_entered', models.DateTimeField(default=datetime.datetime(2018, 9, 6, 12, 54, 21, 786275, tzinfo=utc), blank=True)),
                ('process', models.IntegerField(default=0, verbose_name='Procesados')),
                ('send_sucess', models.IntegerField(default=0, verbose_name='Succed')),
                ('startprocess', models.BooleanField(default=False)),
                ('finished', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='MessagesSend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('send', models.BooleanField(default=False)),
                ('message', models.ForeignKey(related_name='message_send_message', to='bet.Messages')),
                ('userprofile', models.ForeignKey(related_name='message_send_userprofile', to='bet.UserProfile')),
            ],
        ),
    ]
