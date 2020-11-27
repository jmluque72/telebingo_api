import os, sys
import mercadopago
import requests
import bet.models
from django.conf import settings

import json


def run():


    headers = {
        'Content-Type': 'application/json',
    }

    params = (
        ("operation_type", "regular_payment"),
        ("access_token","APP_USR-3577694585926805-073013-c1dfc6577fe8ee9ea71d0d8d195c0684-340752167"),
        ("range", "date_created"),
        ("begin_date", "NOW-1MONTH"),
        ("end_date", "NOW"),
        ("status", "approved")

    )

    response = requests.get('https://api.mercadopago.com/v1/payments/search', headers=headers, params=params)
    mepa = response.json()

    total = mepa.get("paging").get("total")


    headers = {
        'Content-Type': 'application/json',
    }

    params = (
        ("limit", total),
        ("operation_type", "regular_payment"),
        ("access_token","APP_USR-3577694585926805-073013-c1dfc6577fe8ee9ea71d0d8d195c0684-340752167"), 
        ("range", "date_created"),
        ("begin_date", "NOW-1MONTH"),
        ("end_date", "NOW"),
        ("status", "approved")

    )

    response = requests.get('https://api.mercadopago.com/v1/payments/search', headers=headers, params=params)
    mepa = response.json()
    print(mepa)
    for i in mepa.get("results"):
        try:
            print i
            mov = bet.models.ChargeMovement.objects.get(number = i.get("external_reference"))
          
            if mov.state != bet.models.AbstractMovement.STATE.CONFIRMED:
                mov.state = bet.models.AbstractMovement.STATE.CONFIRMED
                mov.user.saldo = mov.user.saldo + mov.amount
                mov.user.save()
                mov.save()
                print "corregido"
            print "movimiento"
        except  Exception as e:
            print str(e)


    return "pep"

