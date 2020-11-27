import pytz, datetime, logging, random

from datetime import timedelta
from django.conf import settings
from bet import models, utils
from datetime import datetime
from django.core.files import File
from bet.utils import send_email
from django.utils import timezone

TZ = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger('agencia24_default')


def run():
    now = timezone.now()
    draws = models.DrawPreprinted.objects.filter(date_limit__lte=now,
                                                 state=models.BaseDraw.STATE.EXTRACT)

    print draws, now
    for d in draws:

        print d.winner_to_provider

        if d.winner_to_provider != None and hasattr(d.winner_to_provider, 'url') and len(d.winner_to_provider.url) > 0:
            continue

        print "*************"

        win = models.WinnerTelebingo.objects.filter(draw=d)
        print win
        try:
            print d

            juego = ""
            if d.game.code == 'telebingo_sc':
                juego = "TB"
                code = "SCTBWNR"
            if d.game.code == 'telebingo_minibingo_sc':
                juego = "MB"
                code = "SCMBWNR"
            if d.game.code == 'telebingo_rebingo_sc':
                juego = "RB"
                code = "SCRBWNR"

            if d.game.code == 'telebingo_lp':
                juego = "TB"
                code = "LPTBVTAS"
            if d.game.code == 'telebingo_minibingo_lp':
                juego = "MB"
                code = "LPMBVTAS"
            if d.game.code == 'telebingo_rebingo_lp':
                juego = "RB"
                code = "LPRBVTAS"

            n = d.number
            name = u'{}{}.txt'.format(code, n.zfill(4))
            fullname = name
            cupons = models.DetailCoupons.objects.filter(coupon__draw=d)

            print cupons, d
            f = open(fullname, "w+")

            for c in win:
                #wtc = models.WinnerTelebingoCoupon.objects.filter(winner = c)
                f.write(juego + ";")
                f.write(d.number + ";")
                if c.type == 0:
                    f.write("Linea" + ";")
                if c.type == 1:
                    f.write("Bingo" + ";")
                f.write(str(d.date_draw) + ";")
                date = d.date_draw + timedelta(days=15)
                f.write(str(date) + ";")
                f.write(c.row_extract.coupon.control + ";")
                f.write(str(c.bet.user.dni) + ";")
                f.write(c.bet.user.user.first_name + " " + c.bet.user.user.last_name + ";")
                f.write(c.bet.user.user.email + ";")
                f.write("\n")

            f.close()
            reopen = open(fullname, "rb")
            django_file = File(reopen)

            d.winner_to_provider.save(fullname, django_file, save=True)
            d.save()

            print d.winner_to_provider

            context = {"draw_number": d.number, "game_name": d.game.name, "user": {"first_name": "Loteria"}}
            attachs = [(name,
                        d.winner_to_provider.read(), 'plain/text')]

            user_email = ""


            if settings.APP_CODE == 'SC':
                email = send_email(None, 'emails/send_winners_email', ["jmluque72@gmail.com", "rodrigo025@gmail.com"], context=context,
                               attachments=attachs, bcc=[user_email], send=True, imgs=None)
            else:
                 email = send_email(None, 'emails/send_winners_email', ["jmluque72@gmail.com", "rodrigo025@gmail.com"], context=context,
                               attachments=attachs, bcc=[user_email], send=True, imgs=None)




            d.winner_to_provider = None
            d.save()

        except Exception as e:
            print e
