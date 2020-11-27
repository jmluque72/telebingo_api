# coding: utf-8

import ssl
import urllib as urllib2
from HTMLParser import HTMLParser
from bet import models


nrosorteo = ''
sorteo = [0, 0, 0, 0, 0]
sorteo0 = []
sorteo0premio1 = []
sorteo0premio2 = []
sorteo0premio3 = []
sorteo1 = []
sorteo1premio1 = []
sorteo1premio2 = []
sorteo1premio3 = []
sorteo2 = []
sorteo2premio1 = []
sorteo2premio2 = []
sorteo2premio3 = []
sorteo3 = []
sorteo3premio1 = []
sorteo3premio2 = []
sorteo3premio3 = []
sorteo4 = []
countextra = 0
premio = [0,0,0]

def isNumber(number):
    try:
        int(number)
        return True
    except:
        return False


def loadPremios(premio1, premio2, premio3, data, isSiempreSale):
    global premio
    if premio[0] == 1 and data != '1Premio':
        if len(premio1) < 3+isSiempreSale:
            if len(premio1) == 0:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]     
                premio1.append(data)
            elif len(premio1) == 1:
                if data[:7] == 'VACANTE':
                    premio1.append(0)
                    premio1.append(premio1[0])
                    premio = [0,0,0]
                else:
                    premio1.append(data)
            elif len(premio1) == 2+isSiempreSale:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]  
                premio1.append(data)
                premio = [0,0,0]
            else:
                premio1.append(data)
    if premio[1] == 1 and data != '2Premio':
        if len(premio2) < 3:
            if len(premio2) == 0:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]     
                premio2.append(data)
            elif len(premio2) == 1:
                if data[:7] == 'VACANTE':
                    premio2.append(0)
                    premio2.append(premio2[0])
                    premio = [0,0,0]
                else:
                    premio2.append(data)
            elif len(premio2) == 2:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]  
                premio2.append(data)
                premio = [0,0,0]
    if premio[2] == 1 and data != '3Premio':
        if len(premio3) < 3:
            if len(premio3) == 0:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]     
                premio3.append(data)
            elif len(premio3) == 1:
                if data[:7] == 'VACANTE':
                    premio3.append(0)
                    premio3.append(premio3[0])
                    premio = [0,0,0]
                else:
                    premio3.append(data)
            elif len(premio3) == 2:
                lendata = len(data) - 2
                data = data[:lendata] + '.' + data[lendata:]  
                premio3.append(data)
                premio = [0,0,0]
    return[premio1, premio2, premio3]


class MyHTMLParser(HTMLParser):
    def handle_data(self, data):

        global nrosorteo
        global sorteo
        global sorteo0
        global premio
        global sorteo1
        global sorteo2
        global sorteo3
        global sorteo4
        global sorteo0premio1
        global sorteo0premio2
        global sorteo0premio3
        global sorteo1premio1
        global sorteo1premio2
        global sorteo1premio3
        global sorteo2premio1
        global sorteo2premio2
        global sorteo2premio3
        global sorteo3premio1
        global sorteo3premio2
        global sorteo3premio3
        global countextra

        data = data.translate(None,'\t\n ')
        data = ''.join(e for e in data if e.isalnum())
        if data[:6] == 'Sorteo':
            i = 6
            while isNumber(data[i]):
                nrosorteo = nrosorteo + data[i]
                i = i + 1
        if data == 'TradicionalPrimerSorteo':
            sorteo =[1, 0, 0, 0, 0]
        if data == 'TradicionalLaSegundadelQuini':
            sorteo =[0, 1, 0, 0, 0]
        if data == 'Revancha':
            sorteo =[0, 0, 1, 0, 0]
        if data == 'SiempreSale':
            sorteo =[0, 0, 0, 1, 0]
        if data == 'PremioExtra':
            sorteo =[0, 0, 0, 0, 1]
        if sorteo[0] == 1:
            if isNumber(data) and int(data) <= 45:
                sorteo0.append(int(data))
            if len(sorteo0) == 6:
                sorteo = [2, 0, 0, 0, 0]
        if sorteo[1] == 1:
            if isNumber(data) and int(data) <= 45:
                sorteo1.append(int(data))
            if len(sorteo1) == 6:
                sorteo = [0, 2, 0, 0, 0]
        if sorteo[2] == 1:
            if isNumber(data) and int(data) <= 45:
                sorteo2.append(int(data))
            if len(sorteo2) == 6:
                sorteo = [0, 0, 2, 0, 0]
        if sorteo[3] == 1:
            if isNumber(data) and int(data) <= 45:
                sorteo3.append(int(data))
            if len(sorteo3) == 6:
                sorteo = [0, 0, 0, 2, 0]
        if sorteo[4] == 1:
            if isNumber(data) and countextra < 18 :
                countextra = countextra + 1
            elif isNumber(data) and countextra == 18:
                if len(sorteo4) == 0:
                    lendata = len(data) - 2
                    data = data[:lendata] + '.' + data[lendata:]  
                    sorteo4.append(data)
                elif len(sorteo4) == 2:
                    lendata = len(data) - 2
                    data = data[:lendata] + '.' + data[lendata:]  
                    sorteo4.append(data)
                else:
                    sorteo4.append(data)
            elif len(sorteo4) == 3:
                sorteo = [0, 0, 0, 0, 2]

        if sorteo[0] == 2:
            if data == '1Premio':
                premio = [1,0,0]
            if data == '2Premio':
                premio = [0,1,0]
            if data == '3Premio':
                premio = [0,0,1]
            aux = loadPremios(sorteo0premio1, sorteo0premio2, sorteo0premio3, data, 0)
            sorteo0premio1 = aux[0]
            sorteo0premio2 = aux[1]
            sorteo0premio3 = aux[2]
        if sorteo[1] == 2:
            if data == '1Premio':
                premio = [1,0,0]
            if data == '2Premio':
                premio = [0,1,0]
            if data == '3Premio':
                premio = [0,0,1]
            aux = loadPremios(sorteo1premio1, sorteo1premio2, sorteo1premio3, data, 0)
            sorteo1premio1 = aux[0]
            sorteo1premio2 = aux[1]
            sorteo1premio3 = aux[2]
        if sorteo[2] == 2:
            if data == '1Premio':
                premio = [1,0,0]
            if data == '2Premio':
                premio = [0,1,0]
            if data == '3Premio':
                premio = [0,0,1]
            aux = loadPremios(sorteo2premio1, sorteo2premio2, sorteo2premio3, data, 0)
            sorteo2premio1 = aux[0]
            sorteo2premio2 = aux[1]
            sorteo2premio3 = aux[2]
        if sorteo[3] == 2:
            if data == '1Premio':
                premio = [1,0,0]
            if data == '2Premio':
                premio = [0,1,0]
            if data == '3Premio':
                premio = [0,0,1]
            aux = loadPremios(sorteo3premio1, sorteo3premio2, sorteo3premio3, data, 1)
            sorteo3premio1 = aux[0]
            sorteo3premio2 = aux[1]
            sorteo3premio3 = aux[2]
            

def run():
    parser = MyHTMLParser()

    urlquini = "http://apps.loteriasantafe.gov.ar:8078/Extractos/paginas/mostrarQuini6.xhtml?display=1"

    context = ssl._create_unverified_context()

    try:
        html_page = urllib2.urlopen(urlquini, context=context)
    except:
        error = True
    parser.feed(str(html_page.read()))

    gamequini6 = models.Game.objects.get(code='quini6')
    quini6 = models.Draw.objects.filter(number=nrosorteo, game=gamequini6)
    
    if quini6.count() == 0:
        return
    else:
        quini6 = quini6.first()
        valid = models.Quini6Results.objects.filter(draw=quini6)
        if valid.count() > 0:
            return

    tra = models.ResultsSet6()
    tra.number1 = sorteo0[0]
    tra.number2 = sorteo0[1]
    tra.number3 = sorteo0[2]
    tra.number4 = sorteo0[3]
    tra.number5 = sorteo0[4]
    tra.number6 = sorteo0[5]
    tra.save()

    tra2 = models.ResultsSet6()
    tra2.number1 = sorteo1[0]
    tra2.number2 = sorteo1[1]
    tra2.number3 = sorteo1[2]
    tra2.number4 = sorteo1[3]
    tra2.number5 = sorteo1[4]
    tra2.number6 = sorteo1[5]
    tra2.save()

    rev = models.ResultsSet6()
    rev.number1 = sorteo2[0]
    rev.number2 = sorteo2[1]
    rev.number3 = sorteo2[2]
    rev.number4 = sorteo2[3]
    rev.number5 = sorteo2[4]
    rev.number6 = sorteo2[5]
    rev.save()

    sie = models.ResultsSet6()
    sie.number1 = sorteo3[0]
    sie.number2 = sorteo3[1]
    sie.number3 = sorteo3[2]
    sie.number4 = sorteo3[3]
    sie.number5 = sorteo3[4]
    sie.number6 = sorteo3[5]
    sie.save()

    ext = models.SingleExtract()
    ext.winners = sorteo4[1]
    prize = models.Prize(type=0, value= sorteo4[2])
    prize.save()
    ext.prize = prize
    ext.save()

    quini6results = models.Quini6Results(draw=quini6, tra=tra, tra2=tra2, rev=rev, sie=sie, ext=ext)
    quini6results.save()

    rowextract = models.RowExtract()
    rowextract.hits = 6
    rowextract.winners = sorteo0premio1[1]
    rowextract.order = 0
    prize = models.Prize(type=0, value= sorteo0premio1[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = tra
    rowextract.save()    
    rowextract = models.RowExtract()
    rowextract.hits = 5
    rowextract.winners = sorteo0premio2[1]
    rowextract.order = 1
    prize = models.Prize(type=0, value= sorteo0premio2[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = tra
    rowextract.save()
    rowextract = models.RowExtract()
    rowextract.hits = 4
    rowextract.winners = sorteo0premio3[1]
    rowextract.order = 2
    prize = models.Prize(type=0, value= sorteo0premio3[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = tra
    rowextract.save()

    rowextract = models.RowExtract()
    rowextract.hits = 6
    rowextract.winners = sorteo1premio1[1]
    rowextract.order = 0
    prize = models.Prize(type=0, value= sorteo1premio1[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = tra2
    rowextract.save()    
    rowextract = models.RowExtract()
    rowextract.hits = 5
    rowextract.winners = sorteo1premio2[1]
    rowextract.order = 1
    prize = models.Prize(type=0, value= sorteo1premio2[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = tra2
    rowextract.save()
    rowextract = models.RowExtract()
    rowextract.hits = 4
    rowextract.winners = sorteo1premio3[1]
    rowextract.order = 2
    prize = models.Prize(type=0, value= sorteo1premio3[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = tra2
    rowextract.save()

    rowextract = models.RowExtract()
    rowextract.hits = 6
    rowextract.winners = sorteo2premio1[1]
    rowextract.order = 0
    prize = models.Prize(type=0, value= sorteo2premio1[2])
    prize.save()
    rowextract.prize = prize
    rowextract.results = rev
    rowextract.save()  

    rowextract = models.RowExtract()
    rowextract.hits = sorteo3premio1[1]
    rowextract.winners = sorteo3premio1[2]
    rowextract.order = 0
    prize = models.Prize(type=0, value= sorteo3premio1[3])
    prize.save()
    rowextract.prize = prize
    rowextract.results = sie
    rowextract.save()    

    # print sorteo0
    # print sorteo0premio1
    # print sorteo0premio2
    # print sorteo0premio3
    # print sorteo1
    # print sorteo1premio1
    # print sorteo1premio2
    # print sorteo1premio3
    # print sorteo2
    # print sorteo2premio1
    # print sorteo3
    # print sorteo3premio1
    # print sorteo4