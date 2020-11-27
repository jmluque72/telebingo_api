#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import defaultdict, OrderedDict
from datetime import datetime
from decimal import Decimal
from itertools import chain
from operator import itemgetter, attrgetter
from os.path import splitext
import hashlib, random
import json
import tempfile
from bet.utils import  send_email_welcome

import logging
import mercadopago
import mimetypes
import requests
import StringIO
from django.http.response import HttpResponse, Http404, JsonResponse, HttpResponseForbidden
import os
import pdfkit
from time import time
import traceback
from smtplib import SMTPException
from random import shuffle
from pdfkit.configuration import Configuration

from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.db import transaction, IntegrityError
from django.db.models import F, Q, Sum
from django.forms import ValidationError
from django.utils import timezone
from passwords.validators import LengthValidator

from spyne.application import Application
from spyne.decorator import rpc
from spyne.model.primitive import Unicode, Integer, Boolean
from spyne.model.complex import Iterable, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.service import ServiceBase

from oauth2_provider.decorators import protected_resource
from registration.backends.default.views import RegistrationView

from bet.utils import EmailMultiRelated
from simple_webservice import register_model, register_call, query_to_dict, \
    model_to_dict, to_simple_types

from django.conf import settings
from bet.models import has_relation
from bet import models, forms, utils
import ast
import base64

from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
import string
# Get an instance of a logger
#logging.basicConfig()
logger = logging.getLogger('agencia24_default')


register_model(models.Game, select=True)

def get_error(texto, response=None):
    return {'response': response, 'stacktrace': '', 'error_msg': texto,  'error': True}


LIMIT_UNDO = 30

@register_call()
@transaction.atomic
def register_user(request, **data):
    """
    :param args: {'username', 'first_name', 'last_name', 'email', 'password',
                'province', 'dni', 'agency'}

    :requires: django-registration, django-passwords
    """


    print "ENTER REGISTER_USER"
    if settings.APP_CODE != 'PWA_SC':
        evaluate_position("register_user", request, data)

    print "CONTINUE"

    data['username'] = data['email'] = data['username'].lower()  # data[username] == data[email]

    if User.objects.filter(username=data['username']).exists():
        return get_error(u'El email ingresado ya pertenece a otro usuario.')

    if models.UserProfile.objects.filter(dni=data['dni']).exists():
        return get_error(u'El DNI ingresado ya pertenece a un usuario del sistema.')

    try:
        validate_email(data['username'])
    except ValidationError:
        return get_error(u'El email ingresado no es válido.')

    """pass_validators = [MinValueValidator(5)]
    try:
        for v in pass_validators:
            v(data['password'])
    except ValidationError as e:
        doc = html5parser.fromstring(u'{}'.format(e.message))
        return get_error(u'{}'.format(e.message))"""

    #pass_validators = [forms.ComplexityValidator(settings.PASSWORD_COMPLEXITY),
    #                   LengthValidator(settings.PASSWORD_MIN_LENGTH)]
    #try:
    #    for validator in pass_validators:
    #        validator(data['password'])
    #except ValidationError as e:
    #    return get_error('\n'.join(e.messages))

    salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
    data['password'] = make_password(data['password'], salt)

    #Formulario para usar registro de django-registration
    form = forms.UserRegistrationForm(data)
    form.is_valid()
    print form.errors.as_text()
    #form.full_clean()

    registration = RegistrationView()
    user = registration.register(request, form)
    user.first_name = data['first_name']
    user.last_name = data['last_name']
    if not settings.SEND_ACTIVATION_EMAIL:
        user.is_active = True
    user.save()
    group = Group.objects.get(name='user')
    group.user_set.add(user)

    profile = models.UserProfile(user=user, dni=data['dni'], province_id=data['province'])
    profile.agency_id = data['agency']
    if 'date_of_birth' in data:
        profile.date_of_birth = data['date_of_birth']

    family = request.user_agent.os.family.upper()
    profile.device_os = getattr(models.UserProfile.DEVICE_OS, family, models.UserProfile.DEVICE_OS.OTHER)
    profile.save()
    assert profile.agency.province == profile.province, 'La agencia no pertenece a la provincia seleccionada.'

    if settings.APP_CODE == 'SF':

        context = {"user": profile.user}
        attachs = []
        user_email = ""

        #email = send_email_welcome(None, 'emails/welcome', [profile.user.email], context=context,
        #               attachments=None, bcc=[user_email], send=True, imgs=None)


    if True and settings.APP_CODE == 'SF':

        m = models.ChargeMovement.objects.create(
            code='CC', user=profile, amount=30,
            method=models.AbstractMovement.PAYMENT_METHODS.MERCADOPAGO,
            type='carga inicial',
            number=999999,
            state=models.AbstractMovement.STATE.CONFIRMED,
            tcargo=None
        )
        profile.saldo = profile.saldo + 30
        profile.save()
        m.confirm_date = m.date
        m.save()



    if settings.SEND_ACTIVATION_EMAIL:

        try:
            activation_key = user.registrationprofile.activation_key
            urls = {'activation': reverse('registration_activate',
                                          kwargs={'activation_key': activation_key})}

            context = {'user': user}
            profile.email_notification(request, models.USER_SETTINGS.MAIL_ACCOUNT_ACTIVATION,
                                       'emails/activation_email', context, urls=urls)
        except SMTPException as e:
            pass


    return {}


@register_call()
def update_gcm_id(request, usercode, gcm_id, **kwargs):
    """
    :param args: {'usercode', 'gcm_id'}
    :return: {account: {...}, name: NAME, dni: DNI}
    """

    family = request.user_agent.os.family.upper()
    device_os = getattr(models.UserProfile.DEVICE_OS, family, None)
    if device_os is None:
        email_message = EmailMultiRelated('DEVICE FAMILY',
                                          '{} {}\n{}'.format(usercode, family, request.user_agent),
                                          settings.DEFAULT_FROM_EMAIL,
                                          ['developer@liricus.com.ar'])
        email_message.send(fail_silently=not settings.DEBUG)

    try:
        profile = models.UserProfile.objects.get(user__username=usercode)
    except models.UserProfile.DoesNotExist:
        return get_error('Usuario incorrecto.')

    profile.devicegsmid = gcm_id
    profile.device_os = getattr(models.UserProfile.DEVICE_OS, family, models.UserProfile.DEVICE_OS.OTHER)
    profile.save()

    result = {
        'account': get_saldo(profile),
        'first_name': profile.user.first_name,
        'last_name': profile.user.last_name,
        'dni': profile.dni
    }
    return result


@register_call()
@protected_resource()
def is_alive(request, session, **args):
    """
    :param args: {}
    :header Authorization: <token_type> <access_token>
    :return: {}
    """
    return {}


@register_call()
@protected_resource()
def update_user_settings(request, session, **args):
    """
    :param args: data [{'setting', 'value'}, ...}, ...]
    :header Authorization: <token_type> <access_token>
    :return: {account: {...}}
    """

    profile = request.user.profile
    for setting in args['data']:
        profile.update_setting(int(setting['setting']), setting['value'])

    return {'account': get_saldo(profile)}



@register_call()
@protected_resource()
def get_userprofile(request, session, **args):
    """
    :header Authorization: <token_type> <access_token>
    :return: {profile: {dni, agency, province, first_name, last_name},
              account: {...}}
    """

    result = model_to_dict(request.user.profile, fields=('dni', 'agency', 'province','date_of_birth'))
    result.update(model_to_dict(request.user, fields=('first_name', 'last_name')))



    return {'profile': result, 'account': get_saldo(request.user.profile)}


@register_call()
@transaction.atomic
@protected_resource()
def update_userprofile(request, session, **args):
    """
    :param args: {dni, agency, province, first_name, last_name}
    :header Authorization: <token_type> <access_token>
    :return: {account: {...}}
    """

    user = request.user
    if args.has_key("first_name"):
        user.first_name = args.get('first_name')

    if args.has_key("last_name"):
       user.last_name = args.get('last_name')

    if 'password' in args:
        user.set_password(args.get('password'))

    user.save()

    profile = user.profile
    if models.UserProfile.objects.filter(dni=args.get('dni')).exclude(id=profile.id).exists():
        return get_error(u'El DNI ingresado ya pertenece a un usuario del sistema.')

    if args.has_key("dni"):
        profile.dni = args.get('dni')

    if args.has_key("province"):
        profile.province_id = args.get('province')

    if args.has_key("agency"):
        profile.agency_id = args.get('agency')

    if 'date_of_birth' in args:
        profile.date_of_birth =  args.get('date_of_birth')
    profile.save()

    assert profile.agency.province == profile.province, 'La agencia no pertenece a la provincia seleccionada.'

    return {'account': get_saldo(profile)}


@register_call()
@protected_resource()
def get_user_settings(request, session, **args):
    """
    :param args: {}
    :header Authorization: <token_type> <access_token>
    :return: {account: {...}, settings: [{setting, value}, ...]}
    """

    profile = request.user.profile
    result = {'account': get_saldo(profile), 'settings': []}

    for setting in models.Setting.objects.all():
        value = profile.get_setting(setting.code)
        result['settings'].append({'setting': setting.code, 'value': value})

    return result


@register_call()
#@protected_resource()
def change_password(request, **data):
    """
    :param data: {'old_password', 'new_password1', 'new_password2'}
    :header Authorization: <token_type> <access_token>
    :return: {}
    """

    #user = request.user
    user = models.UserProfile.objects.get(user__username='luciano').user

    old_password = data.get('old_password', None)
    if not user.check_password(old_password):
        return get_error(u'Su contraseña antigua es incorrecta.')

    password1 = data.get('new_password1', '')
    pass_validators = [forms.ComplexityValidator(settings.PASSWORD_COMPLEXITY),
                       LengthValidator(settings.PASSWORD_MIN_LENGTH)]
    try:
        for validator in pass_validators:
            validator(password1)
    except ValidationError as e:
        return get_error('\n'.join(e.messages))

    password2 = data.get('new_password2', None)
    if password1 and password2:
        if password1 != password2:
            return get_error(u'Las contraseñas no coinciden.')

        user.set_password(password1)
        user.save()

        update_session_auth_hash(request, user)
        return get_saldo(user.profile)

    return get_error(u'Por favor complete todos los campos.')


@register_call()
def password_reset(request, email, **know):
    """
    :param args: {'email'}
    :return: {}
    """

    form = forms.PasswordResetForm({'email': email})
    if form.is_valid():
        opts = {
            'use_https': request.is_secure(),
            'request': request,
        }
        try:
            form.save(**opts)
        except SMTPException as e:
            logger.error(e)
            return get_error('Hubo un error al procesar su solicitud, por favor intente nuevamente.')

    return {}


def get_saldo(userid):
    """ userid can be username or an userprofile instance """

    if isinstance(userid, models.UserProfile):
        currentu = userid
    else:
        try:
            currentu = models.UserProfile.objects.get(user__username=userid)
        except models.UserProfile.DoesNotExist:
            return {}
    return {"playtoday": float(currentu.playtoday), "saldo": float(currentu.saldo)}


def check_saldo(userid, valor):

    try:
        currentu = models.UserProfile.objects.get(user__username=userid)
        return currentu.saldo >= valor
    except models.UserProfile.DoesNotExist:
        return False


def update_saldo(userid, valor):

    currentu = models.UserProfile.objects.get(user__username=userid)
    if currentu is not None:
        currentu.saldo -= valor
        currentu.playtoday += valor
        currentu.save()


@register_call()
def get_active_draw(usercode, **know):

    result = {"games": [], "draw": [], "promotions": []}
    now = timezone.now()

    query = Q(coupon_set__fraction_saldo__gt=0)#, coupon_set__agency__isnull=True)
    try:
        profile = models.UserProfile.objects.get(user__username=usercode)
        #query &= Q(coupon_set__agency=profile.agency)
    except models.UserProfile.DoesNotExist:
        profile = None

    promotions = models.DrawPromotion.objects.filter(draw__date_limit__gte=now,
                                                     draw__game__is_active=True,
                                                     draw__state=models.BaseDraw.STATE.ACTIVE,
                                                     is_active=True).order_by('draw__date_draw')
    for promotion in promotions:
        draw = promotion.draw.parent

        if draw.game.code == models.Game.CODE.QUINIELA:
            if profile is None or not draw.groups.filter(province=profile.province).exists():
                continue

        elif draw.game.type == models.Game.TYPE.PREPRINTED:

            #if profile is None and not draw.coupon_set.filter(agency__isnull=True).exists():
            #    continue
            #elif profile is not None and not draw.coupon_set.filter(agency=profile.agency).exists():
            #    continue
            pass
        promo = model_to_dict(draw)
        promo['suggestion'] = promotion.suggestion
        result["promotions"].append(promo)

    for game in models.Game.objects.filter(is_active=True).order_by('order'):
        if game.code == models.Game.CODE.QUINIELA:
            if not profile:
                continue

            draws = models.DrawQuiniela.objects.filter(groups__date_limit__gte=now, game=game,
                                                       state=models.BaseDraw.STATE.ACTIVE)
            if profile:
                draws = draws.filter(groups__province=profile.province)


            if draws.exists():
                result["games"].append(model_to_dict(game))
                result["draw"].append(model_to_dict(draws.order_by('date_limit').first()))

        elif game.type == models.Game.TYPE.PREPRINTED:
            print game
            #if profile is None:
            #    continue

            print "query",query

            draws = models.DrawPreprinted.objects.filter(query, date_limit__gte=now, game=game,
                                                         state=models.BaseDraw.STATE.ACTIVE)
            if draws.exists():
                print "2", game

                result["games"].append(model_to_dict(game))
                result["draw"].append(model_to_dict(draws.order_by('date_limit').first()))

        elif game.type == models.Game.TYPE.NONPRINTED:
            draws = models.Draw.objects.filter(date_limit__gte=now, game=game, state=models.BaseDraw.STATE.ACTIVE)

            if draws.exists():
                result["games"].append(model_to_dict(game))
                result["draw"].append(model_to_dict(draws.order_by('date_limit').first()))



    lote = query_to_dict(models.Quiniela.objects.all())
    for lo in lote:
        if lo['code'] == 3:
            lo['max_digits'] = 5
        else:
            lo['max_digits'] = 4

    result["lottery"] = lote
    result["lottery_types"] = dict(models.TYPE_CHOICES)
    # Tiempos limites de loteria
    if usercode:
        result["account"] = get_saldo(usercode)

    return result

@register_call()
def regenerate(request,  **know):

    context = None
    a=models.Draw.objects.get(id=7079)
    a.create_extract(request, context, pdf=True)



@register_call()
def get_nonprinted_dates(usercode, gamecode, **know):
    """
    :param args: usercode, gamecode
    :returns {gamecode: [{draw_dict}, ...]}
    """

    now = timezone.now()
    draws = models.Draw.objects.filter(game__code=gamecode, game__is_active=True,
                                       date_limit__gte=now, state=models.BaseDraw.STATE.ACTIVE)

    result = {}
    if usercode:
        result["account"] = get_saldo(usercode)
    result[gamecode] = query_to_dict(draws.order_by('date_limit'))

    return result


@register_call()
def get_quiniseis_dates(usercode,  **know):

    return get_nonprinted_dates(usercode, models.Game.CODE.QUINI6)


@register_call()
def get_brinco_dates(usercode,  **know):

    return get_nonprinted_dates(usercode, models.Game.CODE.BRINCO)


@register_call()
def get_loto5_dates(usercode,  **know):

    return get_nonprinted_dates(usercode, models.Game.CODE.LOTO5)


@register_call()
def get_loto_dates(usercode,  **know):

    return get_nonprinted_dates(usercode, models.Game.CODE.LOTO)


@register_call()
@protected_resource()
def get_quiniela_dates(request,  **know):
    """
    :param args: {}
    :header Authorization: <token_type> <access_token>
    :returns {quiniela: [{date, type, draws: [{quiniela, type, date_draw, number, ...}, ...]}, ...],
        account}
    """
    profile = request.user.profile

    if not models.Game.objects.get(code=models.Game.CODE.QUINIELA).is_active:
        return  {"quiniela": [], "account": get_saldo(profile)}

    now = timezone.now()
    groups = models.QuinielaGroup.objects.filter(province=profile.province,
                                                 date_limit__gte=now).order_by('draws__date_draw').distinct()
    response = {"quiniela": query_to_dict(groups, exclude=('province',)),
                "account": get_saldo(profile)}

    for idx, group in enumerate(groups):
        draws = group.draws.filter(state=models.BaseDraw.STATE.ACTIVE).order_by('date_limit')
        dda = query_to_dict(draws)
        for d in dda:
            if group.type == 3 and group.date_draw.weekday() >= 1 and group.date_draw.weekday() <= 5:
               d['max_digits'] = 5
            else:
               d['max_digits'] = 4
        response["quiniela"][idx]["draws"] = dda

    return response


@register_call()
def get_preprinted_dates(usercode, gamecode, **know):

    result = {}
    query = Q(coupon_set__isnull=False, coupon_set__agency__isnull=False)
    if usercode:
        profile = models.UserProfile.objects.get(user__username=usercode)
        query &= Q(coupon_set__agency=profile.agency)
        result["account"] = get_saldo(profile)

    now = timezone.now()
    draws = models.DrawPreprinted.objects.filter(query, date_limit__gte=now,
                                                 game__code=gamecode, game__is_active=True,
                                                 state=models.BaseDraw.STATE.ACTIVE).distinct()

    result["draws"] = query_to_dict(draws.order_by('date_limit'))

    return result


def hash_time():
    now = datetime.now().isoformat()
    time_hash = hashlib.sha1()
    time_hash.update(now)
    return time_hash.hexdigest() + now

def create_bet(profile, draw, importq, credit=None, trx_code=None):

    if draw is not None and timezone.now() > draw.date_limit:
        return None

    bet = models.Bet.objects.create(
        user=profile,
        date_bet=timezone.now(),
        agency=profile.agency,
        code_trx=trx_code or hash_time(),
    )

    if credit is None:

        movement = models.BetMovement(bet=bet, code='PA', user=profile, amount=-importq)
        movement.confirm_date = timezone.now() # TODO! hace falta confirm_date en apuestas?
        movement.state = models.AbstractMovement.STATE.CONFIRMED
        movement.save()

        profile.saldo -= Decimal(importq)
        profile.playtoday += Decimal(importq)
        profile.save()

    else:

        print "*************", credit, "************"
        '''
        assert credit.accredited == False, u'Credit already used: {}'.format(credit.id)
        assert credit.game == draw.game, u'Credit game incorrect: {}'.format(credit.id)
        assert credit.user == profile, u'Credit user incorrect: {}'.format(credit.id)
        credit.accredited = True
        credit.bet = bet
        credit.save()
        '''

    return bet


def is_redoblona(data, idx):
    return data[idx]['import'] == 0


def check_min_imports(tickets):
    for ticket in tickets:
        total = ticket.detailquiniela_set.aggregate(total=Sum(F('importq'))).get('total') or 0
        if total < models.QUINIELA_MIN_TICKET:
            raise Exception(u'El importe mínimo de ticket es de ${}.'.format(models.QUINIELA_MIN_TICKET))


def evaluate_position(ff, request, know):

    l = []
    l.append(request.user.username)
    l.append(" ")
    l.append(ff)
    l.append(" ")

    if know.has_key("lat"):
        l.append(str(know.get("lat")))
        l.append(" ")
    if know.has_key("lng"):
        l.append(str(know.get("lng")))
        l.append(" ")

    l.append("\n")

    l.append(request.user.username)



    if request.user.username not in ('prueba@mail.com', 'couretotdaniel@gmail.com','rodrigo025@gmail.com', 'lrusconi@hotmail.com','gasrusconi@gmail.com', 'jmluque72@gmail.com', 'ro@ro.com'):

        if know.has_key("lat"):

            latitude = know.get("lat")
            longitude = know.get("lng")
            if latitude == 0.0 or longitude == 0.0:
                l.append("Imposible determinar la ubicacion desde donde esta jugando. Verifique tener activado el GPS.")
                with open("/tmp/geolocalization.txt", "a") as myfile:
                    myfile.write(''.join(l))
                raise IntegrityError("Imposible determinar la ubicacion desde donde esta jugando. Verifique tener activado el GPS.")


            c = "https://maps.googleapis.com/maps/api/geocode/json?latlng="+str(latitude)+","+str(longitude)+"&sensor=false&key=AIzaSyBLUi_NzPBohRLlZ09zpke0GlsqgPqas64"

            response = requests.get(c)

            #print response.text
            resp = response.json()
            l.append(str(resp))

            #print resp
            try:
                arr2 = resp['results']
            except:
                raise IntegrityError("Imposible determinar la ubicacion desde donde esta jugando. Verifique tener activado el GPS.")



            for ar0 in arr2:
                arr = ar0['address_components']
                #print arr, arr, c
                for i in arr:
                    if i['types'][0] == "administrative_area_level_1":

                        #l.append(str(i))

                        print change_text(i['long_name']), settings.APP_CODE
                        l.append(change_text(i['long_name']))

                        if settings.APP_CODE == "CA":
                            if 'Catamarca' not in change_text(i['long_name'])  and 'catamarca' not in change_text(i['long_name']):
                                l.append("Usted no se encuentra en la provincia de Catamarca")
                                with open("/tmp/geolocalization.txt", "a") as myfile:
                                    myfile.write(''.join(l))

                                raise IntegrityError("Usted no se encuentra en la provincia de Catamarca")

                        if settings.APP_CODE == "SC" or settings.APP_CODE == 'PWA_SC':
                            if 'Santa Cruz' not in change_text(i['long_name'])  and 'santa cruz' not in change_text(i['long_name']):
                                l.append("Usted no se encuentra en la provincia de Santa cruz")
                                with open("/tmp/geolocalization.txt", "a") as myfile:
                                    myfile.write(''.join(l))

                                raise IntegrityError("Usted no se encuentra en la provincia de Santa cruz")
                        if settings.APP_CODE == "LP":
                            if change_text(i['long_name']) != "Santa Fe" and change_text(i['long_name']) != "santa fe":
                                l.append("Usted no se encuentra en la provincia de Santa Fe")
                                with open("/tmp/geolocalization.txt", "a") as myfile:
                                    myfile.write(''.join(l))

                                raise IntegrityError("Usted no se encuentra en la provincia de La Pampa")
                        if settings.APP_CODE == "A24":
                            if 'Santa Fe' not in change_text(i['long_name']) and 'santa fe' not in change_text(i['long_name']):
                                l.append("Usted no se encuentra en la provincia de Santa Fe")
                                with open("/tmp/geolocalization.txt", "a") as myfile:
                                    myfile.write(''.join(l))

                                raise IntegrityError("Usted no se encuentra en la provincia de Santa Fe usted esta en " + i['long_name'])
                            #if change_text(i['long_name']) != "Cordoba" and change_text(i['long_name']) != "Córdoba":
                            #    raise IntegrityError("Usted no se encuentra en la provincia de Cordoba")
                        if settings.APP_CODE == "SF":

                            if 'Santa Fe' not in change_text(i['long_name'])  and 'santa fe' not in change_text(i['long_name']):
                                l.append("Usted no se encuentra en la provincia de Santa Fe")
                                with open("/tmp/geolocalization.txt", "a") as myfile:
                                    myfile.write(''.join(l))
                                raise IntegrityError("Usted no se encuentra en la provincia de Santa Fe")

        else:
            raise IntegrityError("Imposible determinar la ubicacion desde donde esta jugando. Verifique tener activado el GPS.")
           #print  resp['status']
        #c = "https://maps.googleapis.com/maps/api/geocode/json?latlng="+args.get+","++&sensor=false&key=AIzaSyDAHgZXfaYvZ4gk1WXifG7w-pku5dztjs8


    l.append(" OKEY ")
    with open("/tmp/geolocalization.txt", "a") as myfile:
        myfile.write(''.join(l))

@register_call()
@protected_resource()
def buy_quiniela(request, data, **know):
    """
    :args data: [{import,number,ubicacion,lottery:[<draw_id>, ...]}]
    """
    assert len(data) > 0, u"'data' attribute is empty."


    evaluate_position("buy_quiniela", request, know)

    profile = request.user.profile

    valor = sum(float(detail["import"]) for detail in data)
    if profile.saldo < valor:
        return get_error("Saldo insuficiente.")

    pk_list = [d['lottery'] for d in data]
    pk_set = set(utils.flat_list(pk_list))
    try:
        earliest = models.QuinielaGroup.objects.filter(province=profile.province, draws__in=pk_set).earliest('date_limit')
    except models.QuinielaGroup.DoesNotExist:
        return get_error(u"Hubo problemas al procesar su apuesta. Por favor intente nuevamente.")

    if timezone.now() > earliest.date_limit:
        return get_error(u"Hora límite del sorteo nro. {} sobrepasada.".format(earliest.number))

    grouped_data = defaultdict(list)
    for detail in data:
        key = tuple(set(detail.pop("lottery")))
        grouped_data[key].append(detail)

    trx = know.get('transaction', None)
    try:
        with transaction.atomic():
            tickets = []
            for key, data in grouped_data.items():
                prev = None

                trx_code = None if not trx else trx + str(len(tickets))
                tickets.append(models.Ticket.objects.create())
                bet = create_bet(profile, None, sum(float(detail["import"]) for detail in data), trx_code=trx_code)

                for idx, detail in enumerate(data):

                    detaillottery = models.DetailQuiniela()
                    detaillottery.group = models.QuinielaGroup.objects.get(province=profile.province, draws=key[0])
                    detaillottery.number = detail["number"]
                    detaillottery.location = detail["ubicacion"]
                    detaillottery.importq = float(detail["import"])
                    detaillottery.state = models.BaseDetail.STATE.NOT_PLAYED
                    detaillottery.bet = bet
                    detaillottery.ticket = tickets[-1]
                    detaillottery.full_clean()
                    detaillottery.save()

                    detaillottery.draws.add(*key)  # detail[lottery] = lista de draws_id

                    if is_redoblona(data, idx) and prev is not None:
                        prev.redoblona = detaillottery
                        prev.save()

                    prev = detaillottery

            check_min_imports(tickets)
            send_quiniela_details(request, tickets)

            return {"account": get_saldo(profile)}
    except ValidationError as e:
        return get_error('\n'.join(e.messages))


def get_quini6_imports(data):
    """
    :param data: argument from buy_quiniseis
    :return: [import detail-0, import detail-1, ..., import detail-n, import-total]
    """
    values = []
    total = 0
    for bet_data in data:
        total_draw = 0
        draw = models.Draw.objects.get(
            game__code=models.Game.CODE.QUINI6,
            id=bet_data['draw_id']
        )
        total_draw += draw.price
        if bet_data['modor']:
            total_draw += draw.price2
        if bet_data['modos']:
            total_draw += draw.price3

        total += total_draw
        values.append(total_draw)

    values.append(total)
    return values

@register_call()
@transaction.atomic
@protected_resource()
def buy_quiniseis(request, data, **know):
    """
    :param args: {'data': [{importq, numbers, draw_id, modot, modor, modos}]}
    :header Authorization: <token_type> <access_token>
    """

    assert len(data) > 0, u"'data' attribute is empty."
    evaluate_position("buy_quiniseis",request, know)


    profile = request.user.profile

    imports = get_quini6_imports(data)
    if profile.saldo < imports[-1]:
        return get_error("Saldo insuficiente.")

    bets = []
    details = []
    trx = know.get('transaction', None)
    for idx, bet in enumerate(data):
        if any(map(lambda x: int(x) > settings.QUINI6_MAX_NUMBER, bet['numbers'])):
            return get_error(u"Los números no pueden ser mayores a {}.".format(settings.QUINI6_MAX_NUMBER))

        draw = models.Draw.objects.get(
            game__code=models.Game.CODE.QUINI6,
            id=bet['draw_id']
        )
        trx_code = None if not trx else trx + str(len(bets))
        currentbet = create_bet(profile, draw, imports[idx], trx_code=trx_code)
        if currentbet is None:
            raise IntegrityError(u"Hora limite del sorteo nro. {} sobrepasada.".format(draw.number))

        bets.append(currentbet)

        state = models.BaseDetail.STATE.NOT_PLAYED
        numbers = bet['numbers']
        numbers.sort()
        detail_quiniseis = models.DetailQuiniSeis(draw=draw, bet=currentbet, state=state)
        detail_quiniseis.number1 = numbers[0]
        detail_quiniseis.number2 = numbers[1]
        detail_quiniseis.number3 = numbers[2]
        detail_quiniseis.number4 = numbers[3]
        detail_quiniseis.number5 = numbers[4]
        detail_quiniseis.number6 = numbers[5]
        detail_quiniseis.tra = bet['modot']
        detail_quiniseis.rev = bet['modor']
        detail_quiniseis.sie = bet['modos']
        detail_quiniseis.importq = float(imports[idx])
        detail_quiniseis.save()

        details.append(detail_quiniseis)

    send_nonprinted_details(request, details)

    return {"account": get_saldo(profile)}


def get_nonprinted_imports(data):
    """
    :param data: argument from buy_nonprinted
    :return: {total: total, <draw_id>: import, ...}
    """
    values = {'total': 0}
    for bet_data in data:
        draw = models.Draw.objects.get(id=bet_data['draw_id'])

        values['total'] += draw.price
        values[draw.id] = draw.price
    return values


@register_call()
@transaction.atomic
@protected_resource()
def buy_brinco(request, data, **know):
    """
    :param args: {'data': [{importq, numbers, draw_id}]}
    :header Authorization: <token_type> <access_token>
    """
    assert len(data) > 0, u"'data' attribute is empty."
    evaluate_position("buy_brinco", request, know)



    profile = request.user.profile

    imports = get_nonprinted_imports(data)
    if profile.saldo < imports['total']:
        return get_error("Saldo insuficiente.")

    bets = []
    details = []
    trx = know.get('transaction', None)
    for bet in data:
        if any(map(lambda x: int(x) > settings.BRINCO_MAX_NUMBER, bet['numbers'])):
            return get_error(u"Los números no pueden ser mayores a {}.".format(settings.BRINCO_MAX_NUMBER))

        draw = models.Draw.objects.get(
            game__code=models.Game.CODE.BRINCO,
            id=bet['draw_id']
        )
        trx_code = None if not trx else trx + str(len(bets))
        currentbet = create_bet(profile, draw, imports[draw.id], trx_code=trx_code)
        if currentbet is None:
            raise IntegrityError(u"Hora limite del sorteo nro. {} sobrepasada.".format(draw.number))

        bets.append(currentbet)

        state = models.BaseDetail.STATE.NOT_PLAYED
        numbers = bet['numbers']
        numbers.sort()
        detail_brinco = models.DetailBrinco(draw=draw, bet=currentbet, state=state)
        detail_brinco.number1 = numbers[0]
        detail_brinco.number2 = numbers[1]
        detail_brinco.number3 = numbers[2]
        detail_brinco.number4 = numbers[3]
        detail_brinco.number5 = numbers[4]
        detail_brinco.number6 = numbers[5]
        detail_brinco.importq = float(bet["importq"])
        detail_brinco.save()

        details.append(detail_brinco)

    send_nonprinted_details(request, details)

    return {"account": get_saldo(profile)}


@register_call()
@transaction.atomic
@protected_resource()
def buy_loto5(request, data, **know):
    """
    :param args: {'data': [{importq, numbers, draw_id}]}
    :header Authorization: <token_type> <access_token>
    """
    assert len(data) > 0, u"'data' attribute is empty."

    evaluate_position("buy_loto5", request, know)


    profile = request.user.profile

    imports = get_nonprinted_imports(data)
    if profile.saldo < imports['total']:
        return get_error("Saldo insuficiente.")

    bets = []
    details = []
    trx = know.get('transaction', None)
    for bet in data:
        if any(map(lambda x: int(x) > settings.LOTO5_MAX_NUMBER, bet['numbers'])):
            return get_error(u"Los números no pueden ser mayores a {}.".format(settings.LOTO5_MAX_NUMBER))

        draw = models.Draw.objects.get(
            game__code=models.Game.CODE.LOTO5,
            id=bet['draw_id']
        )
        trx_code = None if not trx else trx + str(len(bets))
        currentbet = create_bet(profile, draw, imports[draw.id], trx_code=trx_code)
        if currentbet is None:
            raise IntegrityError(u"Hora limite del sorteo nro. {} sobrepasada.".format(draw.number))

        bets.append(currentbet)

        state = models.BaseDetail.STATE.NOT_PLAYED
        numbers = bet['numbers']
        numbers.sort()
        detail_loto5 = models.DetailLoto5(draw=draw, bet=currentbet, state=state)
        detail_loto5.number1 = numbers[0]
        detail_loto5.number2 = numbers[1]
        detail_loto5.number3 = numbers[2]
        detail_loto5.number4 = numbers[3]
        detail_loto5.number5 = numbers[4]
        detail_loto5.importq = float(bet["importq"])
        detail_loto5.save()

        details.append(detail_loto5)

    send_nonprinted_details(request, details)

    return {"account": get_saldo(profile)}


def get_loto_imports(data):
    """
    :param data: argument from buy_loto
    :return: [import detail-0, import detail-1, ..., import detail-n, import-total]
    """
    values = []
    total = 0
    for bet_data in data:
        total_draw = 0
        draw = models.Draw.objects.get(
            game__code=models.Game.CODE.LOTO,
            id=bet_data['draw_id']
        )
        total_draw += draw.price
        if bet_data['modod']:
            total_draw += draw.price2
        if bet_data['modos']:
            total_draw += draw.price3

        total += total_draw
        values.append(total_draw)

    values.append(total)
    return values


@register_call()
@transaction.atomic
@protected_resource()
def buy_loto(request, data, **know):
    """
    :param args: {'data': [{importq, numbers, extras, draw_id, modot, modod, modos}]}
    :header Authorization: <token_type> <access_token>
    """
    assert len(data) > 0, u"'data' attribute is empty."

    evaluate_position("buy_loto", request, know)



    profile = request.user.profile

    imports = get_loto_imports(data)
    if profile.saldo < imports[-1]:
        return get_error("Saldo insuficiente.")

    bets = []
    details = []
    trx = know.get('transaction', None)
    for idx, bet in enumerate(data):
        if any(map(lambda x: int(x) > settings.LOTO_MAX_NUMBER, bet['numbers'])):
            return get_error("Los números no pueden ser mayores a {}.".format(settings.LOTO_MAX_NUMBER))

        if any(map(lambda x: int(x) > settings.LOTO_MAX_EXTRA, bet['extras'])):
            return get_error("Los jackpots no pueden ser mayores a {}.".format(settings.LOTO_MAX_EXTRA))

        draw = models.Draw.objects.get(
            game__code=models.Game.CODE.LOTO,
            id=bet['draw_id']
        )
        trx_code = None if not trx else trx + str(len(bets))
        currentbet = create_bet(profile, draw, imports[idx], trx_code=trx_code)
        if currentbet is None:
            raise IntegrityError(u"Hora limite del sorteo nro. {} sobrepasada.".format(draw.number))

        bets.append(currentbet)

        state = models.BaseDetail.STATE.NOT_PLAYED
        numbers = bet['numbers']
        numbers.sort()
        extras = bet['extras']
        extras.sort()
        detail_loto = models.DetailLoto(draw=draw, bet=currentbet, state=state)
        detail_loto.number1 = numbers[0]
        detail_loto.number2 = numbers[1]
        detail_loto.number3 = numbers[2]
        detail_loto.number4 = numbers[3]
        detail_loto.number5 = numbers[4]
        detail_loto.number6 = numbers[5]

        detail_loto.extra1 = extras[0]
        detail_loto.extra2 = extras[1]

        detail_loto.tra = bet['modot']
        detail_loto.des = bet['modod']
        detail_loto.sos = bet['modos']

        detail_loto.importq = float(imports[idx])
        detail_loto.save()

        details.append(detail_loto)

    send_nonprinted_details(request, details)

    return {"account": get_saldo(profile)}


@register_call()
def get_cupons_lottery(usercode, draw, **know):

    return get_preprinted_coupons(usercode, draw, **know)


@register_call()
def get_cupons_telebingo(usercode, draw, **know):

    return get_preprinted_coupons(usercode, draw, **know)


@register_call()
def get_preprinted_coupons(usercode, draw, **know):

    cupons = models.Coupon.availables.filter(draw=draw)[0:1000]
    result = {}
    if usercode is not None:
        result["account"] = get_saldo(usercode)
    result["cupons"] = query_to_dict(cupons)

    return result


def _buy_preprinted_coupons(request, draw, data, profile, credit=None, **know):
    #print data
    """
    :param args: {'draw', 'data': [{cupon, quantity}]}
    :header Authorization: <token_type> <access_token>
    """

    draw = models.DrawPreprinted.objects.get(id=draw)

    if credit is None:
        if draw.promotion_coupons == models.BaseDraw.PROMOTION.DOSXUNO:
            print len(data), len(data) % 2, draw.price
            if len(data) %2 == 0:
                valor = (draw.price * len(data))/2
            else:
                valor = ((draw.price * (len(data)-1))/2) +  draw.price
        else:
            valor = sum(float(draw.price)*cups["quantity"] for cups in data)

        print valor
        if profile.saldo < valor:
            return get_error("Saldo insuficiente. Ver en 'Preguntas Frecuentes' como cargar saldo")
    else:
        assert len(data) == 1, u'Crédito solo permitido con un billete.'
        valor = 0

    with transaction.atomic():
        if settings.APP_CODE == "CA":
            founddetail = models.DetailCoupons.objects.filter(bet__user=profile)
            count = len(data)
            for f in founddetail:
                if draw in f.bet.draws:
                    count = count +1
            #if count > 2:
                #return get_error("Solo se puede comprar 2 cupones por sorteo")


        trx = know.get('transaction', None)
        bet = create_bet(profile, draw, valor, credit, trx_code=trx)
        if bet is None:
            return get_error(u"Hora límite del sorteo nro. {} sobrepasada.".format(draw.number))

        details = []
        data = sorted(data, key=itemgetter('cupon'))


        for cups in data:
            try:
                coupon = models.Coupon.availables.select_for_update().get(
                    id=cups["cupon"], draw=draw,fraction_saldo__gte=cups["quantity"]
                )
            except models.Coupon.DoesNotExist:
                raise IntegrityError(u"El billete número {} ya fue comprado.".format(cups["cupon"]))

            coupon.fraction_saldo -= cups["quantity"]
            coupon.save()

            detail = models.DetailCoupons.objects.create(
                bet=bet, coupon=coupon,
                fraction_bought=cups["quantity"],
                importq=0 if credit else draw.price*cups["quantity"]
            )
            details.append(detail)

    send_preprinted_details(request, details)

    return {"account": get_saldo(profile)}

def change_text(text):
    return text.encode('utf-8')  # assuming the encoding is UTF-8


@register_call()
@protected_resource()
def buy_preprinted_coupons(request, draw, data, **know):
    print data
    """
        :param args: {'draw', 'data': [{cupon, quantity}]}
        :header Authorization: <token_type> <access_token>
        """
    assert len(data) > 0, u"'data' attribute is empty."

    evaluate_position("buy_preprinted_coupons", request, know)

    return _buy_preprinted_coupons(request, draw, data, request.user.profile, **know)



def serialize_detail(detail):

    if isinstance(detail, models.DetailQuiniela):
        return serialize_quiniela_detail(detail)
    elif isinstance(detail, models.DetailCoupons):
        return serialize_preprinted_detail(detail)
    else:
        return serialize_preprinted_detail(detail)


def serialize_quiniela_detail(detail):

    data = {}
    data['method'] = 'bet'
    data['detail'] = model_to_dict(detail)
    data['detail']['location'] = detail.get_location_display()
    data['detail']['string'] = detail.to_string()

    draw = detail.draws.first() # Todos los draws del detalle siempre tienen la misma fecha y tipo
    data['detail']['date_draw'] = to_simple_types(draw.date_draw)
    data['detail']['date_limit'] = to_simple_types(draw.groups.first().date_limit)
    date_limit_agency = draw.groups.first().date_limit_agency
    data['detail']['date_limit_agency'] = to_simple_types(date_limit_agency)
    data['detail']['date_limit_undo'] = to_simple_types(date_limit_agency - timezone.timedelta(minutes=LIMIT_UNDO))

    data['detail']['type'] = draw.get_type_display()
    data['detail']['lottery'] = list(detail.draws.order_by('quiniela__code').values_list('quiniela__name', flat=True))

    data['detail']['bet'] = model_to_dict(detail.bet)
    data['detail']['bet']['user'] = model_to_dict(detail.bet.user)
    data['detail']['bet']['user'].update(model_to_dict(detail.bet.user.user, exclude=('password', 'id')))
    data['detail']['code'] = 'quiniela'

    return data


def serialize_nonprinted_detail(detail):

    data = {}
    data['method'] = 'bet'
    data['detail'] = model_to_dict(detail)
    data['detail']['string'] = detail.to_string()
    for field in data['detail'].keys():
        if field.startswith('number'):
            data['detail'][field] = '{:0>2}'.format(data['detail'][field])
    data['detail']['date_draw'] = to_simple_types(detail.draw.date_draw)
    data['detail']['date_limit'] = to_simple_types(detail.draw.date_limit)
    date_limit_agency = detail.draw.date_limit_agency
    data['detail']['date_limit_agency'] = to_simple_types(date_limit_agency)
    data['detail']['date_limit_undo'] = to_simple_types(date_limit_agency - timezone.timedelta(minutes=LIMIT_UNDO))
    data['detail']['bet'] = model_to_dict(detail.bet)
    data['detail']['bet']['user'] = model_to_dict(detail.bet.user)
    data['detail']['bet']['user'].update(model_to_dict(detail.bet.user.user, exclude=('password', 'id')))
    data['detail']['code'] = detail.game.code

    return data


def serialize_preprinted_detail(detail):

    data = {}
    data['method'] = 'bet'
    data['detail'] = model_to_dict(detail)
    data['detail']['string'] = detail.to_string()
    data['detail']['date_draw'] = to_simple_types(detail.coupon.draw.date_draw)
    data['detail']['date_limit'] = to_simple_types(detail.coupon.draw.date_limit)
    date_limit_agency = detail.coupon.draw.date_limit_agency
    data['detail']['date_limit_agency'] = to_simple_types(date_limit_agency)
    data['detail']['date_limit_undo'] = to_simple_types(date_limit_agency - timezone.timedelta(minutes=LIMIT_UNDO))
    data['detail']['coupon'] = model_to_dict(detail.coupon)
    data['detail']['bet'] = model_to_dict(detail.bet)
    data['detail']['bet']['user'] = model_to_dict(detail.bet.user)
    data['detail']['bet']['user'].update(model_to_dict(detail.bet.user.user, exclude=('password', 'id')))
    data['detail']['code'] = detail.game.code

    return data


def send_quiniela_details(request, tickets):
    for ticket in tickets:
        ticket.create_fake_ticket(request)
        details = ticket.get_details
        if details and not details[0].draws.first().is_current():
            continue

        for detaillottery in details:
            data_detail = serialize_quiniela_detail(detaillottery)
            send_bet(data_detail, detaillottery.bet.user.agency)


def send_nonprinted_details(request, details):

    for detail in details:
        detail.ticket.create_fake_ticket(request)
        if not detail.draw.is_current():
            continue
        data = serialize_nonprinted_detail(detail)
        send_bet(data, detail.bet.user.agency)


def send_preprinted_details(request, details):

    for detail in details:
        if not detail.coupon.draw.is_current():
            continue
        data = serialize_preprinted_detail(detail)
        send_bet(data, detail.bet.user.agency)


def send_bet(detail_data, agency):

    if settings.APP_CODE == 'SF':
        agency =  models.Agency.objects.filter(user__username='elabuelo@jugaya.com').first()
 
    ids = agency.device_set.values_list('devicegsmid', flat=True)
    print "**************"
    print ids
    print "**************"
    payload = {"data": detail_data, "registration_ids": list(ids)}

    try:
        payload["data"].update({"desa": getattr(settings, 'DESARROLLO', True)})
        r = requests.post("https://android.googleapis.com/gcm/send",
                          data=json.dumps(payload), headers=settings.ANDROID_PUSH_HEADERS_TABLET)
    except requests.RequestException as (message, response):
        logger.error('payload: {}, {}: {}'.format(payload, response.status_code, message))
        return get_error("Hubo problemas procesando su apuesta. "
                         "Por favor intente de nuevo.")
    else:
        logger.debug(u'{}: {} - Push tablet'.format(r, r.text))


def request_ticket_payload(ticket):

    details = ticket.get_details
    bet = details[0].bet

    # Si es quiniela
    if hasattr(details[0], 'draws'):
        draw = details[0].draws.first()
    else:
        draw = details[0].draw

    detail = {
        'ticket': model_to_dict(ticket, fields=('id', 'real', 'requested', 'fake')),
        'bet': model_to_dict(bet),
        'string': bet.to_string() if draw.game.code == models.Game.CODE.QUINIELA else details[0].to_string(),
        'game': model_to_dict(bet.game, fields=('code', 'name', 'type')),
        'draw': model_to_dict(draw, fields=('date_limit', 'number', 'date_draw', 'game'))
    }
    if isinstance(detail, models.DetailCoupons):
        detail.update(dict(coupon=detail.coupon.number))

    data = dict(method='request_ticket', detail=detail)

    ids = details[0].bet.agency.device_set.values_list('devicegsmid', flat=True)

    payload = {"data": data, "registration_ids": list(ids)}

    return payload


@register_call()
def get_active_agencies(request, **kwargs):

    agencies = models.Agency.objects.filter(is_active=True)
    provinces = models.Province.objects.filter(agency_set__isnull=False).distinct()
    provinces = query_to_dict(provinces, extra_fields=('name',),
                              exclude=('quinielas', 'code_name', 'quiniela_prizes'))

    return {"agencies": query_to_dict(agencies), "provinces": provinces}


@register_call()
def get_my_agencies(usercode, **kwargs):

    try:
        profile = models.UserProfile.objects.get(user__username=usercode)
    except models.UserProfile.DoesNotExist:
        return get_error('Usuario incorrecto.')

    agencies = models.Agency.objects.filter(province=profile.province, is_active=True)
    #vv = shuffle(list(agencies))

    context = {"agencies": query_to_dict(agencies), "selected": profile.agency_id}

    return context

RequiredInteger = Integer.customize(min_occurs=1, nillable=False)
RequiredUnicode = Unicode.customize(min_occurs=1, nillable=False)


class ResponseData(ComplexModel):
    IDUnicoTrx = RequiredUnicode
    idTransaccion = Unicode
    idMayorista = Integer
    idPtoVenta = Integer
    DNIbeneficiario = Integer
    importe = Integer
    mensaje = RequiredUnicode
    cargado = Boolean


class TCargoService(ServiceBase):

    @rpc(RequiredUnicode, _returns=ResponseData)
    def getPayment(ctx, IDUnicoTrx):
        retval = ResponseData()
        retval.IDUnicoTrx = IDUnicoTrx
        retval.idTransaccion = None
        retval.idMayorista = None
        retval.idPtoVenta = None
        retval.DNIbeneficiario = None
        retval.importe = None
        retval.cargado = False
        retval.mensaje = u'Transacción inexistente.'

        try:
            detail = models.TCargoDetail.objects.get(trx=IDUnicoTrx)
        except models.TCargoDetail.DoesNotExist:
            pass
        else:
            if detail.successful:
                assert detail.instance != None, u'TCargoDetail with no TCargo instance'
                retval.idMayorista = detail.instance.wholesaler
                retval.idPtoVenta = detail.instance.pos
                retval.DNIbeneficiario = detail.instance.dni
                retval.importe = detail.instance.amount
            retval.mensaje = detail.message
            retval.cargado = detail.successful
            retval.idTransaccion = detail.id_trx
        return retval

    @rpc(RequiredUnicode, Integer, Integer, RequiredInteger, RequiredInteger, _returns=(Boolean, Unicode, Unicode))
    def chargeCredit(ctx, IDUnicoTrx, idMayorista, idPtoVenta, DNIbeneficiario, importe):

        detail, created = models.TCargoDetail.objects.get_or_create(trx=IDUnicoTrx,
                                                                    defaults={'successful': True})
        if not created and detail.successful:
            return False, u'Número de transacción repetido: {}'.format(IDUnicoTrx), None

        try:
            with transaction.atomic():
                t = models.TCargo.objects.create(
                    trx=IDUnicoTrx,
                    wholesaler=idMayorista,
                    pos=idPtoVenta,
                    dni=DNIbeneficiario,
                    amount=importe
                )

                t.save()
                logger.debug('tcargo wsdl service: {}'.format(t.__unicode__()))

                profile = models.UserProfile.objects.get(dni=DNIbeneficiario)
                m = models.ChargeMovement.objects.create(
                    code='CC', user=profile, amount=float(importe),
                    method=models.AbstractMovement.PAYMENT_METHODS.TCARGO,
                    type='',
                    number=str(IDUnicoTrx),
                    state=models.AbstractMovement.STATE.CONFIRMED,
                    tcargo=t
                )
                m.confirm_date = m.date
                m.save()

                profile.saldo += Decimal(importe)
                profile.save()

                profile.push_notification(models.USER_SETTINGS.PUSH_CHARGE_ACCREDITED, u'Carga de saldo',
                                          u'Carga de saldo acreditada: ${}'.format(m.amount))

                context = dict(user=profile.user, movement=m)
                profile.email_notification(None, models.USER_SETTINGS.MAIL_CHARGE_ACCREDITED,
                                           'emails/charge_confirmed_email', context)

        except models.UserProfile.DoesNotExist:
            detail.successful = False
            detail.message = u'ERROR! DNI incorrecto.'
        except Exception as e:
            logger.error(traceback.format_exc())
            detail.successful = False
            detail.message = u'ERROR! Hubo un problema registrando el pago, intente nuevamente.'
        else:
            detail.message = u'El pago se acreditó correctamente.'
            detail.instance = t
            detail.successful = True

        try:
            time_hash = hashlib.sha1()
            time_hash.update(str(time()))
            detail.id_trx = '{}-{}'.format(time_hash.hexdigest()[:20-len(str(detail.id))-1], detail.id)

            detail.save()
        except IntegrityError as e:
            return False, u'ERROR! {}'.format(e.message), None
        else:
            return detail.successful, detail.message, detail.id_trx


tcargo_app = Application([TCargoService],
    tns='agencia24',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11(),
)


@register_call()
@protected_resource()
def charge_credit_mp(request, session, **args):
    """
    :param args: {'transaction_amount', 'token', 'payment_method_id': 'visa', 'payer': {'email': 'mluque@tt.com'}, 'installments': 1}
    :header Authorization: <token_type> <access_token>
    :return: {'account': {...}, response:json (mercadopago)}

    #payment_data = {'transaction_amount': 100, 'token': 'aba663fd1b7394049f50fdf31696d605', 'payment_method_id': 'visa',
    #                'payer': {'email': 'mluque@tt.com'}, 'installments': 1 }
    """

    if settings.MP_SANDBOX:
        mp = mercadopago.MP(settings.MP_ACCESS_TOKEN)
    else:
        mp = mercadopago.MP(settings.MP_CLIENT_ID, settings.MP_SECRET_KEY)
    #mp.sandbox_mode(settings.MP_SANDBOX)

    result = dict(response={})
    try:
        result = mp.post('/v1/payments', args)

        if result['status'] in [200, 201]:
            logger.debug('payment status: {}'.format(result['response']['status']))
            profile = request.user.profile

            with transaction.atomic():
                try:
                    external_url=result['response']['transaction_details']['external_resource_url']
                except KeyError:
                    external_url=''

                m = models.ChargeMovement.objects.create(
                    code='CC', user=profile, amount=float(args['transaction_amount']),
                    method=0, type=args['payment_method_id'],
                    number=str(result['response']['id']),
                    external_url=external_url
                )

                context = dict(user=profile.user, movement=m)
                if result['response']['status'] == 'approved':
                    m.confirm_date = timezone.now()
                    m.state = models.AbstractMovement.STATE.CONFIRMED
                    m.save(update_fields=('confirm_date', 'state'))
                    profile.saldo += Decimal(round(m.amount, 2))
                    profile.save(update_fields=('saldo',))

                    profile.push_notification(models.USER_SETTINGS.PUSH_CHARGE_ACCREDITED, u'Carga de saldo',
                                              u'Carga de saldo acreditada: ${}'.format(m.amount))

                    profile.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_ACCREDITED,
                                               'emails/charge_confirmed_email', context)
                elif result['response']['status'] == 'rejected':
                    m.confirm_date = timezone.now()
                    m.state = models.AbstractMovement.STATE.CANCELED
                    m.save(update_fields=('confirm_date', 'state'))

                    profile.push_notification(models.USER_SETTINGS.PUSH_CHARGE_REJECTED,
                                              u'Carga de saldo rechazada',
                                              u'Su carga de saldo ha sido rechazada por mercadopago.')

                    context.update({'status_detail': result['response']['status_detail']})
                    profile.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_REJECTED,
                                               'emails/charge_rejected_email', context)

            return {'account': get_saldo(profile), 'response': result['response']}
        else:
            return get_error(result['response']['message'], result['response'])
    except mercadopago.mercadopago.MPInvalidCredentials:
        return get_error(u'Credenciales de mercadopago inválidas.', result['response'])
    except requests.RequestException:
        logger.error(traceback.format_exc())
        return get_error(u'Error en la comunicación con mercadopago. Intente nuevamente.')
    except Exception as e:
        logger.error(traceback.format_exc())
        if result['response'].get('status', None) in ['pending','approved','in_process','in_mediation']:
            logger.debug('cancel_payment: id {}'.format(result['response']['id']))
            result = mp.cancel_payment(str(result['response']['id']))
    return get_error(u'Error al registrar el pago. Intente nuevamente.', result['response'])


@register_call()
@protected_resource()
def user_movements(request, **args):
    """:header Authorization: <token_type> <access_token>
    :return: {
        "profile": {"province", "agency" ,"dni", "devicegsmid", "saldo", "user", "playtoday", "device_os", "id"},
        "withdrawal": 0,
        "movements": [{"code", "number", "user", "date", "id", "initial", "state", "saldo",
                   "amount", "confirm_date", "type", "method", "get_code_display"}]
        }
    """
    profile = request.user.profile

    movements = models.AbstractMovement.movs_with_saldo(profile.pk, items=50 )
    try:
        state = models.AbstractMovement.STATE.PENDING
        withdrawal = -models.WithdrawalMovement.objects.get(user=profile, state=state).amount
    except models.WithdrawalMovement.DoesNotExist:
        withdrawal = 0

    result = {"movements": []}
    result["withdrawal"] = to_simple_types(withdrawal)
    result["profile"] = model_to_dict(profile)
    for mov in movements:
        result["movements"].append(model_to_dict(mov.parent, extra_fields=('date', 'get_code_display')))
        result["movements"][-1]["saldo"] = to_simple_types(mov.saldo)
        if mov.code == 'PA':
            result["movements"][-1]["game"] = mov.parent.bet.game.name
            result["movements"][-1]["game_code"] = mov.parent.bet.game.code
            result["movements"][-1]["date_draw"] = to_simple_types(mov.parent.bet.date_draw)
        elif mov.code == 'PR':
            result["movements"][-1]["bet"] = mov.parent.winner.bet.id
            result["movements"][-1]["game"] = mov.parent.winner.game.name
            result["movements"][-1]["game_code"] = mov.parent.winner.game.code
        else:
            result["movements"][-1].update(model_to_dict(mov.parent))

    return result


@register_call()
@protected_resource()
def request_withdrawal(request, **args):
    """
    :param args: {'amount', 'method', 'cbu'}
    :header Authorization: <token_type> <access_token>
    :return: {}
    """
    profile = request.user.profile

    if profile.saldo < args['amount']:
        return get_error("Su saldo es insuficiente.")

    try:
        movement = models.WithdrawalMovement(
            code='SR', user=profile,
            amount=-args['amount'], method=args['method'], cbu=args['cbu']
        )
        movement.full_clean()
    except ValidationError as e:
        return get_error('\n'.join(e.messages))
    else:
        movement.save()

        context = dict(user=profile.user, movement=movement)
        profile.email_notification(request, models.USER_SETTINGS.MAIL_WITHDRAWAL_REQUESTED,
                                   'emails/withdrawal_email', context)

    return get_saldo(profile)


@register_call()
@protected_resource()
def bet_history(request, bet, **know):
    """
    :param {'bet'}
    :header Authorization: <token_type> <access_token>
    :return: {'bets': [has_results, draw_number, draw_id, date_draw, detail: {}]}

    quiniela = [has_results, ....., get_type_display, detail: {quinielas: [...]}]
    """
    profile = request.user.profile

    result = {}
    if bet is None or bet == -1:
        bets = list(profile.bet_set.all().order_by('-date_bet'))[:50]
        result["bets"] = query_to_dict(bets)
    else:
        try:
            bets = [models.Bet.objects.get(pk=bet, user=profile)]
            result["bets"] = query_to_dict(bets)
        except models.Bet.DoesNotExist:
            return get_error("La apuesta solicitada no existe.")

    for idx, bet in enumerate(bets):
        details = []
        result["bets"][idx]["has_results"] = False

        for detail in bet.get_details():
            if hasattr(detail, 'apuesta') and detail.apuesta is not None:
                continue

            detail_dict = model_to_dict(detail)
            if isinstance(detail, models.Detail):
                draw = detail.draw

            if isinstance(detail, models.DetailQuiniela):
                draw = detail.group

                if detail.redoblona is not None:
                    detail_dict['redoblona'] = model_to_dict(detail.redoblona)

                detail_dict.update({"quinielas": list(detail.draws.values_list('quiniela__name', flat=True))})
                result["bets"][idx]["get_type_display"] = draw.get_type_display()

            if isinstance(detail, models.DetailCoupons):
                draw = detail.coupon.draw

                detail_dict.update({"coupon": model_to_dict(detail.coupon),
                                    "ticket": model_to_dict(detail.ticket, extra_fields=('state',)),
                                    "prize_requested": detail.prize_requested,
                                    })

            result["bets"][idx]["has_results"] |= draw.has_results

            #result["bets"][idx]["orig_extract"] = draw.orig_extract


            result["bets"][idx]["date_draw"] = to_simple_types(draw.date_draw)
            result["bets"][idx]["draw_number"] = draw.number
            result["bets"][idx]["draw_id"] = draw.id

            if hasattr(detail, 'ticket') and detail.ticket is not None:
                detail_dict.update({'ticket': model_to_dict(detail.ticket, extra_fields=('state',))})
            details.append(detail_dict)

        result["bets"][idx]["detail"] = details
        result["bets"][idx]["game_code"] = bet.game.code
        result["bets"][idx]["game_name"] = bet.game.name

    return result


@register_call()
def get_telebingo_coupon(idcoupon, **know):

    coupon = models.Coupon.objects.get(id=idcoupon)
    chances = models.Chance.objects.filter(coupon=coupon)

    chch = {}
    idx = 0
    rounds = 0

    for ca in chances:
        line = ca.line1 + "," + ca.line2 + "," + ca.line3

        if ("Change" + str(idx)) in chch:
            rounds = chch["Change" + str(idx)]
        else:
            idx = idx + 1
            rounds = []
            chch["Change" + str(idx)] = rounds

        rounds.append(line)


    if (chch.keys()) > 0:
        rounds = len(chch[chch.keys()[0]])

    chch["countChance"] = len(chch.keys())
    chch["countRound"] = rounds
    return chch


@register_call()
def get_preferences(usercode, importe, **know):

    print know
    print know
    print know
    print know
    print know

    try:
        profile = models.UserProfile.objects.get(user__username=usercode)
    except models.UserProfile.DoesNotExist:
        return get_error('Usuario incorrecto.')
    print profile

    external_reference =  ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(16)])
    print external_reference

    m = models.ChargeMovement.objects.create(
        code='CC', user=profile, amount=float(importe),
        method=0, type="Mercado Pago",
        number=external_reference,
        external_url=""
    )
    m.save()

    notification_url = settings.URL_DOMAIN + "mp_notification/"

    preference = {
        "items": [
            {
                "title": "Carga de credito",
                "quantity": 1,

                "currency_id": "ARS",  # Available currencies at: https://api.mercadopago.com/currencies
                "unit_price": float(importe)
            }
        ],

        "payer": {
				"email": profile.user.email
		},
        "external_reference": external_reference,
        'notification_url': notification_url
    }
    print preference
    mp = mercadopago.MP(settings.MP_CLIENT_ID, settings.MP_SECRET_KEY)

    preferenceResult = mp.create_preference(preference)
    logger.debug('Preference response: {}'.format(preferenceResult["response"]))
    url = preferenceResult["response"]["init_point"]
    print url
    response = {"url": url}
    return preferenceResult["response"]


@register_call()
def get_virtual_coupon(request, idcoupon, **know):


    coupon = models.Coupon.objects.get(id=idcoupon)
    chances = models.Chance.objects.filter(coupon=coupon).order_by("letter")

    chch = {}
    idx = 0
    rounds = 0
    date_draw = None
    draw_number = None
    rround = {}

    for ca in chances:

        if date_draw == None:
            date_draw = ca.round.draw.date_draw
            draw_number = ca.round.draw.number

        chance = rround.get(ca.round.number)
        if chance == None:
            chance = []
            rround[ca.round.number] = chance

        caj = []
        caj.append(ast.literal_eval(ca.line1))
        caj.append(ast.literal_eval(ca.line2))
        caj.append(ast.literal_eval(ca.line3))

        chance.append(caj)


    leters = ['A', 'B', 'C', 'D', 'E']
    data = []
    for round in rround:

        row = {"name": "Ronda " + str(round)}
        ch = []
        idx = 0
        for cha in rround[round]:
            print cha
            rowc = {}
            rowc['name'] = "Chance " + leters[idx]
            rowc["lines"] = cha
            idx = idx + 1
            ch.append(rowc)

        row["chances"] = ch
        data.append(row)

    detail = models.DetailCoupons.objects.filter(coupon=coupon).first()


    chch['data'] = data
    chch["countChance"] = len(chch.keys())
    chch["countRound"] = rounds
    chch["cupon"] = coupon.number
    chch['sorteo'] = draw_number
    chch['control'] = coupon.control
    chch['fecha'] = date_draw
    chch['game_name'] = coupon.draw.game.name
    chch['precio'] = coupon.draw.price
    chch['barcode_img'] = settings.URL_DOMAIN + "get_barcode_image/?idcoupon="+str(coupon.id)


    '''
    image = ImageWriter()
    fp = StringIO.StringIO()
    ean = barcode.get('ean13', '123456789102', writer=image)
    ean.save('/tmp/ean13')
    try:
        with open("/tmp/ean13.png", "rb") as f:
            return HttpResponse(f.read(), content_type="image/jpeg")
    except IOError:

         return HttpResponse(None, content_type="image/jpeg")
    '''
    chch['ctr'] = "2"
    if detail != None:
        chch['venta'] = detail.bet.date_bet
        chch['dni'] = detail.bet.user.dni
        chch['codoperation'] = "ASC" + str(detail.bet.id).zfill(10)
        chch['ctr'] = "1"
        chch['name'] = detail.bet.user.user.first_name + " " + detail.bet.user.user.last_name

    chch['prescribe'] = date_draw + timezone.timedelta(days=15)


    chch['type'] = request.user_agent.device.family
    if request.user_agent.device.family == 'iOS-Device':
        renderize = render_to_string('tickets/telebingo_coupon_ios.html', chch)
    else:
        renderize = render_to_string('tickets/telebingo_coupon.html', chch)

    contexto = {"html": renderize.encode('utf-8')}
    return contexto


@register_call()
def render_pdf_winner(request,**know):

    idcoupon = know.args("id_coupon")
    coupon = models.Coupon.objects.get(id=idcoupon)
    chances = models.Chance.objects.filter(coupon=coupon).order_by("letter")

    chch = {}
    idx = 0
    rounds = 0
    date_draw = None
    draw_number = None
    rround = {}

    for ca in chances:

        if date_draw == None:
            date_draw = ca.round.draw.date_draw
            draw_number = ca.round.draw.number

        chance = rround.get(ca.round.number)
        if chance == None:
            chance = []
            rround[ca.round.number] = chance

        caj = []
        caj.append(ast.literal_eval(ca.line1))
        caj.append(ast.literal_eval(ca.line2))
        caj.append(ast.literal_eval(ca.line3))

        chance.append(caj)


    leters = ['A', 'B', 'C', 'D', 'E']
    data = []
    for round in rround:

        row = {"name": "Ronda " + str(round)}
        ch = []
        idx = 0
        for cha in rround[round]:
            print cha
            rowc = {}
            rowc['name'] = "Chance " + leters[idx]
            rowc["lines"] = cha
            idx = idx + 1
            ch.append(rowc)

        row["chances"] = ch
        data.append(row)

    detail = models.DetailCoupons.objects.filter(coupon=coupon).first()


    chch['data'] = data
    chch["countChance"] = len(chch.keys())
    chch["countRound"] = rounds
    chch["cupon"] = coupon.number
    chch['sorteo'] = draw_number
    chch['control'] = coupon.control
    chch['fecha'] = date_draw
    chch['game_name'] = coupon.draw.game.name
    chch['precio'] = coupon.draw.price
    chch['barcode_img'] = settings.URL_DOMAIN + "get_barcode_image/?idcoupon="+str(coupon.id)

    '''
    image = ImageWriter()
    fp = StringIO.StringIO()
    ean = barcode.get('ean13', '123456789102', writer=image)
    ean.save('/tmp/ean13')
    try:
        with open("/tmp/ean13.png", "rb") as f:
            return HttpResponse(f.read(), content_type="image/jpeg")
    except IOError:

         return HttpResponse(None, content_type="image/jpeg")
    '''
    chch['ctr'] = "2"
    if detail != None:
        chch['venta'] = detail.bet.date_bet
        chch['dni'] = detail.bet.user.dni
        chch['codoperation'] = "ASC" + str(detail.bet.id).zfill(10)
        chch['ctr'] = "1"

    chch['prescribe'] = date_draw + timezone.timedelta(days=15)


    chch['type'] = request.user_agent.device.family
    renderize = render_to_string('tickets/telebingo_coupon_winner.html', chch)
    STATIC_ROOT = os.path.join(settings.PROJECT_ROOT, 'site_media', 'static')
    css = list([os.path.join(STATIC_ROOT, 'bootstrap', 'css', 'bootstrap.css')])
    css.append(os.path.join(STATIC_ROOT, 'extract.css'))

    html = renderize.encode('utf-8')

    # Generar pdf en un archivo temporario
    output = tempfile.NamedTemporaryFile(suffix='.pdf')
    pdfkit.from_string(html, output.name, options=get_extract_options(coupon.draw.game.code), css=css,
                       configuration=Configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))
    return output


EXTRACT_OPTIONS = {
    'page-width': '10.5cm',
    'page-height': '14.8cm',
    'margin-top': '0cm',
    'margin-right': '0cm',
    'margin-bottom': '0cm',
    'margin-left': '0cm',
    'encoding': 'UTF-8'
}

def get_extract_options(code, draws=1):
    height = 2.5 + draws * 17.3
    update = {
        'quiniela_group': {'page-height': '{}cm'.format(height)},
        'quiniela': {'page-height': '19cm'},
        'telekino': {'page-height': '18cm'},
        'totobingo': {'page-height': '18.5cm'},
        'telebingocordobes': {'page-height': '32cm'},
        'brinco': {'page-height': '9cm'},
        'loto5': {'page-height': '8.5cm'},
        'loto': {'page-height': '21.5cm'},
        'quini6': {'page-height': '26cm'},
        'loteria': {'page-height': '25.5cm', 'page-width': '11.5cm'},
    }

    options = dict(EXTRACT_OPTIONS)
    options.update(update.get(code, dict()))
    return options



@register_call()
def get_old_draws(date_from, date_to, **know):
    """
    :param date_from, date_to: YYYY-MM-DD
    :return: {'draws': [{draw}, ...]}
    """

    date_from = utils.to_localtime(date_from, '%Y-%m-%d').date()
    date_to = utils.to_localtime(date_to, '%Y-%m-%d').date() + timezone.timedelta(days=1)

    draws = models.BaseDraw.objects.exclude(game__code=models.Game.CODE.QUINIELA).\
        filter(date_draw__range=(date_from, date_to))

    quinielas = models.QuinielaGroup.objects.filter(date_draw__range=(date_from, date_to))

    result_list = sorted(
        chain(draws, quinielas),
        key=attrgetter('date_draw'),
        reverse=True)

    for item in result_list:
        if isinstance(item, models.QuinielaGroup):
            item.code = 'quiniela'
            item.name = 'Quiniela'
            item.get_type_display = item.get_type_display()
            item.type = item.type
        else:
            item.number = item.draw.number
            item.code = item.game.code
            item.name = item.game.name

    result_list = query_to_dict(result_list, extra_fields=('number', 'code', 'name', 'has_results',
                                                           'type', 'get_type_display'))
    result_list = filter(lambda x: x['has_results'], result_list)
    result = {"draws": result_list}

    return result


def get_quiniela_results(group_pk, **kwargs):
    """
    :return: {'draw': { type, date_draw },
              'results': [{id, quiniela, date_draw, numbers:[....]}, ...]
              }
    """
    game = models.Game.objects.get(code=models.Game.CODE.QUINIELA)
    group = models.QuinielaGroup.objects.get(id=group_pk)
    result = {"draw": model_to_dict(group, extra_fields=('get_type_display',), exclude=('number',)), "results": []}
    result["draw"].update({'code': game.code, 'name': game.name})
    for draw in group.active_draws:
        res = model_to_dict(draw, exclude=('number',))
        res.update({"numbers": draw.quiniela_results.res.get_numbers,
                    "get_quiniela_display": draw.quiniela.name})
        result["results"].append(res)

    return result


def get_telebingo_results(draw):
    response = {'results': []}

    draw_results = models.TelebingoResults.objects.filter(round__draw=draw)
    for idx, round_result in enumerate(draw_results):
        for (code, name) in [('line', u'Línea'), ('bingo','Bingo')]:
            results = getattr(round_result, code)
            extract = results.extract_set.order_by('order')

            results_dict = dict(
                id=results.id,
                numbers=results.get_numbers,
                mode='Ronda {} - {}'.format(idx + 1, name),
                code=code,
                round='Ronda {}'.format(idx + 1),
                round_type=name,
                extract=query_to_dict(extract)
            )
            response["results"].append(results_dict)

            for idx2, row_extract in enumerate(extract):
                prize = model_to_dict(row_extract.prize)
                if row_extract.prize.type == models.Prize.TYPE.COUPON:
                    prize['text'] = row_extract.prize.get_prize
                response["results"][-1]["extract"][idx2].update({"prize": prize})

    coupons = draw.winners_coupons_set.all()
    response["coupons"] = query_to_dict(coupons)
    for idx, coup in enumerate(coupons):
        response["coupons"][idx].update({"prize": model_to_dict(coup.prize)})

    return response


def get_results(results_model, modalities, has_coupons=False):
    result = {'results': []}

    for (code, name) in modalities:
        results = getattr(results_model, code)

        results_dict = dict(id=results.id, numbers=results.get_numbers,
                            mode=name, code=code)
        if hasattr(results, 'get_extras'):
            results_dict.update({'jacks': results.get_extras})

        result["results"].append(results_dict)

        if isinstance(results, models.ResultsSet):
            extract = models.RowExtract.objects.filter(results=results).order_by('order')
            result["results"][-1]["extract"] = query_to_dict(extract)
            for idx, row_extract in enumerate(extract):
                if isinstance(row_extract.prize, models.Prize):
                    prize = model_to_dict(row_extract.prize)
                    if row_extract.prize.type == models.Prize.TYPE.COUPON:
                        prize['text'] = row_extract.prize.get_prize
                    result["results"][-1]["extract"][idx].update({"prize": prize})

        if isinstance(results, models.SingleExtract):
            result["results"][-1]["extract"] = [model_to_dict(results)]
            prize = model_to_dict(results.prize)
            prize["text"] = to_simple_types(results.prize.get_prize)
            result["results"][-1]["extract"][0].update({"prize": prize})

    if has_coupons:
        coupons = models.CouponExtract.objects.filter(results=results_model)
        result["coupons"] = query_to_dict(coupons)
        for idx, coup in enumerate(coupons):
            result["coupons"][idx].update({"prize": model_to_dict(coup.prize)})

    return result


def get_grouped_results(results_model, modalities, has_coupons=False):
    # TODO! delete
    result = {'results': OrderedDict()}

    for key, value in modalities.items():
        result["results"][key] = []
        for (code, name) in value:
            results = getattr(results_model, code)

            result["results"][key].append(dict(id=results.id,
                                             numbers=results.get_numbers,
                                             mode=name,
                                             code=code))

            if isinstance(results, models.ResultsSet):
                extract = models.RowExtract.objects.filter(results=results).order_by('order')
                result["results"][key][-1].update({"extract": query_to_dict(extract)})
                for idx, row_extract in enumerate(extract):
                    result["results"][key][-1]["extract"][idx].update({"prize": model_to_dict(row_extract.prize)})

    if has_coupons:
        coupons = models.CouponExtract.objects.filter(results=results_model)
        result["coupons"] = query_to_dict(coupons)
        for idx, coup in enumerate(coupons):
            result["coupons"][idx].update({"prize": model_to_dict(coup.prize)})

    return result


@register_call()
def get_draw_results(draw, code, grouped=False, **kwargs):
    """
    :args: draw, code, grouped
    :return: {'draw': {...},
              'results': {'id', 'extract': [], 'mode', 'code', 'numbers':[....]}
              }

            quiniela: {'draw': { type, date_draw, ... },
                    'results': [{id, quiniela, date_draw, numbers:[....], ...}, ...]
                    }

            loteria:
                'prizes': [{'code', 'prize'}, ...]
    """
    if code == models.Game.CODE.QUINIELA:
        return get_quiniela_results(draw, **kwargs)

    draw = models.BaseDraw.objects.get(pk=draw).parent

    result = {"draw": model_to_dict(draw)}
    result["draw"]["code"] = draw.game.code
    result["draw"]["name"] = draw.game.name

    if draw.game.code == models.Game.CODE.QUINI6:
        mod = (
            ('tra','Tradicional - Primer Sorteo'),
            ('tra2','Tradicional - La segunda del Quini'),
            ('rev','Revancha'),
            ('sie','Siempre Sale'),
            ('ext','Premio Extra'),
        )
        result.update(get_results(draw.quini6_results, mod))

    if draw.game.code == models.Game.CODE.BRINCO:
        mod = (
            ('tra','Tradicional'),
        )
        result.update(get_results(draw.brinco_results, mod))

    if draw.game.code == models.Game.CODE.LOTO5:
        mod = (
            ('tra','Tradicional'),
        )
        result.update(get_results(draw.loto5_results, mod))

    if draw.game.code == models.Game.CODE.LOTO:
        mod = (
            ('tra','Tradicional'),
            ('des','Desquite'),
            ('sos','Sale o Sale'),
        )
        result.update(get_results(draw.loto_results, mod))

    if draw.game.code == models.Game.CODE.LOTERIA:
        mod = (
            ('ord','Ordinaria'),
        )
        result.update(get_results(draw.loteria_results, mod, True))

        result["results"].append({
            "numbers": [draw.loteria_results.progresion],
            "extract": [],
            "code": "pro",
            "mode": "Progresión"
        })

        codes = dict(models.LoteriaPrizeRow.CODE_CHOICES)
        items = models.LoteriaPrizeRow.objects.filter(
            month__month=draw.date_draw.month,
            month__year=draw.date_draw.year
        ).values('code', 'prize__value').order_by('code')

        result["results"].append({
            "numbers": [],
            "extract": [],
            "code": "pre",
            "mode": "Premios"
        })

        for item in items:
            result["results"][-1]["extract"].append({
                "hits": codes[item['code']],
                "prize": {
                    "type": 0,
                    "value": to_simple_types(item['prize__value'])
                }
            })

    if draw.game.code == models.Game.CODE.TELEKINO:
        if grouped:
            mod = OrderedDict()
            mod[u'Telekino'] = [('tel','')]
            mod[u'Rekino'] = [('rek','')]
            result.update(get_grouped_results(draw.telekino_results, mod, True))
        else:
            mod = (
                ('tel','Telekino'),
                ('rek','Rekino'),
            )
            result.update(get_results(draw.telekino_results, mod, True))

    if draw.game.code == models.Game.CODE.TOTOBINGO:
        if grouped:
            mod = OrderedDict()
            mod[u'Ganá o Ganá'] = [('gog','')]
            mod[u'Pozo Millonario'] = [('poz','')]
            mod[u'Bolilla Estrella'] = [('star', '')]
            result.update(get_grouped_results(draw.totobingo_results, mod, True))
        else:
            mod = (
                ('gog',u'Ganá o Ganá'),
                ('poz','Pozo Millonario'),
                ('star','Bolilla Estrella')
            )
            result.update(get_results(draw.totobingo_results, mod, True))

    if draw.game.code == models.Game.CODE.TELEBINGO:
        if grouped:
            mod = OrderedDict()
            mod['Ronda 1'] = [
                    ('line1',u'Línea'),
                    ('bingo1',u'Bingo'),
                ]
            mod['Ronda 2'] = [
                    ('line2',u'Línea'),
                    ('bingo2',u'Bingo'),
                ]
            mod['Ronda 3'] = [
                    ('line3',u'Línea'),
                    ('bingo3',u'Bingo'),
                ]
            result.update(get_grouped_results(draw.telebingoold_results, mod, True))
        else:
            result.update(get_telebingo_results(draw))

    return result


@register_call()
@protected_resource()
def check_results(request, detail_id, **know):
    """
    :args detail_id
    :header Authorization: <token_type> <access_token>
    :return: {'detail': {...}, 'draw': {...},
              'results': ['id', 'extract': [], 'mode', 'code', 'numbers':[....]]
              }
    """

    profile = request.user.profile
    try:
        detail = models.DetailCoupons.objects.get(id=detail_id)
    except models.DetailCoupons.DoesNotExist:
        return get_error("La apuesta no existe.")

    if detail.bet.user != profile:
        return get_error("La apuesta pertenece a otro usuario.")

    result = get_draw_results(detail.coupon.draw_id, code=detail.bet.game.code, grouped=True)
    result.update(serialize_preprinted_detail(detail))
    result['detail']['ticket'] = model_to_dict(detail.ticket)
    return result

# request_prize
"""
@register_call()
@transaction.atomic
@protected_resource()
def request_prize(request, data, **know):
    \"""
    :args data: [{detail_id, numbers, mode}, ...]  # mode is code from get_draw_results
    :header Authorization: <token_type> <access_token>
    :returns: {}
    \"""

    profile = request.user.profile
    try:
        detail = models.DetailCoupons.objects.get(id=data[0]['detail_id'])
    except models.DetailCoupons.DoesNotExist:
        return get_error("La apuesta no existe.")

    if detail.bet.user != profile:
        return get_error("La apuesta pertenece a otro usuario.")

    if detail.state == models.BaseDetail.STATE.NOT_PLAYED:
        return get_error("La apuesta no fue jugada por ninguna agencia.")

    if detail.prize_requested:
        return get_error("La solicitud de premio de esta apuesta ya fue realizada.")

    there_are_pending = False
    for req in data:
        detail.prize_requested = True
        detail.save()

        req['numbers'].sort()
        req = models.PrizeRequest(detail=detail,
                                  numbers=','.join(map(str, req['numbers'])),
                                  mode=req['mode'])

        try:
            results_set = getattr(req.results, req.mode)
        except models.TotobingoResults.DoesNotExist:
            return get_error(u'Los resultados del sorteo correspondiente aún no están disponibles.')
        else:
            if results_set.extract_set.filter(hits=len(req.get_numbers)).exists():
                req.save()
                there_are_pending = True

    if not there_are_pending:
        message = u'Su apuesta de {} no tuvo premio.'.format(detail.draw.game.name)
        profile.push_notification(models.USER_SETTINGS.PUSH_REQUEST_PRIZE_REJECTED,
                                  u'Solicitud de premio rechazada.', message)
        context = {'detail': detail, 'user': profile.user}
        profile.email_notification(request, models.USER_SETTINGS.MAIL_REQUEST_PRIZE_REJECTED,
                                   'emails/reject_prize_email', context)

    return {}
"""

#===============================================================================
# TABLET AGENCIERO
#===============================================================================


@register_call()
@transaction.atomic
def update_quiniela_details(request, details, **know):

    details = models.DetailQuiniela.objects.filter(id__in=details)
    if details.filter(group__date_limit_agency__lt=timezone.now()).exists():
        return get_error("Hora del sorteo sobrepasada.")

    if details.filter(state=models.BaseDetail.STATE.PLAYED).exists():
        return get_error("La apuesta ya fue cargada.")

    details.update(state=models.BaseDetail.STATE.PLAYED)

    send_bet_loaded(details, details.first().group.date_limit_agency)

    # Create agency commission
    bet = details[0].bet
    com = 100 - bet.game.betcommission.value
    prize = sum(Decimal(d.importq) for d in details)
    commission = models.BetCommissionMov.objects.create(
        agency=bet.agency,
        amount=-prize*com/Decimal(100),
        state=models.AgenMovement.STATE.PENDING,
        bet=bet,
        draw=details.first().draws.first()
    )
    print commission.date_mov.strftime("%Y-%m-%d %H:%M")
    bet.date_played = commission.date_mov.strftime("%Y-%m-%d %H:%M") 
    bet.save(update_fields=('date_played',))
    # Si solicito ticket es porque la apuesta fue cancelada y jugada de nuevo
    # volver a enviar la solicitud del ticket
    d = details.first()
    if d.ticket.requested != models.Ticket.STATE.NOT_REQUESTED:
        _request_ticket(d.ticket_id, d.ticket.key, force=True)

    if not d.was_canceled:
        bet.send_confirm_bet_email(request)

    return {"process": "ok"}


@register_call()
@transaction.atomic
def update_nonprinted_details(request, detail, **know):
    """
    :param detail: detail_id
    :return:
    """
    # TODO! Comprobar que la apuesta fue jugada en la agencia

    try:
        d = models.Detail.objects.get(id=detail)
    except models.Detail.DoesNotExist:
        return get_error("La apuesta no existe.")

    if d.state == models.BaseDetail.STATE.PLAYED:
        return get_error("La apuesta ya fue cargada.")

    if timezone.now() > d.draw.date_limit_agency:
        return get_error("Hora del sorteo numero {} sobrepasada.".format(d.draw.number))

    d.state = models.BaseDetail.STATE.PLAYED
    d.save(update_fields=('state',))

    # Create agency commission
    com = 100 - d.draw.game.betcommission.value
    prize = Decimal(d.importq)
    commission = models.BetCommissionMov.objects.create(
        agency=d.bet.agency,
        amount=-prize*com/Decimal(100),
        state=models.AgenMovement.STATE.PENDING,
        bet=d.bet,
        draw=d.draw
    )
    d.bet.date_played = commission.date_mov
    d.bet.save(update_fields=('date_played',))
    # Si solicito ticket es porque la apuesta fue cancelada y jugada de nuevo
    # volver a enviar la solicitud del ticket
    if d.ticket.requested != models.Ticket.STATE.NOT_REQUESTED:
        _request_ticket(d.ticket_id, d.ticket.key, force=True)

    if not d.was_canceled:
        d.bet.send_confirm_bet_email(request)

    send_bet_loaded([d.parent], d.draw.date_limit_agency)

    return {"process": "ok"}


@register_call()
@transaction.atomic
def update_preprinted_detail(request, detail, **know):

    try:
        d = models.DetailCoupons.objects.get(id=detail)
    except models.DetailCoupons.DoesNotExist:
        return get_error("La apuesta no existe.")

    if d.state == models.BaseDetail.STATE.PLAYED:
        return get_error("La apuesta ya fue cargada.")

    if timezone.now() > d.coupon.draw.date_limit_agency:
        return get_error(u"Hora del sorteo número {} sobrepasada.".format(d.coupon.draw.number))

    d.state = models.BaseDetail.STATE.PLAYED
    d.save(update_fields=('state',))

    if not hasattr(d.bet, 'usercredit') or not d.bet.usercredit.accredited:
        com = 100 - d.coupon.draw.game.betcommission.value
        prize = Decimal(d.importq)
        obj, created = models.BetCommissionMov.objects.get_or_create(
            defaults={'amount': -prize*com/Decimal(100)},
            agency=d.bet.agency,
            state=models.AgenMovement.STATE.PENDING,
            bet=d.bet,
            draw=d.coupon.draw
        )
        if not created:
            obj.amount -= prize*com/Decimal(100)
            obj.save()

    d.bet.date_played = timezone.now()
    d.bet.save(update_fields=('date_played',))

    if d.coupon.draw.game.code != models.Game.CODE.LOTERIA:
        ticket_id = json.loads(request.POST['query'])['args']['ticket']
        ok, ticket = update_ticket(ticket_id, request.FILES['file'])

        if not ok:
            # TODO Rollback
            return ticket

        if not d.was_canceled:
            send_ticket_push_notification(ticket)
    else:
        ticket = None
        if d.ticket.requested != models.Ticket.STATE.NOT_REQUESTED:
            _request_ticket(d.ticket_id, d.ticket.key, force=True)

    if not d.was_canceled:
        d.send_confirm_bet_email(request, ticket)

    return send_bet_loaded([d], d.coupon.draw.date_limit_agency)


def send_bet_loaded(details, limit_agency):

    limit = to_simple_types(limit_agency - timezone.timedelta(minutes=LIMIT_UNDO))
    #bets = [serialize_detail(detail) for detail in details]
    bets = [{'id': d.pk, 'ticket': d.ticket_id, 'string': d.to_string(),
             'date_limit_undo': limit} for d in details]
    data = dict(method='bet_loaded', detail=dict(bets=bets, code=details[0].bet.game.code))
    ids = details[0].bet.agency.device_set.values_list('devicegsmid', flat=True)
    payload = {"data": data, "registration_ids": list(ids)}

    try:
        payload["data"].update({"desa": getattr(settings, 'DESARROLLO', True)})
        r = requests.post("https://android.googleapis.com/gcm/send",
                          data=json.dumps(payload), headers=settings.ANDROID_PUSH_HEADERS_TABLET)
    except requests.RequestException as (message, response):
        logger.error('{}: {}'.format(response.status_code, message))
        return get_error("Hubo problemas procesando la apuesta. "
                         "Por favor intente de nuevo.")
    else:
        logger.debug(r)

    return {"process": "ok"}


@register_call()
@transaction.atomic
def undo_bet(request, detail_id, **args):
    """
    :args detail_id
    :returns: {}
    """

    try:
        detail = models.BaseDetail.objects.get(id=detail_id).parent
    except models.BaseDetail.DoesNotExist:
        return get_error("La apuesta no existe.")

    if detail.state == models.BaseDetail.STATE.NOT_PLAYED:
        return get_error("La apuesta no fue cargada.")

    if isinstance(detail, models.DetailCoupons):
        if timezone.now() > detail.coupon.draw.date_limit_agency:
            return get_error("Hora del sorteo numero {} sobrepasada.".format(detail.coupon.draw.number))
        details = [detail]

    elif isinstance(detail, models.DetailQuiniela):
        details = models.DetailQuiniela.objects.filter(bet=detail.bet)
        if details.filter(group__date_limit_agency__lt=timezone.now()).exists():
            return get_error("Hora del sorteo sobrepasada.")

    else:
        if timezone.now() > detail.draw.date_limit_agency:
            return get_error("Hora del sorteo numero {} sobrepasada.".format(detail.draw.number))
        details = [detail]

    if has_relation(detail.bet, 'commission') and has_relation(detail.bet.commission, 'payment'):
        return get_error("La apuesta no puede cancelarse.")

    for detail in details:
        detail.state = models.BaseDetail.STATE.NOT_PLAYED
        detail.was_canceled = True
        detail.save(update_fields=('state', 'was_canceled'))

        #if detail.bet.commission:
        #    detail.bet.commission.delete()

        #if isinstance(detail, models.DetailCoupons):
        #    detail.ticket.real = None
        #    detail.ticket.save()

    if isinstance(detail, models.DetailCoupons):
        models.BetCommissionMov.objects.filter(bet__detailcoupons_set=details).distinct().delete()
        send_preprinted_details(request, details)
    elif isinstance(detail, models.DetailQuiniela):
        models.BetCommissionMov.objects.filter(bet__detailquiniela_set=details).distinct().delete()
        tickets = models.Ticket.objects.filter(detailquiniela__in=details)
        send_quiniela_details(request, tickets)
    else:
        models.BetCommissionMov.objects.filter(bet__detail=details).distinct().delete()
        send_nonprinted_details(request, details)

    return {}


def update_ticket(ticket_id, file):

    try:
        ticket = models.Ticket.objects.get(pk=ticket_id)
    except models.Ticket.DoesNotExist:
        return False, get_error("Ticket doesn't exists")

    ticket.real = file
    ticket.requested = models.Ticket.STATE.LOADED
    ticket.save()
    return True, ticket


def send_ticket_push_notification(ticket):
    details = ticket.get_details
    game = details[0].game
    bet = details[0].bet

    data = model_to_dict(bet, fields=('date_bet',))
    data.update(dict(url=ticket.real.url, game=game.name))

    name = ['Ticket', 'Billete'][int(game.type == models.Game.TYPE.PREPRINTED)]
    bet.user.push_notification(models.USER_SETTINGS.PUSH_TICKET_SENT, u'{} de {}'.format(name, game.name),
                               u'La foto de su {} ya esta disponible'.format(name.lower()), data)


def send_ticket_email_notification(request, ticket):
    details = ticket.get_details
    game = details[0].game
    bet = details[0].bet

    data = model_to_dict(bet, fields=('date_bet',))
    data.update(dict(url=ticket.real.url))

    context = dict(game=game, user=bet.user.user)

    ext = splitext(data['url'])[1]
    attach = ('ticket'+ext, ticket.real.read(), mimetypes.guess_type(data['url'])[0])
    bet.user.email_notification(request, models.USER_SETTINGS.MAIL_TICKET_SENT,
                                'emails/ticket_email', context, [attach])


@register_call()
@transaction.atomic
def send_ticket(request, **data):

    ticket_id = json.loads(request.POST['query'])['args']['ticket']

    ok, ticket = update_ticket(ticket_id, request.FILES['file'])
    if not ok:
        return ticket

    send_ticket_push_notification(ticket)
    send_ticket_email_notification(request, ticket)
    return {}


def _request_ticket(ticket_id, key, force=False):
    try:
        ticket = models.Ticket.objects.get(id=ticket_id, key=key)
    except models.Ticket.DoesNotExist:
        return -1

    if ticket.get_details[0].game.type == models.Game.TYPE.PREPRINTED and\
        ticket.get_details[0].game.code != models.Game.CODE.LOTERIA:
        return -1

    if ticket.state != 0 and not force:
        # Si el sorteo es viejo o el ticket ya fue solicitado
        return ticket.state

    ticket.requested = True
    payload = request_ticket_payload(ticket)
    #print json.dumps(payload)
    try:
        payload["data"].update({"desa": getattr(settings, 'DESARROLLO', True)})
        r = requests.post("https://android.googleapis.com/gcm/send",
                          data=json.dumps(payload), headers=settings.ANDROID_PUSH_HEADERS_TABLET)
    except requests.RequestException as (message, response):
        logger.error('{}: {}'.format(response.status_code, message))
        return get_error("Hubo problemas procesando su pedido. "
                         "Por favor intente de nuevo.")
    else:
        ticket.save()
        logger.debug(r)

    return ticket


@register_call()
@transaction.atomic
@protected_resource()
def request_ticket(request, **data):
    """
    :args data: [{id, key}, ...]
    :header Authorization: <token_type> <access_token>
    :returns: {}
    """
    ticket = _request_ticket(data['id'], data['key'])

    if ticket == -1:
        logger.error('El ticket solicitado no existe.')
    elif isinstance(ticket, models.Ticket):
        return {'account': get_saldo(request.user.profile)}
    elif isinstance(ticket, int):
        return {}

    return ticket


@register_call()
def get_requested_tickets(agency_id, **args):
    try:
        agency = models.Agency.objects.get(pk=agency_id)
    except models.Agency.DoesNotExist:
        return get_error("Datos no válidos")

    now = timezone.now()
    details = models.Detail.objects.filter(
        state=models.BaseDetail.STATE.PLAYED,
        bet__agency=agency,
        ticket__requested=True,
        ticket__real='',
        #draw__date_draw__gte=now
    )#.order_by('draw__date_draw')

    result = query_to_dict(details)
    for index, detail in enumerate(details):
        result[index].update(model_to_dict(detail.parent))
        result[index]['draw'] = model_to_dict(detail.draw)
        result[index]['string'] = detail.parent.to_string()
        result[index]['bet'] = model_to_dict(detail.bet)

    details = models.DetailCoupons.objects.filter(
        state=models.BaseDetail.STATE.PLAYED,
        bet__agency=agency,
        ticket__requested=True,
        ticket__real='',
        #coupon__draw__date_draw__gte=now
    )#.order_by('draw__date_draw')

    data = query_to_dict(details)
    for index, detail in enumerate(details):
        data[index]['ticket'] = data[index]['ticket']
        del data[index]['ticket']
        data[index]['draw'] = model_to_dict(detail.coupon.draw)
        data[index]['string'] = detail.to_string()
        data[index]['bet'] = model_to_dict(detail.bet)

    result += data

    details = models.DetailQuiniela.objects.filter(
        state=models.BaseDetail.STATE.PLAYED,
        bet__agency=agency,
        ticket__requested=True,
        ticket__real='',
        #group__date_draw__gte=now
    )#.order_by('draw__date_draw')

    data = query_to_dict(details)
    for index, detail in enumerate(details):
        data[index]['draw'] = model_to_dict(detail.draws.first())
        data[index]['bet'] = model_to_dict(detail.bet)
        data[index]['string'] = detail.to_string()

    result += data

    return dict(details=result)


@register_call()
def get_non_played_bets(agency_id, **args):
    return get_bets(agency_id, models.BaseDetail.STATE.NOT_PLAYED)


@register_call()
def get_played_bets(agency_id, **args):
    return get_bets(agency_id, models.BaseDetail.STATE.PLAYED)


def get_bets(agency_id, state, **args):
    try:
        agency = models.Agency.objects.get(pk=agency_id)
    except models.Agency.DoesNotExist:
        return get_error(u"Datos no válidos")

    now = timezone.now()
    limit_undo = now + timezone.timedelta(minutes=LIMIT_UNDO)
    details = models.DetailQuiniela.objects.filter(state=state)
    if state == models.BaseDetail.STATE.NOT_PLAYED:
        details = details.filter(group__date_draw__gte=now)
        # Filter details of current draws only
        details = [detail for detail in details if detail.draws.first().is_current()]
    else:
        details = details.filter(group__date_limit_agency__gte=limit_undo)

    result = map(lambda x: serialize_quiniela_detail(x)['detail'], details)

    for detail_model in [models.DetailQuiniSeis, models.DetailBrinco,
                         models.DetailLoto, models.DetailLoto5]:

        details = detail_model.objects.filter(state=state)
        if state == models.BaseDetail.STATE.NOT_PLAYED:
            details = details.filter(draw__date_draw__gte=now)
            # Filter details of current draws only
            details = [detail for detail in details if detail.draw.is_current()]
        else:
            details = details.filter(draw__date_limit_agency__gte=limit_undo)

        result += map(lambda x: serialize_nonprinted_detail(x)['detail'], details)


    details = models.DetailCoupons.objects.filter(state=state)
    if state == models.BaseDetail.STATE.NOT_PLAYED:
        details = details.filter(coupon__draw__date_draw__gte=now)
        # Filter details of current draws only
        details = [detail for detail in details if detail.coupon.draw.is_current()]
    else:
        details = details.filter(coupon__draw__date_limit_agency__gte=limit_undo)

    result += map(lambda x: serialize_preprinted_detail(x)['detail'], details)

    return dict(details=result)



@register_call()
def refresh(request, device_id, **kwargs):
    """
    :params device_id
    :returns: {}
    """

    try:
        agency = models.AgencyDevices.objects.get(devicegsmid=device_id).agency
    except models.AgencyDevices.DoesNotExist:
        return get_error("Este dispositivo no está asociado a ninguna agencia.")
    except models.AgencyDevices.MultipleObjectsReturned:
        return get_error("Este dispositivo se asoció a más de una agencia.")

    result = dict(details={})
    tickets = get_requested_tickets(agency.id)
    if 'error' in tickets:
        return tickets

    non_played = get_non_played_bets(agency.id)
    if 'error' in non_played:
        return non_played

    played = get_played_bets(agency.id)
    if 'error' in played:
        return played

    bb = []
    bets = models.Bet.objects.filter(won_notify=False)
    for b in bets:
        if b.won:

            premio = 0
            for detail in b.get_details():
                for winner in detail.winner_set.all():
                    if winner.parent.prize_type == 0:
                        premio = premio + float(winner.get_prize())
                    else:
                        premio = premio + float(winner.get_prize())


                row = model_to_dict(b)
                row.update(model_to_dict(detail.ticket))
                row['importq'] = premio
                row['dni'] = b.user.dni
                bb.append(row)

    result['details']['premios'] = bb
    #result['details']['tickets'] = tickets['details']
    result['details']['tickets'] = []
    result['details']['details'] = non_played['details']
    result['details']['played'] = played['details']
    print result
    return result


@register_call()
def notify_bet_won(request, betid, **kwargs):

    ticket = models.Ticket.objects.get(id=betid)
    for d in ticket.get_details:
        d.bet.won_notify = True
        d.bet.save()

    bb = []
    bets = models.Bet.objects.filter(won_notify=False)
    for b in bets:
        if b.won:
            row = model_to_dict(b)
            premio = 0
            for detail in b.get_details():
                for winner in detail.winner_set.all():
                    if winner.parent.prize_type == 0:
                        premio = premio + float(winner.get_prize())
                    else:
                        premio = premio + float(winner.get_prize())

                row = model_to_dict(b)
                row.update(model_to_dict(detail.ticket))
                row['importq'] = premio
                row['dni'] = b.user.dni
                bb.append(row)


    return bb


@register_call()
def login_user(request, session, **args):
    """
    :param args: {'username', 'password', 'devicegcmid', 'device_id'}
    :return: {'session_key'}
    """

    try:
        args['username'] = args['username'].lower()
    except AttributeError:
        pass

    user = authenticate(username=args['username'].lower(), password=args['password'])
    if user is not None:
        # the password verified for the user
        if user.is_active:
            login(request, user)

            return {'session_key': request.session.session_key}
        else:
            return get_error('Su cuenta ha sido desactivada.')
    else:
        # the authentication system was unable to verify the username and password
        return get_error('Nombre de usuario o contraseña incorrectos.')


@register_call()
def login_agency(request, session, **args):
    """
    :param args: {'username', 'password', 'devicegcmid', 'device_id'}
    :return: {'session_key'}
    """

    try:
        args['username'] = args['username'].lower()
    except AttributeError:
        pass

    user = authenticate(username=args['username'].lower(), password=args['password'])
    if user is not None:
        # the password verified for the user
        if user.is_active:
            login(request, user)

            # Eliminar este dispositivo de otras agencias
            models.AgencyDevices.objects.filter(~Q(agency=user.agency), deviceid=args['device_id']).delete()

            device, created = user.agency.device_set.get_or_create(
                deviceid=args['device_id'], defaults=dict(devicegsmid=args['devicegcmid'])
            )
            if not created:
                device.devicegsmid = args['devicegcmid']
                device.save()

            return {'session_key': request.session.session_key}
        else:
            return get_error('Su cuenta ha sido desactivada.')
    else:
        # the authentication system was unable to verify the username and password
        return get_error('Nombre de usuario o contraseña incorrectos.')


@register_call()
def update_agency_gcm_id(request, session, **args):
    """
    :param args: {'device_id', 'devicegcmid'}
    :return: {}
    """
    models.AgencyDevices.objects.filter(deviceid=args['device_id']).update(devicegsmid=args['devicegcmid'])
    return {}


@register_call()
def logout_agency(request, session, **args):
    """
    :param args: {'device_id'}
    :return: {}
    """

    models.AgencyDevices.objects.filter(deviceid=args['device_id']).delete()
    return {}


@register_call()
def summary(request, device_id, **kwargs):
    """
    :params device_id
    :returns: {}
    """

    try:
        agency = models.AgencyDevices.objects.get(devicegsmid=device_id).agency
    except models.AgencyDevices.DoesNotExist:
        return get_error("Este dispositivo no está asociado a ninguna agencia.")
    except models.AgencyDevices.MultipleObjectsReturned:
        return get_error("Este dispositivo se asoció a más de una agencia.")

    today = timezone.now().date()
    state = models.BaseDetail.STATE.PLAYED
    details = models.DetailQuiniela.objects.filter(
        bet__agency=agency, state=state,
        **utils.build_date_query('bet__date_played', today)
    ).order_by('-bet__date_played')

    result = map(lambda x: serialize_quiniela_detail(x)['detail'], details)

    for detail_model in [models.DetailQuiniSeis, models.DetailBrinco,
                         models.DetailLoto, models.DetailLoto5]:

        details = detail_model.objects.filter(
            bet__agency=agency, state=state,
            **utils.build_date_query('bet__date_played', today)
        ).order_by('-bet__date_played')

        result += map(lambda x: serialize_nonprinted_detail(x)['detail'], details)

    details = models.DetailCoupons.objects.filter(
        bet__agency=agency, state=state,
        **utils.build_date_query('bet__date_played', today)
    ).order_by('-bet__date_played')

    result += map(lambda x: serialize_preprinted_detail(x)['detail'], details)

    return {'details': result}



