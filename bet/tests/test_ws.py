from datetime import timedelta

from django.contrib.auth.models import User#, Group
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.utils import timezone

from bet import models

class BuyQuini6TestCase(TestCase):
    def setUp(self):
        print 'setUp: init'
        self.game = models.Game.objects.create(code=models.Game.CODE.QUINI6, name="Quiniseis",
                                   type=models.Game.TYPE.NONPRINTED)

        date = timezone.now() + timedelta(hours=3)
        limit = date - timedelta(minutes=30)
        self.draw = models.Draw.objects.create(game=self.game, date_draw=date, date_limit=limit, number="12345")
        self.usercode = 'usuario'
        self.user = User.objects.create_user(username=self.usercode, email='usuario@mail.com', password='top_secret')
        province = models.Province.objects.create(code_name=5)
        agenciero = User.objects.create_user(username='agenciero', email='agenciero@mail.com', password='top_secret')
        agency = models.Agency.objects.create(name="Agencia24", user=agenciero)
        self.userprofile = models.UserProfile.objects.create(user=self.user, agency=agency, saldo=500, dni=12345678, province=province)

        tra = models.ResultsSet6.objects.create(number1=1,number2=2,number3=3,number4=4,number5=5,number6=6)
        tra2 = models.ResultsSet6.objects.create(number1=0,number2=0,number3=0,number4=0,number5=0,number6=0)
        rev = models.ResultsSet6.objects.create(number1=0,number2=0,number3=0,number4=0,number5=0,number6=0)
        sie = models.ResultsSet6.objects.create(number1=0,number2=0,number3=0,number4=0,number5=0,number6=0)

        ext = models.SingleExtract.objects.create(winners=0, prize=0)

        models.RowExtract.objects.create(hits=5, winners=2, prize=10000, order=1,results=tra)

        self.results = models.Quini6Results.objects.create(draw=self.draw, tra=tra, tra2=tra2,
                                                           rev=rev, sie=sie, ext=ext)
        print 'setUp: end'

    def test_winner_tra_5hits(self):
        """Ganador con 5 aciertos identificado correctamente"""
        c = Client()
        datebet = self.draw.date_draw.strftime("%Y-%m-%d")
        c.post('/ws/call/', {
            "name": "buy_quiniseis",
            "id": 5,
            "args": {"usercode":self.usercode, "draw":0,
                     "data": [{"importq": 20, "datebet": datebet, "datebet_show": "",
                               "modot": True, "modor": True, "modos": True,
                               "numbers": ["01", "02", "03", "04", "05", "20"]}]}
        })

        #print c.get(reverse('quini6_winners', args=(self.draw.pk,)))
        print c.get('quini6/{}/winners/'.format(self.draw.pk))
        print models.Winner.objects.all()
        #self.assertEqual(lion.speak(), 'The lion says "roar"')
        #self.assertEqual(cat.speak(), 'The cat says "meow"')
