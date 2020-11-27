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

sorteo = ''
numeros = []
extracto = [[],[],[]]
validsorteo = False

class MyHTMLParser(HTMLParser):
    def handle_data(self, data):
        global sorteo
        global numeros
        global extracto
        global validsorteo
        data = data.translate(None,'\t\n ')
        data = ''.join(e for e in data if e.isalnum())
        if data == 'SORTEO':
            validsorteo = True
        if data[:9] == 'UNGANADOR':
            data = '1'
        if validsorteo == True and sorteo == '' and isNumber(data) and len(data) == 4:
            sorteo = int(data) 
        if isNumber(data) and int(data) < 37 and len(numeros) < 5:
            numeros.append(int(data))
        if len(numeros) == 5 and isNumber(data) and int(data) <= 5:
            if data == '5':
                extracto[0].append(data)
            if data == '4':
                extracto[1].append(data)
            if data == '3':
                extracto[2].append(data)
        if len(extracto[0]) < 4 and len(extracto[0]) >= 1 and data != '':
            if data == 'Vacante' or data == 'VACANTE':
                data = 0
            if len(extracto[0]) == 3:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:] 
            extracto[0].append(data)
        if len(extracto[1]) < 4 and len(extracto[1]) >= 1 and data != '':
            if data == 'Vacante' or data == 'VACANTE':
                data = 0
            if len(extracto[1]) == 3:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]
            extracto[1].append(data)
        if len(extracto[2]) < 4 and len(extracto[2]) >= 1 and  data != '':
            if data == 'Vacante' or data == 'VACANTE':
                data = 2
            if data == 'RECUPERAVALORAPUESTASIMPLE':
                data = '2000'
            if len(extracto[2]) == 3:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]                
            extracto[2].append(data)
            

def run():
    parser = MyHTMLParser()
    urlquini = "https://www.loteriadelaciudad.gob.ar/site/juegos/loto-5-plus/"
    context = ssl._create_unverified_context()
    try:
        html_page = urllib2.urlopen(urlquini, context=context)
    except:
        error = True
    parser.feed(str(html_page.read()))

    gameloto5 = models.Game.objects.get(code='loto5')
    loto5 = models.Draw.objects.filter(number=sorteo, game=gameloto5)

    if loto5.count() == 0:
        return
    else:
        loto5 = loto5.first()
        valid = models.Loto5Results.objects.filter(draw=loto5)
        if valid.count() > 0:
            return

    tra = models.ResultsSet5()
    tra.number1 = numeros[0]
    tra.number2 = numeros[1]
    tra.number3 = numeros[2]
    tra.number4 = numeros[3]
    tra.number5 = numeros[4]
    tra.save()

    loto5results = models.Loto5Results(draw=loto5, tra=tra)
    loto5results.save()

    for i in range(0,3):
        rowextract = models.RowExtract()
        rowextract.hits = extracto[i][0]
        rowextract.winners = extracto[i][2]
        rowextract.order = i
        prize = models.Prize(type=0, value= extracto[i][3])
        prize.save()
        rowextract.prize = prize
        rowextract.results = tra
        rowextract.save() 
    print('END')
    # print sorteo
    # print numeros
    # print extracto