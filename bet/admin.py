#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.apps import apps
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from bet import models

betapp = apps.get_app_config('bet')
for model in betapp.models.values():
    if model in [models.BaseDraw, models.Draw, models.DrawPreprinted, models.DrawQuiniela, models.LotteryTime,
                 models.Game, models.AbstractMovement, models.Bet, models.AgencyDevices, models.Quiniela,
                 models.UserProfile, models.DetailQuiniela, models.DetailQuiniSeis, models.DetailBrinco,
                 models.DetailLoto5, models.DetailLoto, models.Detail,
                 models.DetailCoupons, models.Ticket, models.PrizeMovement, models.WinnerQuiniela,
                 models.DrawTime, models.LoteriaPrizeRow, models.UserSetting, models.Setting]:
        continue
    admin.site.register(model)


class BaseDrawAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_draw'
    list_filter = ('date_draw', 'game')
    list_display = ('id', 'game', 'date_draw', 'number', 'state')

admin.site.register(models.BaseDraw, BaseDrawAdmin)
admin.site.register(models.Draw, BaseDrawAdmin)
admin.site.register(models.DrawPreprinted, BaseDrawAdmin)

class DrawQuinielaAdmin(admin.ModelAdmin):
    list_display = ('date_draw', 'quiniela', 'type', 'state')
    list_filter = ('date_draw', 'quiniela', 'type')

admin.site.register(models.DrawQuiniela, DrawQuinielaAdmin)

class LotteryTimeAdmin(admin.ModelAdmin):
    list_filter = ('quiniela', 'type')
    list_display = ('quiniela', 'type', 'draw_time', 'draw_limit_agency', 'draw_limit')


admin.site.register(models.LotteryTime, LotteryTimeAdmin)

UserAdmin.list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class GameAdmin(admin.ModelAdmin):
    list_filter = ('type',)
    list_display = ('name', 'code')

#admin.site.unregister(models.Game)
admin.site.register(models.Game, GameAdmin)


class AbstractMovementAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ('code', 'user')
    list_display = ('user', 'code', 'amount', 'date', 'state')

#admin.site.unregister(models.AbstractMovement)
admin.site.register(models.AbstractMovement, AbstractMovementAdmin)


class BetAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_bet'
    list_filter = ('user', 'agency')
    list_display = ('user', 'date_bet', 'agency')

#admin.site.unregister(models.Bet)
admin.site.register(models.Bet, BetAdmin)

class AgencyDevicesAdmin(admin.ModelAdmin):
    list_filter = ('agency',)
    list_display = ('agency', 'deviceid', 'devicegsmid')

#admin.site.unregister(models.AgencyDevices)
admin.site.register(models.AgencyDevices, AgencyDevicesAdmin)


class QuinielaAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

#admin.site.unregister(models.Quiniela)
admin.site.register(models.Quiniela, QuinielaAdmin)


class UserProfileAdmin(admin.ModelAdmin):
    list_filter = ('province', 'agency')
    list_display = ('user', 'agency', 'dni', 'province', 'device_os', 'saldo', 'playtoday')

#admin.site.unregister(models.UserProfile)
admin.site.register(models.UserProfile, UserProfileAdmin)


class DetailQuinielaAdmin(admin.ModelAdmin):
    list_filter = ('state',)
    list_display = ('user', 'bet_id', 'agency', 'number', 'location', 'importq', 'state')

    def user(self, instance):
        return instance.bet.user.user.get_full_name()

    def agency(self, instance):
        return instance.bet.agency.name

    def bet_id(self, instance):
        return instance.bet.id

#admin.site.unregister(models.DetailQuiniela)
admin.site.register(models.DetailQuiniela, DetailQuinielaAdmin)


class NonprintedDetailAdmin(admin.ModelAdmin):
    list_filter = ('state',)
    list_display = ('user', 'bet_id', 'draw_link', 'agency', 'ticket_link', 'state')

    def user(self, instance):
        return instance.bet.user.user.get_full_name()

    def ticket_link(self, obj):
        return u"<a href='/admin/bet/ticket/%s/'>%s</a>" %(obj.ticket.id, obj.ticket.id)
    ticket_link.short_description = 'Ticket'
    ticket_link.allow_tags = True

    def draw_link(self, obj):
        return u"<a href='/admin/bet/draw/%s/'>%s</a>" %(obj.draw.id, obj.draw.date_draw)
    draw_link.short_description = 'Draw'
    draw_link.allow_tags = True

    def agency(self, instance):
        return instance.bet.agency.name

    def bet_id(self, instance):
        return instance.bet.id

#admin.site.unregister(models.DetailQuiniela)
admin.site.register(models.DetailQuiniSeis, NonprintedDetailAdmin)
admin.site.register(models.DetailBrinco, NonprintedDetailAdmin)
admin.site.register(models.DetailLoto, NonprintedDetailAdmin)
admin.site.register(models.DetailLoto5, NonprintedDetailAdmin)


class DetailAdmin(admin.ModelAdmin):
    list_filter = ('state',)
    list_display = ('user', 'bet_id', 'game', 'draw', 'agency', 'importq', 'state')

    def user(self, instance):
        return instance.bet.user.user.get_full_name()

    def agency(self, instance):
        return instance.bet.agency.name

    def game(self, instance):
        return instance.draw.game

    def draw(self, instance):
        return str(instance.draw.id)

    def bet_id(self, instance):
        return instance.bet.id

#admin.site.unregister(models.Detail)
admin.site.register(models.Detail, DetailAdmin)


class PreprintedDetailAdmin(NonprintedDetailAdmin):
    list_display = ('user', 'bet_id', 'coupon_number', 'draw_link', 'agency', 'ticket_link', 'state')

    def draw_link(self, obj):
        return u"<a href='/admin/bet/drawpreprinted/%s/'>%s (%s)</a>" %(obj.draw.id, obj.draw.game.name, obj.draw.date_draw.date())
    draw_link.short_description = 'Draw'
    draw_link.allow_tags = True

    def ticket_link(self, obj):
        return u"<a href='/admin/bet/ticket/%s/'>%s</a>" %(obj.ticket.id, obj.ticket.id)
    ticket_link.short_description = 'Ticket'
    ticket_link.allow_tags = True

    def coupon_number(self, instance):
        return instance.coupon.number

admin.site.register(models.DetailCoupons, PreprintedDetailAdmin)


class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'detail_id', 'get_requested_display')

    def get_requested_display(self, instance):
        return instance.get_requested_display()
    get_requested_display.short_description = 'Requested'

    def game(self, instance):
        details = instance.get_details
        if details:
            return details[0].game.name
        return None

    def detail_id(self, instance):
        details = instance.get_details
        if details:
            return details[0].id
        return None


#admin.site.unregister(models.Ticket)
admin.site.register(models.Ticket, TicketAdmin)

"""
class QuinielaGroupAdmin(admin.ModelAdmin):
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "draws":
            kwargs["queryset"] = models.DrawQuiniela.objects.filter(type=1)
        return super(QuinielaGroupAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


#admin.site.unregister(models.QuinielaGroup)
admin.site.register(models.QuinielaGroup, QuinielaGroupAdmin)
"""


class PrizeMovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'state', 'winner_link')

    def winner_link(self, obj):
        return u"<a href='/admin/bet/winner/%s/'>%s</a>" %(obj.winner.id, obj.winner.id)
    winner_link.short_description = 'Winner'
    winner_link.allow_tags = True

admin.site.register(models.PrizeMovement, PrizeMovementAdmin)


class WinnerQuinielaAdmin(admin.ModelAdmin):
    list_display = ('id', 'notif', 'detail', 'draw', 'info', 'prize', 'hits')

admin.site.register(models.WinnerQuiniela, WinnerQuinielaAdmin)


class DrawTimeAdmin(admin.ModelAdmin):
    list_filter = ('game',)
    list_display = ('game', 'week_day', 'draw_time')


#admin.site.unregister(models.DrawTime)
admin.site.register(models.DrawTime, DrawTimeAdmin)


class LoteriaPrizeRowAdmin(admin.ModelAdmin):
    list_display = ('month', 'code', 'get_prize')
    list_filter = ('month',)

    def get_prize(self, instance):
        return instance.prize.get_prize

#admin.site.unregister(models.DrawTime)
admin.site.register(models.LoteriaPrizeRow, LoteriaPrizeRowAdmin)


class UserSettingAdmin(admin.ModelAdmin):
    list_display = ('profile', 'setting', 'value')
    list_filter = ('profile', 'setting')


#admin.site.unregister(models.DrawTime)
admin.site.register(models.UserSetting, UserSettingAdmin)


class SettingAdmin(admin.ModelAdmin):
    list_display = ('get_setting_display', 'default')

    def get_setting_display(self, instance):
        return instance.get_code_display()

#admin.site.unregister(models.DrawTime)
admin.site.register(models.Setting, SettingAdmin)

class ChanceInline(admin.TabularInline):
    model = models.Chance
    ordering = ('round', 'letter')
    extra = 0

class CouponAdmin(admin.ModelAdmin):
    inlines = [
        ChanceInline,
    ]
    list_filter = ('draw__game', 'agency', 'draw__date_draw', 'draw__number')
    list_display = ('id', 'number', 'draw', 'agency')

    def get_inline_instances(self, request, obj=None):
        if obj is None or not obj.draw.game.code.startswith('telebingo'):
            return []
        return super(CouponAdmin, self).get_inline_instances(request, obj)

admin.site.unregister(models.Coupon)
admin.site.register(models.Coupon, CouponAdmin)


class ChanceAdmin(admin.ModelAdmin):
    model = models.Chance
    list_filter = ('coupon__draw__game',)


admin.site.unregister(models.Chance)
admin.site.register(models.Chance, ChanceAdmin)
