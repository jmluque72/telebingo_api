# -*- coding: utf-8 -*-
from datetime import timedelta
from django.db.models import F
from bet import models

def execute():
    filt = dict(
        #game__type=models.Game.TYPE.PREPRINTED,
        #game__code=models.Game.CODE.QUINIELA,
        id=890
    )
    delta = dict(
        days=-1,
    )

    print models.BaseDraw.objects.filter(**filt).update(
        date_draw=F('date_draw')+timedelta(**delta),
        date_limit=F('date_limit')+timedelta(**delta),
        date_limit_agency=F('date_limit_agency')+timedelta(**delta)
    )
    """print models.QuinielaGroup.objects.filter(draws=models.DrawQuiniela.objects.filter(**filt)).update(
        date=F('date')+timedelta(**delta),
        date_draw=F('date_draw')+timedelta(**delta),
        date_limit=F('date_limit')+timedelta(**delta),
        date_limit_agency=F('date_limit_agency')+timedelta(**delta)
    )"""

if __name__ == '__main__':
    execute()
