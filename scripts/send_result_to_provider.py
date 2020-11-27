import pytz, datetime, logging, random
from datetime import timedelta

from django.conf import settings
from bet import models, utils
from datetime import datetime
from django.core.files import File
from bet.utils import  send_email
from django.utils import timezone


TZ = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger('agencia24_default')

def run():

    now = timezone.now()
    draws = models.DrawPreprinted.objects.filter(date_limit__lte=now,
                                                 state=models.BaseDraw.STATE.ACTIVE)
    for d in draws:

        if d.result_to_provider != None and hasattr(d.result_to_provider, 'url') and  len(d.result_to_provider.url) > 0:
            continue

        try:
            if d.game.code == 'telebingo_sc':
               code = "SCTBVTAS"
            if d.game.code == 'telebingo_minibingo_sc':
               code = "SCMBVTAS"
            if d.game.code == 'telebingo_rebingo_sc':
               code = "SCRBVTAS"

            if d.game.code == 'telebingo_lp':
               code = "LPTBVTAS"
            if d.game.code == 'telebingo_minibingo_lp':
               code = "LPMBVTAS"
            if d.game.code == 'telebingo_rebingo_lp':
               code = "LPRBVTAS"


            print d.game.code
            n = d.number
            name = u'{}{}.txt'.format(code,n.zfill(4))
            fullname = name
            cupons = models.DetailCoupons.objects.filter(coupon__draw=d)
            print cupons, d
            f= open(fullname,"w+")
            countc = 0
            for c in cupons:
                f.write(""  +  c.coupon.number + "\r\n")
                countc = countc + 1

            f.close()
            reopen = open(fullname, "rb")
            django_file = File(reopen)

            d.result_to_provider.save(fullname, django_file, save=True)
            d.save()

            print d.result_to_provider

            context = {"draw_number": d.number, "game_name": d.game.name, "user": {"first_name": "Loteria"}, "countc": countc}
            attachs = [(name,
                d.result_to_provider.read(), 'plain/text')]
            user_email = ""

            # print error

            #email = send_email(None, 'emails/send_bets_email', ["jmluque72@gmail.com", "rodrigo025@gmail.com"], context=context,
            #                   attachments=attachs, bcc=[user_email], send=True, imgs=None)

            if settings.APP_CODE == 'SC':
                email = send_email(None, 'emails/send_bets_email', ["gallegostlb@gmail.com", "edgardovelton@gmail.com", "jmluque72@gmail.com", "rodrigo025@gmail.com"], context=context,
                                attachments=attachs, bcc=[user_email], send=True, imgs=None)
            else:
                email = send_email(None, 'emails/send_bets_email', ["jmluque72@gmail.com", "rodrigo025@gmail.com"], context=context,
                                attachments=attachs, bcc=[user_email], send=True, imgs=None)

        except Exception as e:
            print e
