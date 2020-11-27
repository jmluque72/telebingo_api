# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import hashlib
import logging
import math
import mimetypes
import os
from operator import itemgetter

import pdfkit
import random
import tempfile
import uuid
from datetime import date
from decimal import Decimal
from collections import defaultdict
from pdfkit.configuration import Configuration

from django.contrib.auth.models import User
from django.core import files, mail
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import connection, models, transaction, IntegrityError
from django.db.models import Sum, F, Q
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import timezone

from django.conf import settings
from bet.modelfields import RoundedDecimalField
from bet.storage import OverwriteStorage
from bet.utils import enum, push_notification, send_email, get_current_site, split_rows, parse_header

logger = logging.getLogger('agencia24_default')


LOTERIA_MIN_COUPON = 1000
LOTERIA_MAX_COUPON = 50999
QUINIELA_MIN_IMPORT = 2.0
QUINIELA_MIN_TICKET = 6

DAYS = enum(
        MONDAY=0,
        THUESDAY=1,
        WEDNESDAY=2,
        THURSDAY=3,
        FRIDAY=4,
        SATURDAY=5,
        SUNDAY=6
    )
DAYS_CHOICES = (
    (DAYS.MONDAY, 'Lunes'),
    (DAYS.THUESDAY, 'Martes'),
    (DAYS.WEDNESDAY, 'Miercoles'),
    (DAYS.THURSDAY, 'Jueves'),
    (DAYS.FRIDAY, 'Viernes'),
    (DAYS.SATURDAY, 'Sabado'),
    (DAYS.SUNDAY, 'Domingo')
)

QUINIELA_TYPES = enum(
    PRIMERA=0,
    MATUTINA=1,
    VESPERTINA=2,
    NOCTURNA=3,
    TURISTA=4
)
TYPE_CHOICES = (
    (QUINIELA_TYPES.PRIMERA, 'Primera'),
    (QUINIELA_TYPES.MATUTINA, 'Matutina'),
    (QUINIELA_TYPES.VESPERTINA, 'Vespertina'),
    (QUINIELA_TYPES.NOCTURNA, 'Nocturna'),
    (QUINIELA_TYPES.TURISTA, 'Turista'),
)

QUINIELA_TIMES = tuple(
    [item.lower() for (index,item) in TYPE_CHOICES]
)

USER_SETTINGS = enum(
    MAIL_EXTRACT_SENT=0,
    MAIL_TICKET_SENT=1,
    PUSH_TICKET_SENT=2,
    MAIL_PLAYED_BET=3,
    MAIL_WINNER_NOTIFICATION=4,
    PUSH_WINNER_NOTIFICATION=5,
    MAIL_WITHDRAWAL_APPROVED=6,
    PUSH_WITHDRAWAL_APPROVED=7,
    MAIL_WITHDRAWAL_REQUESTED=8,
    MAIL_CHARGE_ACCREDITED=9,
    PUSH_CHARGE_ACCREDITED=10,
    MAIL_CHARGE_REJECTED=11,
    PUSH_CHARGE_REJECTED=12,
    MAIL_REQUEST_PRIZE_REJECTED=13,
    PUSH_REQUEST_PRIZE_REJECTED=14,
    MAIL_ACCOUNT_ACTIVATION=15,
    STAY_LOGGED_IN=16
)
NOTIF_INTENTS = {
    USER_SETTINGS.PUSH_TICKET_SENT: 'liricus.agencia24.ticket_sent',
    USER_SETTINGS.PUSH_WINNER_NOTIFICATION: 'liricus.agencia24.winner_notification',
    USER_SETTINGS.PUSH_WITHDRAWAL_APPROVED: 'liricus.agencia24.withdrawal_approved',
    USER_SETTINGS.PUSH_CHARGE_ACCREDITED: 'liricus.agencia24.charge_accredited',
    USER_SETTINGS.PUSH_CHARGE_REJECTED: 'liricus.agencia24.charge_rejected',
    USER_SETTINGS.PUSH_REQUEST_PRIZE_REJECTED: 'liricus.agencia24.request_prize_rejected',
}


def picture_prize(obj, fname):
    ext = fname.rsplit('.', 1)[-1]
    picture_name = 'prize_{}_{}'.format(settings.APP_CODE,obj.id)
    picture_name = picture_name + '.' + ext
    return u'/'.join(['pictures', picture_name])

def picture_coupon(obj, fname):
    fn, ext = os.path.splitext(fname)
    coupon_name = 'coupon_{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return u'/'.join(['pictures', coupon_name])

def picture_coupon_th(obj, fname):
    fn, ext = os.path.splitext(fname)
    coupon_name = 'coupon_th_{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return u'/'.join(['pictures', coupon_name])

def picture_ticket(obj, fname):
    fn, ext = os.path.splitext(fname)
    ticket_name = 'ticket_{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return os.path.join('pictures', 'tickets', ticket_name)

def save_extract_file(obj, fname):
    fn, ext = os.path.splitext(fname)
    name = 'extract_{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return os.path.join('pictures', 'extracts', name)

def save_result_file(obj, fname):
    fn, ext = os.path.splitext(fname)
    name = 'result_{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return os.path.join('pictures', 'results', name)

def save_winner_file(obj, fname):
    fn, ext = os.path.splitext(fname)
    name = 'winner_{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return os.path.join('pictures', 'winners', name)

def save_orig_extract_file(obj, fname):
    fn, ext = os.path.splitext(fname)
    name = 'extract_{}_original{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return os.path.join('pictures', 'extracts', name)

def save_extract_group_file(obj, fname):
    fn, ext = os.path.splitext(fname)
    name = 'extract_group{}{}_{}'.format(settings.APP_CODE, obj.id, ext)
    return os.path.join('pictures', 'extracts', name)

def game_logo_picture(obj, fname):
    fn, ext = os.path.splitext(fname)
    name = 'game_{}{}_{}'.format(settings.APP_CODE, obj.code, ext)
    return os.path.join('pictures', name)


def has_relation(object, attr):
    return hasattr(object, 'attr') and getattr(object, attr)


class AbstractMovement(models.Model):

    PAYMENT_METHODS = enum(
        MERCADOPAGO=0,
        TRANSFER=1,
        TCARGO=2,
    )

    PAYMENT_CHOICES = (
        (PAYMENT_METHODS.MERCADOPAGO, 'MercadoPago'),
        (PAYMENT_METHODS.TRANSFER, 'Transferencia Bancaria'),
        (PAYMENT_METHODS.TCARGO, 'TCargo'),
    )

    STATE = enum(
        PENDING=0,
        CONFIRMED=1,
        CANCELED=2,
        TEMP=99,

    )
    STATE_CHOICES = (
        (STATE.PENDING, 'Pendiente'),
        (STATE.CONFIRMED, 'Acreditado'),
        (STATE.CANCELED, 'Cancelado'),
        (STATE.TEMP, 'Temporario'),
    )

    CODE_CHOICES = (
        ('SR', 'Solicitud de retiro'),
        ('PA', 'Pago de apuesta'),
        ('CC', 'Carga de credito'),
        ('PR', 'Premio de apuesta'),
    )

    code = models.CharField(max_length=2, verbose_name='Tipo', choices=CODE_CHOICES)
    user = models.ForeignKey('UserProfile', related_name='movement_set')
    date = models.DateTimeField('Fecha', auto_now_add=True)
    amount = RoundedDecimalField(max_digits=12, decimal_places=2, default=0.0)

    state = models.PositiveIntegerField('Estado', choices=STATE_CHOICES, default=0)
    confirm_date = models.DateTimeField('Fecha de acreditación', blank=True, null=True)

    class Meta:
        get_latest_by = 'confirm_date'

    def clean(self):
        super(AbstractMovement, self).clean()

        if self.confirm_date and self.confirm_date < self.date:
            raise ValidationError({
                NON_FIELD_ERRORS: [
                    'La fecha de confirmación de la transacción '
                    'no puede ser anterior a la fecha de la transacción.'
                ],
            })

    @staticmethod
    def movs_with_saldo(profile_pk, items=None):
        profile = UserProfile.objects.get(pk=profile_pk)
        result_list = []
        saldo = profile.saldo

        movs = AbstractMovement.objects.filter(~Q(amount = 0),
                                               user=profile).exclude(state__in=[AbstractMovement.STATE.TEMP]).order_by('state','-confirm_date','-date')
        if items is not None:
            movs = list(movs)[:items]
        for model in movs:
            model.saldo = saldo
            if model.state == AbstractMovement.STATE.CONFIRMED:
                saldo -= model.amount

            result_list.append(model)
        return result_list

    def __unicode__(self):
        return '{} ${} ({}) - {})'.format(self.get_code_display(), self.amount,
                                         self.user.user.get_full_name(),self.get_state_display())

    @property
    def parent(self):
        if self.code == 'SR':
            return self.withdrawalmovement
        if self.code == 'PA':
            return self.betmovement
        if self.code == 'CC':
            return self.chargemovement
        if self.code == 'PR':
            return self.prizemovement


# Costo de apuesta
class BetMovement(AbstractMovement):

    bet = models.OneToOneField('Bet', related_name='movement')

    @property
    def game(self):
        return self.bet.game

# Premio de juego
class PrizeMovement(AbstractMovement):

    winner = models.OneToOneField('BaseWinner', related_name='movement')


# Cargar credito
class ChargeMovement(AbstractMovement):

    method = models.PositiveIntegerField('Medio de pago',
                                         choices=AbstractMovement.PAYMENT_CHOICES)
    number = models.CharField('Número de transacción', max_length=40, db_index=True)
    type = models.CharField('Tipo', max_length=20)

    initial = RoundedDecimalField(max_digits=12, decimal_places=2, default=0.0)
    external_url = models.URLField(blank=True, null=True)
    tcargo = models.ForeignKey('TCargo', null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.initial = self.amount
        super(ChargeMovement, self).save(*args, **kwargs)


class TCargo(models.Model):

    trx = models.CharField(max_length=20, verbose_name='IDUnicoTrx', unique=True) #IDUnicoTrx
    wholesaler = models.IntegerField('idMayorista', null=True) #idMayorista
    pos = models.IntegerField('idPtoVenta', null=True) #idPtoVenta
    dni = models.IntegerField('DNIbeneficiario') #DNIbeneficiario
    amount = models.PositiveIntegerField('Importe') #importe

    def __unicode__(self):
        return '{} {} {} {} {}'.format(self.trx, self.wholesaler, self.pos,
                                       self.dni, self.amount)


class TCargoDetail(models.Model):

    successful = models.BooleanField()
    message = models.CharField(max_length=255)
    trx = models.CharField(max_length=20, verbose_name='IDUnicoTrx', unique=True) #IDUnicoTrx generado por TCargo
    id_trx = models.CharField(max_length=20, verbose_name='IDTrx', null=True) #ITrx generado por Agencia24
    instance = models.ForeignKey('TCargo', null=True, on_delete=models.SET_NULL)

    def __unicode__(self):
        return u'{} {} {}'.format(self.trx, self.successful, self.message)


# Retiro, Cargar credito
class WithdrawalMovement(AbstractMovement):

    method = models.PositiveIntegerField('Medio de pago',
                                         choices=AbstractMovement.PAYMENT_CHOICES)

    cbu = models.CharField(
        max_length=22, verbose_name='CBU'
        #,
        #validators=[
        #    RegexValidator('^[0-9]{22}$', message='Número de CBU no válido.'),
        #]
    )

    def validate_unique(self, exclude=None):
        super(WithdrawalMovement, self).validate_unique(exclude)

        # Avoid multiple withdrawals
        if self.code == 'SR' and self.state==AbstractMovement.STATE.PENDING:
            if self.user.movement_set.filter(code='SR', state=0).exclude(pk=self.pk).exists():
                raise ValidationError({
                        NON_FIELD_ERRORS: [
                            u'Ya existe una solicitud de retiro pendiente'
                            u' de aprobación.'
                        ],
                })


class Agency(models.Model):

    name = models.CharField('Nombre', max_length=255)
    user = models.OneToOneField(User, verbose_name='Agenciero', related_name='agency')
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de alta')
    is_active = models.BooleanField('Activa', default=True)
    number = models.CharField(max_length=80, verbose_name=u'Número')
    address = models.CharField(max_length=80, verbose_name=u'Dirección')
    # street_number
    city = models.CharField(max_length=80, verbose_name=u'Ciudad')
    neighborhood = models.CharField(max_length=80, verbose_name=u'Barrio')
    # phone_number
    province = models.ForeignKey('Province', verbose_name='Provincia', related_name='agency_set')
    balance = RoundedDecimalField(max_digits=12, decimal_places=2, blank=True, default=0)

    class Meta:
        verbose_name = 'Agencia'

    def calc_balance(self):
        return self.movement_set.filter(
            state=AgenMovement.STATE.PENDING
        ).aggregate(total=Sum(F('amount'))).get('total') or 0

    def __unicode__(self):
        return u'{}'.format(self.name)


class AgencyDevices(models.Model):

    agency = models.ForeignKey('Agency', related_name='device_set')
    deviceid = models.CharField(max_length=255, verbose_name='Tablet ID', unique=True)
    devicegsmid = models.CharField(max_length=255, verbose_name='Device GSM', unique=True)

    def __unicode__(self):
        return u'{}: id {} gsm {}'.format(self.agency.name, self.deviceid, self.devicegsmid[-20:])


class AgenMovement(models.Model):

    STATE = enum(
        PENDING=0,
        CONFIRMED=1
    )
    STATE_CHOICES = (
        (STATE.PENDING, 'Pendiente'),
        (STATE.CONFIRMED, 'Acreditado'),
    )

    CODE = enum(
        BETCOMMISSION=0,
        PRIZECOMMISSION=1,
        COLLECTION=2,
        PAYMENT=3
    )
    CODE_CHOICES = (
        (CODE.BETCOMMISSION, 'Apuesta'),
        (CODE.PRIZECOMMISSION, 'Premio apuesta'),
        (CODE.COLLECTION, 'Cobro'),
        (CODE.PAYMENT, u'Comisión de premio')
    )

    agency = models.ForeignKey('Agency', related_name='movement_set')
    date_mov = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    amount = RoundedDecimalField(max_digits=12, decimal_places=2)
    state = models.PositiveSmallIntegerField('Estado', choices=STATE_CHOICES)
    code = models.PositiveSmallIntegerField(choices=CODE_CHOICES)
    payment = models.ForeignKey('PaymentCommissionMov', related_name='movement_set', null=True)

    @property
    def reason(self):
        if hasattr(self, 'betcommissionmov'):
            return 'Apuesta ' + self.betcommissionmov.bet.game.name
        elif hasattr(self, 'winnercommissionmov'):
            return 'Premio ' + self.winnercommissionmov.winner.game.name
        else:
            if self.amount > 0:
                return u'Pago de comisión'
            else:
                return u'Cobro de comisión'

    @property
    def parent(self):
        if self.code == AgenMovement.CODE.BETCOMMISSION:
            return self.betcommissionmov

        if self.code == AgenMovement.CODE.PRIZECOMMISSION:
            return self.winnercommissionmov

        if hasattr(self, 'paymentcommissionmov'):
            return self.paymentcommissionmov

        return self

    @property
    def real_amount(self):
        return self.amount


class BetCommissionMov(AgenMovement): # BetCommission

    bet = models.OneToOneField('Bet', related_name='commission')
    draw = models.ForeignKey('BaseDraw')
    # draw se usa solo para poder obtener facilmente las comisiones de un sorteo de cierto dia
    # por lo tanto en el caso de la quiniela puede ser cualquiera de los draws de DetailQuiniela

    def save(self, *args, **kwargs):
        if self.code is None:
            self.code = AgenMovement.CODE.BETCOMMISSION

        super(BetCommissionMov, self).save(*args, **kwargs)

    @property
    def real_amount(self):
        return self.bet.importq


class PaymentCommissionMov(AgenMovement):

    date_from = models.DateField()
    date_to = models.DateField()

    @property
    def game(self):
        return self.movement_set.first().parent.draw.game


class WinnerCommissionMov(AgenMovement): # NonprintedWinnerCommission

    # Para los juegos en donde el sistema determina los ganadores
    winner = models.ForeignKey('BaseWinner', related_name='commission_set')

    def save(self, *args, **kwargs):
        if self.code is None:
            self.code = AgenMovement.CODE.PRIZECOMMISSION

        super(WinnerCommissionMov, self).save(*args, **kwargs)

    @property
    def draw(self):
        return self.winner.parent.draw

    @property
    def real_amount(self):
        return self.winner.parent.get_prize()


class Quiniela(models.Model):

    name = models.CharField(max_length=35, verbose_name='Nombre', unique=True)
    code = models.PositiveSmallIntegerField('Codigo Loteria',
                                            blank=True, null=True)
    #premios =

    @staticmethod
    def items_names():
        return [name for (name,) in Quiniela.objects.all().values_list('name')]

    def __unicode__(self):
        return u'{}'.format(self.name)


class Province(models.Model):

    PROVINCE_CHOICES = (
        (0 , u'Buenos Aires'),
        (1 , u'Catamarca'),
        (2 , u'Chaco'),
        (3 , u'Chubut'),
        (4 , u'Córdoba'),
        (5 , u'Corrientes'),
        (6 , u'Entre Ríos'),
        (7 , u'Formosa'),
        (8 , u'Jujuy'),
        (9 , u'La Pampa'),
        (10 , u'La Rioja'),
        (11 , u'Mendoza'),
        (12 , u'Misiones'),
        (13 , u'Neuquén'),
        (14 , u'Río Negro'),
        (15 , u'Salta'),
        (16 , u'San Juan'),
        (17 , u'San Luis'),
        (18 , u'Santa Cruz'),
        (19 , u'Santa Fe'),
        (20 , u'Santiago del Estero'),
        (21 , u'Tierra del Fuego'),
        (22 , u'Tucumán'),
    )

    code_name = models.PositiveSmallIntegerField('Nombre', choices=PROVINCE_CHOICES)
    quinielas = models.ManyToManyField('Quiniela', blank=True)

    quiniela_prizes = models.CommaSeparatedIntegerField(max_length=25, blank=True)
    #[premio 1 cifra, premio 2 cifras, premio 3 cifras, premio 4 cifras}

    @property
    def name(self):
        return self.get_code_name_display()

    @property
    def prizes(self):
        if len(self.quiniela_prizes) == 0:
            logger.error('quiniela_prizes incorrect. {}'.format(self.get_code_name_display()))
            raise

        result = {i+1: int(x) for i,x in enumerate(self.quiniela_prizes.split(','))}
        if len(result) < 4:
            logger.error('quiniela_prizes incorrect. {}'.format(self.get_code_name_display()))
        return result

    def __unicode__(self):
        return u'{}'.format(self.name)


class LotteryTime(models.Model):

    quiniela = models.ForeignKey('Quiniela', related_name='time_set')
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    # week_day

    draw_time = models.TimeField('Hora sorteo')
    draw_limit = models.TimeField('Cierre usuario')
    draw_limit_agency = models.TimeField('Cierre agencia')

    class Meta:
        unique_together = (('quiniela', 'type'),)

    def __unicode__(self):
        return u'{} {} {}'.format(self.quiniela, self.get_type_display(), self.draw_time)


class DrawTime(models.Model):

    game = models.ForeignKey('Game')
    week_day = models.PositiveSmallIntegerField(choices=DAYS_CHOICES)

    draw_time = models.TimeField('Hora sorteo')
    agency_diff = models.PositiveIntegerField('Diferencia agencia (min)')
    user_diff = models.PositiveIntegerField('Diferencia usuario (min)')

    class Meta:
        unique_together = (('game', 'week_day'),)

    def __unicode__(self):
        return u'{} {} {}'.format(self.game, self.get_week_day_display(), self.draw_time)


class UserProfile(models.Model):

    DEVICE_OS = enum(
        OTHER=0,
        ANDROID=1,
        IOS=2,
    )

    OS_CHOICES = (
        (DEVICE_OS.OTHER, 'Otro'),
        (DEVICE_OS.ANDROID, 'Android'),
        (DEVICE_OS.IOS, 'iOS'),
    )

    user = models.OneToOneField(User, related_name='profile')
    saldo = RoundedDecimalField('Saldo', max_digits=12, decimal_places=2, default=0.0, blank=True)
    playtoday = RoundedDecimalField('Jugaste hoy', max_digits=12, decimal_places=2, default=0.0, blank=True)
    agency = models.ForeignKey('Agency', verbose_name='Agencia', related_name='profile_set') #Agencia favorita
    dni = models.PositiveIntegerField('DNI', unique=True)
    date_of_birth = models.DateField('Fecha nacimiento', blank=True, null=True)

    province = models.ForeignKey('Province', verbose_name='Provincia', related_name='profile_set')
    devicegsmid = models.CharField(max_length=255, verbose_name='Device GCM', null=True, blank=True)
    device_os = models.PositiveSmallIntegerField(choices=OS_CHOICES)

    @property
    def last_movement(self):
        return self.movement_set.filter(state=AbstractMovement.STATE.CONFIRMED).latest()


    def __unicode__(self):
        return u'{}'.format(self.user.email)

    def update_setting(self, setting, value):
        if not isinstance(setting, Setting):
            try:
                setting = Setting.objects.get(code=setting)
            except Setting.DoesNotExist:
                logger.error('Setting does not exist: {}'.format(setting))
                return

        try:
            user_setting = self.setting_set.get(setting=setting)
            user_setting.value = value
            user_setting.save()
        except UserSetting.DoesNotExist:
            UserSetting.objects.create(
                profile=self, setting=setting, value=value
            )

    def get_setting(self, setting):
        if not isinstance(setting, Setting):
            try:
                setting = Setting.objects.get(code=setting)
            except Setting.DoesNotExist:
                logger.error('Setting does not exist: {}'.format(setting))
                return None

        try:
            return self.setting_set.get(setting=setting).value
        except UserSetting.DoesNotExist:
            UserSetting.objects.create(
                profile=self, setting=setting, value=setting.default
            )
            return setting.default

    def push_notification(self, _type, title, message, data=None, notif=None):
        try:
            enabled = self.setting_set.get(setting__code=_type).value
        except UserSetting.DoesNotExist:
            enabled = True

        if self.devicegsmid is None or not self.user.is_active or not enabled:
            return

        if NOTIF_INTENTS.has_key(_type):
            notif = notif or {}
            notif.update({'click_action': NOTIF_INTENTS[_type]})

        push_notification(self.device_os, self.devicegsmid, _type, title, message, data, notif)

    def email_notification(self, request, _type, template_prefix, context=None,
                           attachments=None, urls=None, send=True):


        try:
            enabled = self.setting_set.get(setting__code=_type).value
        except UserSetting.DoesNotExist:
            try:
                enabled = Setting.objects.get(code=_type).default or True
            except Setting.DoesNotExist:
                enabled = True

        if not enabled:
            return

        if self.user.is_active or _type == USER_SETTINGS.MAIL_ACCOUNT_ACTIVATION:
            recipients = [self.user.email]
            return send_email(request, template_prefix, recipients, context, attachments, urls, send=send)


USER_SETTINGS_CHOICES = (
    (USER_SETTINGS.MAIL_EXTRACT_SENT, u'MAIL extracto enviado'),
    (USER_SETTINGS.MAIL_TICKET_SENT, u'MAIL ticket enviado'),
    (USER_SETTINGS.PUSH_TICKET_SENT, u'PUSH ticket enviado'),
    (USER_SETTINGS.MAIL_PLAYED_BET, u'MAIL apuesta jugada'),
    (USER_SETTINGS.MAIL_WINNER_NOTIFICATION, u'MAIL notificacion ganador'),
    (USER_SETTINGS.PUSH_WINNER_NOTIFICATION, u'PUSH notificacion ganador'),
    (USER_SETTINGS.MAIL_WITHDRAWAL_APPROVED, u'MAIL retiro aprobado'),
    (USER_SETTINGS.PUSH_WITHDRAWAL_APPROVED, u'PUSH retiro aprobado'),
    (USER_SETTINGS.MAIL_WITHDRAWAL_REQUESTED, u'MAIL solicitud de retiro'),
    (USER_SETTINGS.MAIL_CHARGE_ACCREDITED, u'MAIL saldo acreditado'),
    (USER_SETTINGS.PUSH_CHARGE_ACCREDITED, u'PUSH saldo acreditado'),
    (USER_SETTINGS.MAIL_CHARGE_REJECTED, u'MAIL saldo rechazado'),
    (USER_SETTINGS.PUSH_CHARGE_REJECTED, u'PUSH saldo rechazado'),
    (USER_SETTINGS.MAIL_REQUEST_PRIZE_REJECTED, u'MAIL solicitud premio rechazada'),
    (USER_SETTINGS.PUSH_REQUEST_PRIZE_REJECTED, u'PUSH solicitud premio rechazada'),
    (USER_SETTINGS.MAIL_ACCOUNT_ACTIVATION, u'MAIL activacion de cuenta'),
    (USER_SETTINGS.STAY_LOGGED_IN, u'Mantener sesión iniciada'),
)



class Messages(models.Model):


    PROFILE_TYPE_ENUM = enum(
        ALL=0,
        APOSTARON_ULTIMO_QUINI=1

    )

    TYPE_MESSAGES = (
        (PROFILE_TYPE_ENUM.ALL,      'ALL'),
        (PROFILE_TYPE_ENUM.APOSTARON_ULTIMO_QUINI,      'APOSTARON_ULTIMO_QUINI'),

    )

    text = models.CharField(max_length=255, null=True, blank=True)
    users = models.CharField(max_length=2048, null=True, blank=True)
    type = models.IntegerField(choices=TYPE_MESSAGES, default=2)
    date_entered = models.DateTimeField(default=timezone.now(), blank=True)
    process = models.IntegerField(default=0, verbose_name="Procesados")
    send_sucess = models.IntegerField(default=0, verbose_name="Succed")
    startprocess = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)

    def __unicode__(self):
        return "{}".format(self.text)


class MessagesSend(models.Model):

    message = models.ForeignKey(Messages, related_name="message_send_message")
    userprofile = models.ForeignKey(UserProfile, related_name="message_send_userprofile")
    send = models.BooleanField(default=False)


    def __unicode__(self):
        return "{} {}".format(self.message.text, self.userprofile.user.first_name)



class Setting(models.Model):

    code = models.SmallIntegerField(choices=USER_SETTINGS_CHOICES, unique=True)
    default = models.BooleanField(default=True, blank=True)

    def __unicode__(self):
        return u'{}'.format(self.get_code_display())


class UserSetting(models.Model):

    profile = models.ForeignKey('UserProfile', related_name='setting_set')
    setting = models.ForeignKey('Setting', related_name='user_set')
    value = models.BooleanField()

    class Meta:
        unique_together = (('profile', 'setting'),)

    def __unicode__(self):
        return u'{} {} {}'.format(self.profile.user.get_full_name(),
                                  self.setting.get_code_display(), self.value)


class Game(models.Model):
    CODE = enum(
        QUINIELA='quiniela',
        QUINI6='quini6',  # 1.333.33
        LOTO='loto',  # 1.000
        LOTO5='loto5',
        BRINCO='brinco',  # 1.333.33
        LOTERIA='loteria',
        TELEBINGO='telebingocordobes',
        TELEBINGOCORRENTINO='telebingocorrentino',
        TELEBINGONEUQUINO='telebingoneuquino',
        TELEKINO='telekino',
        TOTOBINGO='totobingo'  # 1.334
    )

    TYPE = enum(
        PREPRINTED=0,
        NONPRINTED=1
    )
    TYPE_CHOICES = (
        (TYPE.PREPRINTED, 'Preimpreso'),
        (TYPE.NONPRINTED, 'No impreso'),
    )

    code = models.CharField(max_length=40, verbose_name='Código', null=False, unique=True)
    name = models.CharField('Nombre', max_length=255)
    type = models.PositiveIntegerField('Tipo', choices=TYPE_CHOICES)
    order = models.PositiveIntegerField('Orden', default=0)
    logo = models.ImageField('Logo', upload_to=game_logo_picture, null=True, blank=True)
    provinces = models.ManyToManyField('Province', blank=True)
    is_active = models.BooleanField(default=True) # Ocultar juegos inactivos

    @property
    def article(self):
        return ['el', 'la'][self.name.endswith('a')]

    def __unicode__(self):
        return u'{}'.format(self.name)


class BetCommission(models.Model):

    game = models.OneToOneField('Game', unique=True) # TODO! Cambiar a ForeignKey cuando se agregue la agencia
    #agency = models.ForeignKey('Agency')
    value = RoundedDecimalField(max_digits=5, decimal_places=2, verbose_name='valor',
        default=12.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])

    #class Meta:
    #    unique_together = (('game', 'agency'))

    def __unicode__(self):
        return u'{} - {}%'.format(self.game, self.value)


#===============================================================================
# DRAW
#===============================================================================

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

class BaseDraw(models.Model):

    class Meta:
        get_latest_by = 'date_draw'

    STATE = enum(
        ACTIVE=0,
        DRAFT=1,
        LOADED=2, # Cuando se cargaron los resultados
        EXTRACT=3, # Cuando se envio el extracto (ya no se puede modificar)
    )
    STATE_CHOICES = (
        (STATE.DRAFT, 'Borrador'),
        (STATE.ACTIVE, 'Publicado'),
        (STATE.LOADED, 'Cargado'),
        (STATE.EXTRACT, 'Extracto enviado'),
    )

    PROMOTION = enum(
        NINGUNO=99,
        DOSXUNO=0,
    )

    PROMOTION_CHOICES = (
        (PROMOTION.NINGUNO, 'Ninguna'),
        (PROMOTION.DOSXUNO, '2 x 1'),
    )

    game = models.ForeignKey('Game', related_name='draw_set')
    date_draw = models.DateTimeField('Fecha sorteo')
    date_limit = models.DateTimeField(u'Hora límite usuario')
    date_limit_agency = models.DateTimeField(u'Hora límite agencia')
    number = models.CharField(max_length=20, verbose_name=u'Número sorteo', null=True, blank=True)
    state = models.PositiveIntegerField('Estado', choices=STATE_CHOICES, default=0)
    prize_text = models.CharField('Premio Texto', default='', max_length=255)

    extract_file = models.FileField(upload_to=save_extract_file, storage=OverwriteStorage(),
                                    blank=True, null=True, verbose_name='Extracto')
    orig_extract = models.FileField(upload_to=save_orig_extract_file, storage=OverwriteStorage(),
                                    blank=True, null=True, verbose_name='Extracto original')

    result_to_provider = models.FileField(upload_to=save_result_file, storage=OverwriteStorage(),
                                    blank=True, null=True, verbose_name='Result to provider')
    winner_to_provider = models.FileField(upload_to=save_winner_file, storage=OverwriteStorage(),
                                          blank=True, null=True, verbose_name='Winner to provider')
    #send_result_to_provider = models.BooleanField('Resultado enviado', blank=True, default=False)
    promotion_coupons = models.PositiveIntegerField('Promocion', choices=PROMOTION_CHOICES, default=99)


    def clean(self):
        super(BaseDraw, self).clean()

        # Don't allow confirm dates older than now.
        if self.date_limit and self.date_limit < timezone.now():
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'La fecha del límite del usuario no puede ser anterior a la fecha actual.'
                    ],
            })

        # Don't allow dates older than now.
        if self.date_draw and self.date_draw < timezone.now():
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'La fecha del sorteo no puede ser anterior a la fecha actual.'
                    ],
            })

        # Don't allow date_limit older than date_draw
        if self.date_draw and self.date_limit and \
                        self.date_draw < self.date_limit:
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'La fecha límite del usuario debe ser anterior'
                        ' a la fecha del sorteo.'
                    ],
            })

        # Don't allow date_limit older than date_limit_agency
        if self.date_limit_agency and self.date_limit and \
                        self.date_limit > self.date_limit_agency:
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'La fecha límite del usuario debe ser anterior'
                        u' a la fecha límite de la agencia.'
                    ],
            })

        if self.state > BaseDraw.STATE.DRAFT and not self.is_old:
            raise ValidationError({
                NON_FIELD_ERRORS: [
                    u'Solo los sorteos antiguos pueden tener estado {}.'.format(self.get_state_display())
                ],
            })

    @property
    def is_old(self):
        return timezone.now() > self.date_draw

    @property
    def is_loaded(self):
        return self.state >= BaseDraw.STATE.LOADED

    @property
    def extract_sent(self):
        return self.state >= BaseDraw.STATE.EXTRACT

    @property
    def parent(self):
        if hasattr(self, 'draw'):
            if hasattr(self.draw, 'drawpreprinted'):
                return self.draw.drawpreprinted
            return self.draw
        if hasattr(self, 'drawquiniela'):
            return self.drawquiniela

    def is_current(self):
        return self.parent.is_current()

    @property
    def has_results(self):
        return self.extract_sent

    def __unicode__(self):
        return u'{} ({}) {}'.format(self.game, self.pk, self.date_draw.date())

    @property
    def next_draw(self):
        try:
            self.get_next_by_date_limit().parent
        except BaseDraw.DoesNotExist:
            return None

    def create_extract(self, request, context=None, pdf=True):
        ctx_dict = {}
        if request is not None:
            ctx_dict = RequestContext(request, ctx_dict)

        site = get_current_site(request)
        protocol = 'https' if request.is_secure() else 'http'
        ctx_dict.update({
            'draw': self.parent,
            'game': self.game,
            'base_url': '{}://{}'.format(protocol, site.domain)
        })
        if context is not None:
            ctx_dict.update(context)

        html = ""
        if self.game.code == 'loto':
            html = render_to_string('extract/loto.html'.format(self.game.code), ctx_dict)
        if self.game.code == 'quini6':
            html = render_to_string('extract/quini6.html'.format(self.game.code), ctx_dict)
        if self.game.code == 'brinco':
            html = render_to_string('extract/brinco.html'.format(self.game.code), ctx_dict)

        if self.game.code.startswith('telebingo'):
            html = render_to_string('extract/telebingocordobes.html'.format(self.game.code), ctx_dict)

        if not pdf:
            return html # TODO! remove return and pdf attribute

        STATIC_ROOT = os.path.join(settings.PROJECT_ROOT, 'site_media', 'static')
        css = list([os.path.join(STATIC_ROOT, 'bootstrap', 'css', 'bootstrap.css')])
        css.append(os.path.join(STATIC_ROOT, 'extract.css'))

        # Generar pdf en un archivo temporario
        output = tempfile.NamedTemporaryFile(suffix='.pdf')
        pdfkit.from_string(html, output.name, options=get_extract_options(self.game.code), css=css,
                           configuration=Configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))

        self.extract_file.save('file_name.pdf', files.File(output))

    def send_game_extract(self, request):
        disabled_users = UserSetting.objects.filter(setting__code=USER_SETTINGS.MAIL_EXTRACT_SENT,
                                                    value=False).values_list('profile', flat=True)

        if self.game.type == Game.TYPE.NONPRINTED:
            tickets = Ticket.objects.filter(detail__draw=self, detail__state=BaseDetail.STATE.PLAYED)
            tickets = tickets.exclude(detail__bet__user__in=disabled_users)
            try:
                users = list(tickets.distinct('detail__bet__user__pk').\
                         values_list('detail__bet__user__pk', 'detail__bet__user__user__email'))
            except NotImplementedError:
                users = list(tickets.values_list('detail__bet__user__pk', 'detail__bet__user__user__email'))
                users = list(set(users))
        else:

            tickets = Ticket.objects.filter(detailcoupons__coupon__draw=self,
                                            detailcoupons__state=BaseDetail.STATE.PLAYED)
            tickets = tickets.exclude(detail__bet__user__in=disabled_users)
            try:
                users = list(tickets.distinct('detailcoupons__bet__user__pk').\
                         values_list('detailcoupons__bet__user__pk', 'detailcoupons__bet__user__user__email'))
            except NotImplementedError:
                users = list(tickets.values_list('detailcoupons__bet__user__pk', 'detailcoupons__bet__user__user__email'))
                users = list(set(users))

        context = None
        if self.game.code == Game.CODE.LOTERIA:
            context = {'lp': self.loteria_prize}

        self.create_extract(request, context)
        attachs = [(u'{}-{}.pdf'.format(self.game.code, self.number),
                    self.extract_file.read(), 'application/pdf')]

        emails = []
        for user_id, user_email in users:
            if self.game.type == Game.TYPE.NONPRINTED:
                user_tickets = tickets.filter(detail__bet__user__pk=user_id)
                imgs = None
            else:
                user_tickets = tickets.filter(detailcoupons__bet__user__pk=user_id)
                imgs = [ticket.real for ticket in user_tickets if ticket.real]

            context = {'draw': self, 'game': self.game, 'tickets': user_tickets}
            email = send_email(request, 'emails/extract_email', [], context=context,
                               attachments=attachs, bcc=[user_email], send=False, imgs=imgs)
            if email:
                emails.append(email)

        connection = mail.get_connection(fail_silently=not settings.DEBUG)
        # Manually open the connection
        connection.open()
        # Send the two emails in a single call -
        connection.send_messages(emails)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        connection.close()

    @property
    def loteria_prize(self):
        assert self.game.code == Game.CODE.LOTERIA
        return LoteriaPrize.objects.get(month=self.date_draw.month, year=self.date_draw.year)


class Draw(BaseDraw):

    prize_image = models.ImageField(
        upload_to=picture_prize, null=True, blank=True, verbose_name='Avatar'
    )

    price = RoundedDecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Precio',
        validators=[MinValueValidator(0.0)]
    )

    price2 = RoundedDecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Precio 2',
        validators=[MinValueValidator(0.0)]
    )
    price3 = RoundedDecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Precio 3',
        validators=[MinValueValidator(0.0)]
    )

    def validate_unique(self, exclude=None):
        super(Draw, self).validate_unique(exclude)

        # Avoid multiple draws with the same time
        if Draw.objects.filter(game=self.game, date_draw=self.date_draw).exclude(pk=self.pk).exists():
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'Ya existe un sorteo de {} con la fecha ingresada.'.format(self.game.name),
                    ],
            })

        # Avoid multiple draws with the same number
        if Draw.objects.filter(game=self.game, number=self.number).exclude(pk=self.pk).exists():
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'Ya existe un sorteo de {} con numero {}.'.format(self.game.name, self.number),
                    ],
            })

    def is_current(self):
        now = timezone.now()
        count = Draw.objects.filter(game__code=self.game.code,
                                    #state=BaseDraw.STATE.ACTIVE,
                                    date_draw__gt=now,
                                    date_draw__lt=self.date_draw).count()
        # QUINI6 y LOTO los miercoles puede apostarse para el domingo
        if self.game.code in [Game.CODE.LOTO, Game.CODE.QUINI6] and now.weekday() == 2: # wednesday
            return count <= 1
        else:
            return count == 0


class CsvImportError(Exception):
    pass


class DrawPreprinted(Draw):
    coupon_image = models.ImageField(
        upload_to=picture_coupon, null=True, blank=True, verbose_name='Billete completo'
    )
    coupon_thumbnail = models.ImageField(
        upload_to=picture_coupon_th, null=True, blank=True, verbose_name='Billete miniatura'
    )
    fractions = models.PositiveSmallIntegerField('Fracciones', default=1, blank=True)

    rounds = models.PositiveSmallIntegerField('Rondas', blank=True, null=True,
                                              validators=[MinValueValidator(1)])
    chances = models.PositiveSmallIntegerField('Chances', blank=True, null=True,
                                              validators=[MinValueValidator(1)])

    TBG_STATE = enum(
        PENDING=0,
        NOTIFIED=1,
    )
    TBG_STATE_CHOICES = (
        (TBG_STATE.PENDING, 'Pendiente'),
        (TBG_STATE.NOTIFIED, 'Notificado'),
    )
    tbg_state = models.PositiveIntegerField('Estado (Tbg)', choices=TBG_STATE_CHOICES,
                                            blank=True, default=0)

    def validate_unique(self, exclude=None):
        super(DrawPreprinted, self).validate_unique(exclude)

        date_draw = self.date_draw
        if date_draw is None:
            return

        # Avoid multiple draws with the same time
        if DrawPreprinted.objects.filter(
            date_draw__year=date_draw.year, date_draw__month=date_draw.month, date_draw__day=date_draw.day,
            game=self.game).exclude(pk=self.pk).exists():
            raise ValidationError({
                NON_FIELD_ERRORS: [
                    u'Ya existe un sorteo de {} con la fecha ingresada.'.format(self.game.name),
                ],
            })

    def load_coupons(self, csvfile):

        reader = csv.reader(csvfile, delimiter=str(';'))
        headers = reader.next()

        if self.game.code == Game.CODE.TELEBINGOCORRENTINO:
            idx_number = headers.index('BILLETE')
            idx_control = headers.index('CONTROL')
        else:
            idx_number = headers.index('BILLETE')
            idx_control = headers.index('CONTROL')

        if self.game.code == Game.CODE.TELEBINGONEUQUINO:
            reader = split_rows(csvfile, reader, idx_control + 1)

        rounds = {str(_round.number): _round for _round in self.round_set.all()}
        print rounds
        print rounds
        print rounds
        print rounds
        print rounds

        rows = 0
        with transaction.atomic():
            for row in reader:
                print row
                #chances = {(round,chance): [[...], [...], [...]], ...}
                chances = defaultdict(lambda: [[], [], []])
                for col, value in enumerate(row):
                    try:
                        current = parse_header(headers[col])
                        #print row[idx_number], current
                    except CsvImportError:
                        continue
                    else:
                        cur_chance = chances[(current['round'], current['chance'])]
                        cur_chance[current['row']].insert(current['col'], value.replace('*','0'))

                try:
                    coupon = Coupon.objects.create(
                        fraction_saldo=1,
                        draw=self, number=row[idx_number],
                        control=row[idx_control]
                    )
                except IntegrityError as err:
                    raise CsvImportError('Ya existe el billete número {} para este sorteo.'.format(row[idx_number]))

                try:
                    chance_list = []

                    print chances
                    for (round_num,chance_letter),lines in chances.items():
                        #round_inst = self.round_set.get(number=round_num)
                        print rounds, round_num
                        chance_list.append(Chance(
                            coupon=coupon, round=rounds[round_num], letter=chance_letter,
                            line1=','.join(lines[0]), line2=','.join(lines[1]), line3=','.join(lines[2])
                        ))
                    print chance_list
                    Chance.objects.bulk_create(chance_list)
                except KeyError as e:
                    print e
                    print e
                    print e
                    print e
                    print e
                    print e
                    print e
                    print e

                    raise CsvImportError('El número de chances del archivo no se corresponde con el del sorteo.')
                except IntegrityError as err:
                    raise CsvImportError(err.message)

                rows += 1

        return rows

    @staticmethod
    def parse_prize(prize, commit=False):

        if prize == 'OTRO BILLETE':
            prize = Prize(type=Prize.TYPE.COUPON)
            if commit:
                prize.save()
            return prize

        value = None
        text = ''
        _type = Prize.TYPE.CASH
        try:
            value = float(prize.replace(',', '.', 1))
        except ValueError:
            _type = Prize.TYPE.OTHER
            text = prize
        finally:
            prize = Prize(type=_type, value=value, text=text)
            if commit:
                prize.save()
        return prize

    @staticmethod
    def parse_numbers(numbers, commit=False):
        line, bingo = numbers.strip().split('<**<')
        line_result_set = VariableResultsSet.objects.create(numbers=line.replace(' ',','))
        bingo_result_set = VariableResultsSet.objects.create(numbers=bingo.replace(' ',','))
        if commit:
            line_result_set.save()
            bingo_result_set.save()
        return line_result_set, bingo_result_set

    def import_extract(self, csvfile):
        #assert self.game.code == Game.CODE.TELEBINGO, 'import_extract can only be called from telebingocordobes draw instance'

        ROW_TYPE = enum(
            INFO=1,
            RESULTS=2,
            WINNER=3,
        )

        PRIZE_TYPE = enum(
            LINE='LINEA',
            BINGO='BINGO',
            ENDING='TERMINACION',
            COUPON='NO GANADOR',
            CHANCE_LOCAL='CHANCE LOCAL',

        )

        COLS = enum(
            ROW_TYPE=0,
            DRAW_NUMBER=1,
            DRAW_DATE=2,
            ROUND_NUMBER=1,
            ROUND_RESULTS=2,
            PRIZE_TYPE=4,
            PRIZE=5,
            COUPON_NUMBER=1,
            DNI=1,
            PRIZE_ROUND_NUMBER=2,
            PRIZE_ROUND_CHANCE=3,
        )

        reader = csv.reader(csvfile, delimiter=str(';'))

        TbgRowExtract.objects.filter(coupon__draw=self).delete()
        TbgCouponExtract.objects.filter(draw=self).delete()
        TbgEndingExtract.objects.filter(coupon__draw=self).delete()
        TelebingoResults.objects.filter(round__draw=self).delete()
        self.coupon_extract_set.all().delete()

        try:
            with transaction.atomic():
                results_sets = {}
                for row in reader:
                    if int(row[COLS.ROW_TYPE]) == ROW_TYPE.INFO:
                        draw_number = row[COLS.DRAW_NUMBER]
                        draw_date = row[COLS.DRAW_DATE]

                        if self.number != draw_number:
                            raise CsvImportError('El número de sorteo no coincide.')
                        if self.date_draw.strftime('%d/%m/%Y') != draw_date:
                            raise CsvImportError('La fecha del sorteo no coincide.')

                    elif int(row[COLS.ROW_TYPE]) == ROW_TYPE.RESULTS:
                        try:
                            round = self.round_set.get(number=row[COLS.ROUND_NUMBER])
                        except Round.DoesNotExist:
                            raise CsvImportError('La cantidad de rondas no coincide.')

                        line, bingo = self.parse_numbers(row[COLS.ROUND_RESULTS], commit=True)
                        TelebingoResults.objects.create(round=round, line=line, bingo=bingo)
                        results_sets[round.number] = {'line': line, 'bingo': bingo}

                    elif int(row[COLS.ROW_TYPE]) == ROW_TYPE.WINNER:

                        prize = self.parse_prize(row[COLS.PRIZE], commit=True)

                        if row[COLS.PRIZE_TYPE] == PRIZE_TYPE.COUPON:
                            TbgCouponExtract.objects.create(draw=self, number=row[COLS.DNI], prize=prize)
                            continue

                        coupon_number = row[COLS.COUPON_NUMBER]
                        try:
                            coupon = self.coupon_set.get(number=coupon_number)
                        except Coupon.DoesNotExist:
                            #raise CsvImportError('El billete número {}, ganador de {}, '
                            #                     'no fue cargado en el sistema.'.format(coupon_number, prize.get_prize))
                            continue

                        if row[COLS.PRIZE_TYPE] == PRIZE_TYPE.LINE:
                            round_number = int(row[COLS.PRIZE_ROUND_NUMBER])

                            TbgRowExtract.objects.create(
                                hits=5, winners=0, order=round_number, coupon=coupon,
                                results=results_sets[round_number]['line'], prize=prize)

                        elif row[COLS.PRIZE_TYPE] == PRIZE_TYPE.BINGO :
                            round_number = int(row[COLS.PRIZE_ROUND_NUMBER])

                            TbgRowExtract.objects.create(
                                hits=15, winners=0, order=round_number, coupon=coupon,
                                results=results_sets[round_number]['bingo'], prize=prize)

                        elif row[COLS.PRIZE_TYPE] == PRIZE_TYPE.ENDING:
                            TbgEndingExtract.objects.create(coupon=coupon, prize=prize, ending=True)

                        elif row[COLS.PRIZE_TYPE] == PRIZE_TYPE.CHANCE_LOCAL:
                            chance = row[COLS.PRIZE_ROUND_CHANCE]
                            round_number = int(row[COLS.PRIZE_ROUND_NUMBER])

                            if chance == '':
                                change = 0

                            if round_number == '':
                                round_number = 0

                            TbgEndingExtract.objects.create(coupon=coupon, prize=prize, description=row[COLS.PRIZE_TYPE], round=round_number, chance=chance, ending=False)

                        else:
                            raise CsvImportError('No se encontro el premio ' + row[COLS.PRIZE_TYPE])


        #except Exception as err:
        #    raise CsvImportError(err.message)
        except CsvImportError:
            raise


class DrawQuiniela(BaseDraw):

    quiniela = models.ForeignKey('Quiniela')
    type = models.PositiveSmallIntegerField('Tipo', choices=TYPE_CHOICES)

    class Meta:
        verbose_name = 'Draw Quiniela (Concurso)'
        verbose_name_plural = 'Draws Quiniela (Concursos)'

    def is_current(self):
        now = timezone.now()
        current_tz = timezone.get_current_timezone()
        local_date_draw = current_tz.normalize(self.date_draw)
        return local_date_draw.date() == now.date() and self.date_draw > now

    def validate_unique(self, exclude=None):
        super(DrawQuiniela, self).validate_unique(exclude)

        date_draw = self.date_draw
        if date_draw is None:
            return

        if DrawQuiniela.objects.filter(
                date_draw__year=date_draw.year, date_draw__month=date_draw.month, date_draw__day=date_draw.day,
                quiniela=self.quiniela, type=self.type
            ).exclude(pk=self.pk).exists():

            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'Ya existe un sorteo para la quiniela {} - {} el dia {}.'.format(
                            self.quiniela.name, self.get_type_display(),
                            self.date_draw.strftime('%d-%m-%Y')),
                    ],
            })

    def __unicode__(self):
        if self.pk:
            return u'({}) {} {} {}'.format(self.pk, self.date_draw.date(),
                                          self.quiniela, self.get_type_display())
        else:
            return u'new'


class QuinielaGroup(models.Model):

    date = models.DateField('Fecha')
    province = models.ForeignKey('Province', verbose_name='Provincia')
    type = models.PositiveSmallIntegerField('Tipo', choices=TYPE_CHOICES)
    draws = models.ManyToManyField('DrawQuiniela', verbose_name='Concursos', related_name='groups')

    number = models.CharField(max_length=20, verbose_name=u'Número de sorteo')

    date_draw = models.DateTimeField(blank=True, null=True) # min(draws.date_draw)
    date_limit = models.DateTimeField(u'Hora límite usuario', blank=True, null=True)
    date_limit_agency = models.DateTimeField(blank=True, null=True) # min(draws.date_limit_agency)

    extract_file = models.FileField(upload_to=save_extract_group_file, storage=OverwriteStorage(),
                                    blank=True, null=True, verbose_name='Extracto')
    state = models.PositiveIntegerField('Estado', choices=BaseDraw.STATE_CHOICES, default=BaseDraw.STATE.ACTIVE)

    class Meta:
        unique_together = (('date','province','type'),)
        verbose_name = 'Quiniela Group (Sorteo)'
        verbose_name_plural = 'Quiniela Groups (Sorteos)'

    @property
    def extract_sent(self):
        return self.state == BaseDraw.STATE.EXTRACT

    @property
    def has_results(self):
        return self.extract_sent

    @property
    def active_draws(self):
        return self.draws.exclude(state=BaseDraw.STATE.DRAFT).order_by('quiniela__code')

    @property
    def is_loaded(self):
        return not self.draws.filter(state__lt=BaseDraw.STATE.LOADED).exists()

    def create_extract(self, request, context=None, pdf=True):
        ctx_dict = {}
        if request is not None:
            ctx_dict = RequestContext(request, ctx_dict)

        site = get_current_site(request)
        protocol = 'https' if request.is_secure() else 'http'
        ctx_dict.update({
            'group': self,
            'game': self.draws.first().game,
            'base_url': '{}://{}'.format(protocol, site.domain)
        })
        if context is not None:
            ctx_dict.update(context)

        html = render_to_string('extract/quiniela_group.html', ctx_dict)
        if not pdf:
            return html # TODO! remove return and pdf attribute

        STATIC_ROOT = os.path.join(settings.PROJECT_ROOT, 'site_media', 'static')
        css = list([os.path.join(STATIC_ROOT, 'bootstrap', 'css', 'bootstrap.css')])
        css.append(os.path.join(STATIC_ROOT, 'extract.css'))

        # Generar pdf en un archivo temporario
        output = tempfile.NamedTemporaryFile(suffix='.pdf')
        draws = self.active_draws.count()
        pdfkit.from_string(html, output.name, options=get_extract_options('quiniela_group', draws),
                           css=css, configuration=Configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))

        self.extract_file.save('file_name.pdf', files.File(output))

    def update_extract_sent(self):
        self.state = BaseDraw.STATE.EXTRACT
        self.save()
        self.active_draws.update(state=BaseDraw.STATE.EXTRACT)

    def send_game_extract(self, request):
        disabled_users = UserSetting.objects.filter(setting__code=USER_SETTINGS.MAIL_EXTRACT_SENT,
                                                    value=False).values_list('profile', flat=True)
        #details = self.detail_set.filter(state=BaseDetail.STATE.PLAYED).exclude(bet__user__in=disabled_users)
        #recipients = list(details.values_list('bet__user__user__email', flat=True))

        self.create_extract(request, None)
        attachs = [(u'{}-{}.pdf'.format(Game.CODE.QUINIELA, self.number),
                    self.extract_file.read(), 'application/pdf')]

        self.update_extract_sent()

        tickets = Ticket.objects.filter(detailquiniela__group=self, detailquiniela__state=BaseDetail.STATE.PLAYED)
        tickets = tickets.exclude(detailquiniela__bet__user__in=disabled_users)
        users = list(tickets.distinct('detailquiniela__bet__user__pk'). \
                     values_list('detailquiniela__bet__user__pk', 'detailquiniela__bet__user__user__email'))

        emails = []
        for user_id, user_email in users:
            user_tickets = tickets.filter(detailquiniela__bet__user__pk=user_id).distinct()

            context = {'game': self.draws.first().game, 'draw': self, 'tickets': user_tickets}
            email = send_email(request, 'emails/extract_email', [], context=context,
                               attachments=attachs, bcc=[user_email], send=False)
            if email:
                emails.append(email)

        connection = mail.get_connection(fail_silently=not settings.DEBUG)
        # Manually open the connection
        connection.open()
        # Send the two emails in a single call -
        connection.send_messages(emails)
        # The connection was already open so send_messages() doesn't close it.
        # We need to manually close the connection.
        connection.close()


    def __unicode__(self):
        return u'({}) {} {} {} - draws: {}'.format(self.pk, self.date, self.province,
                                          self.get_type_display(), self.draws.all().count())


class QuinielaTemplate(models.Model):

    province = models.ForeignKey('Province')
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    draws = models.CommaSeparatedIntegerField(max_length=250) #Hasta 50 combinaciones
    # draws => [(quiniela_id, type),(quiniela_id, type), ...]
    weekdays = models.CommaSeparatedIntegerField(max_length=13, blank=True, null=True)
    # weekdays NULL=> todos los dias, [0,1,2]=> solo lunes, martes y miercoles


class DrawPromotion(models.Model):

    draw = models.OneToOneField('BaseDraw', related_name='promotion', verbose_name='Sorteo')
    suggestion = models.CharField('Sugerencia', max_length=255, blank=True)
    is_active = models.BooleanField('Activa', blank=True, default=True)

    def __unicode__(self):
        return u'{} ({}): {}'.format(self.draw.game, self.draw.date_draw.date(), self.suggestion)


#===============================================================================
# END DRAW
#===============================================================================

"""class QuinielaByState(models.Model):

    def __unicode__(self):
        return u'{}'.format(self.datec)"""

class Bet(models.Model):

    user = models.ForeignKey('UserProfile', related_name='bet_set')
    date_bet = models.DateTimeField('Fecha Apuesta')
    code_trx = models.CharField(max_length=80, verbose_name='Transaccion', default=uuid.uuid4, unique=True)
    agency = models.ForeignKey('Agency', related_name='bet_set', verbose_name='Agencia')
    date_played = models.DateTimeField('Fecha jugada', null=True)
    won_notify = models.BooleanField("Notificado que gano", default=False)

    @property
    def importq(self):
        return sum(detail.importq for detail in self.get_details())

    @property
    def state(self):
        if any(getattr(detail, 'state') == BaseDetail.STATE.NOT_PLAYED for detail in self.get_details()):
            return BaseDetail.STATE.NOT_PLAYED
        else:
            return BaseDetail.STATE.PLAYED

    @property
    def get_state_display(self):
        return BaseDetail.STATE_CHOICES[self.state][1]

    @property
    def won(self):
        return any(map(lambda x: x.winner_set.exists(), self.get_details()))

    @property
    def date_draw(self):
        detail = self.get_details()[0]
        if isinstance(detail, DetailCoupons):
            return detail.coupon.draw.date_draw
        elif isinstance(detail, DetailQuiniela):
            return detail.group.date_draw
        else:
            return detail.draw.date_draw

    @property
    def draws(self):
        if hasattr(self, 'detail'):
            return [self.detail.draw]

        if self.detailquiniela_set.exists():
            draws = []
            for detail in self.detailquiniela_set.all():
                draws += detail.draws.all()
            return draws

        if self.detailcoupons_set.exists():
            return [detail.coupon.draw for detail in self.detailcoupons_set.all()]

        logger.error('Bet without detail: {}'.format(self.pk))
        return None

    @property
    def game(self):
        if hasattr(self, 'detail'):
            return self.detail.draw.game

        if self.detailquiniela_set.exists():
            return self.detailquiniela_set.first().draws.first().game

        if self.detailcoupons_set.exists():
            return self.detailcoupons_set.first().coupon.draw.game

        logger.error('Bet without detail: {}'.format(self.pk))
        return None

    def get_details(self):
        if hasattr(self, 'detail'):

            if hasattr(self.detail, 'detailquiniseis'):
                return [self.detail.detailquiniseis]
            if hasattr(self.detail, 'detailbrinco'):
                return [self.detail.detailbrinco]
            if hasattr(self.detail, 'detailloto5'):
                return [self.detail.detailloto5]
            if hasattr(self.detail, 'detailloto'):
                return [self.detail.detailloto]

        if self.detailquiniela_set.exists():
            return self.detailquiniela_set.all()

        if self.detailcoupons_set.exists():
            return self.detailcoupons_set.all()

        return []

    def to_string(self):
        details = self.get_details()
        string_list = []
        if self.game.code == Game.CODE.QUINIELA:
            for detail in details:
                string_list.append(detail.to_string(include_name=False))
        else:
            for detail in details:
                string_list.append(detail.to_string())
        return u'-' + u'\n-'.join(string_list)

    def send_confirm_bet_email(self, request):

        detail = self.get_details()[0]
        profile = self.user
        context = {
                'game': self.game,
                'agency': profile.agency,
                'user': profile.user
            }

        urls = dict(ticket=reverse('bet:request_ticket',
                                   kwargs={'id': detail.ticket_id, 'key': detail.ticket.key}))

        attachs = [('ticket.pdf', detail.ticket.fake.read(), 'application/pdf')]
        profile.email_notification(request, USER_SETTINGS.MAIL_PLAYED_BET, 'emails/confirm_bet_email',
                                   context, attachments=attachs, urls=urls)

    def delete(self, using=None):
        if self.state == BaseDetail.STATE.PLAYED:
            raise Exception('Already played bets cannot be deleted.')

        with transaction.atomic(using):
            try:
                if self.movement.state == AbstractMovement.STATE.CONFIRMED:
                    self.user.saldo += abs(self.movement.amount)
                    self.user.save(update_fields=('saldo',))
                #self.movement.delete()
            except AttributeError:
                pass

            for detail in self.get_details():
                try:
                    detail.ticket.delete()
                except AttributeError:
                    pass

                if isinstance(detail, DetailQuiniela):
                    detail.draws.clear()
                    if detail.redoblona:
                        detail.redoblona.delete()
                elif isinstance(detail, DetailCoupons):
                    detail.coupon.fraction_saldo += detail.fraction_bought
                    detail.coupon.save(update_fields=('fraction_saldo',))
                #detail.delete()

            super(Bet, self).delete(using)

    def __unicode__(self):
        return u'{} -{}- {}'.format(self.user, self.game.name, self.date_bet.replace(microsecond=0))


class CouponQuerySet(models.QuerySet):
    def ordered(self):
        if connection.vendor == 'postgresql':
            cast_to_int_function = 'number::integer'
        else:
            cast_to_int_function = 'CAST(number as integer)'
        return self.extra(select={'int_num': cast_to_int_function}).order_by('int_num')


class CouponManager(models.Manager.from_queryset(CouponQuerySet)):
    def get_queryset(self):
        return super(CouponManager, self).get_queryset().filter(agency__isnull=False,
                                                                fraction_saldo__gt=0)

class Coupon(models.Model):

    template_name = 'coupons/coupon_html.html'

    draw = models.ForeignKey('DrawPreprinted', verbose_name='Sorteo', related_name='coupon_set')
    number = models.CharField('Billete', max_length=40)
    fraction_sales = models.PositiveIntegerField('Fracciones compradas', blank=True, default=0)
    fraction_saldo = models.PositiveIntegerField('Fracciones disponibles', blank=True, default=0)
    control = models.CharField(max_length=13, blank=True)
    agency = models.ForeignKey('Agency', verbose_name='Agencia', blank=True, null=True)

    objects = CouponQuerySet.as_manager()
    availables = CouponManager()

    @property
    def available(self):
        return self.fraction_saldo > 0

    @property
    def is_telebingo(self):
        return self.draw.game.code.startswith('telebingo')

    @property
    def fractions_bought(self):
        return self.detailcoupon_set.aggregate(total=Sum(F('fraction_bought'))).get('total') or 0

    @property
    def results(self):
        if hasattr(self.round, 'results'):
            return map(int, self.round.results.bingo.split(','))
        else:
            return []

    def to_html(self, request=None):
        chance_list = self.chance_set.order_by('round__number', 'letter')
        context = {
            'coupon': self,
            'chances': chance_list,
            'request': request
        }
        return render_to_string(self.template_name, context)

    def __unicode__(self):
        return u'{} {}'.format(self.draw, self.number)


class LoteriaCoupon(Coupon):

    progresion = models.PositiveSmallIntegerField(validators=[MaxValueValidator(11)])


class Round(models.Model):

    #coupon = models.ForeignKey('Coupon', related_name='round_set')
    draw = models.ForeignKey('DrawPreprinted', related_name='round_set',
                             limit_choices_to={'game__code__startswith': 'telebingo'})
    number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    def clean(self):
        super(Round, self).clean()

        if self.number > self.draw.rounds:
            raise ValidationError({
                'number': [
                    'Número máximo de rondas: {}.'.format(self.draw.rounds),
                ],
            })

    def validate_unique(self, exclude=None):
        super(Round, self).validate_unique(exclude)

        # Avoid multiple rounds with the same number
        if self.draw.round_set.filter(number=self.number).exists():
            raise ValidationError({
                NON_FIELD_ERRORS: [
                    'Ya existe la ronda {} del sorteo numero {}.'.format(self.number, self.draw.number),
                ],
            })

    def __unicode__(self):
        return 'Sorteo {} - ronda {}'.format(self.draw.number, self.number)




class Chance(models.Model):

    LETTER_CHOICES = (
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    )
    letter = models.CharField(max_length=1, choices=LETTER_CHOICES)
    coupon = models.ForeignKey('Coupon', related_name='chance_set',
                               limit_choices_to={'draw__game__code__startswith': 'telebingo'})
    round = models.ForeignKey('Round', related_name='chance_set')

    line1 = models.CommaSeparatedIntegerField(max_length=22) # del 01 al 90, 0 -> *
    line2 = models.CommaSeparatedIntegerField(max_length=22)
    line3 = models.CommaSeparatedIntegerField(max_length=22)

    class Meta:
        unique_together = (('coupon', 'round', 'letter'),)

    def clean(self):
        super(Chance, self).clean()

        if self.coupon:
            if self.letter and map(itemgetter(0), Chance.LETTER_CHOICES).index(self.letter)+1 > self.coupon.draw.chances:
                raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u"Chance '{}' incorrecta. El billete contiene {} chances".format(self.letter,
                                                                                       self.coupon.draw.chances)
                    ],
                })

    def unique_error_message(self, model_class, unique_check):
        if model_class == type(self) and unique_check == ('coupon', 'round', 'letter'):
            return 'Ya existe la chance {} para la ronda {} del billete número {}.'.format(self.letter,
                                                                                         self.round.number,
                                                                                         self.coupon.number)
        else:
            return super(Chance, self).unique_error_message(model_class, unique_check)

    @property
    def bingo_results(self):
        if hasattr(self.round, 'results'):
            return self.round.results.bingo.numbers.split(',')
        else:
            return []

    @property
    def line_results(self):
        print self.round.id
        if hasattr(self.round, 'results'):
            return self.round.results.line.numbers.split(',')
        else:
            return []

    @property
    def lines(self):
        i=1
        while hasattr(self, 'line{}'.format(i)):
            yield getattr(self, 'line{}'.format(i))
            i += 1

    @property
    def splitted_lines(self):
        for line in self.lines:
            yield line.split(',')

    def __unicode__(self):
        return 'Billete {}{} - ronda {}'.format(self.coupon.number, self.letter, self.round.number)


class PrizeRequest(models.Model):

    STATE = enum(
        PENDING=0,
        ACCEPTED=1,
        REJECTED=2,
    )
    STATE_CHOICES = (
        (STATE.PENDING, 'Pendiente'),
        (STATE.ACCEPTED, 'Aceptado'),
        (STATE.REJECTED, 'Rechazado'),
    )

    detail = models.ForeignKey('DetailCoupons', verbose_name='Detalle')
    numbers = models.CommaSeparatedIntegerField('Coincidencias', max_length=152) # hasta 50 numeros de 2 cifras
    state = models.PositiveSmallIntegerField(choices=STATE_CHOICES, default=STATE.PENDING)
    mode = models.CharField(max_length=12) # Modaliad de juego. Ej. 'sos' en loto. (code de get_draw_results) # TODO! Rename to code
    date = models.DateTimeField(auto_now_add=True)

    @property
    def get_numbers(self):
        if self.numbers:
            return map(int, self.numbers.split(','))
        return []

    @property
    def game(self):
        return self.detail.coupon.draw.game

    @property
    def get_mode(self):
        return unicode(self.results._meta.get_field(self.mode).verbose_name)

    @property
    def results(self):
        draw = self.detail.coupon.draw
        if draw.game.code == Game.CODE.TELEBINGO:
            return draw.telebingoold_results

        return getattr(draw, draw.game.code+'_results')

    @property
    def winning_bet(self):
        """ Returns True if there aren't prize request PENDING for the same detail
        and at least one was winner """
        pending = self.detail.prizerequest_set.filter(state=PrizeRequest.STATE.PENDING).exists()
        winner = self.detail.prizerequest_set.filter(state=PrizeRequest.STATE.ACCEPTED).exists()
        return not pending and winner

    @property
    def losing_bet(self):
        """ Returns True if all prize requests are REJECTED for the same detail """
        return not self.detail.prizerequest_set.exclude(state=PrizeRequest.STATE.REJECTED).exists()


class UserCredit(models.Model):

    user = models.ForeignKey('UserProfile')
    expiration = models.DateTimeField()
    winner = models.OneToOneField('Winner')
    game = models.ForeignKey('Game')
    agency = models.ForeignKey('Agency')
    accredited = models.BooleanField(default=False)
    bet = models.OneToOneField('Bet', blank=True, null=True)

    def __unicode__(self):
        return u'{} {} {}'.format(self.id, self.game, self.accredited)


class BaseWinner(models.Model):

    info = models.CharField(max_length=80, blank=True)
    prize_tax = models.PositiveIntegerField('Premio con impuestos', null=True)
    notif = models.BooleanField('Notificado', default=False)

    @property
    def parent(self):
        if hasattr(self, 'winner'):
            return self.winner.parent
        elif hasattr(self, 'winnertelebingocoupon'):
            return self.winnertelebingocoupon
        return self

    @property
    def bet(self):
        return self.get_winners[0].detail.parent.bet

    @property
    def game(self):
        return self.get_winners[0].detail.parent.game

    @property
    def draw(self):
        return self.get_winners[0].detail.parent.group

    @property
    def prize_type(self):
        return Prize.TYPE.CASH

    @property
    def get_winners(self):
        if hasattr(self, 'winner'):
            return [self.winner]
        return self.winnerquiniela_set.all()

    def get_details(self):
        details = []
        for winner in self.get_winners:
            details.append(winner.detail)
        return set(details)

    def get_prize(self):
        return sum([w.prize for w in self.get_winners])

    def should_be_paid(self):
        """Indica si el premio debe pagarse por agencia24"""
        prize = self.get_prize()
        taxes = self.game.gametax_set.get(province=self.bet.agency.province)
        return prize <= taxes.min

    def prize_with_taxes(self):

        prize = self.get_prize()

        # Si gano menos de lo que aposto no tiene impuestos
        importq = sum([detail.importq for detail in self.get_details()])
        if prize <= importq:
            return prize, [], prize

        taxes = self.game.gametax_set.get(province=self.bet.agency.province)
        tax_list = []

        allv = prize
        t_prize = prize
        if prize > taxes.min_nat and taxes.nat_tax != 0:
            imp = prize * taxes.nat_tax/Decimal(100)
            t_prize -= imp
            tax_list.append({'message': 'Impuesto nacional', 'tax': taxes.nat_tax, 'val': imp})

        if prize > taxes.min_prov and taxes.prov_tax != 0:
            imp = prize * taxes.prov_tax/Decimal(100)
            t_prize -= imp
            tax_list.append({'message': 'Impuesto provincial', 'tax': taxes.prov_tax, 'val': imp})

        return t_prize, tax_list, allv

    def __unicode__(self):
        return u'{} - {}...'.format(self.pk, self.info)


class Winner(BaseWinner):

    detail = models.ForeignKey('BaseDetail', verbose_name='Detalle') # Un mismo ticket(detail) puede ganar tradicional y revancha
    draw = models.ForeignKey('BaseDraw', verbose_name='Sorteo', related_name='winner_set')

    def should_be_paid(self):
        """Indica si el premio debe pagarse por agencia24"""
        if self.prize_type != Prize.TYPE.CASH:
            return False


        prize = self.get_prize()
        taxes = self.game.gametax_set.get(province=self.bet.agency.province)
        return prize <= taxes.min

    def clean(self):
        super(Winner, self).clean()

        if self.detail and self.draw:
            detail =  self.get_detail
            if not isinstance(detail, DetailQuiniela):
                if detail.draw.pk != self.draw.pk:
                    raise ValidationError({
                        NON_FIELD_ERRORS: [
                            'El sorteo no se corresponde con la jugada del usuario.'
                        ],
                    })

    @property
    def get_detail(self):
        return self.detail.parent

    @property
    def bet(self):
        return self.get_detail.bet

    @property
    def game(self):
        return self.draw.game

    def get_prize(self):
        if self.parent is not None:
            return self.parent.get_prize()

        return 0

    def hits(self):
        if hasattr(self, 'winnersingleextract'):
            return self.winnersingleextract.hits
        if hasattr(self, 'winnerextract'):
            return self.winnerextract.hits
        if hasattr(self, 'winnertelebingo'):
            return self.winnertelebingo.hits
        elif hasattr(self, 'winnerquini6extra'):
            return self.winnerquini6extra.hits
        elif hasattr(self, 'winnerquiniela'):
            return None

        return 0

    @property
    def parent(self):
        if hasattr(self, 'winnersingleextract'):
            return self.winnersingleextract
        if hasattr(self, 'winnerextract'):
            return self.winnerextract
        if hasattr(self, 'winnertelebingo'):
            return self.winnertelebingo
        elif hasattr(self, 'winnerquini6extra'):
            return self.winnerquini6extra
        elif hasattr(self, 'winnerquiniela'):
            return self.winnerquiniela
        elif hasattr(self, 'winnerloteria'):
            return self.winnerloteria

        return None

    def prize_with_taxes(self):
        assert(self.parent.prize_type == Prize.TYPE.CASH)

        prize = self.get_prize()
        detail = self.get_detail
        # Si gano menos de lo que aposto no tiene impuestos
        if prize <= detail.importq:
            return prize, [], prize

        taxes = detail.game.gametax_set.get(province=detail.bet.agency.province)

        tax_list = []
        t_prize = prize
        allv = prize
        if prize > taxes.min_nat and taxes.nat_tax != 0:
            imp = prize * taxes.nat_tax/Decimal(100)
            t_prize -= imp
            tax_list.append({'message': 'Impuesto nacional', 'tax': taxes.nat_tax, 'val': imp})

        if prize > taxes.min_prov and taxes.prov_tax != 0:
            imp = prize * taxes.prov_tax/Decimal(100)
            t_prize -= imp
            tax_list.append({'message': 'Impuesto provincial', 'tax': taxes.prov_tax, 'val': imp})

        return t_prize, tax_list, allv

    def __unicode__(self):
        return u'{}: notificado {}'.format(self.draw.game.name, self.notif)


class WinnerExtract(Winner):
    extract = models.ForeignKey('RowExtract', verbose_name='Fila Extracto', related_name='winner_set')

    def get_prize(self):
        return self.extract.get_prize

    @property
    def prize_type(self):
        return self.extract.prize_type

    @property
    def hits(self):
        return self.extract.hits

    def __unicode__(self):
        return u'{} aciertos, premio {}, notificado {}'.format(self.extract.hits, self.extract.get_prize, self.notif)


class TbgRowExtractManager(models.Manager):
    def get_queryset(self):
        return super(TbgRowExtractManager, self).get_queryset().filter(type__in=[WinnerTelebingo.TYPE.LINE, 
                                                                                 WinnerTelebingo.TYPE.BINGO])

class TbgEndingExtractManager(models.Manager):
    def get_queryset(self):
        return super(TbgEndingExtractManager, self).get_queryset().filter(type=WinnerTelebingo.TYPE.COUPON)

class WinnerTelebingoQuerySet(models.QuerySet):
    def filter_by_draw(self, draw):
        return self.filter(Q(row_extract__isnull=False, row_extract__coupon__draw=draw) |
                           Q(ending_extract__isnull=False, ending_extract__coupon__draw=draw))


class WinnerTelebingo(Winner):
    TYPE = enum(
        LINE=0,
        BINGO=1,
        ENDING=3,
        CHANCE_LOCAL=4,
    )

    TYPE_CHOICES = (
        (TYPE.LINE, u'Linea'),
        (TYPE.BINGO, u'Bingo'),
        (TYPE.ENDING, u'Extras'),
        (TYPE.CHANCE_LOCAL, u'Chance Local'),
    )

    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    row_extract = models.OneToOneField('TbgRowExtract', related_name='winner', blank=True, null=True)
    ending_extract = models.OneToOneField('TbgEndingExtract', related_name='winner', blank=True, null=True)

    objects = WinnerTelebingoQuerySet.as_manager()
    row_objects = TbgRowExtractManager()
    ending_objects = TbgEndingExtractManager()

    @property
    def extract(self):
        if self.type in [WinnerTelebingo.TYPE.LINE, WinnerTelebingo.TYPE.BINGO]:
            return self.row_extract
        elif self.type == WinnerTelebingo.TYPE.CHANCE_LOCAL:
            return self.extras_extract
        return self.ending_extract

    def get_prize(self):
        return self.extract.get_prize

    @property
    def prize_type(self):
        return self.extract.prize_type

    @property
    def hits(self):
        if self.type == WinnerTelebingo.TYPE.LINE:
            return 5
        if self.type == WinnerTelebingo.TYPE.BINGO:
            return 15
        return 1

    def clean(self):
        super(WinnerTelebingo, self).clean()

        if self.type in [WinnerTelebingo.TYPE.LINE, WinnerTelebingo.TYPE.BINGO]:
            if not self.row_extract:
                raise ValidationError({
                    'row_extract': ['Este campo es obligatorio.'],
                })
            elif self.row_extract.coupon.draw.pk != self.draw.pk:
                raise ValidationError({
                    NON_FIELD_ERRORS: ['El sorteo no corresponde.'],
                })

        if self.type == WinnerTelebingo.TYPE.ENDING:
            if not self.ending_extract:
                raise ValidationError({
                    'ending_extract': ['Este campo es obligatorio.'],
                })
            elif self.ending_extract.coupon.draw.pk != self.draw.pk:
                raise ValidationError({
                    NON_FIELD_ERRORS: ['El sorteo no corresponde.'],
                })

    def __unicode__(self):
        return '{}'.format(self.get_type_display())


class WinnerTelebingoCoupon(BaseWinner):

    extract = models.OneToOneField('TbgCouponExtract', related_name='winner')

    def prize_with_taxes(self):
        assert(self.parent.prize_type == Prize.TYPE.CASH)

        prize = self.get_prize()
        game = self.extract.draw.game
        try:
            province = game.provinces.get()
        except Province.MultipleObjectsReturned:
            logger.error('{} pertenece a mas de una provincia. '
                         'Imposible determinar impuestos de premio'.format(game.name))
            province = game.provinces.first()

        taxes = game.gametax_set.get(province=province)

        allv = prize
        tax_list = []
        t_prize = prize
        if prize > taxes.min_nat and taxes.nat_tax != 0:
            imp = prize * taxes.nat_tax/Decimal(100)
            t_prize -= imp
            tax_list.append({'message': 'Impuesto nacional', 'tax': taxes.nat_tax, 'val': imp})

        if prize > taxes.min_prov and taxes.prov_tax != 0:
            imp = prize * taxes.prov_tax/Decimal(100)
            t_prize -= imp
            tax_list.append({'message': 'Impuesto provincial', 'tax': taxes.prov_tax, 'val': imp})

        return t_prize, tax_list, allv

    @property
    def draw(self):
        return self.extract.draw

    def should_be_paid(self):
        """Indica si el premio debe pagarse por agencia24.
        False porque No hay manera de determinar si el billete fue comprado desde la APP """
        return False

    def get_prize(self):
        return self.extract.get_prize

    def __unicode__(self):
        return u'premio {}, notificado {}'.format(self.extract.get_prize, self.notif)


class WinnerSingleExtract(Winner):

    extract = models.ForeignKey('SingleExtract', verbose_name='Extracto', related_name='winner_set')

    def get_prize(self):
        return self.extract.get_prize

    @property
    def prize_type(self):
        return Prize.TYPE.CASH

    @property
    def hits(self):
        # Quini6Extra
        return 6

    def __unicode__(self):
        return u'{} aciertos, premio {}, notificado {}'.format(self.hits, self.extract.get_prize, self.notif)


class WinnerQuiniela(Winner):

    prize = RoundedDecimalField('Premio', max_digits=12, decimal_places=2)
    hits = models.PositiveSmallIntegerField()
    winner_ticket = models.ForeignKey('BaseWinner', null=True)

    def get_prize(self):
        return self.prize

    @property
    def prize_type(self):
        return Prize.TYPE.CASH


class WinnerLoteria(Winner):

    TYPE = enum(
        LOCATION=0,
        PROGRESION=1,
        ENDING=2,
        APPROACH=3,
    )
    TYPE_CHOICES = (
        (TYPE.LOCATION, u'Ubicación'),
        (TYPE.PROGRESION, u'Progresión'),
        (TYPE.ENDING, u'Terminación'),
        (TYPE.APPROACH, u'Aproximación'),
    )

    prize = RoundedDecimalField('Premio', max_digits=12, decimal_places=2)
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)

    def get_prize(self):
        return self.prize

    @property
    def prize_type(self):
        return Prize.TYPE.CASH


class LoteriaPrizeRow(models.Model):

    CODE = enum(
        LOCATION1=0,
        LOCATION2=1,
        LOCATION3=2,
        LOCATION4=3,
        LOCATION5=4,
        LOCATION6_10=5,
        LOCATION11_20=6,

        APPROACH1=7,
        APPROACH2=8,
        APPROACH3=9,

        ENDING1_4=10,
        ENDING1_3=11,
        ENDING1_2=12,
        ENDING2_2=13,
        ENDING3_2=14,
        ENDING1_1=15,

        PROGRESION=16,
    )
    CODE_CHOICES = (
        (CODE.LOCATION1, u'1° PREMIO'),
        (CODE.LOCATION2, u'2° PREMIO'),
        (CODE.LOCATION3, u'3° PREMIO'),
        (CODE.LOCATION4, u'4° PREMIO'),
        (CODE.LOCATION5, u'5° PREMIO'),
        (CODE.LOCATION6_10, u'6° AL 10° PREMIO'),
        (CODE.LOCATION11_20, u'11° AL 20° PREMIO'),

        (CODE.APPROACH1, u'ANTERIOR Y POSTERIOR DEL 1° PREMIO'),
        (CODE.APPROACH2, u'ANTERIOR Y POSTERIOR DEL 2° PREMIO'),
        (CODE.APPROACH3, u'ANTERIOR Y POSTERIOR DEL 3° PREMIO'),

        (CODE.ENDING1_4, u'4 ULTIMAS CIFRAS DEL 1° PREMIO'),
        (CODE.ENDING1_3, u'3 ULTIMAS CIFRAS DEL 1° PREMIO'),
        (CODE.ENDING1_2, u'2 ULTIMAS CIFRAS DEL 1° PREMIO'),
        (CODE.ENDING2_2, u'2 ULTIMAS CIFRAS DEL 2° PREMIO'),
        (CODE.ENDING3_2, u'2 ULTIMAS CIFRAS DEL 3° PREMIO'),
        (CODE.ENDING1_1, u'ULTIMA CIFRA DEL 1° PREMIO'),

        (CODE.PROGRESION, u'PROGRESION 11 EN 11')
    )

    code = models.PositiveSmallIntegerField(choices=CODE_CHOICES)
    prize = models.ForeignKey('Prize')
    month = models.ForeignKey('LoteriaPrize', related_name='prizes')

    def __unicode__(self):
        return u'{:0>2}/{} - {}: {}'.format(self.month.month, self.month.year, self.get_code_display(), self.prize.get_prize)


class LoteriaPrize(models.Model):

    month = models.PositiveSmallIntegerField('Mes', validators=[MinValueValidator(1),
                                                                             MaxValueValidator(12)])
    year = models.PositiveSmallIntegerField(u'Año', validators=[MinValueValidator(2016),
                                                                             MaxValueValidator(2099)])

    class Meta:
        unique_together = (('month', 'year'),)

    @staticmethod
    def get_by_draw(draw):
        return LoteriaPrize.objects.get(month=draw.date_draw.month, year=draw.date_draw.year)

    def location_prize(self, location):
        if location > 10:
            return self.prizes.get(code=LoteriaPrizeRow.CODE.LOCATION11_20).prize.value
        elif location > 5:
            return self.prizes.get(code=LoteriaPrizeRow.CODE.LOCATION6_10).prize.value
        else:
            return self.prizes.get(code=getattr(LoteriaPrizeRow.CODE, 'LOCATION{}'.format(location))).prize.value

    def progresion_prize(self):
        return self.prizes.get(code=LoteriaPrizeRow.CODE.PROGRESION).prize.value

    def approach_prize(self, location):
        return self.prizes.get(code=getattr(LoteriaPrizeRow.CODE, 'APPROACH{}'.format(location))).prize.value

    def ending_prize(self, digits, location):
        return self.prizes.get(code=getattr(LoteriaPrizeRow.CODE, 'ENDING{}_{}'.format(location, digits))).prize.value

    def __unicode__(self):
        return u'{}'.format(date.strftime(date(self.year,self.month,1), '%B %Y'))


class Ticket(models.Model):
    """ Representa un billete de un juego pre-impreso, o el ticket de un juego no-impreso"""

    STATE = enum(
        NOT_REQUESTED=0,
        REQUESTED=1,
        LOADED=2,
    )
    STATE_CHOICES = (
        (STATE.NOT_REQUESTED, u'No Solicitado'),
        (STATE.REQUESTED, u'Solicitado'),
        (STATE.LOADED, u'Cargado'),
    )

    # Si es pre impreso fake no es necesario, no puede crearse un billete ficticio
    fake = models.FileField(upload_to=picture_ticket, storage=OverwriteStorage(),
                            blank=True, null=True, verbose_name='Pseudo-Ticket')
    real = models.ImageField(upload_to=picture_ticket, storage=OverwriteStorage(),
                             blank=True, null=True, verbose_name='Ticket Real')
    requested = models.PositiveSmallIntegerField(default=STATE.NOT_REQUESTED, choices=STATE_CHOICES)
    key = models.CharField(max_length=56, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            salt = hashlib.sha224(str(random.random())).hexdigest()[:5]
            self.key = hashlib.sha224(salt).hexdigest()

        super(Ticket, self).save(*args, **kwargs)

    @staticmethod
    def get_state_display(state):
        if state == -1:
            return u'El ticket solicitado no existe.'
        elif state == 0:  # (not is_old, Ticket.STATE.NOT_REQUESTED)
            return u'El ticket no fue solicitado.'
        elif state == 1 or state == 4:  # (, Ticket.STATE.REQUESTED)
            return u'Tu ticket ya fue solicitado. En breve recibirás un email con la foto de tu ticket.'

        elif state == 2 or state == 5:  # (, Ticket.STATE.LOADED)
            return u'Tu ticket ya está disponible. Ingresá a la aplicación y buscalo en la apuesta correspondiente.'

        elif state == 3:  # (is_old, Ticket.STATE.NOT_REQUESTED)
            return u'No puede solicitar un ticket de un sorteo ya jugado.'
        elif state == 6:  # detail_state == STATE.NOT_PLAYED
            return u''

    @property
    def draw_is_old(self):
        if hasattr(self, 'detail'):
            return self.detail.draw.is_old
        elif hasattr(self, 'detailcoupons'):
            return self.detailcoupons.coupon.draw.is_old
        elif self.detailquiniela_set.first() is not None:
            detail = self.detailquiniela_set.first()
            if detail is None:
                raise Exception('Ticket without detail')

            return timezone.now() > detail.group.date_draw
        else:
            raise Exception('Ticket without detail')

    @property
    def game(self):
        if hasattr(self, 'detail'):
            return self.detail.draw.game
        elif hasattr(self, 'detailcoupons'):
            return self.detailcoupons.coupon.draw.game
        elif self.detailquiniela_set.first() is not None:
            detail = self.detailquiniela_set.first()
            if detail is None:
                raise Exception('Ticket without detail')

            return detail.draws[0].game
        else:
            raise Exception('Ticket without detail')

    @property
    def detail_state(self):
        if hasattr(self, 'detail'):
            return self.detail.state
        elif hasattr(self, 'detailcoupons'):
            return self.detailcoupons.state
        elif self.detailquiniela_set.first() is not None:
            detail = self.detailquiniela_set.first()
            if detail is None:
                raise Exception('Ticket without detail')

            return detail.state
        else:
            raise Exception('Ticket without detail')

    @property
    def state(self):
        if self.detail_state == BaseDetail.STATE.NOT_PLAYED:
            return 6

        is_old = True
        states = {
            (not is_old, Ticket.STATE.NOT_REQUESTED):   0,
            (not is_old, Ticket.STATE.REQUESTED):       1,
            (not is_old, Ticket.STATE.LOADED):          2,
            (is_old, Ticket.STATE.NOT_REQUESTED):       3,
            (is_old, Ticket.STATE.REQUESTED):           4,
            (is_old, Ticket.STATE.LOADED):              5,
            #detail_state == STATE.NOT_PLAYED           6,
        }

        return states[(self.draw_is_old, self.requested)]

    @property
    def get_details(self):

        if hasattr(self, 'detail'):  # NO IMPRESO
            return [self.detail.parent]
        elif hasattr(self, 'detailcoupons'):  # PREIMPRESO
            return [self.detailcoupons]
        elif hasattr(self, 'detailquiniela_set'):  # QUINIELA
            return self.detailquiniela_set.all()

        raise Exception('Orphan Ticket')

    def create_fake_ticket(self, request, pdf=True):

        ctx_dict = {}
        if request is not None:
            ctx_dict = RequestContext(request, ctx_dict)

        details = self.get_details
        detail = details[0]
        pdf_options = detail.TICKET_OPTIONS
        lotteries = []
        if isinstance(detail, DetailQuiniela):
            pdf_options.update({'page-height': '{}cm'.format(7.75+0.5*len(details))})
            lotteries = detail.draws.values_list('quiniela__name', flat=True)

        #site = get_current_site(request)
        #protocol = 'https' if request.is_secure() else 'http'
        ctx_dict.update({
            'details': details,
            'lotteries': lotteries,
            'game': detail.game,
            'bet': detail.bet,
            'agency': detail.bet.agency,
            #'base_url': '{}://{}'.format(protocol, site.domain)
        })

        html = render_to_string('tickets/{}.html'.format(detail.game.code), ctx_dict)
        if not pdf:
            return html  # TODO! remove return and pdf attribute

        STATIC_ROOT = os.path.join(settings.PROJECT_ROOT, 'site_media', 'static')
        css = list([os.path.join(STATIC_ROOT, 'bootstrap', 'css', 'bootstrap.css')])
        css.append(os.path.join(STATIC_ROOT, 'tickets.css'))

        # Generar pedf en un archivo temporario
        output = tempfile.NamedTemporaryFile(suffix='.pdf')
        pdfkit.from_string(html, output.name, options=pdf_options, css=css,
                           configuration=Configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))

        # Guardar archivo temporario en FileField
        self.fake.save('file_name.pdf', files.File(output))

    def send_fake_ticket_email(self, request):

        detail = self.get_details[0]
        profile = detail.bet.user
        game = detail.game
        is_preprinted = game.type == Game.TYPE.PREPRINTED

        context = {
            'game': game,
            'preprinted': is_preprinted,
            'agency': profile.agency,
            'user': profile.user,
            'quiniela': detail.draws.first().get_type_display() if isinstance(detail, DetailQuiniela) else None
        }
        attachs = []
        if not is_preprinted:
            attachs.append(('ticket.pdf', self.fake.read(), 'application/pdf'))
        profile.email_notification(request, USER_SETTINGS.MAIL_TICKET_SENT,
                                   'emails/fake_ticket_email', context, attachs)


#===============================================================================
# DETAILS
#===============================================================================


class BaseDetail(models.Model):
    STATE = enum(
        NOT_PLAYED=0,
        PLAYED=1
    )
    STATE_CHOICES = (
        (STATE.NOT_PLAYED, 'No Jugado'),
        (STATE.PLAYED, 'Jugado'),
    )

    TICKET_OPTIONS = {
        'page-height': '8cm',
        'page-width': '9cm',
        'margin-top': '0.5cm',
        'margin-right': '0.5cm',
        'margin-bottom': '0.5cm',
        'margin-left': '0.5cm',
        'encoding': 'UTF-8'
    }

    importq = RoundedDecimalField('Importe', max_digits=12, decimal_places=2, blank=True, null=True)
    state = models.PositiveIntegerField('Estado', choices=STATE_CHOICES, default=0)
    was_canceled = models.BooleanField('Fue cancelada', default=False)

    def __unicode__(self):
        return u'{} {}'.format(self.importq, self.state)

    @property
    def parent(self):
        if hasattr(self, 'detail'):
            return self.detail.parent
        elif hasattr(self, 'detailquiniela'):
            return self.detailquiniela
        elif hasattr(self, 'detailcoupons'):
            return self.detailcoupons

        logger.error('BaseDetail with no parent')


class Detail(BaseDetail):
    bet = models.OneToOneField('Bet', related_name='detail')
    draw = models.ForeignKey('Draw', verbose_name='Sorteo', related_name='detail_set')
    ticket = models.OneToOneField('Ticket', blank=True, null=True, verbose_name='Ticket')

    def __unicode__(self):
        return u'{} {}'.format(self.bet, self.draw)

    @property
    def game(self):
        return self.draw.game

    @property
    def parent(self):
        if hasattr(self, 'detailquiniseis'):
            return self.detailquiniseis
        if hasattr(self, 'detailbrinco'):
            return self.detailbrinco
        if hasattr(self, 'detailloto5'):
            return self.detailloto5
        if hasattr(self, 'detailloto'):
            return self.detailloto

        logger.error('BaseDetail with no parent')

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.ticket = Ticket.objects.create()
        super(Detail, self).save(*args,**kwargs)


class DetailCoupons(BaseDetail):

    coupon = models.ForeignKey('Coupon', related_name='detailcoupon_set', limit_choices_to={'agency__isnull': False})
    bet = models.ForeignKey('Bet', related_name='detailcoupons_set')
    fraction_bought = models.PositiveIntegerField('Fracciones compradas')
    ticket = models.OneToOneField('Ticket', blank=True, null=True, verbose_name='Billete')
    prize_requested = models.BooleanField(default=False)

    def __unicode__(self):
        return u'{} {} {}'.format(self.coupon, self.bet, self.fraction_bought)

    @property
    def draw(self):
        return self.coupon.draw

    @property
    def game(self):
        return self.coupon.draw.game

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.ticket = Ticket.objects.create()
        super(DetailCoupons, self).save(*args,**kwargs)

    def to_string(self):
        if self.game.code == Game.CODE.LOTERIA:
            return u'Jugada de LOTERIA - {:0>5} - {} Fracciones'.format(
                self.coupon.number, self.fraction_bought
            )
        else:
            return u'Jugada de {} - {:0>5}'.format(
                self.game.name.upper(), self.coupon.number
            )

    def send_confirm_bet_email(self, request, ticket=None):
        """ Envia mail confirmando que la apuesta fue jugada.
        Adjunta ticket si no es None, si no envia url para solicitar ticket """

        profile = self.bet.user
        attachs = []
        urls = {}
        context = {
            'game': self.game,
            'agency': profile.agency,
            'user': profile.user,
            'preprinted': True,
            'ticket': ticket is not None,
        }

        if ticket is None:
            urls = dict(ticket=reverse('bet:request_ticket', kwargs={'id': self.ticket_id,
                                                                     'key': self.ticket.key}))
        else:
            ext = os.path.splitext(ticket.real.url)[1]
            attachs = [(u'{}-{}{}'.format(self.game.code, self.draw.number, ext),
                        ticket.real.read(), mimetypes.guess_type(ticket.real.url)[0])]

        profile.email_notification(request, USER_SETTINGS.MAIL_PLAYED_BET, 'emails/confirm_bet_email',
                                   context, attachments=attachs, urls=urls)


class DetailQuiniela(BaseDetail):
    bet = models.ForeignKey('Bet', related_name='detailquiniela_set')
    draws = models.ManyToManyField('DrawQuiniela', verbose_name='Sorteos', related_name='detail_set')

    number = models.CharField(max_length=5, verbose_name='Numero', validators=[
        RegexValidator('^[0-9]{1,5}$', message='Ingrese un número de 1 a 5 cifras'),
    ])
    location = models.PositiveIntegerField('Ubicación', validators=[
        MinValueValidator(1), MaxValueValidator(20)
    ])
    ticket = models.ForeignKey('Ticket', blank=True, null=True, verbose_name='Ticket')

    redoblona = models.OneToOneField('self', blank=True, null=True, related_name='apuesta')

    group = models.ForeignKey('QuinielaGroup', null=True, related_name='detail_set')

    @property
    def game(self):
        return self.draws.first().game

    @property
    def lotteries(self):
        return self.draws.order_by('quiniela__code').values_list('quiniela__name', flat=True)

    @property
    def get_type_display(self):
        return self.draws.first().get_type_display()

    def real_import(self, code=None, lot_winned=None):
        """ Obtiene el importe real apostado a cada loteria
         $10 en 3 loterías: $3.34, $3.33, $3.33
         $5 en 3 loterías: $1.67, $1.67, $1.66
        """

        print "********* CALCULO DEL IMPORTE ", code, (round(self.importq / self.draws.count(), 2)), self.draws.count(), self.importq

        if code is None:
            return round(self.importq / self.draws.count(), 2)

        importq = float(self.importq)
        count = self.draws.count()
        equal_parts = int(importq / count * 100) / 100.0
        remainder = int(math.ceil((importq - equal_parts * count) * 100))  # cents


        print "********* REMAIN DEL IMPORTE ", equal_parts, lot_winned

        if remainder == 0:
            return equal_parts

        lotteries = self.draws.order_by('quiniela__code')
        #codes = lotteries.values_list('quiniela__code', flat=True)

        lot_winned.sort()
        codes = lot_winned
        print "*********", codes, lot_winned
        print "********* REMAIN DEL IMPORTE ", codes, list(codes), code
        if list(codes).index(code) != None:
            return equal_parts

        lottery_index = list(codes).index(code) + 1

        #lottery_index = list(codes).index(code) + 1


        print "********* REMAIN DEL IMPORTE2 ", lottery_index, remainder, lotteries, codes, lottery_index, remainder

        #if lottery_index <= remainder:
        if 3 in codes:
            if code == 3:
                return equal_parts + 0.01
        else:
            if lottery_index == 1:
                return equal_parts + 0.01


        return equal_parts

    @property
    def draw_number(self):
        return self.draws.first().groups.get(province=self.bet.agency.province).number

    def get_location_display(self):
        if self.location == 1:
            return 'A la cabeza'
        return 'A los {}'.format(self.location)

    def to_string(self, include_name=True):
        if hasattr(self, 'apuesta'):
            return u''

        rdbn = ''
        if self.redoblona is not None:
            rdbn = ' RDBN {} {}'.format(self.redoblona.number, self.redoblona.get_location_display())
        codes = map(unicode, self.draws.values_list('quiniela__code', flat=True))

        name = u'Jugada de QUINIELA - ' if include_name else u''

        return u'{}${} al {} {}{} - {}'.format(
            name, self.importq, self.number, self.get_location_display(), rdbn, ', '.join(codes)
        )

    def clean(self):
        super(DetailQuiniela, self).clean()

        if self.importq != 0 and self.importq < QUINIELA_MIN_IMPORT:
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'El importe mínimo de apuesta es de ${}.'.format(QUINIELA_MIN_IMPORT)
                    ],
                })

        if (round(self.importq*100,2)) % 10 != 0:
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'El importe debe ser múltiplo de 10 cvos.'
                    ],
                })

        if self.redoblona is not None:
            if len(self.number) != 2 or len(self.redoblona.number) != 2:
                raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'Jugada no válida: Redoblona requiere dos números de dos cifras.'
                    ],
                })

            if self.location not in [1,5,10,20] or self.redoblona.location not in [1,5,10,20]:
                raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'Jugada no válida: Redoblona requiere ubicaciones 5, 10 o 20.'
                    ],
                })

            if self.location > self.redoblona.location:
                location = self.location
                number = self.number
                self.location = self.redoblona.location
                self.number = self.redoblona.number
                self.redoblona.location = location
                self.redoblona.number = number
                #raise ValidationError({
                #    NON_FIELD_ERRORS: [
                #        "Jugada no válida: La ubicación del primer número debe ser igual o menor que la del segundo.'
                #    ],
                #})

        # No puede apostar 1 sola cifra a los premios
        if len(self.number) == 1 and self.location > 5:
            raise ValidationError({
                    NON_FIELD_ERRORS: [
                        u'Puede apostar una cifra sólo hasta el quinto lugar.'
                    ],
            })

    def __unicode__(self):
        redoblona = ''
        if hasattr(self, 'apuesta'):
            redoblona = '(redoblona de %s)' %self.apuesta.pk
        elif self.redoblona:
            redoblona = '(con redoblona %s)' %self.redoblona.pk

        return u'{} - ${} {} {} {}'.format(self.pk,
                                             self.importq, self.number,
                                             self.get_location_display(),
                                             redoblona)


class DetailQuiniSeis(Detail):

    number1 = models.PositiveIntegerField('Numero 1', validators=[MaxValueValidator(settings.QUINI6_MAX_NUMBER)])
    number2 = models.PositiveIntegerField('Numero 2', validators=[MaxValueValidator(settings.QUINI6_MAX_NUMBER)])
    number3 = models.PositiveIntegerField('Numero 3', validators=[MaxValueValidator(settings.QUINI6_MAX_NUMBER)])
    number4 = models.PositiveIntegerField('Numero 4', validators=[MaxValueValidator(settings.QUINI6_MAX_NUMBER)])
    number5 = models.PositiveIntegerField('Numero 5', validators=[MaxValueValidator(settings.QUINI6_MAX_NUMBER)])
    number6 = models.PositiveIntegerField('Numero 6', validators=[MaxValueValidator(settings.QUINI6_MAX_NUMBER)])
    tra = models.BooleanField(default=True)
    rev = models.BooleanField(default=True)
    sie = models.BooleanField(default=True)

    @property
    def numbers(self):
        return [getattr(self, 'number'+str(i)) for i in range(1,7)]

    def to_string(self):
        mod = ['',' TRA'][self.tra]+['',' REV'][self.rev]+['',' SIE'][self.sie]
        return u'Jugada de QUINI6 - {:0>2} {:0>2} {:0>2} {:0>2} {:0>2} {:0>2} - {}'.format(
            self.number1, self.number2, self.number3, self.number4,
            self.number5, self.number6, mod
        )

    def __unicode__(self):
        return u'{} {} - {}'.format(self.pk, self.draw, self.to_string())


class DetailBrinco(Detail):

    number1 = models.PositiveIntegerField('Numero 1', validators=[MaxValueValidator(settings.BRINCO_MAX_NUMBER)])
    number2 = models.PositiveIntegerField('Numero 2', validators=[MaxValueValidator(settings.BRINCO_MAX_NUMBER)])
    number3 = models.PositiveIntegerField('Numero 3', validators=[MaxValueValidator(settings.BRINCO_MAX_NUMBER)])
    number4 = models.PositiveIntegerField('Numero 4', validators=[MaxValueValidator(settings.BRINCO_MAX_NUMBER)])
    number5 = models.PositiveIntegerField('Numero 5', validators=[MaxValueValidator(settings.BRINCO_MAX_NUMBER)])
    number6 = models.PositiveIntegerField('Numero 6', validators=[MaxValueValidator(settings.BRINCO_MAX_NUMBER)])

    TICKET_OPTIONS = dict(BaseDetail.TICKET_OPTIONS)
    TICKET_OPTIONS.update({'page-height':'7.5cm'})

    @property
    def numbers(self):
        return [getattr(self, 'number'+str(i)) for i in range(1,7)]

    def to_string(self):
        return u'Jugada de BRINCO - {:0>2} {:0>2} {:0>2} {:0>2} {:0>2} {:0>2}'.format(
            self.number1, self.number2, self.number3,
            self.number4, self.number5, self.number6
        )

    def __unicode__(self):
        return u'{} - {}'.format(self.draw, self.to_string())


class DetailLoto5(Detail):

    number1 = models.PositiveIntegerField('Numero 1', validators=[MaxValueValidator(settings.LOTO5_MAX_NUMBER)])
    number2 = models.PositiveIntegerField('Numero 2', validators=[MaxValueValidator(settings.LOTO5_MAX_NUMBER)])
    number3 = models.PositiveIntegerField('Numero 3', validators=[MaxValueValidator(settings.LOTO5_MAX_NUMBER)])
    number4 = models.PositiveIntegerField('Numero 4', validators=[MaxValueValidator(settings.LOTO5_MAX_NUMBER)])
    number5 = models.PositiveIntegerField('Numero 5', validators=[MaxValueValidator(settings.LOTO5_MAX_NUMBER)])

    TICKET_OPTIONS = dict(BaseDetail.TICKET_OPTIONS)
    TICKET_OPTIONS.update({'page-height':'7.5cm'})

    @property
    def numbers(self):
        return [getattr(self, 'number'+str(i)) for i in range(1,6)]

    def to_string(self):
        return u'Jugada de LOTO5 - {:0>2} {:0>2} {:0>2} {:0>2} {:0>2}'.format(
            self.number1, self.number2, self.number3,
            self.number4, self.number5
        )

    def __unicode__(self):
        return u'{} - {}'.format(self.draw, self.to_string())


class DetailLoto(Detail):

    number1 = models.PositiveIntegerField('Numero 1', validators=[MaxValueValidator(settings.LOTO_MAX_NUMBER)])
    number2 = models.PositiveIntegerField('Numero 2', validators=[MaxValueValidator(settings.LOTO_MAX_NUMBER)])
    number3 = models.PositiveIntegerField('Numero 3', validators=[MaxValueValidator(settings.LOTO_MAX_NUMBER)])
    number4 = models.PositiveIntegerField('Numero 4', validators=[MaxValueValidator(settings.LOTO_MAX_NUMBER)])
    number5 = models.PositiveIntegerField('Numero 5', validators=[MaxValueValidator(settings.LOTO_MAX_NUMBER)])
    number6 = models.PositiveIntegerField('Numero 6', validators=[MaxValueValidator(settings.LOTO_MAX_NUMBER)])

    extra1 = models.PositiveIntegerField('Extra 1', validators=[MaxValueValidator(settings.LOTO_MAX_EXTRA)])
    extra2 = models.PositiveIntegerField('Extra 2', validators=[MaxValueValidator(settings.LOTO_MAX_EXTRA)])

    tra = models.BooleanField('Tradicional', default=True)
    des = models.BooleanField('Desquite', default=True)
    sos = models.BooleanField('Sale o sale', default=True)

    #Detail.TICKET_OPTIONS.update({'page-height': '9cm'})

    @property
    def numbers(self):
        return [getattr(self, 'number'+str(i)) for i in range(1,7)]

    @property
    def extras(self):
        return [getattr(self, 'extra'+str(i)) for i in range(1,3)]

    def to_string(self):
        mod = ['',' TRA'][self.tra]+['',' DES'][self.des]+['',' SOS'][self.sos]
        return u'Jugada de LOTO - {:0>2} {:0>2} {:0>2} {:0>2} {:0>2} {:0>2} | {} {} - {}'.format(
            self.number1, self.number2, self.number3, self.number4,
            self.number5, self.number6, self.extra1, self.extra2, mod
        )

    def __unicode__(self):
        return u'{} {} - {}'.format(self.pk, self.draw, self.to_string())

#===============================================================================
# RESULTADOS
#===============================================================================

class Prize(models.Model):
    TYPE = enum(
        CASH=0,
        COUPON=1,
        OTHER=2
    )
    TYPE_CHOICES = (
        (TYPE.CASH, 'Dinero'),
        (TYPE.COUPON, u'Otro Billete'),
        (TYPE.OTHER, u'Otro Premio'),
    )

    type = models.SmallIntegerField(choices=TYPE_CHOICES, default=TYPE.CASH)
    value = RoundedDecimalField(max_digits=12, decimal_places=2, verbose_name='Premio', blank=True, null=True)
    text = models.CharField(max_length=100, verbose_name='Premio', blank=True)

    @property
    def get_prize(self):
        if self.type == Prize.TYPE.CASH:
            return self.value
        if self.type == Prize.TYPE.OTHER:
            return self.text
        return u'Otro Billete'

    def save(self, *args, **kwargs):
        if self.type == Prize.TYPE.COUPON:
            self.text = u'Otro Billete'

        super(Prize, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'{}'.format(self.get_prize)


class SingleExtract(models.Model):
    winners = models.PositiveIntegerField('Ganadores')
    prize = models.OneToOneField('Prize', blank=True, null=True)

    @property
    def get_numbers(self):
        result = []
        if hasattr(self, 'quini6_ext'):
            result += self.quini6_ext.tra.get_numbers
            result += self.quini6_ext.tra2.get_numbers
            result += self.quini6_ext.rev.get_numbers
        return result

    @property
    def get_prize(self):
        return self.prize.get_prize

    def __unicode__(self):
        return u'({}) {} ganadores, premio {}'.format(self.pk, self.winners, self.prize)


class RowExtract(models.Model):

    hits = models.CharField('Aciertos', max_length=20)
    winners = models.PositiveIntegerField('Ganadores')
    order = models.PositiveIntegerField('Orden')
    results = models.ForeignKey('ResultsSet', related_name='extract_set')
    prize = models.OneToOneField('Prize', blank=True, null=True)

    def __unicode__(self):
        return u'{} aciertos, {} ganadores, premio {}, order {}'.format(self.hits, self.winners,
                                                                        self.prize.get_prize, self.order)

    @property
    def get_prize(self):
        return self.prize.get_prize

    @property
    def prize_type(self):
        return self.prize.type


class TbgRowExtract(RowExtract):

    coupon = models.ForeignKey('Coupon')

    def __unicode__(self):
        return u'{}, premio {}'.format(self.coupon, self.prize.get_prize)


class CouponExtract(models.Model):
    """ Premios por numero de Billete """
    number = models.CharField('Nro. Billete', max_length=40)
    results = models.ForeignKey('PreprintedResults', related_name='coupon_extract_set')
    prize = models.OneToOneField('Prize')

    @property
    def draw(self):
        return self.results.parent.draw

    def __unicode__(self):
        return '{} {} {}'.format(self.draw, self.number, self.prize.get_prize)


class TbgCouponExtract(models.Model):

    draw = models.ForeignKey('DrawPreprinted', related_name='coupon_extract_set')
    number = models.PositiveIntegerField('DNI')
    prize = models.OneToOneField('Prize')

    @property
    def get_prize(self):
        return self.prize.get_prize

    @property
    def prize_type(self):
        return self.prize.type

    def __unicode__(self):
        return '{} {} {}'.format(self.draw, self.number, self.prize.get_prize)


class TbgEndingExtract(models.Model):

    coupon = models.OneToOneField('Coupon', null=True)
    prize = models.OneToOneField('Prize')
    description = models.CharField('Descripcion', max_length=40, blank=True, null=True)
    round = models.IntegerField('Ronda', default=1, null=True, blank=True)
    chance = models.CharField('Chance', max_length=1, null=True, blank=True)
    ending = models.BooleanField('Termination', default=True)

    @property
    def get_prize(self):
        return self.prize.get_prize

    @property
    def prize_type(self):
        return self.prize.type

    def __unicode__(self):
        return '{} {} {}'.format(self.coupon.draw, self.coupon.number[-2:], self.get_prize)


class ResultsSet(models.Model):

    @property
    def parent(self):
        if hasattr(self, 'resultssetstar'):
            return self.resultssetstar

        if hasattr(self, 'resultsset5'):
            return self.resultsset5.parent

        if hasattr(self, 'variableresultsset'):
            return self.variableresultsset

        return []

    @property
    def get_numbers(self):
        parent = self.parent
        i = 1
        numbers = []
        while hasattr(parent, 'number{}'.format(i)):
            numbers.append(getattr(parent, 'number{}'.format(i)))
            i += 1
        return numbers


class VariableResultsSet(ResultsSet):
    numbers = models.CommaSeparatedIntegerField(max_length=152) # hasta 50 numeros de 2 cifras

    @property
    def get_numbers(self):
        if self.numbers:
            return map(int, self.numbers.split(','))
        return []


class ResultsSetStar(ResultsSet):
    #TOTOBINGO
    star = models.PositiveIntegerField('Bolilla Estrella', validators=[MinValueValidator(1),
                                                                                    MaxValueValidator(24)])

    @property
    def get_numbers(self):
        return [self.star]


class ResultsSet5(ResultsSet):
    number1 = models.PositiveIntegerField('Numero 1', validators=[MaxValueValidator(99999)])
    number2 = models.PositiveIntegerField('Numero 2', validators=[MaxValueValidator(99999)])
    number3 = models.PositiveIntegerField('Numero 3', validators=[MaxValueValidator(99999)])
    number4 = models.PositiveIntegerField('Numero 4', validators=[MaxValueValidator(99999)])
    number5 = models.PositiveIntegerField('Numero 5', validators=[MaxValueValidator(99999)])

    @property
    def parent(self):
        if hasattr(self, 'resultsset6'):
            return self.resultsset6.parent

        return self

    def __unicode__(self):
        return u'{:0>2} {:0>2} {:0>2} {:0>2} {:0>2}'.format(self.number1, self.number2, self.number3,
                                           self.number4, self.number5)


class ResultsSet6(ResultsSet5):
    number6 = models.PositiveIntegerField('Numero 6', validators=[MaxValueValidator(99999)])

    @property
    def parent(self):
        if hasattr(self, 'resultsset6extra'):
            return self.resultsset6extra

        if hasattr(self, 'resultsset12'):
            return self.resultsset12.parent

        return self

    def __unicode__(self):
        return u'{} {:0>2}'.format(super(ResultsSet6, self).__unicode__(), self.number6)


class ResultsSet6Extra(ResultsSet6):
    #Loto: 6 numeros mas 2 extra

    extra1 = models.PositiveIntegerField('Extra 1', validators=[MaxValueValidator(9)])
    extra2 = models.PositiveIntegerField('Extra 2', validators=[MaxValueValidator(9)])

    @property
    def get_extras(self):
        return [getattr(self, 'extra'+str(i)) for i in range(1,3)]

    def __unicode__(self):
        return u'{} {:0>2} {:0>2}'.format(super(ResultsSet6Extra, self).__unicode__(), self.extra1, self.extra2)


class ResultsSet12(ResultsSet6):
    #TOTOBINGO
    number7 = models.PositiveIntegerField('Numero 7', validators=[MaxValueValidator(99999)])
    number8 = models.PositiveIntegerField('Numero 8', validators=[MaxValueValidator(99999)])
    number9 = models.PositiveIntegerField('Numero 9', validators=[MaxValueValidator(99999)])
    number10 = models.PositiveIntegerField('Numero 10', validators=[MaxValueValidator(99999)])
    number11 = models.PositiveIntegerField('Numero 11', validators=[MaxValueValidator(99999)])
    number12 = models.PositiveIntegerField('Numero 12', validators=[MaxValueValidator(99999)])

    @property
    def parent(self):
        if hasattr(self, 'resultsset15'):
            return self.resultsset15.parent

        return self


class ResultsSet15(ResultsSet12):
    #TELEKINO
    number13 = models.PositiveIntegerField('Numero 13', validators=[MaxValueValidator(99999)])
    number14 = models.PositiveIntegerField('Numero 14', validators=[MaxValueValidator(99999)])
    number15 = models.PositiveIntegerField('Numero 15', validators=[MaxValueValidator(99999)])

    @property
    def parent(self):
        if hasattr(self, 'resultsset20'):
            return self.resultsset20

        return self


class ResultsSet20(ResultsSet15):
    number16 = models.PositiveIntegerField('Numero 16', validators=[MaxValueValidator(99999)])
    number17 = models.PositiveIntegerField('Numero 17', validators=[MaxValueValidator(99999)])
    number18 = models.PositiveIntegerField('Numero 18', validators=[MaxValueValidator(99999)])
    number19 = models.PositiveIntegerField('Numero 19', validators=[MaxValueValidator(99999)])
    number20 = models.PositiveIntegerField('Numero 20', validators=[MaxValueValidator(99999)])


class Quini6Results(models.Model):
    draw = models.OneToOneField('Draw', verbose_name='Sorteo', related_name='quini6_results')
    tra = models.OneToOneField('ResultsSet6', verbose_name='Tradicional 1', related_name='quini6_tra')
    tra2 = models.OneToOneField('ResultsSet6', verbose_name='Tradicional 2', related_name='quini6_tra2')
    rev = models.OneToOneField('ResultsSet6', verbose_name='Revancha', related_name='quini6_rev')
    sie = models.OneToOneField('ResultsSet6', verbose_name='Siempre Sale', related_name='quini6_sie')

    ext = models.OneToOneField('SingleExtract', verbose_name='Premio Extra', related_name='quini6_ext')

    def __unicode__(self):
        if self.draw:
            return u'{}'.format(self.draw)
        else:
            return u'Empty Quini6Results'


class Loto5Results(models.Model):
    draw = models.OneToOneField('Draw', verbose_name='Sorteo', related_name='loto5_results')
    tra = models.OneToOneField('ResultsSet5', verbose_name='Tradicional', related_name='loto5_results')

    def __unicode__(self):
        if self.draw:
            return u'{}'.format(self.draw)
        else:
            return u'Empty Loto5Results'


class BrincoResults(models.Model):
    draw = models.OneToOneField('Draw', verbose_name='Sorteo', related_name='brinco_results')
    tra = models.OneToOneField('ResultsSet6', verbose_name='Tradicional', related_name='brinco_results')
    tra2 = models.OneToOneField('ResultsSet6', verbose_name='Tradicional 2', related_name='brinco_results_2', null=True, blank=True)

    def __unicode__(self):
        if self.draw:
            return u'{}'.format(self.draw)
        else:
            return u'Empty BrincoResults'


class LotoResults(models.Model):
    draw = models.OneToOneField('Draw', verbose_name='Sorteo', related_name='loto_results')
    tra = models.OneToOneField('ResultsSet6Extra', verbose_name='Tradicional', related_name='loto_tra')
    des = models.OneToOneField('ResultsSet6Extra', verbose_name='Desquite', related_name='loto_des')
    sos = models.OneToOneField('ResultsSet6', verbose_name='Sale o Sale', related_name='loto_sos')

    def __unicode__(self):
        if self.draw:
            return u'{}'.format(self.draw)
        else:
            return u'Empty LotoResults'


class PreprintedResults(models.Model):

    @property
    def parent(self):
        if hasattr(self, 'telekinoresults'):
            return self.telekinoresults
        if hasattr(self, 'loteriaresults'):
            return self.loteriaresults
        if hasattr(self, 'totobingoresults'):
            return self.totobingoresults
        if hasattr(self, 'telebingoresults'):
            return self.telebingoresults


class TelekinoResults(PreprintedResults):
    draw = models.OneToOneField('DrawPreprinted', verbose_name='Sorteo', related_name='telekino_results')
    tel = models.OneToOneField('ResultsSet15', verbose_name='Telekino', related_name='telekino_tel')
    rek = models.OneToOneField('ResultsSet15', verbose_name='Rekino', related_name='telekino_rek')

    def __unicode__(self):
        if self.draw:
            return u'{}'.format(self.draw)
        else:
            return u'Empty TelekinoResults'


class LoteriaResults(PreprintedResults):

    draw = models.OneToOneField('DrawPreprinted', verbose_name='Sorteo', related_name='loteria_results')
    ord = models.OneToOneField('ResultsSet20', verbose_name='Ordinaria', related_name='loteria_ord')
    progresion = models.PositiveSmallIntegerField(validators=[MaxValueValidator(11)])

    def __unicode__(self):
        if self.draw:
            return u'{}'.format(self.draw)
        else:
            return u'Empty LoteriaResults'


class TotobingoResults(PreprintedResults):
    draw = models.OneToOneField('DrawPreprinted', verbose_name='Sorteo', related_name='totobingo_results')
    gog = models.OneToOneField('VariableResultsSet', verbose_name=u'Ganá o Ganá', related_name='totobingo')
    poz = models.OneToOneField('ResultsSet12', verbose_name='Pozo Millonario', related_name='totobingo')
    star = models.OneToOneField('ResultsSetStar', verbose_name='Bolilla Estrella', related_name='totobingo')


class TelebingoResults(PreprintedResults):
    round = models.OneToOneField('Round', related_name='results')

    line = models.OneToOneField('VariableResultsSet', related_name='tbg_line_result')
    bingo = models.OneToOneField('VariableResultsSet', related_name='tbg_bingo_result')

    @property
    def draw(self):
        return self.round.draw


class QuinielaResults(models.Model):
    draw = models.OneToOneField('DrawQuiniela', verbose_name='Sorteo', related_name='quiniela_results')
    res = models.OneToOneField('ResultsSet20', verbose_name='Quiniela', related_name='quiniela')


class GameTax(models.Model):

    province = models.ForeignKey('Province')
    game = models.ForeignKey('Game')

    nat_tax = RoundedDecimalField(max_digits=5, decimal_places=2, verbose_name='Impuesto Nacional',
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    prov_tax = RoundedDecimalField(max_digits=5, decimal_places=2, verbose_name='Impuesto Provincial',
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    min_nat = RoundedDecimalField(max_digits=8, decimal_places=2, verbose_name='Minimo Nacional',
        validators=[MinValueValidator(0.0)])
    min_prov = RoundedDecimalField(max_digits=8, decimal_places=2, verbose_name='Minimo Provincial',
        validators=[MinValueValidator(0.0)])

    min = RoundedDecimalField(max_digits=8, decimal_places=2, verbose_name='Valor min para cobrar en Loteria.',
                              validators=[MinValueValidator(0.0)])

    class Meta:
        unique_together = (('province', 'game'),)

    def __unicode__(self):
        return u'{} - {}'.format(self.province, self.game)


