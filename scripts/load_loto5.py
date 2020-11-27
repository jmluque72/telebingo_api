# coding: utf-8

import json
from pprint import pprint
from datetime import datetime, timedelta
from bet import models
import os

# Script de carga de sorteos del mes del loto5


def run():
    print('START LOAD LOTO 5')
    with open('./scripts/files/loto5.json') as f:
        data = json.load(f)
    for i in data:
        date = datetime.strptime(i['Fecha'], '%d/%m/%Y')
        sorteo = i['Sorteo']
        hora_sorteo = i['HoraSorteo'].split(':')
        date_draw = date.replace(
            hour=int(hora_sorteo[0]), minute=int(hora_sorteo[1]))
        fecha_cierre = datetime.strptime(i['FechaCierre'], '%d/%m/%Y')
        hora_cierre = i['HoraAgencia'].split(':')
        date_limit_agency = fecha_cierre.replace(
            hour=int(hora_cierre[0]), minute=int(hora_cierre[1]))
        date_limit = date_limit_agency - timedelta(minutes=15)
        monto = i['Monto']
        price = i['Precio']
        game = models.Game.objects.get(code='loto5')

        valid = models.Draw.objects.filter(number=sorteo, game=game)
        if valid.count() == 0:
            drawBrinco = models.Draw()
            drawBrinco.game = game
            drawBrinco.date_draw = date_draw
            drawBrinco.date_limit_agency = date_limit_agency
            drawBrinco.date_limit = date_limit
            drawBrinco.number = sorteo
            drawBrinco.state = 0
            drawBrinco.prize_text = monto
            drawBrinco.price = price
            drawBrinco.save()
    # os.remove('./scripts/sorteos.json')
    print('END')
