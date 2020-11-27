# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0013_auto_20160630_1221'),
    ]

    operations = [
        migrations.AlterField(
            model_name='setting',
            name='code',
            field=models.SmallIntegerField(unique=True, choices=[(0, 'MAIL extracto enviado'), (1, 'MAIL ticket enviado'), (2, 'PUSH ticket enviado'), (3, 'MAIL apuesta jugada'), (4, 'MAIL notificacion ganador'), (5, 'PUSH notificacion ganador'), (6, 'MAIL retiro aprobado'), (7, 'PUSH retiro aprobado'), (8, 'MAIL solicitud de retiro'), (9, 'MAIL saldo acreditado'), (10, 'PUSH saldo acreditado'), (11, 'MAIL saldo rechazado'), (12, 'PUSH saldo rechazado'), (13, 'MAIL solicitud premio rechazada'), (14, 'PUSH solicitud premio rechazada'), (15, 'MAIL activacion de cuenta'), (16, 'Mantener sesi\xf3n iniciada')]),
        ),
    ]
