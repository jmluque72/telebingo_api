# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0029_auto_20160926_1420'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='NonprintedWinnerComm',
            new_name='WinnerCommissionMov',
        ),
        migrations.RemoveField(
            model_name='preprintedwinnercomm',
            name='agenmovement_ptr',
        ),
        migrations.RemoveField(
            model_name='preprintedwinnercomm',
            name='draw',
        ),
        migrations.DeleteModel(
            name='PreprintedWinnerComm',
        ),
    ]
