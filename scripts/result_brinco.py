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

numbers = []
state = [0,0]
extract = [['','',''],['','',''],['','',''],['','','']]
x = 0
y = 0
c = 0
sorteo = ""
class MyHTMLParser(HTMLParser):

    def handle_data(self, data):
        global state,x,y,c,sorteo
        data = data.translate(None,'\t\n ')
        data = data.translate(None,'.')
        data = data.replace(',','.')
        #print data

        if data[:6] == 'Sorteo':
            i = 6
            while isNumber(data[i]):
                sorteo = sorteo + data[i]
                i = i + 1
        if state[0] == 1:
            if isNumber(data):
                numbers.append(data)
        if state[1] == 1:
            extract[y][x] = data
            x = x + 1
            c = c + 1
            if x > 2:
                x = 0
                y = y + 1
            if c >= 12:
                state = [0,0]
        if data == "Extracciones":
            state = [1,0]
        if data == "Premios$":
            state = [0,1]

def run():
    context = ssl._create_unverified_context()
    url = 'http://apps.loteriasantafe.gov.ar:8078/Extractos/paginas/mostrarBrinco.xhtml?display=1'
    parser = MyHTMLParser()
    error = False
    try:
        html_page = urllib2.urlopen(url, context=context)
    except:
        error = True
    parser.feed(str(html_page.read()))

    print sorteo

    for i in numbers:
        print i

    for n in extract:
        print n

    gamebrinco = models.Game.objects.get(code='brinco')
    brinco = models.Draw.objects.filter(number=sorteo, game=gamebrinco)

    if brinco.count() == 0:
        return
    else:
        brinco = brinco.first()
        valid = models.BrincoResults.objects.filter(draw=brinco)
        if valid.count() > 0:
            return

    tra = models.ResultsSet6()
    tra.number1 = numbers[0]
    tra.number2 = numbers[1]
    tra.number3 = numbers[2]
    tra.number4 = numbers[3]
    tra.number5 = numbers[4]
    tra.number6 = numbers[5]
    tra.save()

    BrincoResults = models.BrincoResults(draw=brinco, tra=tra)
    BrincoResults.save()

    for i in range(0,4):
        rowextract = models.RowExtract()
        rowextract.hits = 6 - i
        if extract[i][1] == 'VACANTE*' or extract[i][1] == 'VACANTE':
            rowextract.winners = 0
        else:
            rowextract.winners = extract[i][1]
        rowextract.order = i
        prize = models.Prize(type=0, value= extract[i][2])
        prize.save()
        rowextract.prize = prize
        rowextract.results = tra
        rowextract.save()


#def saveNumbers(draw, array_numbers):
