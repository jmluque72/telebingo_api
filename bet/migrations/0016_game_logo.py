# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0015_auto_20160809_1639'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='logo',
            field=models.ImageField(upload_to=bet.models.game_logo_picture, null=True, verbose_name=b'Logo', blank=True),
        ),
    ]
