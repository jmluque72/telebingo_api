# coding: utf-8

import ssl
import urllib as urllib2
from HTMLParser import HTMLParser
from bet import models

def isNumber(number):
    try:
        int(number)
        return True
    except:
        return False

validsorteo = False
array_info = []
sorteo = ''

class MyHTMLParser(HTMLParser):
    def handle_data(self, data):

        global validsorteo
        global array_info
        global sorteo

        data = data.translate(None,'\t\n ')
        data = ''.join(e for e in data if e.isalnum() or e == '+')
        if data == 'SORTEO':
            validsorteo = True
        if validsorteo == True and sorteo == '' and isNumber(data) and len(data) == 4:
            sorteo = int(data)
        if data == 'Vacante' or data == 'VACANTE':
            data = '0'
        if data[:9] == 'UNGANADOR':
            data = '1'
        if data == 'JACKPOT6+2JACK':
            data = '6 + 2 Jack'
        if data == '6+1JACK':
            data = '6 + 1 Jack'
        if data == 'Loto6':
            data = '6'
        if data == '5+2':
            data = '5 + 2 Jack'
        if data == '5+1':
            data = '5 + 1 Jack'
        if data == '4+2':
            data = '4 + 2 Jack'
        if data == '4+1':
            data = '4 + 1 Jack'
        if data == '3+2':
            data = '3 + 2 Jack'
        if data == '3+1':
            data = '3 + 1 Jack'
        if data == 'Desquite6':
            data = '6'
        if len(data) < 15 and len(data) > 0 and validsorteo == True and data != 'PremiosFijos':
            array_info.append(data)
            # print data

def run():

    global array_info
    global sorteo

    parser = MyHTMLParser()

    urlquini = "https://www.loteriadelaciudad.gob.ar/site/juegos/loto-plus/"

    context = ssl._create_unverified_context()

    try:
        html_page = urllib2.urlopen(urlquini, context=context)
    except:
        error = True
    parser.feed(str(html_page.read()))


    gameloto = models.Game.objects.get(code='loto')
    loto = models.Draw.objects.filter(number=sorteo, game=gameloto)

    if loto.count() == 0:
        return
    else:
        loto = loto.first()
        valid = models.LotoResults.objects.filter(draw=loto)
        if valid.count() > 0:
            return

    tra = models.ResultsSet6Extra()
    tra.number1 = int(array_info[2])
    tra.number2 = int(array_info[3])
    tra.number3 = int(array_info[4])
    tra.number4 = int(array_info[5])
    tra.number5 = int(array_info[6])
    tra.number6 = int(array_info[7])
    tra.extra1 = int(array_info[8])
    tra.extra2 = int(array_info[9])
    tra.save()

    des = models.ResultsSet6Extra()
    des.number1 = int(array_info[54])
    des.number2 = int(array_info[55])
    des.number3 = int(array_info[56])
    des.number4 = int(array_info[57])
    des.number5 = int(array_info[58])
    des.number6 = int(array_info[59])
    des.extra1 = int(array_info[60])
    des.extra2 = int(array_info[61])
    des.save()

    sos = models.ResultsSet6()
    sos.number1 = int(array_info[79])
    sos.number2 = int(array_info[80])
    sos.number3 = int(array_info[81])
    sos.number4 = int(array_info[82])
    sos.number5 = int(array_info[83])
    sos.number6 = int(array_info[84])
    sos.save()

    lotoresults = models.LotoResults(draw=loto, tra=tra, des=des, sos=sos)
    lotoresults.save()

    for i in range(0,12):
        rowextract = models.RowExtract()
        rowextract.hits = array_info[14+(i*3)]
        rowextract.winners = array_info[15+(i*3)]
        rowextract.order = i
        platica = array_info[16+(i*3)]
        if i < 3:
            lendata = len(platica) - 2
            platica = platica[:lendata] + '.' + platica[lendata:]
        prize = models.Prize(type=0, value= platica)
        prize.save()
        rowextract.prize = prize
        rowextract.results = tra
        rowextract.save()

    for j in range(0,3):
        print(j)
        rowextract = models.RowExtract()
        rowextract.hits = array_info[66+(j*3)]
        rowextract.winners = array_info[67+(j*3)]
        rowextract.order = j
        platica = array_info[68+(j*3)]
        lendata = len(platica) - 2
        platica = platica[:lendata] + '.' + platica[lendata:]
        prize = models.Prize(type=0, value= platica )
        prize.save()
        rowextract.prize = prize
        rowextract.results = des
        rowextract.save()

    rowextract = models.RowExtract()
    rowextract.hits = array_info[93]
    rowextract.winners = array_info[94]
    rowextract.order = 0
    platica = array_info[95]
    lendata = len(platica) - 2
    platica = platica[:lendata] + '.' + platica[lendata:]
    prize = models.Prize(type=0, value= platica)
    prize.save()
    rowextract.prize = prize
    rowextract.results = sos
    rowextract.save()

    print('END')
