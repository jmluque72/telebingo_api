# coding: utf-8

import json
from pprint import pprint
from datetime import datetime
from bet import models
import os

# Script de carga de sorteos del mes del loto

def run():
    print('START LOAD LOTO')
    with open('./scripts/files/loto.json') as f:
        data = json.load(f)
    for i in data:
        fecha = datetime.strptime(i['Fecha'], '%d/%m/%Y')
        sorteo = i['Sorteo']
        hora_sorteo = i['HoraSorteo'].split(':')
        fecha_cierre = datetime.strptime(i['FechaCierre'], '%d/%m/%Y')
        hora_agencia = i['HoraAgencia'].split(':')
        hora_app = i['HoraApp'].split(':')
        monto = i['Monto']
        tradicional = i['Tradicional']
        revancha = i['Revancha']
        sale = i['Sale']

        date_draw = fecha.replace(
            hour=int(hora_sorteo[0]), minute=int(hora_sorteo[1]))
        date_limit_agency = fecha_cierre.replace(
            hour=int(hora_agencia[0]), minute=int(hora_agencia[1]))
        date_limit = fecha_cierre.replace(
            hour=int(hora_app[0]), minute=int(hora_app[1]))
        game = models.Game.objects.get(code='loto')

        valid = models.Draw.objects.filter(number=sorteo, game=game)
        if valid.count() == 0:
            drawQuini = models.Draw()
            drawQuini.game = game
            drawQuini.date_draw = date_draw
            drawQuini.date_limit_agency = date_limit_agency
            drawQuini.date_limit = date_limit
            drawQuini.number = sorteo
            drawQuini.state = 0
            drawQuini.prize_text = monto
            drawQuini.price = tradicional
            drawQuini.price2 = revancha
            drawQuini.price3 = sale
            drawQuini.save()
    # os.remove('./scripts/sorteos.json')
    print('END')
