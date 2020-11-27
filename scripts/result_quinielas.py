# coding: utf-8

import ssl
import urllib as urllib2
from HTMLParser import HTMLParser
from bet import models

numbers1 = []
numbers2 = []
numbers3 = []
numbers4 = []
numbers5 = []
numbers6 = []
sorteo = ''
loteria = ''

def isNumber(number):
    try:
        int(number)
        return True
    except:
        return False

class MyHTMLParser(HTMLParser):
    def handle_data(self, data):
        global loteria
        global sorteo

        data = data.translate(None,'\t\n ')
        if data[:6] == 'Sorteo':
            i = 6
            while isNumber(data[i]):
                sorteo = sorteo + data[i]
                i = i + 1
        if data[:3] == '1-L':
            loteria = '1'
        if data[:3] == '2-L':
            loteria = '2'
        if data[:3] == '3-L':
            loteria = '3'
        if data[:3] == '4-L':
            loteria = '4'
        if data[:3] == '5-L':
            loteria = '5'
        if data[:3] == '6-L':
            loteria = '6'
        if len(data) >= 3:
            try:
                if 0 <= int(data) <= 99999:
                    if loteria == '1':
                        numbers1.append(data)
                    if loteria == '2':
                        numbers2.append(data)
                    if loteria == '3':
                        numbers3.append(data)
                    if loteria == '4':
                        i = len(numbers4)
                        if len(numbers3[i]) == 4:
                            data = numbers3[i][0] + data
                        else:
                            data = numbers3[i][1] + data
                        numbers4.append(data)
                    if loteria == '5':
                        numbers5.append(data)
                    if loteria == '6':
                        numbers6.append(data)
            except:
                pass

def run():

    global numbers1
    global numbers2
    global numbers3
    global numbers4
    global numbers5
    global numbers6
    global sorteo
    error = False

    parser = MyHTMLParser()

    urlprimero = "http://apps.loteriasantafe.gov.ar:8078/Extractos/paginas/mostrarQuinielaElPrimero.xhtml?display=1"
    urlmatutina = "http://apps.loteriasantafe.gov.ar:8078/Extractos/paginas/mostrarQuinielaMatutina.xhtml?display=1"
    urlvespertina = "http://apps.loteriasantafe.gov.ar:8078/Extractos/paginas/mostrarQuinielaVespertina.xhtml?display=1"
    urlnoctura = "http://apps.loteriasantafe.gov.ar:8078/Extractos/paginas/mostrarQuinielaNocturna.xhtml?display=1"

    context = ssl._create_unverified_context()
    urls = [urlprimero, urlmatutina, urlvespertina, urlnoctura]

    tipo = 0

    for url in urls:
        numbers1 = []
        numbers2 = []
        numbers3 = []
        numbers4 = []
        numbers5 = []
        numbers6 = []
        sorteo = ''
        try:
            html_page = urllib2.urlopen(url, context=context)
        except:
            error = True
        parser.feed(str(html_page.read()))

        # print(sorteo)
        # print(numbers1)
        # print(numbers2)
        # print(numbers3)
        # print(numbers4)
        # print(numbers5)
        # print(numbers6)

        if ((len(numbers1) != 20 and len(numbers1) !=0) or (len(numbers2) != 20 and len(numbers2) !=0) \
                or (len(numbers3) != 20 and len(numbers3) !=0) or (len(numbers4) != 20 and len(numbers4) !=0) \
                or (len(numbers5) != 20 and len(numbers5) !=0)  or (len(numbers6) != 20 and len(numbers6)!=0)):
            error = True

        if not error:
            group = models.QuinielaGroup.objects.filter(number=sorteo, type=tipo)
            tipo = tipo + 1
            if group.count() != 0:
                draws = group.first().draws.all()
                for draw in draws:
                    print(draw)
                    resultset = models.QuinielaResults.objects.filter(draw=draw).first()
                    if resultset is None:
                        if draw.quiniela.code == 1 and len(numbers1) == 20:
                            print('entro1')
                            saveNumbers(draw, numbers1)
                        if draw.quiniela.code == 2 and len(numbers2) == 20:
                            print('entro2')
                            saveNumbers(draw, numbers2)
                        if draw.quiniela.code == 3 and len(numbers3) == 20:
                            print('entro3')
                            saveNumbers(draw, numbers3)
                        if draw.quiniela.code == 4 and len(numbers4) == 20:
                            print('entro4')
                            saveNumbers(draw, numbers4)
                        if draw.quiniela.code == 5 and len(numbers5) == 20:
                            print('entro5')
                            saveNumbers(draw, numbers5)
                        if draw.quiniela.code == 6 and len(numbers6) == 20:
                            print('entro6')
                            saveNumbers(draw, numbers6)


def saveNumbers(draw, array_numbers):

    resultset20 = models.ResultsSet20()
    resultset20.number1 = array_numbers[0]
    resultset20.number2 = array_numbers[1]
    resultset20.number3 = array_numbers[2]
    resultset20.number4 = array_numbers[3]
    resultset20.number5 = array_numbers[4]
    resultset20.number6 = array_numbers[5]
    resultset20.number7 = array_numbers[6]
    resultset20.number8 = array_numbers[7]
    resultset20.number9 = array_numbers[8]
    resultset20.number10 = array_numbers[9]
    resultset20.number11 = array_numbers[10]
    resultset20.number12 = array_numbers[11]
    resultset20.number13 = array_numbers[12]
    resultset20.number14 = array_numbers[13]
    resultset20.number15 = array_numbers[14]
    resultset20.number16 = array_numbers[15]
    resultset20.number17 = array_numbers[16]
    resultset20.number18 = array_numbers[17]
    resultset20.number19 = array_numbers[18]
    resultset20.number20 = array_numbers[19]
    resultset20.save()
    resultset = models.QuinielaResults(draw=draw, res=resultset20)
    resultset.save()
