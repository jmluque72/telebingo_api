# coding: utf-8

import json
from pprint import pprint
from datetime import datetime, timedelta
from bet import models
import os

def run():
    print('START LOAD QUINIELAS')
    # Sorteos: Primera -> 0 ; Matutina -> 1 ; Vespertina -> 2 ; Nocturna ->3

    sorteos = [0, 1, 2, 3]
    with open('./scripts/files/quinielas.json') as f:
        data = json.load(f)
    for i in data:
        date = datetime.strptime(i['Dia'], '%d/%m/%Y')
        for sorteo in sorteos:
            if i[str(sorteo)]['Sorteo'] is not None:
                time = i[str(sorteo)]['Hora'].split(':')
                date_draw = date.replace(hour=int(time[0]), minute=int(time[1]))
                date_limit_agency = date_draw - timedelta(minutes=15)
                date_limit = date_draw - timedelta(minutes=30)
                valid = models.QuinielaGroup.objects.filter(number=i[str(sorteo)]['Sorteo'], type=sorteo)
		if valid.count() == 0:
                    quinielaGroup = models.QuinielaGroup()
                    quinielaGroup.date = date
                    quinielaGroup.date_draw = date_draw
                    quinielaGroup.date_limit_agency = date_limit_agency
                    quinielaGroup.date_limit = date_limit
                    quinielaGroup.province = models.Province.objects.get(id=i['provincia'])
                    quinielaGroup.number = i[str(sorteo)]['Sorteo']
                    # Estado 0 -> Publicado ; 1 -> Borrador
                    quinielaGroup.state = 0
                    quinielaGroup.type = sorteo
                    quinielaGroup.save()
                    for quiniela in str(i[str(sorteo)]['Loterias']):
			print(date)
                        
                        drawQuiniela = models.DrawQuiniela()
                        drawQuiniela.quiniela = models.Quiniela.objects.get(code=quiniela)
                        drawQuiniela.type = sorteo
                        drawQuiniela.game = models.Game.objects.get(code='quiniela')
                        drawQuiniela.date_draw = date_draw
                        drawQuiniela.date_limit_agency = date_limit_agency
                        drawQuiniela.date_limit = date_limit
                        drawQuiniela.number = i[str(sorteo)]['Sorteo']
                        # Estado 0 -> Publicado ; 1 -> Borrador
                        drawQuiniela.state = 0
                        drawQuiniela.save()
                        quinielaGroup.draws.add(drawQuiniela)
    # os.remove('./scripts/sorteos.json')
    print('END')
