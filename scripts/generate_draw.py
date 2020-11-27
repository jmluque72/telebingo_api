import pytz, datetime, logging, random
from datetime import timedelta

from django.conf import settings
from bet import models, utils

TZ = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger('agencia24_default')

def execute():

    quiniela()
    #load_templates()

    quinimodel("quini6", 11, 5, 4)
    quinimodel("brinco", 10)
    quinimodel("loto", 12, 5, 3)
    quinimodel("loto5", 3)
    quinimodel("loteria")
    quinimodel("totobingo")
    quinimodel("telekino")
    quinimodel("telebingocordobes")


def quiniela():

    # exclude nacional para no generar tantos
    lotteries = models.Quiniela.objects.exclude(pk=3)

    number = 49784
    today = datetime.date.today()
    g = models.Game.objects.get(code="quiniela")

    for i in range(0,30):

        if today.weekday() ==  6: # Domingos no hay sorteos
            today += timedelta(days=1)
            continue

        for lottery in lotteries:

            for _type in range(4):
                if lottery.name == "Santiago del Estero" and\
                                    (today.weekday() != 4 or _type != models.QUINIELA_TYPES.NOCTURNA):
                    continue
                    # Sgo del Estero solo nocturna de los viernes

                draw = models.DrawQuiniela(game=g, quiniela=lottery, type=_type)
                draw.number = str(number)
                draw.state = 0

                number += 1

                ltime = models.LotteryTime.objects.get(quiniela=lottery, type=_type)
                draw.date_draw = datetime.datetime.combine(today, ltime.draw_time)
                draw.date_limit = datetime.datetime.combine(today, ltime.draw_limit)
                draw.date_limit_agency = datetime.datetime.combine(today, ltime.draw_time) - timedelta(minutes=10)

                draw.save()
                print draw

        today += timedelta(days=1)

def load_templates(days=30):

    start_date = datetime.date.today()
    end_date = start_date + timedelta(days=days)


    for single_date in utils.daterange(start_date, end_date):
        weekday = single_date.weekday()
        templates = utils.filter_by_csig(models.QuinielaTemplate, 'weekdays', weekday)

        for template in templates:
            group, created = models.QuinielaGroup.objects.get_or_create(
                province=template.province,
                type=template.type,
                date=single_date
            )

            query = utils.build_date_query('date_draw', single_date)
            draws = models.DrawQuiniela.objects.filter(**query)

            #if weekday == 4 and template.type == 3:
            #    import pdb; pdb.set_trace()

            # template.draws es una lista de la forma [quiniela0,type0,quiniela1,type1,......]
            for quiniela, _type in utils.pairwise(eval(template.draws)):
                try:
                    draw = draws.get(quiniela=quiniela,type=_type)
                except models.DrawQuiniela.DoesNotExist:
                    continue

                group.draws.add(draw)

            group.save()

def quinimodel(code, price=18, price2=None, price3=None):
    
    today = datetime.date.today()
    g = models.Game.objects.get(code=code)

    for i in range(0,100):
        date_draw = datetime.datetime.combine(today, datetime.time(21,0,0, tzinfo=TZ))

        if  today.weekday() != 2 and today.weekday() !=  6:
            today = today + timedelta(days=1)
            continue

        if code in ['loteria', 'telekino', 'telebingocordobes', 'totobingo']:
            model = models.DrawPreprinted
        else:
            model = models.Draw

        draws = model.objects.filter(game=g, date_draw=date_draw)
        if draws.count() == 0:

            draw = model(game=g, state=0, number=str(23019 + i), date_draw=date_draw)
            draw.date_limit = draw.date_draw - timedelta(hours=2)
            draw.date_limit_agency = draw.date_draw - timedelta(minutes=10)
            if code == 'quini6':
                draw.prize_text = "$ 32.000.000"
            if code == 'brinco':
                draw.prize_text = "$ 60.000.000"
            if code == 'loto':
                draw.prize_text = "$ 14.000.000"
            if code == 'loto5':
                draw.prize_text = "$ 90.000.000"
            if code == 'loteria':
                draw.prize_text = "$ 32.000.000"
            if code == 'totobingo':
                draw.prize_text = "$ 32.000.000"
            if code == 'telekino':
                draw.prize_text = "$ 40.000.000"
            if code == 'telebingocordobes':
                draw.prize_text = "$ 100.000.000"
        
            draw.price =  price
            draw.price2 = price2
            draw.price3 = price3
            draw.save()

        """
            if g.type == models.Game.TYPE.PREPRINTED:
                for i in range(0,20):
                    if code == models.Game.CODE.LOTERIA:
                        coupon = models.LoteriaCoupon(draw=draw)
                        coupon.progresion = random.randint(0,11)
                        saldo = 3
                    else:
                        coupon = models.Coupon(draw=draw)
                        saldo = 1

                    coupon.fraction_saldo = saldo
                    coupon.fraction_sales = saldo
                    coupon.number = str(43884 + draw.pk)

                    coupon.save()"""

        today = today + timedelta(days=1)

if __name__ == '__main__':
    execute()
