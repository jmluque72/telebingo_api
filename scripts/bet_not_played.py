import pytz, datetime, logging, random
from datetime import timedelta
import logging

from django.conf import settings
from bet import models, utils
from datetime import datetime
from django.core.files import File
from bet.utils import  send_email_welcome
from django.utils import timezone


TZ = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger('agencia24_default')

def run():

    now = timezone.now()
    try:

        filter = models.Bet.objects.filter().order_by("-id")

        #filter = models.BaseDetail.objects.filter(state=models.BaseDetail.STATE.NOT_PLAYED)
        for bet in filter:
	    print bet.id
            for detail in bet.get_details():
                if detail.state == models.BaseDetail.STATE.NOT_PLAYED:
                    print "entro"
		    dra = None
		    if isinstance(detail, models.DetailQuiniela):
		        dra = detail.group
                    else:
                        dra = detail.draw

                    if dra.date_limit_agency < now:
			print "limit"
                        userp = bet.user
                        if isinstance(detail, models.DetailCoupons):
                            details = [detail]

                        elif isinstance(detail, models.DetailQuiniela):
                            details = models.DetailQuiniela.objects.filter(bet=detail.bet)

                        else:
                            details = [detail]
			print details
                        for detail in details:
                            print "entro 1",detail
			    has_cancel = False
                            if detail.was_canceled:
                                has_cancel = True	
                            detail.state = models.BaseDetail.STATE.NOT_PLAYED
                            detail.was_canceled = True
                            detail.save()

                            #if detail.bet.commission:
                            #    detail.bet.commission.delete()

                            #if isinstance(detail, models.DetailCoupons):
                            #    detail.ticket.real = None
                            #    detail.ticket.save()

                        #if isinstance(detail, models.DetailCoupons):
                        #   models.BetCommissionMov.objects.filter(bet__detailcoupons_set=details).distinct().delete()
                        #elif isinstance(detail, models.DetailQuiniela):
                        #    models.BetCommissionMov.objects.filter(bet__detailquiniela_set=details).distinct().delete()
                        #else:
                        #    models.BetCommissionMov.objects.filter(bet__detail=details).distinct().delete()
                        print has_cancel
			if has_cancel:
			    continue

                        context = {"user": userp.user, "game": bet.game.name}
                        attachs = []
                        user_email = ""
			print "vol a actualizAR",bet.importq
                        userp.saldo = userp.saldo + bet.importq
                        userp.save()
			break
                        #email = send_email_welcome(None, 'emails/bet_not_played', ["jmluque72@gmail.com"], context=context,
                        #               attachments=None, bcc=[user_email], send=True, imgs=None)



    except Exception as e:
        print u' '.join((str(e))).encode('utf-8').strip()

