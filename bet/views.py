#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import mercadopago
import pytz
import string
import random
import ast
import StringIO
import csv
from hubarcode.code128 import Code128Encoder
import math
import tempfile
import os

from collections import defaultdict, OrderedDict
from datetime import datetime, date
from decimal import Decimal
from braces.views import LoginRequiredMixin
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core import mail
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import connection, IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.db.models.expressions import Func
from django.forms.formsets import BaseFormSet
from django.forms.models import ModelForm, modelformset_factory
from django.http.response import HttpResponse, Http404, JsonResponse, HttpResponseForbidden,HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django_modalview.generic.component import ModalButton, ModalResponse
from django_modalview.generic.edit import ModalFormUtilView

from bet import forms, models, utils
from bet.models import CsvImportError
from bet.utils import to_localtime
from bet.webservices import _buy_preprinted_coupons, _request_ticket
from simple_webservice.serializer import to_simple_types
from django.http import HttpResponse

import pdfkit
from pdfkit.configuration import Configuration
from tzlocal import get_localzone # $ pip install tzlocal

# Get an instance of a logger
#logging.basicConfig()
logger = logging.getLogger('agencia24_default')


tz_today = lambda : timezone.now().today()


def is_admin(u):
    return u.groups.filter(name='admin').exists()


def is_agenciero(u):
    return u.groups.filter(name='agenciero').exists()

def is_user(u):
    return u.groups.filter(name='user').exists()

@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def home(request):
    return render(request, 'base.html')


def terminos_y_condiciones(request):
    return render(request, 'terminos_y_condiciones.html')

def como_jugar(request):
    return render(request, 'como_se_juega.html')

def FAQ(request):
    return render(request, 'faq.html')

def politicas(request):
    return render(request, 'politicas.html')



def games(request):

    if settings.APP_CODE == 'SF':
        return HttpResponseRedirect("http://help.jugaya.com/index.html", None)

    return redirect("bet:games_login")


@login_required()
@user_passes_test(lambda user: is_admin(user) or is_agenciero(user) or is_user(user),
                  login_url='/denied', redirect_field_name=None)
def games_login(request):


    if is_agenciero(request.user):
        return redirect('bet:draws')
    elif is_user(request.user):
        return redirect('bet:user_profile_saldo')

    game_list = models.Game.objects.all().order_by('order')
    return render(request, 'games.html', {'games': game_list})


@login_required()
@user_passes_test(lambda user: is_user(user),
                  login_url='/denied', redirect_field_name=None)
def user_profile_saldo(request):
    if is_agenciero(request.user):
        return redirect('bet:draws')


    profile = models.UserProfile.objects.get(user=request.user)
    pending = models.ChargeMovement.objects.filter(user=profile,state=0)
    pendingvalue = 0
    for p in pending:
        pendingvalue = pendingvalue + p.amount

    return render(request, 'user_profile_saldo.html', {'profile': profile, 'msg': ""})


def terms(request):

    return render(request, 'terms.html')


def como_se_juega(request):

    return render(request, 'como_se_juega.html')



def get_draws(request, date_str, province_id, group_id=None, tipo=None):

    group_draws = []
    if group_id is not None:
        group = get_object_or_404(models.QuinielaGroup, pk=group_id)
        group_draws = group.draws.values_list('pk', flat=True)

    date_draw = to_localtime(date_str, '%Y-%m-%d').date()
    quiniela_list = models.Province.objects.get(id=province_id).quinielas.all()

    query = utils.build_date_query('date_draw', date_draw)
    query.update({'quiniela__in': quiniela_list})
    if tipo is not None:
        query.update({'type': tipo})
    draw_list = models.DrawQuiniela.objects.filter(**query)
    draw_list = draw_list.values('pk','number','quiniela__name','type','date_draw')

    for draw in draw_list:
        draw['type'] = models.DrawQuiniela(type=draw['type']).get_type_display()
        draw['selected'] = draw['pk'] in group_draws

        d = draw['date_draw'].astimezone(pytz.timezone(settings.TIME_ZONE))
        draw['date'] = d.strftime("%H:%M")

    return JsonResponse(dict(draws=list(draw_list)))


def get_promotion_draws(request, game_id, promotion_id=None):

    now = timezone.now()
    instances = models.BaseDraw.objects.filter(game=game_id, date_draw__gte=now).order_by('date_draw')
    #draw_list = instances.values('pk','number','date_draw')
    draw_list = []

    selected_id = None
    if promotion_id is not None:
        selected_id = get_object_or_404(models.DrawPromotion, id=promotion_id).draw_id

    for instance in instances:
        instance = instance.parent

        draw = {'pk': instance.pk, 'selected': instance.pk == selected_id}

        d = instance.date_draw.astimezone(pytz.timezone(settings.TIME_ZONE))
        if isinstance(instance, models.DrawQuiniela):
            draw['value'] = u'{} - {} {}'.format(d.strftime("%d/%m/%y"), instance.quiniela.name, instance.get_type_display())
        else:
            draw['value'] = u'{} - {}'.format(d.strftime("%d/%m/%y"), instance.number)
        draw_list.append(draw)

    return JsonResponse(dict(draws=draw_list))


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def quiniela_group(request, pk=None):

    if pk:
        # Obtengo la instancia draw correspondiente (editando jugada)
        group = get_object_or_404(models.QuinielaGroup, pk=pk)
    else:
        # Creo una nueva instancia (creando jugada)
        group = models.QuinielaGroup()

    groupForm = forms.QuinielaGroupForm(request.POST or None, instance=group)
    if request.method == 'POST':

        if groupForm.is_valid():
            with transaction.atomic():
                group = groupForm.save(commit=False)
                group.save()
                groupForm.save_m2m()

            return redirect('bet:quinielas')

    context = {'groupForm': groupForm, 'group': group}
    return render(request, 'quiniela.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def draw_quiniela(request, draw_pk=None):
    # TODO! Ver los problemas que pueden darse al cambiar un concurso que ya esta asociado con un sorteo

    if draw_pk:
        # Obtengo la instancia draw correspondiente (editando jugada)
        draw = get_object_or_404(models.DrawQuiniela, pk=draw_pk)
        game = draw.game
        is_old = draw.is_old
        groups = draw.groups.all()
    else:
        # Creo una nueva instancia (creando jugada)
        game = models.Game.objects.get(code='quiniela')
        draw = models.DrawQuiniela(game=game, state=0)
        is_old = False
        groups = []

    readonly = not is_admin(request.user) or is_old

    if request.method == 'POST':

        drawForm = forms.QuinielaForm(request.POST, instance=draw)
        if drawForm.is_valid():
            with transaction.atomic():
                drawForm.save()

            return redirect('bet:draws_quiniela')
    else:
        drawForm = forms.QuinielaForm(instance=draw, readonly=readonly)

    context = {'drawForm': drawForm, 'readonly': readonly, 'groups': groups}
    return render(request, 'quiniela_draw.html', context)


# for Quini6, Loto, Loto5 and Brinco
@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def draw_nonprinted(request, code, draw_pk=None):

    if draw_pk:
        # Obtengo la instancia draw correspondiente (editando jugada)
        draw = get_object_or_404(models.Draw, pk=draw_pk, game__code=code)
        game = draw.game
        is_old = draw.is_old
    else:
        # Creo una nueva instancia (creando jugada)
        game = models.Game.objects.get(code=code)
        draw = models.Draw(game=game, state=0)
        is_old = False

        if not hasattr(game, 'betcommission'):
            msg = u'Debe cargar la comisión de {} en Configuración.'.format(game.name)
            messages.add_message(request, messages.WARNING, msg)

    readonly = not is_admin(request.user) or is_old

    if request.method == 'POST':
        #print request.POST
        drawForm = forms.NonprintedForm(code, request.POST, request.FILES, instance=draw)
        if drawForm.is_valid():
            draw.save()

            msg = u'Sorteo creado correctamente.'
            messages.add_message(request, messages.SUCCESS, msg)
            #return redirect(get_recently_visited(request, 1))
            return redirect('bet:draws')
    else:
        drawForm = forms.NonprintedForm(code, instance=draw, readonly=readonly)

    context = {'drawForm': drawForm, 'game': game, 'readonly': readonly}
    return render(request, 'nonprinted_draw.html', context)


# for Telekino, Loteria and TeleBingo Cordobes
@login_required()
@transaction.atomic()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def draw_preprinted_add(request, code):

    game = get_object_or_404(models.Game, code=code)
    initial = {'fractions': 3}
    if code.startswith('telebingo'):
        try:
            latest = models.DrawPreprinted.objects.filter(game=game).latest('date_draw')
        except models.DrawPreprinted.DoesNotExist:
            pass
        else:
            initial['rounds'] = latest.rounds
            initial['chances'] = latest.chances

    if not hasattr(game, 'betcommission'):
        msg = u'Debe cargar la comisión de {} en Configuración.'.format(game.name)
        messages.add_message(request, messages.WARNING, msg)

    if request.method == 'POST':
        instance = models.DrawPreprinted(game=game)
        drawForm = forms.PreprintedForm(code, request.POST, request.FILES, instance=instance)

        if drawForm.is_valid():
            instance = drawForm.save(commit=False)
            instance.game = game
            instance.save()

            msg = u'Sorteo creado correctamente.'
            messages.add_message(request, messages.SUCCESS, msg)

            if code == models.Game.CODE.LOTERIA:
                year, month = instance.date_draw.year, instance.date_draw.month
                if not models.LoteriaPrize.objects.filter(
                                                    month=month, year=year).exists():

                    msg = u'Debe cargar los premios de Lotería para este mes.'
                    messages.add_message(request, messages.WARNING, msg)
                    return redirect('bet:loteria_prizes', year, month)
            elif code.startswith('telebingo'):
                round_list = [models.Round(draw=instance, number=num + 1) for num in range(instance.rounds)]
                models.Round.objects.bulk_create(round_list)
                return redirect('bet:admin_coupons', instance.pk)

            return redirect('bet:draw_preprinted_edit', code, instance.pk)
    else:
        drawForm = forms.PreprintedForm(code, initial=initial)

    context = {'drawForm': drawForm, 'game': game, 'readonly': False}
    return render(request, 'preprinted_draw.html', context)


# for Telekino, Loteria and TeleBingo Cordobes
@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def draw_preprinted_edit(request, code, draw_pk):

    instance = get_object_or_404(models.DrawPreprinted, pk=draw_pk, game__code=code)
    if not hasattr(instance.game, 'betcommission'):
        msg = u'Debe cargar la comisión de {} en Configuración.'.format(instance.game.name)
        messages.add_message(request, messages.WARNING, msg)

    readonly = not is_admin(request.user) or instance.is_old

    if request.method == 'POST':
        drawForm = forms.PreprintedForm(code, request.POST, request.FILES, instance=instance)

        if drawForm.is_valid():
            drawForm.save()

            msg = u'Sorteo modificado correctamente.'
            messages.add_message(request, messages.SUCCESS, msg)

            if code == models.Game.CODE.LOTERIA:
                year, month = instance.date_draw.year, instance.date_draw.month
                if not models.LoteriaPrize.objects.filter(
                                                    month=month, year=year).exists():

                    msg = u'Debe cargar los premios de Lotería para este mes.'
                    messages.add_message(request, messages.WARNING, msg)
                    return redirect('bet:loteria_prizes', year, month)

            return redirect('bet:draw_preprinted_edit', code, instance.pk)
    else:
        drawForm = forms.PreprintedForm(code, instance=instance, readonly=readonly)

    context = {'drawForm': drawForm, 'game': instance.game, 'readonly': readonly}
    return render(request, 'preprinted_draw.html', context)


def get_barcode_image(request):

    idcoupon = request.GET['idcoupon']
    coupon = models.Coupon.objects.get(id=idcoupon)

    nn = str(coupon.draw.number).zfill(3) + str(coupon.number).zfill(6)
    nn = long(nn)
    print nn
    DV = str((nn % 7))
    print DV

    key = DV + str(coupon.draw.number).zfill(3) + str(coupon.number).zfill(6)

    encoder = Code128Encoder(key)
    print key,
    encoder.save("/tmp/ean" + str(coupon.id) + ".png")
    try:
        with open("/tmp/ean" + str(coupon.id) + ".png", "rb") as f:
            return HttpResponse(f.read(), content_type="image/jpeg")
    except IOError:

         return HttpResponse(None, content_type="image/jpeg")



def get_virtual_coupon(request):

    idcoupon = 212259
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


    if detail != None:
       chch['venta'] = detail.bet.date_bet
       chch['dni'] = detail.bet.user.dni
       chch['codoperation'] = detail.bet.id

    chch['prescribe'] = date_draw + timezone.timedelta(days=15)

    renderize = render(request, 'tickets/telebingo_coupon_ios.html', chch)
    contexto = {"response": renderize}
    return renderize


@login_required()
@user_passes_test(is_agenciero, login_url='/denied', redirect_field_name=None)
def coupons(request, draw_pk):
    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk)
    readonly = draw.is_old

    if draw.game.code == models.Game.CODE.LOTERIA:
        coupon_model = models.LoteriaCoupon
        template = 'coupons/lottery_coupons.html'
    else:
        coupon_model = models.Coupon
        template = 'coupons/coupons.html'

    initial = []
    queryset = coupon_model.objects.filter(draw=draw, agency=request.user.agency).order_by('number')

    if queryset.count() == 0 and draw.is_old:
        messages.add_message(request, messages.ERROR, 'No ha cargado billetes para este sorteo.')
        return redirect('bet:old_draws')

    elif queryset.count() == 0 and draw.game.code == models.Game.CODE.LOTERIA:
        try:
            # Obtener los numeros y fracciones de los billetes cargados por el agenciero
            # en el sorteo anterior
            prev_draw = models.DrawPreprinted.objects.filter(
                game=draw.game, date_draw__lt=draw.date_draw, coupon_set__isnull=False
            ).latest('date_draw')

            min_func = 'LEAST' if connection.vendor == 'postgresql' else 'MIN'
            # las fracciones no pueden superar la cantidad de fracciones de este sorteo
            initial = request.user.agency.coupon_set.filter(draw=prev_draw).annotate(
                min_fraction_sales=Func(F('fraction_sales'), draw.fractions, function=min_func)
            ).values('number', 'min_fraction_sales')
            initial = [{'number': x['number'], 'fraction_sales': x['min_fraction_sales']} for x in initial]
        except models.DrawPreprinted.DoesNotExist:
            pass

    CouponFormSet = forms.createCouponFormSet(draw.game.code, readonly)

    if request.method == 'POST' and request.POST.has_key('save'):
        couponFormSet = CouponFormSet(request.POST, instance=draw, game=draw.game, fractions=draw.fractions)
        if couponFormSet.is_valid():
            instances = couponFormSet.save(commit=False)
            for obj in couponFormSet.deleted_objects:
                if not obj.detailcoupon_set.exists():
                    obj.delete()
                else:
                    msg = 'Imposible eliminar el billete {}.'.format(obj.number)
                    messages.add_message(request, messages.ERROR, msg)

            for instance in instances:
                instance.agency = request.user.agency
                instance.save()

            if couponFormSet.has_changed():
                messages.add_message(request, messages.SUCCESS, 'Billetes guardados correctamente.')

            # Si hay usuarios con premio de billete pendiente para este juego, asignarlos.
            apply_credits(request, draw)

            return redirect('bet:coupons', draw.pk)
    else:
        couponFormSet = CouponFormSet(instance=draw, queryset=queryset, game=draw.game,
                                      fractions=draw.fractions, initial=initial)

    context = {'couponFormSet': couponFormSet, 'draw': draw, 'readonly': readonly}
    return render(request, template, context)


@login_required()
@user_passes_test(is_agenciero, login_url='/denied', redirect_field_name=None)
def telebingo_coupons(request, draw_pk):
    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk)

    draw_coupons = draw.coupon_set.order_by('number')
    agency_coupons = draw_coupons.filter(agency=request.user.agency)
    if draw.is_old and agency_coupons.count() == 0:
        messages.add_message(request, messages.ERROR, 'No ha cargado billetes para este sorteo.')
        return redirect('bet:old_draws')

    CouponFormSet = forms.createCouponFormSet(draw.game.code, readonly=draw.is_old)

    if request.method == 'POST' and not draw.is_old:
        couponFormSet = CouponFormSet(request.POST, instance=draw, game=draw.game)
        if couponFormSet.is_valid():
            if couponFormSet.has_changed():
                instances = couponFormSet.save(commit=False)
                for obj in couponFormSet.deleted_objects:
                    if not obj.detailcoupon_set.exists():
                        obj.agency = None
                        obj.save(update_fields=('agency',))
                    else:
                        msg = u'Imposible eliminar el billete {}.'.format(obj.number)
                        messages.add_message(request, messages.ERROR, msg)

                for instance in instances:
                    coupon = draw_coupons.get(number=instance.number)
                    coupon.agency = request.user.agency
                    coupon.save(update_fields=('agency',))

                messages.add_message(request, messages.SUCCESS, 'Billetes guardados correctamente.')

                # Si hay usuarios con premio de billete pendiente para este juego, asignarlos.
                apply_credits(request, draw, agency=request.user.agency)

            return redirect('bet:telebingo_coupons', draw.pk)
    else:
        couponFormSet = CouponFormSet(instance=draw, queryset=agency_coupons, game=draw.game)



    context = {'couponFormSet': couponFormSet, 'draw': draw, 'readonly': draw.is_old, "app": "SC"}
    return render(request, 'coupons/coupons.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def admin_coupons(request, draw_pk):
    instance = get_object_or_404(models.DrawPreprinted, pk=draw_pk)
    coupon_list = instance.coupon_set.all()
    total = coupon_list.count()
    coupon_list = coupon_list.filter(agency__isnull=False).ordered()
    registered = coupon_list.count()
    sold = coupon_list.filter(detailcoupon_set__isnull=False).count()

    agency = request.GET.get('agency', '')
    if agency:
        coupon_list = coupon_list.filter(agency=agency)

    state = request.GET.get('state', '')
    if state:
        st = int(state) == 0
        coupon_list = coupon_list.filter(detailcoupon_set__isnull=st)

    form = forms.FilterCouponsForm(request.GET)
    context = {
        'total': total,
        'registered': registered,
        'sold': sold,
        'coupons': coupon_list,
        'form': form,
        'draw': instance,
    }
    return render(request, 'coupons/admin_coupons.html', context)


class ImportCouponsModal(LoginRequiredMixin, ModalFormUtilView):

    form_class = forms.ImportFileForm

    def __init__(self, *args, **kwargs):
        super(ImportCouponsModal, self).__init__(*args, **kwargs)
        self.form_content_template_name = 'coupons/import_coupons_form.html'
        self.title = 'Importar billetes de Telebingo'
        self.submit_button.value = 'Importar'
        self.submit_button.loading_value = 'Importando...'
        self.close_button = ModalButton(value='Cancelar', button_type='default')

    def dispatch(self, request, *args, **kwargs):
        self.object = models.DrawPreprinted.objects.get(pk=kwargs.get('pk'))
        return super(ImportCouponsModal, self).dispatch(request, *args,**kwargs)

    def get_success_url(self):
        return reverse('bet:import_coupons', kwargs={'pk': self.object.pk})

    def util_on_form_valid(self, file, **kwargs):
        try:
            rows = self.object.load_coupons(file)
        except models.CsvImportError as err:
            self.response = ModalResponse(err.message, 'error')
        else:
            self.response = ModalResponse('{} billetes cargados.'.format(rows), 'success')
            self.close_button.value = 'Cerrar'
            self.submit_button.display = False


def get_coupons_numbers(request, exclude_sold=True):

    results = []
    if request.is_ajax():
        term = request.GET.get('term', '')
        draw = request.GET.get('draw', None)
        if draw is None:
            return JsonResponse(results)

        coupons = models.Coupon.objects.filter(draw=draw, number__startswith=term)
        if exclude_sold:
            coupons = coupons.filter(agency__isnull=True)

        for coupon_obj in coupons[:10]:
            coupon_json = {}
            coupon_json['id'] = coupon_obj.id
            coupon_json['label'] = coupon_obj.number
            coupon_json['value'] = coupon_obj.number
            results.append(coupon_json)

    return HttpResponse(json.dumps(results), 'application/json')



def get_coupons_numbers_range(request, exclude_sold=True):

    results = []
    if request.is_ajax():
        start = request.GET.get('start', '')
        end = request.GET.get('end', '')
        draw = request.GET.get('draw', None)
        if draw is None:
            return JsonResponse(results)


        print start,end
        coupons = models.Coupon.objects.filter(draw=draw, number__gte=start,number__lte=end,agency__isnull=True)
        results = {"msg": str(coupons.count()) + " cumplen con la condición"}

    return HttpResponse(json.dumps(results), 'application/json')


def make_coupons_range(request, exclude_sold=True):

    results = []
    if request.is_ajax():
        start = request.GET.get('start', '')
        end = request.GET.get('end', '')
        draw = request.GET.get('draw', None)
        if draw is None:
            return JsonResponse(results)

        print start,end
        coupons = models.Coupon.objects.filter(draw=draw, number__gte=start,number__lte=end,agency__isnull=True)
        results = {"msg": str(coupons.count()) + " fueron cargados a esta agencia"}
        for coupon in coupons:
            coupon.agency = request.user.agency
            coupon.save(update_fields=('agency',))

    return HttpResponse(json.dumps(results), 'application/json')


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def coupon_html(request, coupon_id):
    from django.http import HttpResponse
    instance = models.Coupon.objects.get(id=coupon_id)
    return HttpResponse(instance.to_html(request))


def apply_credits(request, draw, notify=True, agency=None):
    # Si hay usuarios con premio de billete pendiente para este juego, asignarlos.
    now = timezone.now()
    credits = draw.game.usercredit_set.filter(expiration__gt=now, accredited=False)
    if agency:
        credits = credits.filter(agency=request.user.agency)
    if not credits.exists():
        return

    if draw.game.type != models.Game.TYPE.PREPRINTED:
        return

    coupons = draw.coupon_set.all()

    for credit in credits:
        coupon = random.choice(coupons.filter(agency=credit.agency, fraction_saldo__gt=0))
        data = [{'cupon': coupon.id, 'quantity': 1}]
        result = _buy_preprinted_coupons(request, draw.id, data, credit.user, credit)
        if 'error' in result:
            logger.error(u'Error al asignar premio de billete. Credit {}'.format(credit.pk))
            continue

        if notify:
            profile = credit.user
            subject = u'Premio de {}'.format(draw.game.name)
            message = u'Se te ha asignado el billete número {} de {}'.format(coupon.number, draw.game.name)
            data = {'coupon': data[0]['cupon']}
            profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION,
                                      subject, message, data=data)

            context = {'message': message, 'user': profile.user, 'subject': subject}
            profile.email_notification(request, models.USER_SETTINGS.MAIL_WINNER_NOTIFICATION,
                                       'emails/generic_email', context)


@login_required()
@user_passes_test(lambda user: is_admin(user) or is_agenciero(user),
                  login_url='/denied', redirect_field_name=None)
def draws(request):
    agenciero = False
    game_name = None # Nombre del juego filtrado, si es que hay un filtro por code
    game_list = models.Game.objects.all().values('code', 'name')

    draw_list = models.BaseDraw.objects.exclude(game__code=models.Game.CODE.QUINIELA).order_by('date_draw')

    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)

    # SI es agenciero solo muestro preimpresos de su provincia
    if not is_admin(request.user):
        agency = request.user.agency
        draw_list = draw_list.filter(game__type=0)
        draw_list = draw_list.filter(Q(game__provinces__isnull=True) | Q(game__provinces=agency.province))
        agenciero = True

    if date_from:
        dt = max(to_localtime(date_from), timezone.now())
    else:
        dt = timezone.now()

    draw_list = draw_list.select_related().filter(date_draw__gte=dt)

    if date_to:
        dt = to_localtime(date_to) + timezone.timedelta(days=1)
        draw_list = draw_list.filter(date_draw__lt=dt)
    if code:
        draw_list = draw_list.filter(game__code=code)
        game_name = models.Game.objects.get(code=code).name
    if state:
        draw_list = draw_list.filter(state=state)


    form = forms.FilterDrawsForm(request.GET, agenciero=agenciero)
    context = {'draws': draw_list, 'games': game_list, 'form': form, 'game_name': game_name}
    return render(request, 'draws.html', context)



@login_required
def send_push(request, pk=None):

    if request.POST:
        messages_form = forms.MessagesForm(request.POST, request.FILES, prefix="messages")
        if messages_form.is_valid() :
            marca = messages_form.save(commit=False)
            marca.save()

            mad = models.UserProfile.objects.all()
            #if marca.type == 0:
            #    mad = mad.filter()

            print mad
            if marca.users != None and len(marca.users) > 0:
                uu = marca.users.split(",")
                mad = mad.filter(id__in=uu)


            for prof in mad:

                print prof
                msend = models.MessagesSend(message=marca,userprofile=prof,send=False)
                msend.save()

        return redirect("bet:send_push")


    push = forms.MessagesForm(prefix="messages")
    pushs = models.Messages.objects.all();
    for pa in pushs:
        pa.totals = len(models.MessagesSend.objects.filter(message=pa))

    context = {
        "push_form": push,
        "pushs": pushs
    }

    return render(request, 'send_push.html', context)






@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def draws_quiniela(request):
    draws = models.DrawQuiniela.objects.all().order_by('date_draw')

    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    state = request.GET.get('state', None)
    tipo = request.GET.get('type', None)
    quiniela = request.GET.get('quiniela', None)

    if date_from:
        dt = max(to_localtime(date_from), timezone.now())
    else:
        dt = timezone.now()
    draws = draws.filter(date_draw__gte=dt)

    if date_to:
        dt = to_localtime(date_to)+timezone.timedelta(days=1)
        draws = draws.filter(date_draw__lt=dt)
    if tipo:
        draws = draws.filter(type=tipo)
    if quiniela:
        draws = draws.filter(quiniela=quiniela)
    if state:
        draws = draws.filter(state=state)

    form = forms.FilterDrawsQuinielaForm(request.GET)
    context = {'draws': draws, 'form': form}
    return render(request, 'draws_quiniela.html', context)


@login_required()
@user_passes_test(lambda user: is_admin(user) or is_agenciero(user),
                  login_url='/denied', redirect_field_name=None)
def old_draws(request):

    game_name = None # Nombre del juego filtrado, si es que hay un filtro por code
    games = models.Game.objects.all().values('code','name')

    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)

    draw_list = models.BaseDraw.objects.exclude(game__code=models.Game.CODE.QUINIELA).order_by('-date_draw')

    if date_from:
        draw_list = draw_list.filter(date_draw__gte=to_localtime(date_from, '%d/%m/%Y'))

    if date_to:
        date_to = to_localtime(date_to) + timezone.timedelta(days=1)
        dt = min(date_to, timezone.now())
    else:
        dt = timezone.now()
    draw_list = draw_list.filter(date_draw__lt=dt)

    if code:
        draw_list = draw_list.filter(game__code=code)
        game_name = models.Game.objects.get(code=code).name
    if state:
        draw_list = draw_list.filter(state=state)

    form = forms.FilterDrawsForm(request.GET, is_old=True, agenciero=is_agenciero(request.user))
    context = {'draws': draw_list, 'games': games, 'form': form, 'game_name': game_name}
    return render(request, 'old_draws.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def quinielas(request):
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    province = request.GET.get('province', None)
    type = request.GET.get('type', None)

    groups = models.QuinielaGroup.objects.all().order_by('date','type')

    if date_from:
        dt = to_localtime(date_from)
    else:
        dt = timezone.now()
    groups = groups.filter(date__gte=dt)

    if date_to:
        groups = groups.filter(date__lte=to_localtime(date_to))
    if province:
        groups = groups.filter(province=province)
    if type:
        groups = groups.filter(type=type)

    form = forms.FilterQuinielaForm(request.GET)
    context = {'groups': groups, 'form': form}
    return render(request, 'quinielas.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def old_quinielas(request):
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    tipo = request.GET.get('type', None)
    province = request.GET.get('province', None)
    state = request.GET.get('state', None)

    groups = models.QuinielaGroup.objects.all().order_by('-date_draw')

    if date_from:
        groups = groups.filter(Q(date_draw__gte=to_localtime(date_from)) | Q(date_draw__isnull=True))

    if date_to:
        date_to = to_localtime(date_to) + timezone.timedelta(days=1)
        dt = min(date_to, timezone.now())
    else:
        dt = timezone.now()
    groups = groups.filter(Q(date_draw__lt=dt) | Q(date_draw__isnull=True))

    if province:
        groups = groups.filter(province=province)
    if tipo:
        groups = groups.filter(type=tipo)
    if state:
        groups = groups.filter(state=state)

    form = forms.FilterQuinielaForm(request.GET, is_old=True)
    context = {'groups': groups, 'form': form}
    return render(request, 'old_quinielas.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def agencies(request):
    agencies = models.Agency.objects.all()
    movements = models.AgenMovement.objects.all()
    total = movements.filter(
        state=models.AgenMovement.STATE.PENDING
    ).aggregate(total=Sum(F('amount'))).get('total') or 0

    context = {'agencies': agencies, 'total': total}
    return render(request, 'agencies/agencies.html', {'agencies': agencies, 'total': total})


def filter_agency_movs(agency, query):

    number = query.get('number', None) or None
    if number:
        query = Q(code__gte=models.AgenMovement.CODE.COLLECTION, id=number) | Q(payment=number)
        return agency.movement_set.filter(query).order_by('-date_mov')

    game = query.get('game', None) or None
    date_from_str = query.get('date_from', None) or None
    date_to_str = query.get('date_to', None) or None
    if date_from_str is None or date_to_str is None:
        return agency.movement_set.all().order_by('-date_mov')

    date_from = to_localtime(date_from_str)
    date_to = to_localtime(date_to_str) + timezone.timedelta(days=1)

    if game is None:
        query = Q(betcommissionmov__draw__date_draw__range=(date_from, date_to))
        query |= Q(winnercommissionmov__winner__winnerquiniela__draw__date_draw__range=(date_from, date_to))
        query |= Q(winnercommissionmov__winner__winner__draw__date_draw__range=(date_from, date_to))
    else:
        query = Q(betcommissionmov__draw__game__code=game,
                  betcommissionmov__draw__date_draw__range=(date_from, date_to))
        if game == models.Game.CODE.QUINIELA:
            query |= Q(winnercommissionmov__winner__winnerquiniela__draw__game__code=game,
                       winnercommissionmov__winner__winnerquiniela__draw__date_draw__range=(date_from, date_to))
        else:
            query |= Q(winnercommissionmov__winner__winner__draw__game__code=game,
                       winnercommissionmov__winner__winner__draw__date_draw__range=(date_from, date_to))

    #query |= Q(winnercommissionmov__isnull=True, betcommissionmov__isnull=True)


    if settings.APP_CODE == 'SF':
        return agency.movement_set.filter(query,).order_by('-date_mov')
    else:
        return agency.movement_set.filter(query).order_by('-date_mov')


@login_required()
@user_passes_test(lambda user: is_admin(user) or is_agenciero(user),
                  login_url='/denied', redirect_field_name=None)
def agency(request, agency_pk=None):

    if agency_pk is None:
        if not is_agenciero(request.user):
            raise Http404

        instance = request.user.agency
    else:
        instance = get_object_or_404(models.Agency, pk=agency_pk)

    ########## DELETE ##########
    msg = 'Agency balance ({}): db={}, calc={}'
    if instance.balance != instance.calc_balance():
        logger.error(msg.format(instance.id, instance.balance, instance.calc_balance()))
    else:
        logger.debug(msg.format(instance.id, instance.balance, instance.calc_balance()))
    ############################

    form = forms.FilterAgencyMovsForm(request.GET)
    movements = filter_agency_movs(instance, request.GET).distinct()

    movements = movements.exclude(code__in=[models.AgenMovement.CODE.PRIZECOMMISSION])

    pending = confirmed = tickets = prizes = 0
    for mov in movements.filter(code__in=[models.AgenMovement.CODE.BETCOMMISSION,
                                          models.AgenMovement.CODE.PRIZECOMMISSION]):
        if mov.state == models.AgenMovement.STATE.PENDING:
            pending += mov.amount
        else:
            confirmed += mov.amount
        if mov.code == models.AgenMovement.CODE.PRIZECOMMISSION:
            prizes += mov.amount
        else:
            tickets += mov.parent.real_amount

    context = {'form': form, 'movements': movements, 'agency': instance, 'prizes': prizes,
               'pending': pending, 'confirmed': confirmed, 'tickets': tickets}

    return render(request, 'agencies/agency.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def edit_agency(request, agency_pk = None):

    if agency_pk:
        agency = get_object_or_404(models.Agency, pk=agency_pk)
        message = u'Agencia modificada con éxito'
    else:
        user = User(is_active=True)
        agency = models.Agency(user=user)
        message = u'Agencia creada con éxito'

    agencyForm = forms.AgencyForm(request.POST or None, instance=agency)
    userForm = forms.AgencyUserForm(request.POST or None, instance=agency.user)
    if request.method == 'POST':
        if agencyForm.is_valid() and userForm.is_valid():
            if not agency.user_id:
                instance = agencyForm.save(commit=False)
                instance.user = userForm.save(request=request, creating=True)
                instance.save()

                agen_group = Group.objects.get(name='agenciero')
                agen_group.user_set.add(instance.user)
            else:
                userForm.save()
                agencyForm.save()

            messages.add_message(request, messages.SUCCESS, message)
            return redirect('bet:agencies')

    context = {'agencyForm': agencyForm, 'pk': agency_pk, 'userForm': userForm}
    return render(request, 'agencies/edit_agency.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
@transaction.atomic()
def agency_commission(request, agency_pk):

    instance = get_object_or_404(models.Agency, pk=agency_pk)

    movs = request.POST.get('movs').split(',')
    movements = instance.movement_set.filter(id__in=movs, state=models.AgenMovement.STATE.PENDING)
    amount = movements.aggregate(total=Sum(F('amount')))['total'] or 0

    if amount > 0:
        code = models.AgenMovement.CODE.COLLECTION
    else:
        code = models.AgenMovement.CODE.PAYMENT

    payment = models.PaymentCommissionMov.objects.create(
        date_from=to_localtime(request.POST.get('date_from'), format='%d/%m/%Y').date(),
        date_to=to_localtime(request.POST.get('date_to'), format='%d/%m/%Y').date(),
        agency=instance, code=code, amount=-amount,
        state=models.AgenMovement.STATE.CONFIRMED)
    movements.update(state=models.AgenMovement.STATE.CONFIRMED,
                     payment=payment)

    messages.add_message(request, messages.SUCCESS, u'Operación completada con éxito.')
    return redirect('bet:agency', agency_pk)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def users(request):

    profiles = models.UserProfile.objects.all()

    user = request.GET.get('user', None)
    state = request.GET.get('state', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)

    if date_from:
        profiles = profiles.filter(user__date_joined__gte=to_localtime(date_from))

    if date_to:
        date_to = to_localtime(date_to) + timezone.timedelta(days=1)
        dt = min(date_to, timezone.now())
    else:
        dt = timezone.now()
    profiles = profiles.filter(user__date_joined__lt=dt)

    if user:
        profiles = profiles.filter(pk=int(user))

    if state:
        profiles = profiles.filter(user__is_active=state)

    form = forms.FilterUsersForm(request.GET)
    return render(request, 'user/users.html', {'profiles': profiles, 'form': form})


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def edit_user(request, profile_pk):
    profile = get_object_or_404(models.UserProfile, pk=profile_pk)
    user = profile.user

    if request.method == 'POST':
        profileForm = forms.UserProfileForm(request.POST, instance=profile)
        userForm = forms.UserForm(request.POST, instance=user)

        if profileForm.is_valid() and userForm.is_valid():
            with transaction.atomic():
                profileForm.save()
                userForm.save()

            return HttpResponse(render_to_string('user/edit_user_success.html', {'user': user}))
    else:
        profileForm = forms.UserProfileForm(instance=profile)
        userForm = forms.UserForm(instance=user)

    context = {'profileForm': profileForm, 'userForm': userForm, 'pk': profile_pk}
    return render(request, 'user/edit_user.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def user(request, pk):
    profile = get_object_or_404(models.UserProfile, pk=pk)
    movements = models.AbstractMovement.movs_with_saldo(pk)

    state = models.AbstractMovement.STATE.PENDING
    withdrawal = profile.movement_set.filter(code='SR', state=state).order_by('-date').last()

    context = {'profile': profile, 'movements': movements,
               'withdrawal': withdrawal}
    return render(request, 'user/user.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
@transaction.atomic
def approve_withdrawal(request, pk):
    instance = get_object_or_404(models.WithdrawalMovement, pk=pk)
    profile = instance.user
    if instance.state == models.AbstractMovement.STATE.PENDING:
        pending = models.BetMovement.objects.filter(
            user=profile,
            state=models.AbstractMovement.STATE.PENDING,
            bet__date_bet__gt=F('date')
        ).aggregate(total=Sum(F('amount'))).get('total') or 0
        instance.amount = max(instance.amount, pending - profile.saldo)

        instance.state = models.AbstractMovement.STATE.CONFIRMED
        instance.confirm_date = timezone.now()
        instance.save()

        profile.saldo += instance.amount
        profile.save(update_fields=('saldo',))

        msg = u'Solicitud de retiro aprobada: ${}'.format(-instance.amount)
        profile.push_notification(models.USER_SETTINGS.PUSH_WITHDRAWAL_APPROVED, u'Retiro de dinero', msg)
        context = dict(user=profile.user, movement=instance)
        profile.email_notification(request, models.USER_SETTINGS.MAIL_WITHDRAWAL_APPROVED,
                                   'emails/confirm_withdrawal_email', context)

        messages.add_message(request, messages.SUCCESS, u'Solicitud de retiro acreditada.')
    else:
        messages.add_message(request, messages.ERROR, u'La solicitud de retiro ya está acreditada.')

    return redirect('bet:user', profile.pk)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def movement_detail(request, pk):
    movement = get_object_or_404(models.AbstractMovement, pk=pk)

    if hasattr(movement, 'betmovement'):
        tipo = 'betmovement'
    elif hasattr(movement, 'chargemovement'):
        tipo = 'chargemovement'
    elif hasattr(movement, 'withdrawalmovement'):
        tipo = 'withdrawalmovement'
    else:
        tipo = 'prizemovement'

    context = {'movement': getattr(movement, tipo)}
    return render(request, 'movs/{}_detail.html'.format(tipo), context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
def send_extract(request, draw_pk):

    draw = get_object_or_404(models.Draw, pk=draw_pk)
    if not draw.is_old:
        return redirect('bet:{}_results'.format(draw.game.code), draw_pk)

    if draw.extract_sent:
        msg = 'El extracto de este sorteo ya fue enviado.'
        messages.add_message(request, messages.WARNING, msg)
        return redirect('bet:{}_results'.format(draw.game.code), draw_pk)

    draw.send_game_extract(request)
    draw.state = models.BaseDraw.STATE.EXTRACT
    draw.save(update_fields=('state',))

    msg = 'Extracto enviado.'
    messages.add_message(request, messages.SUCCESS, msg)
    if draw.game.code == models.Game.CODE.LOTERIA:
        update_loteria_winners(draw.drawpreprinted)
        return redirect('bet:loteria_winners', draw_pk)

    if draw.game.code.startswith('telebingo'):
        update_telebingo_winners(draw.drawpreprinted)
        return redirect('bet:telebingo_winners', draw_pk)

    if draw.game.type == models.Game.TYPE.PREPRINTED:
        return redirect('bet:{}_results'.format(draw.game.code), draw_pk)

    update_nonprinted_winners(draw)

    return redirect('bet:nonprinted_winners', draw_pk)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
def send_quiniela_extract(request, group_pk):

    group = get_object_or_404(models.QuinielaGroup, pk=group_pk)
    if group.state == models.BaseDraw.STATE.EXTRACT:
        msg = u'El extracto de este sorteo ya fue enviado.'
        messages.add_message(request, messages.WARNING, msg)
        return redirect('bet:old_quinielas')

    if not group.state == models.BaseDraw.STATE.LOADED:
        msg = u'Debe cargar los resultados antes de poder enviar el extracto del sorteo.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:quiniela_results', group.pk)

    group.send_game_extract(request)

    msg = u'Extracto enviado.'
    messages.add_message(request, messages.SUCCESS, msg)

    update_quiniela_winners(group)

    return redirect('bet:quiniela_winners', group_pk)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def quini6_results(request, draw_pk):
    draw = get_object_or_404(models.Draw, pk=draw_pk, game__code=models.Game.CODE.QUINI6)
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        results = models.Quini6Results.objects.get(draw=draw)
    except models.Quini6Results.DoesNotExist:
        results = models.Quini6Results(draw=draw)

    if hasattr(results, 'tra'):
        tra = results.tra
        tra2 = results.tra2
        rev = results.rev
        sie = results.sie
        ext = results.ext
    else:
        tra = models.ResultsSet6()
        tra2 = models.ResultsSet6()
        rev = models.ResultsSet6()
        sie = models.ResultsSet6()
        ext = models.SingleExtract()

    traQuerySet = models.RowExtract.objects.filter(results=tra)
    tra2QuerySet = models.RowExtract.objects.filter(results=tra2)
    revQuerySet = models.RowExtract.objects.filter(results=rev)
    sieQuerySet = models.RowExtract.objects.filter(results=sie)

    ExtractFormSetTra = forms.createExtractFormSet(numbers=6, min_num=3)
    ExtractFormSet = forms.createExtractFormSet(numbers=6, min_num=1)
    ExtractFormSetSie = forms.createExtractFormSet(numbers=6, min_num=1)
    initial=[{'hits':i} for i in range(6,3,-1)]

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:quini6_results', draw.pk)

        traForm = forms.ResultsSet6Form(request.POST, instance=tra, prefix='tra')
        extractFormTra = ExtractFormSetTra(request.POST, instance=tra, prefix='tra')

        tra2Form = forms.ResultsSet6Form(request.POST, instance=tra2, prefix='tra2')
        extractFormTra2 = ExtractFormSetTra(request.POST, instance=tra2, prefix='tra2')

        revForm = forms.ResultsSet6Form(request.POST, instance=rev, prefix='rev')
        extractFormRev = ExtractFormSet(request.POST, instance=rev, prefix='rev')

        sieForm = forms.ResultsSet6Form(request.POST, instance=sie, prefix='sie')
        extractFormSie = ExtractFormSetSie(request.POST, instance=sie, prefix='sie', readonly=False)

        extractFormExt = forms.SinlgeExtractForm(request.POST, instance=ext, prefix='ext', hidden_hits=True)

        resultsSets = [tra, tra2, rev, sie]
        resultsForms = [traForm, tra2Form, revForm, sieForm]
        extractFormSets = [extractFormTra, extractFormTra2, extractFormRev, extractFormSie]

        if all(map(ModelForm.is_valid, resultsForms)) and all(map(BaseFormSet.is_valid, extractFormSets))\
                and extractFormExt.is_valid():
            with transaction.atomic():
                map(forms.ResultsSet6Form.save, resultsForms)
                extractFormExt.save()

                results.tra = tra
                results.tra2 = tra2
                results.rev = rev
                results.sie = sie
                results.ext = ext
                results.save()

                for index, formSet in enumerate(extractFormSets):
                    instances = formSet.save(commit = False)
                    for order, instance in enumerate(instances):
                        instance.results = resultsSets[index]
                        if instance.pk is None:
                            instance.order = order
                        instance.save()

                draw.state = models.BaseDraw.STATE.LOADED
                draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:quini6_results', draw.pk)
    else:
        traForm = forms.ResultsSet6Form(instance=tra, prefix='tra')
        extractFormTra = ExtractFormSetTra(instance=tra, queryset=traQuerySet, initial=initial, prefix='tra')

        tra2Form = forms.ResultsSet6Form(instance=tra2, prefix='tra2')
        extractFormTra2 = ExtractFormSetTra(instance=tra2, queryset=tra2QuerySet, initial=initial, prefix='tra2')

        revForm = forms.ResultsSet6Form(instance=rev, prefix='rev')
        extractFormRev = ExtractFormSet(instance=rev, queryset=revQuerySet, initial=initial, prefix='rev')

        sieForm = forms.ResultsSet6Form(instance=sie, prefix='sie')
        extractFormSie = ExtractFormSetSie(instance=sie, queryset=sieQuerySet, initial=initial,
                                           prefix='sie', readonly=False)

        extractFormExt = forms.SinlgeExtractForm(instance=ext, prefix='ext')

    context = {'draw': draw, 'traForm': traForm, 'tra2Form': tra2Form,
               'revForm': revForm, 'sieForm': sieForm,
               'extractFormTra': extractFormTra, 'extractFormTra2': extractFormTra2,
               'extractFormRev': extractFormRev, 'extractFormSie': extractFormSie,
               'extractFormExt': [extractFormExt]}
    return render(request, 'results/quini6_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def loto5_results(request, draw_pk):
    draw = get_object_or_404(models.Draw, pk=draw_pk, game__code=models.Game.CODE.LOTO5)
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        results = models.Loto5Results.objects.get(draw=draw)
    except models.Loto5Results.DoesNotExist:
        results = models.Loto5Results(draw=draw)

    if hasattr(results, 'tra'):
        tra = results.tra
    else:
        tra = models.ResultsSet5()

    queryset = models.RowExtract.objects.filter(results=tra)
    ExtractFormSet = forms.createExtractFormSet(numbers=5, min_num=3)
    initial=[{'hits':i} for i in range(5,2,-1)]

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:loto5_results', draw.pk)

        resultsForm = forms.ResultsSet5Form(request.POST, instance=tra)
        extractFormSet = ExtractFormSet(request.POST, instance=tra)

        if resultsForm.is_valid() and extractFormSet.is_valid():
            with transaction.atomic():
                resultsForm.save()
                results.tra = tra
                results.save()

                instances = extractFormSet.save(commit = False)
                for order, instance in enumerate(instances):
                    instance.results = tra
                    if instance.pk is None:
                        instance.order = order
                    instance.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:loto5_results', draw.pk)
    else:
        resultsForm = forms.ResultsSet5Form(instance=tra)
        extractFormSet = ExtractFormSet(instance=tra, queryset=queryset, initial=initial)

    context = {'draw': draw, 'resultsForm': resultsForm, 'extractFormSet': extractFormSet}
    return render(request, 'results/loto5_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def brinco_results(request, draw_pk):
    draw = get_object_or_404(models.Draw, pk=draw_pk, game__code=models.Game.CODE.BRINCO)
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        results = models.BrincoResults.objects.get(draw=draw)
    except models.BrincoResults.DoesNotExist:
        results = models.BrincoResults(draw=draw)

    if hasattr(results, 'tra'):
        tra = results.tra
        tra2 = results.tra2
    else:
        tra = models.ResultsSet6()
        tra2 = models.ResultsSet6()

    queryset = models.RowExtract.objects.filter(results=tra)
    queryset2 = models.RowExtract.objects.filter(results=tra2)
    ExtractFormSet = forms.createExtractFormSet(numbers=6, min_num=4)
    ExtractFormSet2 = forms.createExtractFormSet(numbers=6, min_num=1)
    initial=[{'hits':i} for i in range(6,2,-1)]
    initial2=[{'hits':i} for i in range(6,2,-1)]

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:brinco_results', draw.pk)

        resultsForm = forms.ResultsSet6Form(request.POST, instance=tra, prefix='tra')
        extractFormSet = ExtractFormSet(request.POST, instance=tra, prefix='tra')

        resultsForm2 = forms.ResultsSet6Form(request.POST, instance=tra2, prefix='tra2')
        extractFormSet2 = ExtractFormSet(request.POST, instance=tra2, prefix='tra2')

        if resultsForm.is_valid() and extractFormSet.is_valid() and resultsForm2.is_valid() and extractFormSet2.is_valid():
            with transaction.atomic():
                resultsForm.save()
                resultsForm2.save()
                results.tra = tra
                results.tra2 = tra2
                results.save()

                instances = extractFormSet.save(commit = False)
                for order, instance in enumerate(instances):
                    instance.results = tra
                    if instance.pk is None:
                        instance.order = order
                    instance.save()

                instances = extractFormSet2.save(commit = False)
                for order, instance in enumerate(instances):
                    instance.results = tra2
                    if instance.pk is None:
                        instance.order = order
                    instance.save()
            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()


            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:brinco_results', draw.pk)




    else:
        resultsForm = forms.ResultsSet6Form(instance=tra,prefix='tra')
        extractFormSet = ExtractFormSet(instance=tra, queryset=queryset, initial=initial,prefix='tra')

        resultsForm2 = forms.ResultsSet6Form(instance=tra2,prefix='tra2')
        extractFormSet2 = ExtractFormSet2(instance=tra2, queryset=queryset2, initial=initial2,prefix='tra2')

    context = {'draw': draw, 'resultsForm2': resultsForm2, 'extractFormSet2': extractFormSet2, 'resultsForm': resultsForm, 'extractFormSet': extractFormSet}
    return render(request, 'results/brinco_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
#MLG
def loto_results(request, draw_pk):
    draw = get_object_or_404(models.Draw, pk=draw_pk, game__code=models.Game.CODE.LOTO)
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        results = models.LotoResults.objects.get(draw=draw)
    except models.LotoResults.DoesNotExist:
        results = models.LotoResults(draw=draw)

    if hasattr(results, 'tra'):
        tra = results.tra
        des = results.des
        sos = results.sos
    else:
        tra = models.ResultsSet6Extra()
        des = models.ResultsSet6Extra()
        sos = models.ResultsSet6()

    traQuerySet = models.RowExtract.objects.filter(results=tra)
    desQuerySet = models.RowExtract.objects.filter(results=des)
    sosQuerySet = models.RowExtract.objects.filter(results=sos)

    ExtractFormSetTra = forms.createExtractFormSet(min_num=12)
    ExtractFormSet = forms.createExtractFormSet(numbers=6, min_num=3)
    ExtractFormSetSos = forms.createExtractFormSet(numbers=6, min_num=1)

    init = [(i,j) for i in range(6,2,-1) for j in range(2,-1,-1) if i+j>=5]
    initial=[{'hits': '%s%s' %(i,' + %s Jack' %j if j else '')} for (i,j) in init]
    initial.append({'hits': '4'})
    initial.append({'hits': '3 + 1 Jack'})
    initial.append({'hits': '3'})



    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:loto_results', draw.pk)

        traForm = forms.ResultsSet6ExtraForm(request.POST, instance=tra, prefix='tra')
        extractFormTra = ExtractFormSetTra(request.POST, instance=tra, prefix='tra')

        desForm = forms.ResultsSet6ExtraForm(request.POST, instance=des, prefix='des')
        extractFormDes = ExtractFormSet(request.POST, instance=des, prefix='des')

        sosForm = forms.ResultsSet6Form(request.POST, instance=sos, prefix='sos')
        extractFormSos = ExtractFormSetSos(request.POST, instance=sos, prefix='sos', readonly=False)

        resultsSets = [tra, des, sos]
        resultsForms = [traForm, desForm, sosForm]
        extractFormSets = [extractFormTra, extractFormDes, extractFormSos]

        if all(map(ModelForm.is_valid, resultsForms)) and all(map(BaseFormSet.is_valid, extractFormSets)):
            traForm.save()
            desForm.save()
            sosForm.save()

            results.tra = tra
            results.des = des
            results.sos = sos
            results.save()

            for index, formSet in enumerate(extractFormSets):
                instances = formSet.save(commit = False)
                for order, instance in enumerate(instances):
                    instance.results = resultsSets[index]
                    if instance.pk is None:
                        instance.order = order
                    instance.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:loto_results', draw.pk)
    else:

        traForm = forms.ResultsSet6ExtraForm(instance=tra, prefix='tra')
        extractFormTra = ExtractFormSetTra(instance=tra, queryset=traQuerySet, initial=initial, prefix='tra')

        desForm = forms.ResultsSet6ExtraForm(instance=des, prefix='des')
        extractFormDes = ExtractFormSet(instance=des, queryset=desQuerySet, initial=[{'hits': '6'},{'hits': '6 + 1 Jack'}, {'hits': '6 + 2 Jack' }], prefix='des')

        sosForm = forms.ResultsSet6Form(instance=sos, prefix='sos')
        extractFormSos = ExtractFormSetSos(instance=sos, queryset=sosQuerySet,
                                           initial=[{'hits': '5'}], prefix='sos',
                                           readonly=False)


    context = {'draw': draw, 'traForm': traForm, 'desForm': desForm, 'sosForm': sosForm,
               'extractFormTra': extractFormTra, 'extractFormDes': extractFormDes,
               'extractFormSos': extractFormSos}
    return render(request, 'results/loto_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def telekino_results(request, draw_pk):

    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk,
                             game__code=models.Game.CODE.TELEKINO)
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        results = models.TelekinoResults.objects.get(draw=draw)
    except models.TelekinoResults.DoesNotExist:
        results = models.TelekinoResults(draw=draw)

    if hasattr(results, 'tel'):
        tel = results.tel
        rek = results.rek
    else:
        tel = models.ResultsSet15()
        rek = models.ResultsSet15()

    telQuerySet = models.RowExtract.objects.filter(results=tel)
    rekQuerySet = models.RowExtract.objects.filter(results=rek)
    cupQuerySet = models.CouponExtract.objects.filter(results=results)

    ExtractFormSetTel = forms.createExtractFormSet(numbers=15, min_num=5)
    ExtractFormSet = forms.createExtractFormSet(numbers=15, min_num=1)
    CouponResultsFormSet = forms.createCouponResultsFormSet(min_num=5, max_num=10)
    initial=[{'hits':i} for i in range(15,10,-1)]

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:telekino_results', draw.pk)

        telForm = forms.ResultsSet15Form(request.POST, instance=tel, prefix='tel')
        extractFormTel = ExtractFormSetTel(request.POST, instance=tel, prefix='tel')

        rekForm = forms.ResultsSet15Form(request.POST, instance=rek, prefix='rek')
        extractFormRek = ExtractFormSet(request.POST, instance=rek, prefix='rek', readonly=False)

        couponFormSet = CouponResultsFormSet(request.POST, instance=results, prefix='cup')

        resultsSets = [tel, rek]
        resultsForms = [telForm, rekForm]
        extractFormSets = [extractFormTel, extractFormRek]

        if all(map(ModelForm.is_valid, resultsForms)) \
                and all(map(BaseFormSet.is_valid, extractFormSets)) \
                and couponFormSet.is_valid():

            map(forms.ResultsSet15Form.save, resultsForms)
            results.tel = tel
            results.rek = rek
            results.save()

            for index, formSet in enumerate(extractFormSets):
                instances = formSet.save(commit = False)
                for order, instance in enumerate(instances):
                    instance.results = resultsSets[index]
                    if instance.pk is None:
                        instance.order = order
                    instance.save()

            couponFormSet.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:telekino_results', draw.pk)
    else:
        telForm = forms.ResultsSet15Form(instance=tel, prefix='tel')
        extractFormTel = ExtractFormSetTel(instance=tel, queryset=telQuerySet, initial=initial, prefix='tel')

        rekForm = forms.ResultsSet15Form(instance=rek, prefix='rek')
        extractFormRek = ExtractFormSet(instance=rek, queryset=rekQuerySet, prefix='rek', readonly=False)

        couponFormSet = CouponResultsFormSet(instance=results, queryset=cupQuerySet, prefix='cup')

    context = {'draw': draw, 'telForm': telForm, 'rekForm': rekForm,
               'extractFormTel': extractFormTel, 'extractFormRek': extractFormRek,
               'couponFormSet': couponFormSet}
    return render(request, 'results/telekino_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def loteria_results(request, draw_pk):
    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk,
                             game__code=models.Game.CODE.LOTERIA)
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        models.LoteriaPrize.get_by_draw(draw)
    except models.LoteriaPrize.DoesNotExist:
        msg = 'Debe cargar los premios de la lotería para poder acceder a los resultados.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:loteria_prizes', draw.date_draw.year,
                        '{:0>2}'.format(draw.date_draw.month), draw.pk)

    try:
        results = models.LoteriaResults.objects.get(draw=draw)
    except models.LoteriaResults.DoesNotExist:
        results = models.LoteriaResults(draw=draw)

    if hasattr(results, 'ord'):
        ordinaria = results.ord
    else:
        ordinaria = models.ResultsSet20()

    resultsForm = forms.ResultsSetLotteryForm(request.POST or None, instance=ordinaria)
    progForm = forms.ProgresionLotteryForm(request.POST or None, instance=results)

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:loteria_results', draw.pk)

        if resultsForm.is_valid() and progForm.is_valid():
            results = progForm.save(commit=False)
            results.ord = resultsForm.save()
            results.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados modificados exitosamente.')
            return redirect('bet:loteria_results', draw_pk)

    context = {'draw': draw, 'resultsForm': resultsForm, 'progForm': progForm}

    return render(request, 'results/loteria_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def totobingo_results(request, draw_pk):
    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk,
                             game__code=models.Game.CODE.TOTOBINGO)

    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    try:
        results = models.TotobingoResults.objects.get(draw=draw)
    except models.TotobingoResults.DoesNotExist:
        results = models.TotobingoResults(draw=draw)

    if hasattr(results, 'poz'):
        gog = results.gog
        poz = results.poz
        star = results.star
    else:
        gog = models.VariableResultsSet()
        poz = models.ResultsSet12()
        star = models.ResultsSetStar()


    gogQuerySet = models.RowExtract.objects.filter(results=gog)
    pozQuerySet = models.RowExtract.objects.filter(results=poz)
    starQuerySet = models.RowExtract.objects.filter(results=star)
    cupQuerySet = models.CouponExtract.objects.filter(results=results)

    VariableFormSet = forms.createVariableResultsFormSet(max_value=54, extra=4)
    initialGog = [{'number': x} for x in gog.numbers.split(',')]

    ExtractFormSetGog = forms.createExtractFormSet(numbers=0, min_num=1)
    ExtractFormSetPoz = forms.createExtractFormSet(numbers=12, min_num=5)
    ExtractFormSetStar = forms.createExtractFormSet(numbers=1, min_num=1)
    CouponResultsFormSet = forms.createCouponResultsFormSet(min_num=1, max_num=5)
    initial=[{'hits':i} for i in range(12,8,-1)] + [{'hits': 0}]

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:totobingo_results', draw.pk)

        gogForm = forms.VariableResultsForm(request.POST, instance=gog, sort_numbers=True)
        gogFormSet = VariableFormSet(request.POST, min_num=4)
        extractFormGog = ExtractFormSetGog(request.POST, instance=gog, prefix='gog')

        pozForm = forms.ResultsSet12Form(request.POST, instance=poz)
        extractFormPoz = ExtractFormSetPoz(request.POST, instance=poz, prefix='poz')

        starForm = forms.ResultsSetStarForm(request.POST, instance=star)
        extractFormStar = ExtractFormSetStar(request.POST, instance=star, prefix='star',
                                             hidden_hits=True, prize_type=models.Prize.TYPE.COUPON)

        couponFormSet = CouponResultsFormSet(request.POST, instance=results, prefix='cup')

        resultsSets = [gog, poz, star]
        resultsForms = [gogForm, pozForm, starForm]
        extractFormSets = [extractFormGog, extractFormPoz, extractFormStar]

        if all(map(ModelForm.is_valid, resultsForms))\
            and all(map(BaseFormSet.is_valid, extractFormSets))\
            and couponFormSet.is_valid() and gogFormSet.is_valid():

            gogForm.save()
            pozForm.save()
            starForm.save()

            results.gog = gog
            results.poz = poz
            results.star = star
            results.save()

            for index, formSet in enumerate(extractFormSets):
                instances = formSet.save(commit = False)
                for order, instance in enumerate(instances):
                    instance.results = resultsSets[index]
                    if instance.pk is None:
                        instance.order = order
                    instance.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            couponFormSet.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:totobingo_results', draw.pk)
    else:
        gogForm = forms.VariableResultsForm(instance=gog, sort_numbers=True)
        gogFormSet = VariableFormSet(initial=initialGog)
        extractFormGog = ExtractFormSetGog(instance=gog, queryset=gogQuerySet,
                                           prefix='gog', initial=[{'hits':'4'}])

        pozForm = forms.ResultsSet12Form(instance=poz)
        extractFormPoz = ExtractFormSetPoz(instance=poz, queryset=pozQuerySet,
                                           initial=initial, prefix='poz')

        starForm = forms.ResultsSetStarForm(instance=star)
        extractFormStar = ExtractFormSetStar(instance=star, queryset=starQuerySet,
                                             initial=[{'hits': '1'}], prefix='star',
                                             hidden_hits=True, prize_type=models.Prize.TYPE.COUPON)

        couponFormSet = CouponResultsFormSet(instance=results, queryset=cupQuerySet, prefix='cup')

    context = {'draw': draw, 'gogForm': gogForm, 'pozForm': pozForm, 'starForm': starForm,
               'extractFormGog': extractFormGog, 'gogFormSet': gogFormSet,
               'extractFormPoz': extractFormPoz, 'extractFormStar': extractFormStar,
               'couponFormSet': couponFormSet}
    return render(request, 'results/totobingo_results.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def telebingo_results(request, draw_pk):

    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk,
                             game__code__startswith='telebingo')

    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    results_form = forms.ImportFileForm(request.POST or None, request.FILES or None, prefix='results')
    extract_form = forms.ImportFileForm(request.POST or None, request.FILES or None,
                                        prefix='extract', supported_ext=('.pdf',), initial={'file': draw.orig_extract})

    ending_count = ending_number = None
    extra_extracts = []
    if request.method == 'POST':
        if 'results' in request.POST:
            if draw.extract_sent:
                msg = 'Los resultados de este sorteo no pueden modificarse.'
                messages.add_message(request, messages.ERROR, msg)
                return redirect('bet:telebingo_results', draw.pk)

            if results_form.is_valid():
                try:
                    draw.import_extract(results_form.cleaned_data['file'])
                except CsvImportError as e:
                    results_form.add_error('file', e.message)
                else:
                    draw.state = models.BaseDraw.STATE.LOADED
                    draw.save()

                    messages.add_message(request, messages.SUCCESS, 'Resultados cargados exitosamente.')
                    return redirect('bet:telebingocordobes_results', draw.pk)
        else:
            if extract_form.is_valid():
                draw.orig_extract = extract_form.cleaned_data['file']
                draw.save(update_fields=('orig_extract',))

                messages.add_message(request, messages.SUCCESS, 'Extracto cargado exitosamente.')
                return redirect('bet:telebingocordobes_results', draw.pk)
    else:
        ending_extracts = models.TbgEndingExtract.objects.filter(coupon__draw=draw, ending=True)
        extra_extracts = models.TbgEndingExtract.objects.filter(coupon__draw=draw, ending=False)

        ending_count = ending_extracts.count()
        if ending_count > 0:
            ending_number = ending_extracts.first().coupon.number[-2:]


    #mlgmlgmlg
    print extra_extracts
    context = {'results_form': results_form, 'extract_form': extract_form, 'draw': draw,
               'ending_count': ending_count, 'ending_number': ending_number, "extras": extra_extracts}
    return render(request, 'results/telebingo_results.html', context)


"""@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def telebingo_results2(request, draw_pk):

    draw = get_object_or_404(models.DrawPreprinted, pk=draw_pk,
                             game__code__startswith='telebingo')
    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_draws')

    results = models.TelebingoResults.objects.filter(round__draw=draw)
    if not results.exists():
        results = [models.TelebingoResults(round=r) for r in draw.round_set.order_by('number')]

    VariableFormSetLine = forms.createVariableResultsFormSet(max_value=90, extra=5)
    VariableFormSetBingo = forms.createVariableResultsFormSet(max_value=90, extra=20)

    round_list = []
    for result in results:
        if hasattr(result, 'line'):
            line = getattr(result, 'line')
            bingo = getattr(result, 'bingo')
        else:
            line = models.VariableResultsSet()
            bingo = models.VariableResultsSet()

        initialLine = [{'number': x} for x in line.get_numbers]
        initialBingo = [{'number': x} for x in bingo.get_numbers]

        try:
            instance = models.RowExtract.objects.get(results=line)
        except models.RowExtract.DoesNotExist:
            instance = models.RowExtract(results=line, hits='5', order=0)

        prefix = 'line-{}'.format(result.round.number)
        lineForm = forms.VariableResultsForm(request.POST or None, instance=line, prefix=prefix)
        lineFormSet = VariableFormSetLine(request.POST or None, min_num=5, initial=initialLine, prefix=prefix)
        #extractFormLine = forms.PreprintedExtractForm(request.POST or None,
        #                                              instance=instance,
        #                                              prefix=prefix,
        #                                              prize_type=-1,
        #                                              initial={'value': '20000'})

        extractFormSetLine = forms.TbgExtractFormSet(request.POST or None, instance=line, prefix=prefix+'_extract',
                                                     prize_type=-1, hidden_hits=True, readonly=False,
                                                     draw=draw, initial=[{'value': '20000'}])

        try:
            instance = models.RowExtract.objects.get(results=bingo)
        except models.RowExtract.DoesNotExist:
            instance = models.RowExtract(results=bingo, hits='15', order=0)

        prefix = 'bingo-{}'.format(result.round.number)
        bingoForm = forms.VariableResultsForm(request.POST or None, instance=bingo, prefix=prefix)
        bingoFormSet = VariableFormSetBingo(request.POST or None, min_num=15, initial=initialBingo, prefix=prefix)
        #extractFormBingo = forms.PreprintedExtractForm(request.POST or None,
        #                                               instance=instance,
        #                                               prefix=prefix,
        #                                               prize_type=-1,
        #                                               initial={'value': '50000'})

        extractFormSetBingo = forms.TbgExtractFormSet(request.POST or None, instance=bingo, prefix=prefix+'_extract',
                                                      prize_type=-1, hidden_hits=True, readonly=False,
                                                      draw=draw, initial=[{'value': '50000'}])

        round_dict = {
            'line': {
                #'extractForms': [extractFormLine],
                'extractForms': extractFormSetLine,
                'resultsForm': lineForm,
                'formSet': lineFormSet,
            },
            'bingo': {
                #'extractForms': [extractFormBingo],
                'extractForms': extractFormSetBingo,
                'resultsForm': bingoForm,
                'formSet': bingoFormSet,
            }
        }
        round_list.append(round_dict)

    if request.method == 'POST':
        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:telebingo_results', draw.pk)

        couponFormSet = forms.TbgCouponResultsFormSet(request.POST, instance=draw, prefix='cup')

        if forms.telebingo_forms_are_valid(round_list) and couponFormSet.is_valid():
            for idx, round_dict in enumerate(round_list):
                line_inst = round_dict['line']['resultsForm'].save()
                bingo_inst = round_dict['bingo']['resultsForm'].save()

                results[idx].line = line_inst
                results[idx].bingo = bingo_inst
                results[idx].save()

                instances = round_dict['line']['extractForms'].save(commit=False)
                for instance in instances:
                    instance.results = line_inst
                    instance.save()

                instance = round_dict['bingo']['extractForms'].save(commit=False)
                for instance in instances:
                    instance.results = bingo_inst
                    instance.save()

            couponFormSet.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados guardados exitosamente.')
            return redirect('bet:telebingocordobes_results', draw.pk)
    else:
        cupQuerySet = models.TbgCouponExtract.objects.filter(coupon__draw=draw)
        couponFormSet = forms.TbgCouponResultsFormSet(instance=draw, queryset=cupQuerySet, prefix='cup')

    context = {'draw': draw, 'couponFormSet': couponFormSet, 'round_list': round_list}
    return render(request, 'results/telebingo_results.html', context)"""


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def quiniela_results(request, group_pk, quiniela_pk=None):

    group = get_object_or_404(models.QuinielaGroup, pk=group_pk)

    try:
        draw = group.draws.get(quiniela=quiniela_pk)
    except models.DrawQuiniela.DoesNotExist:
        draw = group.draws.first()

    if not draw.is_old:
        msg = 'Imposible acceder a los resultados de un juego no finalizado.'
        messages.add_message(request, messages.ERROR, msg)
        return redirect('bet:old_quinielas')

    try:
        results = models.QuinielaResults.objects.get(draw=draw)
        res = results.res
    except models.QuinielaResults.DoesNotExist:
        results = models.QuinielaResults(draw=draw)
        res = models.ResultsSet20()

    resultsForm = forms.ResultsSet20Form(request.POST or None, instance=res)

    if request.method == 'POST':

        if draw.state == models.BaseDraw.STATE.EXTRACT:
            msg = 'Los resultados de este sorteo no pueden modificarse.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:quiniela_results', group_pk)

        if resultsForm.is_valid():
            results.res = resultsForm.save()
            results.save()

            draw.state = models.BaseDraw.STATE.LOADED
            draw.save()

            if group.is_loaded:
                group.state = models.BaseDraw.STATE.LOADED
                group.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados cargados exitosamente.')
            return redirect('bet:quiniela_results', group_pk, draw.quiniela_id)

    saved = group.draws.filter(state__in=[models.BaseDraw.STATE.LOADED, models.BaseDraw.STATE.EXTRACT])
    context = {'resultsForm': resultsForm, 'saved': saved, 'group': group, 'cur_draw': draw}

    return render(request, 'results/quiniela_results.html', context)

"""
@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
def delete_quiniela_results(request):

    if request.method == 'POST':
        try:
            year, month, day = request.POST['year'], request.POST['month'], request.POST['day']
            lottery = request.POST['lottery']
            type = request.POST['type']


            date_draw = date(int(year), int(month), int(day))
            query = utils.build_date_query('date_draw', date_draw)
            query.update({
                'quiniela': lottery,
                'type': type
            })

            draw = models.DrawQuiniela.objects.get(**query)
            if draw.state == models.BaseDraw.STATE.EXTRACT:
                msg = u'No puede eliminar resultados después de enviar el extracto.'
                messages.add_message(request, messages.ERROR, msg)
                return redirect('bet:draws_quiniela')

            with transaction.atomic():
                draw.quiniela_results.delete()

                draw.state = models.BaseDraw.STATE.ACTIVE
                draw.save()

            messages.add_message(request, messages.SUCCESS, 'Resultados eliminados correctamente.')
            return redirect('bet:quiniela_results', date_draw.strftime("%Y-%m-%d"))

        except models.DrawQuiniela.DoesNotExist:
            pass
        except KeyError:
            pass

        messages.add_message(request, messages.ERROR, 'Error al eliminar los resultados.')
        return redirect('bet:draws_quiniela')"""


def filter_movements(query, all):

    data = models.AbstractMovement.objects.filter(state=models.AbstractMovement.STATE.CONFIRMED).order_by('-date')

    date_from = query.get('date_from', None)
    date_to = query.get('date_to', None)
    code = query.get('code', None)
    user_pk = query.get('user', None)
    draw = query.get('draw', None)

    if date_from:
        data = data.filter(date__gte=to_localtime(date_from))

    if date_to:
        dt = to_localtime(date_to) + timezone.timedelta(days=1)
    else:
        dt = timezone.now()

    data = data.filter(date__lt=dt)

    if user_pk:
        data = data.filter(user__pk=int(user_pk))

    if code:
        data = data.filter(code=code)

    if draw:
        print draw
        dr = models.DrawPreprinted.objects.filter(pk=draw).first()
        print dr
        data = data.filter(code='PA')
        abc = []
        for d in data:
            if d.code == 'PA' and len(d.parent.bet.draws) > 0 and d.parent.bet.draws[0].number == dr.number:
                d.number = dr.number
                abc.append(d)

        return abc

    return data

def filter_payments(query, all):

    if all:
        data = models.AbstractMovement.objects.all().order_by('-date')
    else:
       data = models.AbstractMovement.objects.filter(code__in=['SR', 'CC']).order_by('-date')

    date_from = query.get('date_from', None)
    date_to = query.get('date_to', None)
    code = query.get('code', None)
    method = query.get('method', None)
    state = query.get('state', None)
    user_pk = query.get('user', None)

    if date_from:
        data = data.filter(date__gte=to_localtime(date_from))

    if date_to:
        dt = to_localtime(date_to) + timezone.timedelta(days=1)
    else:
        dt = timezone.now()
    data = data.filter(date__lt=dt)

    if user_pk:
        data = data.filter(user__pk=int(user_pk))

    if code:
        data = data.filter(code=code)

    if method:
        data = data.filter(Q(chargemovement__method=method) | Q(withdrawalmovement__method=method))

    if state != '-1': # -1 Corresponde a 'Todos' (seteado en forms.py)
        data = data.filter(state=state)

    return data


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def payments(request):

    query = request.GET.copy()
    if not query.get('state', ''):
        query['state'] = '0'

    instances = filter_payments(query, False)
    total = sum(x for (x,) in instances.values_list('amount'))

    form = forms.FilterPaymentsForm(query)

    context = {'form': form, 'total': total, 'instances': instances,
               'confirmed': models.AbstractMovement.STATE.CONFIRMED,
               'state_choices': models.AbstractMovement.STATE_CHOICES}
    return render(request, 'payments.html', context)



@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def movements_all(request):

    query = request.GET.copy()

    print query
    instances = filter_movements(query, True)
    total =  0

    if 'export_excel'  in query:

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="movmientos.csv"'

        writer = csv.writer(response,delimiter=';',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        row = []
        row.append("Agencia")
        row.append("Juego")
        row.append("Sorteo")
        row.append("Fecha")
        row.append("Fecha")
        row.append("Usuario")
        row.append("Movmiento")
        row.append("Monto")
        writer.writerow(row)

        for ca in instances:
            row = []
            if ca.code == 'PA' and len(ca.parent.bet.draws) > 0:
                if ca.parent.bet.date_played == None and settings.APP_CODE != 'SC':
                    continue

	    	row.append(ca.parent.bet.agency.name)
                row.append(fill_none(ca.parent.bet.draws[0].game.name))
                datec = ca.parent.bet.draws[0].date_draw.astimezone(get_localzone()).strftime("%d/%m/%y %H:%M")
                row.append(ca.parent.bet.draws[0].number)
	    	row.append(datec)
            else:
                row.append("")
                row.append("")
                row.append("")
                row.append("")

            row.append(ca.date.astimezone(get_localzone()).strftime("%d/%m/%y %H:%M"))
            row.append(fill_none(ca.user.user.first_name)+ " " + fill_none(ca.user.user.last_name))
            if ca.code == 'SR':
                row.append("Solicitud de retiro")
            if ca.code == 'PA':
                row.append("Pago de apuesta")
            if ca.code == 'CC':
                row.append("Carga de credito")
            if ca.code == 'PR':
                row.append("Premio de apuesta")
            row.append(str(ca.amount))

            writer.writerow(row)


        return response

    form = forms.FilterMovementsForm(query)

    context = {'form': form, 'total': total, 'instances': instances,
               'confirmed': models.AbstractMovement.STATE.CONFIRMED,
               'state_choices': models.AbstractMovement.STATE_CHOICES}
    return render(request, 'movements_all.html', context)




@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
def update_payment(request, payment_id):
    instance = get_object_or_404(models.AbstractMovement, id=payment_id)
    if instance.state == models.AbstractMovement.STATE.CONFIRMED:
        err = u'Imposible modificar un movimiento confirmado.'
        messages.add_message(request, messages.ERROR, err)
        return redirect(reverse('bet:payments') + '?state=0')

    instance.amount = float(request.POST.get('amount').replace(',','.'))
    instance.state = int(request.POST.get('state'))

    if instance.code == 'CC' and instance.amount > instance.chargemovement.initial:
        err = u'Imposible acreditar un saldo mayor al solicitado por el usuario.'
        messages.add_message(request, messages.ERROR, err)
        return redirect(reverse('bet:payments') + '?state=0')

    with transaction.atomic():

        instance.confirm_date = timezone.now()
        instance.save()

        # Al enviar el mail todavia no se guardo la instancia
        instance.parent.amount = instance.amount

        profile = instance.user
        if instance.state == models.AbstractMovement.STATE.CONFIRMED:
            if instance.code == 'SR':
                pending = models.BetMovement.objects.filter(
                    user=profile,
                    state=models.AbstractMovement.STATE.PENDING,
                    bet__date_bet__gt=F('date')
                ).aggregate(total=Sum(F('amount'))).get('total') or 0
                instance.amount = max(instance.amount, pending - profile.saldo)

            profile.saldo += Decimal(round(instance.amount, 2))
            profile.save(update_fields=('saldo',))

            if instance.code == 'CC':
                msg = u'Carga de saldo acreditada: ${}'.format(instance.amount)
                profile.push_notification(models.USER_SETTINGS.PUSH_CHARGE_ACCREDITED, u'Carga de saldo', msg)
                context = dict(user=profile.user, movement=instance.parent)
                profile.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_ACCREDITED,
                                           'emails/charge_confirmed_email', context)
            else:
                msg = u'Solicitud de retiro aprobada: ${}'.format(-instance.amount)
                profile.push_notification(models.USER_SETTINGS.PUSH_WITHDRAWAL_APPROVED, u'Retiro de dinero', msg)
                context = dict(user=profile.user, movement=instance.parent)
                profile.email_notification(request, models.USER_SETTINGS.MAIL_WITHDRAWAL_APPROVED,
                                           'emails/confirm_withdrawal_email', context)

        elif instance.state == models.AbstractMovement.STATE.CANCELED and instance.code == 'CC':
            msg = u'Su carga de saldo ha sido rechazada.'
            profile.push_notification(models.USER_SETTINGS.PUSH_CHARGE_REJECTED, u'Carga de saldo rechazada', msg)
            context = dict(user=profile.user, movement=instance.parent)
            profile.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_REJECTED,
                                       'emails/charge_rejected_email', context)

        return redirect(reverse('bet:payments') + '?state=0')


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def old_payments(request):

    query = request.GET.copy()
    if not query.get('state', ''):
        query['state'] = '0'

    data = filter_payments(query, False)
    total = sum(x for (x,) in data.values_list('amount'))

    form = forms.FilterPaymentsForm(query)
    formSet = forms.PaymentFormSet(request.POST or None, queryset=data)

    if request.method == 'POST' and formSet.is_valid():
        with transaction.atomic():
            try:
                instances = formSet.save()
            except ValidationError:
                err = u'Imposible acreditar un saldo mayor al solicitado por el usuario.'
                messages.add_message(request, messages.ERROR, err)
                return redirect(reverse('bet:payments') + '?state=0')

            for instance in instances:
                profile = instance.user
                if instance.state == models.AbstractMovement.STATE.CONFIRMED:

                    if instance.code == 'CC':
                        msg = u'Carga de saldo acreditada: ${}'.format(instance.amount)
                        profile.push_notification(models.USER_SETTINGS.PUSH_CHARGE_ACCREDITED, u'Carga de saldo', msg)
                        context = dict(user=profile.user, movement=instance)
                        profile.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_ACCREDITED,
                                                   'emails/confirm_charge_email', context)
                    else:
                        msg = u'Solicitud de retiro aprobada: ${}'.format(-instance.amount)
                        profile.push_notification(models.USER_SETTINGS.PUSH_WITHDRAWAL_APPROVED, u'Retiro de dinero', msg)
                        context = dict(user=profile.user, movement=instance)
                        profile.email_notification(request, models.USER_SETTINGS.MAIL_WITHDRAWAL_APPROVED,
                                                   'emails/withdrawal_confirm_email', context)

            return redirect(reverse('bet:payments') + '?state=0')

    context = {'formSet': formSet, 'form': form, 'total': total,
               'confirmed': models.AbstractMovement.STATE.CONFIRMED}
    return render(request, 'payments.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def bets(request):

    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    agency = request.GET.get('agency', None)
    state = request.GET.get('state', None)
    game = request.GET.get('game', None)
    selected_user = request.GET.get('user', None)

    bet_list = models.Bet.objects.select_related('detail').all().order_by('-date_bet')

    if date_from:
        bet_list = bet_list.filter(date_bet__gte=to_localtime(date_from))

    if date_to:
        dt = to_localtime(date_to) + timezone.timedelta(days=1)
        bet_list = bet_list.filter(date_bet__lt=dt)

    if agency:
        bet_list = bet_list.filter(agency=agency)

    if selected_user:
        bet_list = bet_list.filter(user=selected_user)

    if game:
        if game == models.Game.CODE.QUINIELA:
            query = Q(detailquiniela_set__isnull=False)
        else:
            query  = Q(detail__draw__game__code=game)
            query |= Q(detailcoupons_set__coupon__draw__game__code=game)

        bet_list = bet_list.filter(query)

    if state:
        query  = Q(detail__state=state)
        query |= Q(detailcoupons_set__state=state)
        query |= Q(detailquiniela_set__state=state)
        bet_list = bet_list.filter(query)

    bet_list = bet_list.distinct()
    total  = bet_list.aggregate(total=Sum(F('detail__importq')))['total'] or 0
    total += bet_list.aggregate(total=Sum(F('detailcoupons_set__importq')))['total'] or 0
    total += bet_list.aggregate(total=Sum(F('detailquiniela_set__importq')))['total'] or 0

    form = forms.FilterBetsForm(request.GET)
    context = {'bet_list': bet_list, 'form': form, 'total': total, "app_code": settings.APP_CODE}
    return render(request, 'bets.html', context)


#================================== WINNERS ======================================

def filter_prize_requests(query):
    data = models.PrizeRequest.objects.all().order_by('date')

    date_from = query.get('date_from', None)
    date_to = query.get('date_to', None)
    game = query.get('game', None)
    state = query.get('state', None)

    if date_from:
        data = data.filter(date__gte=to_localtime(date_from))

    if date_to:
        dt = to_localtime(date_to)
    else:
        dt = timezone.now()
    data = data.filter(date__lt=dt)

    if game:
        data = data.filter(detail__coupon__draw__game=game)

    if state != '-1': # -1 Corresponde a 'Todos' (seteado en forms.py)
        data = data.filter(state=state)

    return data


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def prize_requests(request):

    query = request.GET.copy()
    if not query.get('state', ''):
        query['state'] = str(models.PrizeRequest.STATE.PENDING)

    form = forms.FilterPrizeRequestForm(query)
    requests = filter_prize_requests(query)

    context = {'requests': requests, 'form': form}
    return render(request, 'winners/prize_requests.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def prize_request(request, request_id):
    req = get_object_or_404(models.PrizeRequest, id=request_id)

    results_set = getattr(req.results, req.mode)
    results_set.name = req.results._meta.get_field(req.mode).verbose_name
    row_extract = results_set.extract_set.get(hits=len(req.get_numbers))

    if request.method == 'POST':
        if req.state != models.PrizeRequest.STATE.PENDING:
            msg = u'No puede modificar esta solicitud.'
            messages.add_message(request, messages.ERROR, msg)
            return redirect('bet:prize_requests')

        profile = req.detail.bet.user

        if request.POST.has_key('reject'):
            req.state = models.PrizeRequest.STATE.REJECTED
            req.save(update_fields=('state',))
            if req.losing_bet:
                message = u'Su apuesta de {} no tuvo premio.'.format(req.game.name)
                profile.push_notification(models.USER_SETTINGS.PUSH_REQUEST_PRIZE_REJECTED,
                                          u'Solicitud de premio rechazada.', message)
                context = {'detail': req.detail, 'user': profile.user}
                profile.email_notification(request, models.USER_SETTINGS.MAIL_REQUEST_PRIZE_REJECTED,
                                           'emails/reject_prize_email', context)

        if request.POST.has_key('accept'):
            req.state = models.PrizeRequest.STATE.ACCEPTED
            req.save(update_fields=('state',))

            winner = models.WinnerExtract.objects.create(
                detail=req.detail, extract=row_extract,
                draw=req.detail.coupon.draw, info=results_set.name,
            )
            send_winner_notification(request, winner)

        return redirect('bet:prize_requests')

    context = {'prize_request': req, 'results_set': results_set, 'row_extract': row_extract}
    return render(request, 'winners/prize_request.html', context)


def update_nonprinted_winners(draw):

    delete_winners([draw])
    if draw.game.code == models.Game.CODE.QUINI6:
        update_quini6_winners(draw)

    if draw.game.code == models.Game.CODE.LOTO:
        update_loto_winners(draw)

    if draw.game.code == models.Game.CODE.LOTO5:
        update_loto5_winners(draw)

    if draw.game.code == models.Game.CODE.BRINCO:
        update_brinco_winners(draw)


def update_quini6_winners(draw):

    drawDetails = models.DetailQuiniSeis.objects.filter(draw=draw,
                                                        state=models.BaseDetail.STATE.PLAYED)

    extResults = set()
    sixHitsWinners = [] # Lista de id's de Winners con 6 aciertos en tra, tra2 y rev (para excluir de premio extra)

    modalities = OrderedDict([('tra', 'Tradicional Primer Sorteo'),
                              ('tra2', 'Tradicional La segunda del quini'),
                              ('rev', 'Revancha'),
                              ('sie', 'Siempre Sale')])

    for code, name in modalities.items():
        data = {'quini6_%s__draw' %code: draw.pk}
        resultsObj = models.ResultsSet6.objects.get(**data)

        results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,7))
        if code != 'sie':
            extResults = extResults.union(results)

        detailsObjs = drawDetails.filter(**{code[:3]: True})
        for detailObj in detailsObjs:
            detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))

            hits = len(detail & results)
            for extract in resultsObj.extract_set.all().order_by('order'):
                if hits == int(extract.hits):
                    winner, created = models.WinnerExtract.objects.get_or_create(
                        detail=detailObj, extract=extract, draw=draw, info=name,
                    )

                    if hits == 6 and code != 'sie':
                        sixHitsWinners.append(winner.pk)
                    break

    #PREMIO EXTRA
    # Todos los que jugaron a trad, revancha y siempre sale
    data = {'tra': True, 'rev': True, 'sie': True}
    detailsObjs = drawDetails.filter(**data)
    # Menos los que tuvieron 6 aciertos en tra, tra2 y rev
    detailsObjs = detailsObjs.exclude(winner__in=sixHitsWinners)

    for detailObj in detailsObjs:
        detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))

        hits = len(detail & extResults)
        if hits == 6:
            models.WinnerSingleExtract.objects.get_or_create(
                detail=detailObj, draw=draw, info='Premio extra',
                extract=draw.quini6_results.ext
            )
            break


def update_brinco_winners(draw):

    resultsObj = models.ResultsSet6.objects.get(brinco_results__draw=draw)
    results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,7))

    drawDetails = models.DetailBrinco.objects.filter(draw=draw,
                                                     state=models.BaseDetail.STATE.PLAYED)
    for detailObj in drawDetails:
        detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))

        hits = len(detail & results)
        for extract in resultsObj.extract_set.all().order_by('order'):
            if hits == int(extract.hits):
                models.WinnerExtract.objects.get_or_create(
                        detail=detailObj, extract=extract, draw=draw, info='Tradicional',
                    )
                break

    resultsObj = models.ResultsSet6.objects.get(brinco_results_2__draw=draw)
    results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,7))

    drawDetails = models.DetailBrinco.objects.filter(draw=draw,
                                                     state=models.BaseDetail.STATE.PLAYED)
    for detailObj in drawDetails:
        detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))

        hits = len(detail & results)
        for extract in resultsObj.extract_set.all().order_by('order'):
            if hits == int(extract.hits):
                models.WinnerExtract.objects.get_or_create(
                        detail=detailObj, extract=extract, draw=draw, info='Tradicional',
                    )
                break



def update_loto5_winners(draw):

    resultsObj = models.ResultsSet5.objects.get(loto5_results__draw=draw)
    results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,6))

    drawDetails = models.DetailLoto5.objects.filter(draw=draw,
                                                    state=models.BaseDetail.STATE.PLAYED)
    for detailObj in drawDetails:
        detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,6))

        hits = len(detail & results)
        for extract in resultsObj.extract_set.all().order_by('order'):
            if hits == int(extract.hits):
                models.WinnerExtract.objects.get_or_create(detail=detailObj, extract=extract, draw=draw,
                                              info='Tradicional')
                break


def update_loto_winners(draw):

    resultsObj = models.ResultsSet6Extra.objects.get(loto_tra__draw=draw)

    modalities = OrderedDict()
    modalities['des'] = 'Desquite'
    modalities['sos'] = 'Sale o Sale'

    results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,7))
    resultsExt = set(getattr(resultsObj, 'extra'+str(i)) for i in range(1,3))

    drawDetails = models.DetailLoto.objects.filter(draw=draw,
                                                   state=models.BaseDetail.STATE.PLAYED)
    nn = []

    print "***********", drawDetails
    detailsObjs = drawDetails.filter(tra=True)
    for detailObj in detailsObjs:
        detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))
        detailExt = set(getattr(detailObj, 'extra'+str(i)) for i in range(1,3))

        hits = len(detail & results)
        hitsExt = len(detailExt & resultsExt)
        for extract in resultsObj.extract_set.all().order_by('order'):
            if '{} + {} Jack'.format(hits, hitsExt) == extract.hits:
                nn.append(hitsExt)
                models.WinnerExtract.objects.get_or_create(
                        detail=detailObj, extract=extract, draw=draw, info='Tradicional'
                    )
                break

    for code, name in modalities.items():
        data = {'loto_%s__draw' %code: draw.pk}


        if code == 'des':

            resultsObj = models.ResultsSet6Extra.objects.get(loto_des__draw=draw)
            results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,7))
            resultsExt = set(getattr(resultsObj, 'extra'+str(i)) for i in range(1,3))


            detailsObjs = drawDetails.filter(des=True)
            for detailObj in detailsObjs:
                detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))
                detailExt = set(getattr(detailObj, 'extra'+str(i)) for i in range(1,3))

                hits = len(detail & results)
                hitsExt = len(detailExt & resultsExt)
                for extract in resultsObj.extract_set.all().order_by('order'):
                    nn.append(hitsExt)
                    if '{} + {} Jack'.format(hits, hitsExt) == extract.hits:
                        models.WinnerExtract.objects.get_or_create(
                                detail=detailObj, extract=extract, draw=draw, info=name
                            )
                        break
        else:

            print "*******", data, nn
            resultsObj = models.ResultsSet6.objects.get(**data)

            results = set(getattr(resultsObj, 'number'+str(i)) for i in range(1,7))
            print "*********1", results, resultsObj

            detailsObjs = drawDetails.filter(**{code: True})
            print "********2*",detailsObjs, drawDetails

            for detailObj in detailsObjs:
                print "********2*",detailObj

                detail = set(getattr(detailObj, 'number'+str(i)) for i in range(1,7))

                #aca va el cambio
                hits = len(detail & results)
                print "********3*",hits
                print "********3*",hits
                print "********3", resultsObj.extract_set.all()
                for extract in resultsObj.extract_set.all().order_by('order'):
                    print "*********5",extract

                    if hits == int(extract.hits):
                        print "*********6",extract.prize
                        prize = extract.prize
                        prize.value =prize.value * 2
                        extract.prize = prize

                        models.WinnerExtract.objects.get_or_create(
                            detail=detailObj, extract=extract, draw=draw, info=name
                        )
                        break


def count_hits(detail_number, results):
    digits = len(detail_number)
    hits = 0
    for number in results:
        if int(detail_number) == number % (10**digits):
            hits += 1
    return hits


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def nonprinted_winners(request, draw_pk):

    draw = get_object_or_404(models.Draw, pk=draw_pk)

    winners = models.Winner.objects.filter(draw=draw)
    not_notified = winners.filter(notif=False).count() > 0

    formset = forms.WinnerFormSet(request.POST or None, queryset=winners)
    if request.method == 'POST' and formset.is_valid():
        instances = formset.save()

        emails = []
        for instance in instances:
            notif = send_winner_notification(request, instance.parent, send=False)
            if notif is not None:
                emails.append(notif)

        if instances: # si se notifico a alguien cerrar el sorteo
            connection = mail.get_connection(fail_silently=not settings.DEBUG)
            # Manually open the connection
            connection.open()
            # Send the two emails in a single call -
            connection.send_messages(emails)
            # The connection was already open so send_messages() doesn't close it.
            # We need to manually close the connection.
            connection.close()

    context = {'draw': draw, 'not_notified': not_notified, 'formset': formset}
    return render(request, 'winners/nonprinted_winners.html', context)


def update_telebingo_winners(draw):
    delete_winners([draw])
    #played_details = models.DetailCoupons.objects.filter(coupon__draw=draw,
    #                                                     state=models.BaseDetail.STATE.PLAYED)

    played_details = models.DetailCoupons.objects.filter(coupon__draw=draw)

    draw_details = played_details.filter(coupon__tbgrowextract__isnull=False)
    print draw_details
    for detail in draw_details:
        for extract in detail.coupon.tbgrowextract_set.all():
            print extract
            if extract.hits == '5':
                _type = models.WinnerTelebingo.TYPE.LINE
            else:
                _type = models.WinnerTelebingo.TYPE.BINGO
            models.WinnerTelebingo.objects.create(type=_type, row_extract=extract,
                                                  detail=detail, draw=draw)

    for coupon_extract in draw.coupon_extract_set.all():
        if models.UserProfile.objects.filter(dni=coupon_extract.number).exists():
            models.WinnerTelebingoCoupon.objects.create(extract=coupon_extract)

    draw_details = played_details.filter(coupon__tbgendingextract__isnull=False)
    for detail in draw_details:
        models.WinnerTelebingo.objects.create(type=models.WinnerTelebingo.TYPE.ENDING,
                                              ending_extract=detail.coupon.tbgendingextract,
                                              detail=detail, draw=draw)



def update_loteria_winners(draw):
    delete_winners([draw])

    resultsObj = models.ResultsSet20.objects.get(loteria_ord__draw=draw)
    results = resultsObj.get_numbers

    drawDetails = models.DetailCoupons.objects.filter(coupon__draw=draw,
                                                      state=models.BaseDetail.STATE.PLAYED)


    prizes = models.LoteriaPrize.get_by_draw(draw)
    for detailObj in drawDetails:
        coupon_number = int(detailObj.coupon.number)
        fraction_proportion = detailObj.fraction_bought/Decimal(draw.fractions)

        location_winner = False
        for pos, number in enumerate(results):

            if coupon_number == number:
                models.WinnerLoteria.objects.get_or_create(
                    detail=detailObj,
                    draw=draw,
                    info='{}° Premio'.format(pos+1),
                    prize=prizes.location_prize(pos+1)*fraction_proportion,
                    type=models.WinnerLoteria.TYPE.LOCATION
                )
                location_winner = True

        if location_winner:
            continue

        # PROGRESION
        if detailObj.coupon.loteriacoupon.progresion == draw.loteria_results.progresion:
            models.WinnerLoteria.objects.get_or_create(
                    detail=detailObj,
                    draw=draw,
                    info=u'Progresión',
                    prize=prizes.progresion_prize()*fraction_proportion,
                    type=models.WinnerLoteria.TYPE.PROGRESION
                )

        # TERMINACIONES
        endings = [(4,1),(3,1),(2,1),(2,2),(2,3),(1,1)] # (digits, location)
        for digits, location in endings:
            if digits == len(str(results[location-1])):
                # Si el num en primera posicion tiene cuatro cifras ignorar terminacion de 4 digitos
                continue

            if detailObj.coupon.number.endswith('{}'.format(results[location-1])[-digits:]):
                models.WinnerLoteria.objects.get_or_create(
                        detail=detailObj,
                        draw=draw,
                        info=u'{} dígitos'.format(digits),
                        prize=prizes.ending_prize(digits, location)*fraction_proportion,
                        type=models.WinnerLoteria.TYPE.ENDING
                    )
                break

        # APROXIMACIONES
        for pos, number in enumerate(results[:3]):
            if int(coupon_number) == models.LOTERIA_MAX_COUPON and int(number) == models.LOTERIA_MIN_COUPON:
                info = 'Anterior'
            elif coupon_number == number - 1:
                info = 'Anterior'
            elif int(coupon_number) == models.LOTERIA_MIN_COUPON and int(number) == models.LOTERIA_MAX_COUPON:
                info = 'Posterior'
            elif coupon_number == number + 1:
                info = 'Posterior'
            else:
                continue

            models.WinnerLoteria.objects.get_or_create(
                detail=detailObj,
                draw=draw,
                info='{}° Premio - {}'.format(pos+1, info),
                prize=prizes.approach_prize(pos+1)*fraction_proportion,
                type=models.WinnerLoteria.TYPE.APPROACH
            )


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def telebingo_winners(request, draw_id):

    draw = get_object_or_404(models.DrawPreprinted, id=draw_id)

    winners = models.WinnerTelebingo.objects.filter_by_draw(draw)
    coupon_winners = models.WinnerTelebingoCoupon.objects.filter(extract__draw=draw)
    total = winners.filter(notif=False).count() + coupon_winners.filter(notif=False).count()

    formset = forms.WinnerFormSet(request.POST or None, queryset=winners)
    coupons_formset = forms.WinnerFormSet(request.POST or None, queryset=coupon_winners, prefix='coupon')
    if request.method == 'POST' and formset.is_valid() and coupons_formset.is_valid():
        instances = formset.save()
        coupons_instances = coupons_formset.save()

        emails = []
        conn = mail.get_connection(fail_silently=not settings.DEBUG)
        # Manually open the connection
        conn.open()
        for instance in instances:
            notif = send_winner_notification(request, instance.parent, send=False)
            if notif is not None:
                emails.append(notif)

        for instance in coupons_instances:
            notif = send_tbg_coupon_winner_notification(request, instance.parent,send=False)
            if notif is not None:
                emails.append(notif)

        # Send the two emails in a single call -
        conn.send_messages(emails)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        conn.close()

        return redirect('bet:telebingo_winners', draw_id)

    context = {'draw': draw, 'not_notified': total > 0, 'formset': formset,
               'coupons_formset': coupons_formset, 'total': total}
    return render(request, 'winners/telebingo_winners.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def loteria_winners(request, draw_id):

    draw = get_object_or_404(models.DrawPreprinted, id=draw_id)

    winners = draw.winner_set.order_by('info')
    not_notified = winners.filter(notif=False).count() > 0

    formset = forms.WinnerFormSet(request.POST or None, queryset=winners)
    if request.method == 'POST' and formset.is_valid():
        instances = formset.save()

        emails = []
        conn = mail.get_connection(fail_silently=not settings.DEBUG)
        # Manually open the connection
        conn.open()
        for instance in instances:
            notif = send_winner_notification(request, instance.parent, send=False)
            if notif is not None:
                emails.append(notif)

        # Send the two emails in a single call -
        conn.send_messages(emails)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        conn.close()

        return redirect('bet:loteria_winners', draw_id)

    context = {'draw': draw, 'not_notified': not_notified, 'formset': formset}
    return render(request, 'winners/loteria_winners.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@transaction.atomic
def loteria_prizes(request, year=None, month=None, draw_pk=None):

    if month is None:
        today = tz_today()
        month = today.month
        year = today.year
    try:
        lp = models.LoteriaPrize.objects.get(year=year, month=month)
    except models.LoteriaPrize.DoesNotExist:
        lp = models.LoteriaPrize(year=year, month=month)

    monthForm = forms.MonthForm(initial={'month': date(int(year), int(month), 1)})

    prizesQuerySet = models.LoteriaPrizeRow.objects.filter(month=lp).order_by('code')

    initial=[{'code': i} for i in range(len(models.LoteriaPrizeRow.CODE_CHOICES))]

    if request.method == 'POST':
        prizeFormSet = forms.LoteriaPrizeFormSet(request.POST, instance=lp, prefix='prize')

        if prizeFormSet.is_valid():
            if lp.pk is None:
                lp.save()
                instances = prizeFormSet.save(commit=False)
                for instance in instances:
                    instance.month = lp
                    instance.save()
            else:
                prizeFormSet.save()

            messages.add_message(request, messages.SUCCESS, 'Premios guardados correctamente.')
            if draw_pk is not None:
                return redirect('bet:loteria_results', draw_pk)
            else:
                return redirect('bet:loteria_prizes', year, month)
    else:
        prizeFormSet = forms.LoteriaPrizeFormSet(instance=lp, queryset=prizesQuerySet,
                                                 initial=initial, prefix='prize')

    #filterForm = forms.LoteriaPrizeFilter(request.GET)

    current = date(int(year),int(month),1)
    prev_date = current - relativedelta(months=1)
    next_date = current + relativedelta(months=1)
    context = {'prizeFormSet': prizeFormSet, 'date': current, 'next_date': next_date,
               'prev_date': prev_date, 'draw_pk': draw_pk, 'form': monthForm}
    return render(request, 'config/loteria_prizes.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def quiniela_winners(request, group_pk):

    group = get_object_or_404(models.QuinielaGroup, pk=group_pk)

    winners = models.BaseWinner.objects.filter(winnerquiniela__detail__detailquiniela__group=group).distinct()
    not_notified = winners.filter(notif=False).count() > 0

    formset = forms.BaseWinnerFormSet(request.POST or None, queryset=winners)
    if request.method == 'POST' and formset.is_valid():
        instances = formset.save()

        emails = []
        connection = mail.get_connection(fail_silently=not settings.DEBUG)
        # Manually open the connection
        connection.open()
        for instance in instances:
            notif = send_quiniela_winner_notification(request, instance, send=False)
            if notif is not None:
                emails.append(notif)

        # Send the two emails in a single call -
        connection.send_messages(emails)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        connection.close()

        return redirect('bet:quiniela_winners', group_pk)

    context = {'redoblona': True, 'group': group,
               'draw': {'game': {'code': 'quiniela'}}, 'not_notified': not_notified, 'formset': formset}
    return render(request, 'winners/quiniela_winners.html', context)


def update_quiniela_winners(group):

    #delete_quiniela_winners(group)
    draws = group.draws.all()
    quinielaResults = models.QuinielaResults.objects.filter(draw__in=draws).order_by('draw__type','draw__quiniela')

    #redoblona = False
    base_winners = defaultdict(lambda : None)

    lot_winned = []

    for resultsObj in quinielaResults:
        numbers = resultsObj.res.get_numbers

        for detailObj in resultsObj.draw.detail_set.filter(state=models.BaseDetail.STATE.PLAYED):
            prizes = detailObj.bet.agency.province.prizes

            # si es redoblona lo ignoro
            if hasattr(detailObj, 'apuesta'):
                continue

            digits = len(detailObj.number)

            #ES ACA MLG
            print "*********** AD", digits, detailObj
            # TODO! tope de banca, cuantas repeticiones se cuentan en redoblona?
            hits = count_hits(detailObj.number, numbers[:detailObj.location])
            if hits > 0:
                lot_winned.append(resultsObj.draw.quiniela.code)


    for resultsObj in quinielaResults:
        numbers = resultsObj.res.get_numbers

        for detailObj in resultsObj.draw.detail_set.filter(state=models.BaseDetail.STATE.PLAYED):
            prizes = detailObj.bet.agency.province.prizes

            # si es redoblona lo ignoro
            if hasattr(detailObj, 'apuesta'):
                continue

            digits = len(detailObj.number)

            #ES ACA MLG
            print "*********** AD", digits, detailObj
            # TODO! tope de banca, cuantas repeticiones se cuentan en redoblona?
            hits = count_hits(detailObj.number, numbers[:detailObj.location])
            day = resultsObj.draw.date_draw.weekday()
            if hits > 0:
                real_import = detailObj.real_import(resultsObj.draw.quiniela.code, lot_winned)
                print "********************* ACA ACA ACA", real_import, hits, digits, prizes, detailObj.location, day, resultsObj.draw.quiniela, resultsObj.draw.quiniela.code
                real_import = round(real_import, 2)
                if settings.APP_CODE == 'SF':

                    if detailObj.location == 1:
                        if digits == 1:
                            prize = hits * 7.00 * real_import
                        elif digits == 2:
                            prize = hits * 70.00 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize = hits * 700.00 * real_import
                            else:
                                prize = hits * 600.00 * real_import
                        elif digits == 4:
                            prize = hits * 3500 * real_import
                        elif digits == 5:
                            prize = hits * 10000 * real_import

                    elif detailObj.location == 2:
                        if digits == 1:
                            prize = hits * 3.50 * real_import
                        elif digits == 2:
                            prize = hits * 35.00 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize = hits * 350.00 * real_import
                            else:
                                prize =hits *  300.00 * real_import
                        elif digits == 4:
                            prize = hits * 1750 * real_import
                        elif digits == 5:
                            prize = hits * 5000 * real_import

                    elif detailObj.location == 3:
                        if digits == 1:
                            prize = hits * 2.33 * real_import
                        elif digits == 2:
                            prize = hits * 23.33 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize =hits *  233.33 * real_import
                            else:
                                prize =hits *  200.00 * real_import
                        elif digits == 4:
                            prize = hits * 1166.67 * real_import
                        elif digits == 5:
                            prize = hits * 3300 * real_import

                    elif detailObj.location == 4:
                        if digits == 1:
                            prize = hits * 1.75 * real_import
                        elif digits == 2:
                            prize =hits *  17.50 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize =hits *  175.00 * real_import
                            else:
                                prize = hits * 150.00 * real_import
                        elif digits == 4:
                            prize = hits * 875.00 * real_import
                        elif digits == 5:
                            prize = hits * 2500 * real_import

                    elif detailObj.location == 5:
                        if digits == 1:
                            prize = hits * 1.40 * real_import
                        elif digits == 2:
                            prize = hits * 14.00 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize = hits * 140.00 * real_import
                            else:
                                prize = hits * 120.00 * real_import
                        elif digits == 4:
                            prize = hits * 700.00 * real_import
                        elif digits == 5:
                            prize = hits * 2000 * real_import

                    elif detailObj.location == 10:

                        if digits == 1:
                            prize = hits * 0.70 * real_import
                        elif digits == 2:
                            prize = hits * 7.00 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize =hits *  70.00 * real_import
                            else:
                                prize =hits *  60.00 * real_import
                        elif digits == 4:
                            prize = hits * 350.00 * real_import
                        elif digits == 5:
                            prize = hits * 1000 * real_import

                    elif detailObj.location == 20:
                        if digits == 1:
                            prize = hits * 0.35 * real_import
                        elif digits == 2:
                            prize = hits * 3.50 * real_import
                        elif digits == 3:
                            if day == 6:
                                prize = hits * 35.00 * real_import
                            else:
                                prize = hits * 30.00 * real_import
                        elif digits == 4:
                            prize = hits * 175.00 * real_import
                        elif digits == 5:
                            prize = hits * 500 * real_import
                else:
                   prize = hits * real_import * round(prizes[digits]/float(detailObj.location),2)

                if detailObj.redoblona is not None:
                    shift = int(detailObj.location == 1) # Si la primer jugada fue a la cabeza
                                                        # los premios se corren una posicion

                    red_hits = count_hits(detailObj.redoblona.number,
                                          numbers[shift:detailObj.redoblona.location+shift])

                    if detailObj.number == detailObj.redoblona.number:
                        # Si es al mismo numero se cuenta un solo acierto de la primer jugada
                        prize /= hits
                        hits = 1

                        if red_hits < 2: # Si el numero es el mismo debe aparecer al menos 2 veces
                            red_hits = 0

                    if detailObj.location == 1 and detailObj.redoblona.location==20:
                        division = 19.0
                    else:
                        division = float(detailObj.redoblona.location)


                    vv = truncate(prizes[digits]/division, 2)
                    print "*************************"
                    print str(vv)
                    print str(prizes[digits]/division)
                    print "*************************"

                    prize *= red_hits * vv

                if prize > 0:
                    bw = base_winners[detailObj.bet] = base_winners[detailObj.bet] or models.BaseWinner.objects.create(info='')
                    winner, created = models.WinnerQuiniela.objects.get_or_create(
                        detail=detailObj, draw=resultsObj.draw, info=resultsObj.draw.get_type_display(),
                        prize=prize, hits=hits, winner_ticket=bw
                    )
                    if detailObj.redoblona is not None:
                        winner.redoblona = {'number': detailObj.redoblona.number,
                                            'location': detailObj.redoblona.get_location_display()}
                        #redoblona = True



#================================= ENDWINNERS ====================================

@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
@require_POST
def lottery_time(request):
    if not request.is_ajax():
        return HttpResponseForbidden()

    type_id = request.POST.get('type_id') or None
    quinielas = request.POST.getlist('quinielas[]') or [request.POST.get('quinielas')]
    if '' in quinielas:
        quinielas.remove('')

    try:
        lt = models.LotteryTime.objects.filter(
            quiniela__in=quinielas,
            type=type_id
        ).earliest('draw_time')
        draw_date = datetime.combine(tz_today(), lt.draw_time).strftime('%Y-%m-%d %H:%M')
        draw_limit = datetime.combine(tz_today(), lt.draw_limit).strftime('%Y-%m-%d %H:%M')
        draw_limit_agency = datetime.combine(tz_today(), lt.draw_limit_agency).strftime('%Y-%m-%d %H:%M')
        #draw_limit_agency = (datetime.combine(tz_today(), lt.draw_time) - timezone.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M')

        return JsonResponse({'draw_date': draw_date,
                             'draw_limit': draw_limit,
                             'draw_limit_agency': draw_limit_agency})

    except models.LotteryTime.DoesNotExist:
        return JsonResponse(dict())


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def quiniela_number(request, date_str, lottery, type):
    if not request.is_ajax():
        return HttpResponseForbidden()

    try:
        date_draw = to_localtime(date_str, '%Y-%m-%d').date()
        query = utils.build_date_query('date_draw', date_draw)
        query.update({
            'quiniela': lottery,
            'type': type
        })
        number = models.DrawQuiniela.objects.get(**query).number
        return JsonResponse(dict(number=number))
    except models.DrawQuiniela.DoesNotExist:
        return JsonResponse(dict())


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def provinces(request):

    form = forms.QuinielasProvinceForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            province_id = form.cleaned_data['province']
            quinielas_ids = form.cleaned_data['quinielas']

            province = models.Province.objects.get(pk=int(province_id)+1)
            #province.quinielas.clear()
            quinielas = models.Quiniela.objects.filter(pk__in=quinielas_ids)
            province.quinielas = quinielas

            return redirect('bet:provinces')

    return render(request, 'quinielas_by_province.html', {'form': form})


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def get_quinielas_by_provice(request, province_id=None):

    if not request.is_ajax():
        return HttpResponseForbidden()

    try:
        province = models.Province.objects.get(id=province_id)
        quinielas = province.quinielas.values_list('pk', flat=True)
    except models.Province.DoesNotExist:
        quinielas = []

    return JsonResponse(dict(quinielas=list(quinielas)))


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def bet_detail(request, pk, code):
    game = get_object_or_404(models.Game, code=code)
    bet = get_object_or_404(models.Bet, pk=pk)
    details = bet.get_details()

    if game.type == models.Game.TYPE.PREPRINTED:
        code = 'coupons'

    if game.code == models.Game.CODE.QUINIELA:
        q_details = defaultdict(list)

        for detail in details:
            q_details[tuple(set(detail.draws.all()))].append(detail)

        details = dict(q_details)

    context = {'details': details, 'game': game, 'bet': bet}
    return render(request, 'details/{}_details.html'.format(code), context)
    #return render(request, 'basebet_details.html', context)


@login_required()
@user_passes_test(lambda user: is_admin(user) or is_agenciero(user),
                  login_url='/denied', redirect_field_name=None)
def agen_movement_detail(request, pk):
    mov = get_object_or_404(models.AgenMovement, pk=pk).parent
    if not is_admin(request.user) and mov.agency.user != request.user:
        raise PermissionDenied

    context = {'movement': mov}
    return render(request, 'agen_movements/{}_details.html'.format(mov.code), context)
    #return render(request, 'basebet_details.html', context)


def request_ticket(request, id, key):
    ticket = _request_ticket(id, key)
    if isinstance(ticket, models.Ticket):
        context = {'error': False}
    elif isinstance(ticket, int):
        context = {'error': True, 'message': models.Ticket.get_state_display(ticket)}
        if ticket == 1 or ticket == 2:
            context['error'] = False
    else:
        context = {'error': True, 'message': ticket['error_msg']}

    return render(request, 'ticket_requested.html', context)


def send_quiniela_winner_notification(request, winner, send=True):
    profile = winner.bet.user
    prize, taxes, total = winner.prize_with_taxes()
    should_be_paid = winner.should_be_paid()

    try:
        with transaction.atomic():

            # Si el premio no se paga en la agencia no generar movimientos de Premio
            if should_be_paid:
                profile.saldo += prize
                profile.save(update_fields=('saldo',))

                mov = models.PrizeMovement.objects.create(
                    code='PR',
                    user=profile,
                    amount=prize,
                    state=models.PrizeMovement.STATE.CONFIRMED,
                    winner=winner
                )
                mov.confirm_date = timezone.now()
                mov.save()

                # AGENCY MOVEMENT
                agen_mov = models.WinnerCommissionMov(
                    agency=winner.bet.agency,
                    amount=prize,
                    state=models.AgenMovement.STATE.PENDING,
                    winner=winner
                )
                agen_mov.save()
            else:
                recipients = [settings.SERVER_EMAIL]
                context = {'winner': winner, 'game': winner.game, 'user': profile.user}
                utils.send_email(request, 'emails/extern_winner_email', recipients, context)

            winner.notif = True
            winner.save(update_fields=('notif',))

    except IntegrityError as e:
        logger.error("Error al notificar ganador. winner pk={}. \n{}".format(winner.pk, e))
    else:
        message = u'¡Felicitaciones! Has ganado ${} en la quiniela.'.format(round(prize, 2))
        data = {'game': winner.game.name, 'amount': to_simple_types(round(prize, 2)),
                'date_draw': to_simple_types(winner.draw.date_draw),
                'number': winner.draw.number}
        profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'¡Ganaste!', message, data=data)

        context = {'winner': winner, 'game': winner.game, 'user': profile.user, 'taxes': taxes, 't_prize': prize}
        return profile.email_notification(request, models.USER_SETTINGS.MAIL_WINNER_NOTIFICATION,
                                          'emails/winner_quiniela_email', context, send=send)


def send_winner_notification(request, winner, send=True):

    if winner.prize_type == models.Prize.TYPE.COUPON:
        return send_coupon_winner_notification(request, winner, send)
    elif winner.prize_type == models.Prize.TYPE.CASH:
        return send_cash_winner_notification(request, winner, send)
    else:
        return send_other_winner_notification(request, winner, send)


def send_coupon_winner_notification(request, winner, send=True):
    detail = winner.get_detail
    profile = detail.bet.user

    credit = models.UserCredit.objects.create(
        user=profile,
        expiration=detail.draw.date_draw + timezone.timedelta(days=15),
        winner=winner,
        agency=detail.bet.agency,
        game=detail.bet.game
    )

    # Si ya hay coupones disponibles se le asigna uno
    coupons = models.Coupon.objects.filter(draw__game=detail.coupon.draw.game,
                                           draw__date_draw__lt=credit.expiration,
                                           draw__date_limit__gt=timezone.now(),
                                           fraction_saldo__gte=detail.fraction_bought,
                                           agency=detail.coupon.agency)
    if coupons.exists():
        apply_credits(request, coupons.earliest('draw__date_draw').draw, notify=False)

        message = u'¡Felicitaciones! Ganaste otro billete de {}.'.format(winner.game.name)
    else:
        message = u'¡Felicitaciones! Ganaste otro billete de {}. ' \
                  u'Recibirás tu premio antes del próximo sorteo.'.format(winner.game.name)

    data = {'game': winner.game.name, 'amount': to_simple_types(winner.get_prize()),
            'date_draw': to_simple_types(winner.draw.date_draw),
            'number': winner.draw.number}
    profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'¡Ganaste!', message, data=data)



    winner.notif = True
    winner.save(update_fields=('notif',))
    return result


def send_other_winner_notification(request, winner, send=True):
    assert (winner.prize_type == models.Prize.TYPE.OTHER)

    detail = winner.get_detail
    profile = detail.bet.user

    # NOTIFICAR A AGENCIA24
    recipients = [settings.SERVER_EMAIL]
    context = {'winner': winner, 'game': winner.draw.game, 'user': detail.bet.user.user}
    utils.send_email(request, 'emails/extern_winner_email', recipients, context)

    winner.notif = True
    winner.save(update_fields=('notif',))

    # NOTIFICAR AL USUARIO
    game = winner.game
    prize = winner.get_prize()
    try:
       message = u'¡Felicitaciones! Has ganado {} en {} {}.'.format(round(prize, 2), game.article, game.name)
       data = {'game': game.name, 'amount': to_simple_types(round(prize, 2)),
            'date_draw': to_simple_types(winner.draw.date_draw),
            'number': winner.draw.number}
       profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'¡Ganaste!', message, data=data)

    except Exception as e:
       message = u'¡Felicitaciones! Has ganado {} en {} {}.'.format(prize, game.article, game.name)
       data = {'game': game.name, 'amount': prize,
            'date_draw': to_simple_types(winner.draw.date_draw),
            'number': winner.draw.number}
       profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'¡Ganaste!', message, data=data)


    context = {'winner': winner, 'game': game, 'user': detail.bet.user.user}
    return profile.email_notification(request, models.USER_SETTINGS.MAIL_WINNER_NOTIFICATION,
                                      'emails/winner_email', context, send=send)


def change_text(text):
    return text.encode('utf-8')

def send_cash_winner_notification(request, winner, send=True):
    assert(winner.prize_type == models.Prize.TYPE.CASH)
    #assert(winner.notif == False)
    print "********",type(winner) ,"*********"
    profile = winner.get_detail.bet.user
    agency = winner.get_detail.bet.agency

    game = winner.game
    prize, taxes, total = winner.prize_with_taxes()
    should_be_paid = winner.should_be_paid()

    try:
        with transaction.atomic():

            # Si el premio no se paga en la agencia no generar movimientos de Premio
            if should_be_paid:
                profile.saldo += prize
                profile.save(update_fields=('saldo',))

                mov = models.PrizeMovement.objects.create(
                    code='PR',
                    user=profile,
                    amount=prize,
                    state=models.PrizeMovement.STATE.CONFIRMED,
                    winner=winner
                )
                mov.confirm_date = timezone.now()
                mov.save()

                # AGENCY MOVEMENT
                agen_mov = models.WinnerCommissionMov(
                    agency=agency,
                    amount=prize,
                    state=models.AgenMovement.STATE.PENDING,
                    winner=winner
                )
                agen_mov.save()
            else:
                recipients = [settings.SERVER_EMAIL]
                context = {'winner': winner, 'game': game, 'user': profile.user}
                utils.send_email(request, 'emails/extern_winner_email', recipients, context)

            winner.notif = True
            winner.save(update_fields=('notif',))

    except IntegrityError as e:
        logger.error("Error al notificar ganador. winner pk={}. \n{}".format(winner.pk, e))
    else:
        message = u'¡Felicitaciones! Has ganado ${} en {} {}.'.format(round(total, 2), game.article, game.name)
        data = {'game': game.name, 'amount': to_simple_types(round(total, 2)),
                'date_draw': to_simple_types(winner.draw.date_draw),
                'number': winner.draw.number}
        profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'¡Ganaste!', message, data=data)
        telebingogame = winner.draw.game.code.startswith("telebingo")

        date_prescribe = winner.draw.date_draw + timezone.timedelta(days=15)


        drawstr = ""
        if winner.draw.game.code.startswith("telebingo"):
            c = ""
            if winner.type == 0:
                c = "Linea"
            if winner.type == 1:
                c = "Bingo"
            drawstr = "Sorteo N " + str(winner.draw.number) + " – "+ c +" - Billete Nº " + str(winner.get_detail.coupon.number) + " – Fecha Sorteo " + to_simple_types(
                winner.draw.date_draw) + "– Prescripción " + str(date_prescribe)

            #result = profile.email_notification(request, models.USER_SETTINGS.MAIL_WINNER_NOTIFICATION,
            #                                    'emails/winner_email', context, send=send)

            #print "TELEBINGOGAME ", telebingogame, change_text(drawstr)


        #mlgmlgmlg
        attach = None
        if winner.draw.game.code.startswith("telebingo"):
            html =  get_winner_virtual_coupon(request, winner.get_detail.coupon.id)
            STATIC_ROOT = os.path.join(settings.PROJECT_ROOT, 'site_media', 'static')
            css = list([os.path.join(STATIC_ROOT, 'bootstrap', 'css', 'bootstrap.css')])
            css.append(os.path.join(STATIC_ROOT, 'tickets.css'))

            output = tempfile.NamedTemporaryFile(suffix='.pdf')
            #pdfkit.from_string(html, output.name, css=css, options=get_extract_options( winner.draw.game.code,1),
            #                   configuration=Configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))

            #attach = ('cupon.pdf', output.read(),'application/pdf')
            #attach = [attach]
	    attach = []
        context = {'winner': winner, 'game': game, 'user': profile.user, 'taxes': taxes, 't_prize': prize,'telebingogame': telebingogame,
                   'telebingogame_draw': drawstr}
        return profile.email_notification(request, models.USER_SETTINGS.MAIL_WINNER_NOTIFICATION,
                                           'emails/winner_email', context, send=send, attachments=attach)


def send_tbg_coupon_winner_notification(request, winner, send=True):
    assert(winner.prize_type == models.Prize.TYPE.CASH)
    assert(isinstance(winner, models.WinnerTelebingoCoupon))
    #assert(winner.notif == False)

    print "*********" , type(winner) , "***********"

    try:
        profile = models.UserProfile.objects.get(dni=winner.extract.number)
    except models.UserProfile.DoesNotExist:
        logger.error(u'Intentando notificar "NO GANADOR" de usuario que no está en el sistema.')
        return

    game = winner.extract.draw.game
    prize, taxes, total = winner.prize_with_taxes()


    try:
        with transaction.atomic():
            recipients = [settings.SERVER_EMAIL]
            context = {'winner': winner, 'game': game, 'user': profile.user}
            utils.send_email(request, 'emails/extern_winner_email', recipients, context)

            winner.notif = True
            winner.save(update_fields=('notif',))

    except IntegrityError as e:
        logger.error("Error al notificar ganador. winner pk={}. \n{}".format(winner.pk, e))
    else:
        message = u'¡Felicitaciones! Has ganado ${} en {} {}.'.format(round(total, 2), game.article, game.name)
        data = {'game': game.name, 'amount': to_simple_types(round(total, 2)),
                'date_draw': to_simple_types(winner.draw.date_draw),
                'number': winner.draw.number}
        profile.push_notification(models.USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'¡Ganaste!', message, data=data)

        telebingogame = winner.draw.game.code.startswith("telebingo")

        date_prescribe = winner.draw.date_draw + timezone.timedelta(days=15)

        drawstr = "Sorteo Nº " + winner.draw.draw_number + " – “Línea o Bingo” “1º 2º 3º etc.” Ronda - Billete Nº " + winner.get_detail.coupon.number + " – Fecha Sorteo " + to_simple_types(
            winner.draw.date_draw) + "– Prescripción " + date_prescribe


        print "TELEBINGOGAME ", telebingogame, drawstr

        context = {'winner': winner, 'game': game, 'user': profile.user, 'taxes': taxes, 't_prize': prize, 'telebingogame': telebingogame,
                   'telebingogame_draw': drawstr}

        return profile.email_notification(request, models.USER_SETTINGS.MAIL_WINNER_NOTIFICATION,
                                          'emails/winner_email', context, send=send)


def delete_winners(draws):

    winners = models.Winner.objects.filter(draw__in=draws)
    for w in winners:
        if not w.notif:
            continue
        profile = w.get_detail.bet.user
        profile.saldo -= w.get_prize()
        profile.save(update_fields=('saldo',))
    winners.delete()


def delete_quiniela_winners(group):

    details = models.DetailQuiniela.objects.filter(group=group, winner__isnull=False)
    for detail in details:
        profile = detail.bet.user
        for w in detail.winner_set.all():
            base = w.parent.winner_ticket
            if not w.notif:
                continue

            profile.saldo -= w.get_prize()
            profile.save(update_fields=('saldo',))
        if not detail.winner_set.exists():
            base.delete()
        detail.winner_set.all().delete()


def fix(request):  #TODO! DELETE
    tk = dq = bet = 0
    for d in models.DetailQuiniela.objects.all():
        if d.draws.first() is None:
            dq += 1
            d.delete()

    for b in models.Bet.objects.all():
        if b.game is None:
            bet += 1
            b.delete()

    for t in models.Ticket.objects.all():
        try:
            t.get_details()
        except:
            tk += 1
            t.delete()

    msg = u'{} DetailQuiniela(s) deleted, {} Bet(s) deleted, {} Ticket(s) deleted'.format(dq, bet, tk)
    messages.add_message(request, messages.SUCCESS, msg)
    return redirect('bet:games')


def faketicket(request, ticket_pk):
    ticket = models.Ticket.objects.get(id=ticket_pk)
    ticket.create_fake_ticket(request)

    from bet.utils import get_current_site
    sitedomain = get_current_site(request).domain
    protocol = 'https' if request.is_secure() else 'http'
    url = "{}://{}{}".format(protocol, sitedomain, ticket.fake.url)

    return render(request, 'tickets/fake.html', {'url': url})

def faketicket_html(request, ticket_pk):
    ticket = models.Ticket.objects.get(id=ticket_pk)
    html = ticket.create_fake_ticket(request, pdf=False)

    return HttpResponse(html)


def create_extract(request, draw_pk):
    draw = get_object_or_404(models.BaseDraw, pk=draw_pk)

    context = None
    if draw.game.code == models.Game.CODE.LOTERIA:
        context = {'lp': draw.loteria_prize}

    html = draw.create_extract(request, context)

    from bet.utils import get_current_site
    sitedomain = get_current_site(request).domain
    protocol = 'https' if request.is_secure() else 'http'
    url = "{}://{}{}".format(protocol, sitedomain, draw.extract_file.url)

    return render(request, 'extract/fake.html', {'url': url})

def extract_html(request, draw_pk):
    draw = get_object_or_404(models.BaseDraw, pk=draw_pk)

    context = None
    if draw.game.code == models.Game.CODE.LOTERIA:
        context = {'lp': draw.loteria_prize}

    html = draw.create_extract(request, context, pdf=False)

    return HttpResponse(html)


def create_group_extract(request, group_pk):
    group = get_object_or_404(models.QuinielaGroup, pk=group_pk)

    html = group.create_extract(request)

    from bet.utils import get_current_site
    sitedomain = get_current_site(request).domain
    protocol = 'https' if request.is_secure() else 'http'
    url = "{}://{}{}".format(protocol, sitedomain, group.extract_file.url)

    return render(request, 'extract/fake.html', {'url': url})


def extract_group_html(request, group_pk):
    group = get_object_or_404(models.QuinielaGroup, pk=group_pk)

    html = group.create_extract(request, None, pdf=False)

    return HttpResponse(html)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def game_taxes(request):

    province = request.GET.get('province', None) or None

    taxes = models.GameTax.objects.filter(province=province)

    game_list = list(models.Game.objects.values_list('pk', flat=True))

    GameTaxFormSet = modelformset_factory(models.GameTax, forms.GameTaxForm, extra=0, min_num=len(game_list))

    if request.method == 'POST':
        taxesFormSet = GameTaxFormSet(request.POST, prefix='tax')

        if taxesFormSet.is_valid():
            instances = taxesFormSet.save(commit=False)
            for instance in instances:
                instance.province_id = province
                instance.save()

            msg = u'Impuestos guardados correctamente.'
            messages.add_message(request, messages.SUCCESS, msg)

            return redirect(reverse('bet:game_taxes') + '?province=' + province)
    else:
        initial=[{'game': g, 'province': province} for g in game_list]
        taxesFormSet = GameTaxFormSet(queryset=taxes, initial=initial, prefix='tax')

    filterForm = forms.GameTaxFilter(request.GET)

    context = {'taxesFormSet': taxesFormSet, 'filterForm': filterForm}
    return render(request, 'config/game_taxes.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def bet_commissions(request):

    commissions = models.BetCommission.objects.order_by('game__pk')
    formset = modelformset_factory(models.BetCommission, forms.BetCommissionForm,
                                   extra=0, min_num=commissions.count())

    if request.method == 'POST':
        commFormSet = formset(request.POST, prefix='comm')

        if commFormSet.is_valid():
            commFormSet.save()

            msg = u'Comisiones guardadas correctamente.'
            messages.add_message(request, messages.SUCCESS, msg)

            return redirect(reverse('bet:bet_commissions'))
    else:
        commFormSet = formset(queryset=commissions, prefix='comm')

    context = {'commFormSet': commFormSet}
    return render(request, 'config/bet_commissions.html', context)


@require_POST
@csrf_exempt
def android_error(request):
    utils.send_email(request, 'emails/admins_email', [x[1] for x in settings.ADMINS],
                     request.POST, imgs=[])
    return HttpResponse()




@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def promotions(request):

    instances = models.DrawPromotion.objects.order_by('draw__date_draw')

    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)

    if date_from:
        dt = to_localtime(date_from)
    else:
        dt = timezone.now()

    instances = instances.select_related().filter(draw__date_limit__gte=dt)

    if date_to:
        dt = to_localtime(date_to) + timezone.timedelta(days=1)
        instances = instances.filter(draw__date_draw__lt=dt)
    if code:
        instances = instances.filter(draw__game__code=code)
    if state:
        instances = instances.filter(is_active=int(state))


    form = forms.FilterPromotionsForm(request.GET)
    context = {'promotions': instances, 'form': form}
    return render(request, 'promotions.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def promotion(request, promo_pk=None):

    initial = {}
    if promo_pk is not None:
        instance = get_object_or_404(models.DrawPromotion, pk=promo_pk)
        initial = {'game': instance.draw.game}
    else:
        instance = models.DrawPromotion()

    form = forms.DrawPromotionForm(request.POST or None, instance=instance, initial=initial)
    if request.method == 'POST' and form.is_valid():
        form.save()

        context = {'title': u'Promoción',
                   'message': u'Promoción {} exitosamente.'.format('editada' if promo_pk else 'creada')}
        return render(request, 'promotion_success.html', context)

    context = {'promotion': instance, 'form': form}
    return render(request, 'promotion.html', context)


@login_required()
@user_passes_test(is_admin, login_url='/denied', redirect_field_name=None)
def prod2desa(request):
    from scripts.prod2desa import copy_draws

    _from = request.GET.get('from', None)
    _to = request.GET.get('to', None)
    if _from and _to:
        try:
            copy_draws(_from, _to)
            messages.add_message(request, messages.SUCCESS, 'Exito rotundo en la copia de sorteos')
        except:
            messages.add_message(request, messages.ERROR, 'No se pudo che')

    return redirect('bet:home')


def extract_email(request, bet_id, email=False):
    from bet.utils import send_email

    instance = get_object_or_404(models.Bet, id=bet_id)
    draw = instance.draws[0]

    if instance.game.code == models.Game.CODE.QUINIELA:
        group = instance.detailquiniela_set.first().group
        if group.extract_file is None:
            group.create_extract(request, None)

        tickets = models.Ticket.objects.filter(detailquiniela__group=group,
                                               detailquiniela__state=models.BaseDetail.STATE.PLAYED)

        try:
            user_tickets = tickets.filter(detailquiniela__bet__user__pk=instance.user_id).distinct()
        except NotImplementedError:
            user_tickets = tickets.filter(detailquiniela__bet__user__pk=instance.user_id)

        context = {'game': group.draws.first().game, 'draw': group, 'tickets': user_tickets}

        if email:
            attachs = [(u'{}-{}.pdf'.format(models.Game.CODE.QUINIELA, group.number),
                        group.extract_file.read(), 'application/pdf')]
            send_email(request, 'emails/extract_email', [], context=context,
                               attachments=attachs, bcc=[instance.user.user.email])

        return render(request, 'emails/extract_email.html', context)

    imgs = None
    if instance.game.type == models.Game.TYPE.NONPRINTED:
        tickets = models.Ticket.objects.filter(detail__draw=draw, detail__state=models.BaseDetail.STATE.PLAYED)

    else:
        tickets = models.Ticket.objects.filter(detailcoupons__coupon__draw=draw,
                                        detailcoupons__state=models.BaseDetail.STATE.PLAYED)
        if email:
            imgs = [ticket.real for ticket in tickets if ticket.real]

    context = None
    if draw.game.code == models.Game.CODE.LOTERIA:
        context = {'lp': draw.loteria_prize}

    if draw.extract_file is None:
        draw.create_extract(request, context)

    if draw.game.type == models.Game.TYPE.NONPRINTED:
        user_tickets = tickets.filter(detail__bet__user__pk=instance.user_id)
    else:
        user_tickets = tickets.filter(detailcoupons__bet__user__pk=instance.user_id)

    context = {'draw': draw, 'game': draw.game, 'tickets': user_tickets}
    if email:
        attachs = [(u'{}-{}.pdf'.format(draw.game.code, draw.number),
                    draw.extract_file.read(), 'application/pdf')]
        send_email(request, 'emails/extract_email', [], context=context,
                           attachments=attachs, bcc=[instance.user.user.email], imgs=imgs)
    return render(request, 'emails/extract_email.html', context)


@csrf_exempt
def mp_notification(request):

    try:
        client_ip = request.META['REMOTE_ADDR']
        print client_ip
        topic = request.GET.get('topic')
    except KeyError:
        return HttpResponse(
            '<h1>400 Bad Request.</h1>'
            'Missing parameter topic',
            status=400
        )
    try:
        id = request.GET.get('id')
    except KeyError:
        return HttpResponse(
            '<h1>400 Bad Request.</h1>'
            'Missing parameter id',
            status=400
        )
    logger.debug('topic: {}, id: {}'.format(topic, id))
    print "*********************** MERCADO PAGO"
    print 'topic: {}, id: {}'.format(topic, id)

    if topic != 'payment':
        return HttpResponse("<h1>200 OK</h1>", status=200)
        #return HttpResponse('invalid topic', status=400)

    mp = mercadopago.MP(settings.MP_CLIENT_ID, settings.MP_SECRET_KEY)
    #mp.sandbox_mode(True)

    payment_info = mp.get_payment_info(id)
    #utils.send_email(request, 'emails/mp_notification_email', ['developer@liricus.com.ar'],
    #                 {'payment_info': json.dumps(payment_info, indent=4), 'id': id})
    logger.debug('payment_info: {}'.format(payment_info))
    print "*********************** MERCADO PAGO"
    print payment_info

    if payment_info["status"] == 200:
        try:

            print payment_info["response"]["collection"]["external_reference"]

            mov = models.ChargeMovement.objects.filter(number=payment_info["response"]["collection"]["external_reference"]).first()
            if mov == None:
                mov = models.ChargeMovement.objects.get(number=id)


            status = payment_info["response"]["collection"]["status"]
            if status == 'approved':

                if mov.state == models.AbstractMovement.STATE.CONFIRMED:
                    return HttpResponse("<h1>200 OK</h1>", status=200)


                with transaction.atomic():
                    mov.confirm_date = timezone.now()
                    mov.state = models.AbstractMovement.STATE.CONFIRMED
                    mov.save(update_fields=('confirm_date', 'state'))
                    mov.user.saldo += Decimal(round(mov.amount, 2))
                    mov.user.save(update_fields=('saldo',))

                mov.user.push_notification(models.USER_SETTINGS.PUSH_CHARGE_ACCREDITED, u'Carga de saldo',
                                           u'Carga de saldo acreditada: ${}'.format(mov.amount))

                context = dict(user=mov.user, movement=mov)
                mov.user.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_ACCREDITED,
                                            'emails/charge_confirmed_email', context)

            elif status in ['cancelled', 'rejected']:
                mov.confirm_date = timezone.now()
                mov.state = models.AbstractMovement.STATE.CANCELED
                mov.save(update_fields=('confirm_date', 'state'))

                mov.user.push_notification(models.USER_SETTINGS.PUSH_CHARGE_REJECTED,
                                          u'Carga de saldo rechazada',
                                          u'Su carga de saldo ha sido rechazada por mercadopago.')

                status_detail = payment_info["response"]["collection"].get("status_detail", None)
                context = dict(user=mov.user, movement=mov, status_detail=status_detail)
                mov.user.email_notification(request, models.USER_SETTINGS.MAIL_CHARGE_REJECTED,
                                           'emails/charge_rejected_email', context)
            elif status in ['pending']:

                mov.state = models.AbstractMovement.STATE.PENDING
                mov.save()


        except AttributeError as err:
            logger.error('Payment info: {}'.format(err.message))
        except models.ChargeMovement.DoesNotExist:
            logger.error('Payment info: ChargeMovement with number={} does not exists.'.format(id))

    return HttpResponse("<h1>200 OK</h1>", status=201)


@login_required()
def get_preferences_charge(request):

    profile = models.UserProfile.objects.get(user=request.user)
    external_reference =  ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(16)])

    m = models.ChargeMovement.objects.create(
                    code='CC', user=profile, amount=float(request.GET['import']),
                    method=0, type="Mercado Pago",
                    number=external_reference,
                    external_url="", state=models.ChargeMovement.STATE.TEMP
    )
    m.save()

    notification_url = settings.URL_DOMAIN + "mp_notification/"
    return_url = settings.URL_DOMAIN + "user_profile_saldo/"
    #notification_url = host + reverse('bet:mp_notification')


    preference = {
        "items": [
            {
                "title": "Carga de credito",
                "quantity": 1,

                "currency_id": "ARS",  # Available currencies at: https://api.mercadopago.com/currencies
                "unit_price": float(request.GET['import'])
            }
        ], "external_reference": external_reference,
            'notification_url': notification_url,
            "back_urls" :{
                "success": return_url,
                "pending": return_url,
                "failure": return_url,
            },
    }
    print preference
    mp = mercadopago.MP(settings.MP_CLIENT_ID, settings.MP_SECRET_KEY)

    preferenceResult = mp.create_preference(preference)
    logger.debug('Preference response: {}'.format(preferenceResult["response"]))
    url = preferenceResult["response"]["init_point"]
    print url
    response = {"url": url}
    return HttpResponse(json.dumps(response), content_type="application/json")


def mp_sandbox(request):

    preference = {
        "items": [
            {
                "title": "Multicolor kite",
                "quantity": 1,
                "currency_id": "ARS",  # Available currencies at: https://api.mercadopago.com/currencies
                "unit_price": 50.0
            }
        ]
    }
    mp = mercadopago.MP(settings.MP_CLIENT_ID, settings.MP_SECRET_KEY)
    #mp = mercadopago.MP('TEST-7191890181668709-011815-e963396baa26fc59386ce88a299b0c3c__LB_LA__-203650259')
    # mp.sandbox_mode(True)

    preferenceResult = mp.create_preference(preference)
    logger.debug('Preference response: {}'.format(preferenceResult["response"]))
    url = preferenceResult["response"]["sandbox_init_point"]

    output = """
    <!doctype html>
    <html>
    	<head>
    		<title>Pay</title>
    	</head>
    	<body>
    		<a href="{url}">Pay</a>
    	</body>
    </html>
    """.format(url=url)

    return HttpResponse(output)


def truncate(number, digits):
    stepper = pow(10.0, digits)
    return math.trunc(stepper * number) / stepper



def get_winner_virtual_coupon(request, idcoupon):

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
    chch['name'] = ""

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
    renderize = render_to_string('tickets/telebingo_coupon.html', chch)

    return renderize


EXTRACT_OPTIONS = {
    'page-width': '10.5cm',
    'page-height': '20.8cm',
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
    return options

    options.update(update.get(code, dict()))
    return options

def fill_none(data):

    if data == None:
        return ""
    else:
        return unicode(data).encode('utf-8').strip()


