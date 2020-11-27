#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

from spyne.server.django import DjangoView

from bet import views, models
from bet.webservices import tcargo_app

PREPRINTED_CODES = '|'.join([code for (code,) in models.Game.objects.\
                            filter(type=models.Game.TYPE.PREPRINTED).values_list('code')])

NONPRINTED_CODES = '|'.join([code for (code,) in models.Game.objects.\
                            filter(type=models.Game.TYPE.NONPRINTED).\
                            exclude(code=models.Game.CODE.QUINIELA).values_list('code')])

DATE_REGEXP = '(?P<date_str>\d{4}-\d{1,2}-\d{1,2})'

urlpatterns = patterns('',
    url(r'^$', views.games, name='home'),
    url(r'^games_login/$', views.games_login, name='games_login'),

    url(r'^games/$', views.games, name='games'),





    url(r'^terminos_y_condiciones/$', views.terminos_y_condiciones, name='terminos_y_condiciones'),
    url(r'^como_jugar/$', views.como_jugar, name='como_jugar'),
    url(r'^FAQ/$', views.FAQ, name='FAQ'),
    url(r'^politicas/$', views.politicas, name='politicas'),

    url(r'^get_preferences_charge/$', views.get_preferences_charge, name='get_preferences_charge'),


    url(r'^users/$', views.users, name='users'),
    url(r'^user_profile_saldo/$', views.user_profile_saldo, name='user_profile_saldo'),

    url(r'^terms/$', views.terms, name='terms'),
    url(r'^como_se_juega/$', views.como_se_juega, name='como_se_juega'),


    url(r'^user/(\d+)/$', views.user, name='user'),
    url(r'^edit_user/(\d+)/$', views.edit_user, name='edit_user'),

    url(r'^payments/$', views.payments, name='payments'),
    url(r'^movements_all/$', views.movements_all, name='movements_all'),



    url(r'^update_payment/(\d+)/$', views.update_payment, name='update_payment'),
    url(r'^approve_withdrawal/(\d+)/$', views.approve_withdrawal, name='approve_withdrawal'),
    url(r'^movement_detail/(\d+)/$', views.movement_detail, name='movement_detail'),

    url(r'^bets/$', views.bets, name='bets'),
    url(r'^bet_detail/(\d+)/(\w+)/$', views.bet_detail, name='bet_detail'),

    url(r'^get_barcode_image/$', views.get_barcode_image, name='get_barcode_image'),


    #================================ SETTINGS ========================================

    url(r'^loteria_prizes/$', views.loteria_prizes, name='loteria_prizes'),
    url(r'^loteria_prizes/(\d{4})/(\d{1,2})/$', views.loteria_prizes, name='loteria_prizes'),
    url(r'^loteria_prizes/(\d{4})/(\d{1,2})/(\d+)/$', views.loteria_prizes, name='loteria_prizes'),

    url(r'^game_taxes/$', views.game_taxes, name='game_taxes'),
    url(r'^bet_commissions/$', views.bet_commissions, name='bet_commissions'),

    url(r'^promotions/$', views.promotions, name='promotions'),
    url(r'^pomotion/(\d+)/$', views.promotion, name='promotion'),
    url(r'^pomotion/$', views.promotion, name='promotion'),

    url(r'^get_promotion_draws/(?P<game_id>\d+)/(?P<promotion_id>\d+)/$', views.get_promotion_draws, name='get_promotion_draws'),
    url(r'^get_promotion_draws/(?P<game_id>\d+)/$', views.get_promotion_draws, name='get_promotion_draws'),

    #================================ AGENCIES ========================================

    url(r'^agencies/$', views.agencies, name='agencies'),
    url(r'^edit_agency/(\d+)/$', views.edit_agency, name='edit_agency'),
    url(r'^edit_agency/$', views.edit_agency, name='edit_agency'),
    url(r'^agency/(\d+)/$', views.agency, name='agency'),
    url(r'^agency/(\d+)/commission/$', views.agency_commission, name='agency_commission'),

    url(r'^movements/$', views.agency, name='agency'),
    url(r'^agenmov_detail/(\d+)/$', views.agen_movement_detail, name='agen_movement_detail'),

    url(r'^movements_all/$', views.movements_all, name='movements_all'),



    #================================ DRAWS ========================================
    url(r'^(%s)/(\d+)/draw_edit/$' % NONPRINTED_CODES, views.draw_nonprinted, name='draw_nonprinted_edit'),
    url(r'^(%s)/draw_add/$' % NONPRINTED_CODES, views.draw_nonprinted, name='draw_nonprinted_add'),

    url(r'^(%s)/(\d+)/draw_edit/$' %PREPRINTED_CODES, views.draw_preprinted_edit, name='draw_preprinted_edit'),
    url(r'^(%s)/draw_add/$' %PREPRINTED_CODES, views.draw_preprinted_add, name='draw_preprinted_add'),

    url(r'^quiniela/(\d+)/draw_edit/$', views.draw_quiniela, name='draw_quiniela_edit'),
    url(r'^quiniela/draw_add/$', views.draw_quiniela, name='draw_quiniela_add'),

    url(r'^coupons/([a-zA-Z0-9]{1,40})/$', views.coupons, name='coupons'),
    url(r'^admin_coupons/(\d+)/$', views.admin_coupons, name='admin_coupons'),
    url(r'^telebingo_coupons/([a-zA-Z0-9]{1,40})/$', views.telebingo_coupons, name='telebingo_coupons'),
    url(r'^import_coupons/(?P<pk>[0-9]+)/$', views.ImportCouponsModal.as_view(), name='import_coupons'),
    url(r'^coupon_html/(\d+)/$', views.coupon_html, name='coupon_html'),
    url(r'^get_coupons_numbers/exclude_sold/', views.get_coupons_numbers, {'exclude_sold': False}),
    url(r'^get_coupons_numbers/', views.get_coupons_numbers),


    url(r'^get_coupons_numbers_range/', views.get_coupons_numbers_range),
    url(r'^make_coupons_range/', views.make_coupons_range),


    url(r'^get_virtual_coupon/', views.get_virtual_coupon),
    url(r'^send_push/$', views.send_push, name='send_push'),


    url(r'^draws/$', views.draws, name='draws'),
    url(r'^old_draws/$', views.old_draws, name='old_draws'),

    url(r'^draws_quiniela/$', views.draws_quiniela, name='draws_quiniela'),
    url(r'^old_quinielas/$', views.old_quinielas, name='old_quinielas'),
    #=============================== ENDDRAW =======================================

    url(r'^request_ticket/(?P<id>[0-9]+)/(?P<key>\w+)/$',
        views.request_ticket, name='request_ticket'),

                       #=============================== RESULTS =======================================
    url(r'^quiniela/(\d+)/results/$', views.quiniela_results, name='quiniela_results'),
    url(r'^quiniela/(\d+)/results/(\d+)/$', views.quiniela_results, name='quiniela_results'),

    url(r'^quiniela/%s/number/(?P<lottery>\d+)/(?P<type>\d+)/$' %DATE_REGEXP,
        views.quiniela_number, name='quiniela_number'),
    #url(r'^quiniela/delete_results/$', views.delete_quiniela_results, name='delete_quiniela_results'),

    url(r'^quini6/(\d+)/results/$', views.quini6_results, name='quini6_results'),
    url(r'^loto/(\d+)/results/$', views.loto_results, name='loto_results'),
    url(r'^loto5/(\d+)/results/$', views.loto5_results, name='loto5_results'),
    url(r'^brinco/(\d+)/results/$', views.brinco_results, name='brinco_results'),

    url(r'^telekino/(\d+)/results/$', views.telekino_results, name='telekino_results'),
    url(r'^totobingo/(\d+)/results/$', views.totobingo_results, name='totobingo_results'),
    url(r'^loteria/(\d+)/results/$', views.loteria_results, name='loteria_results'),
    url(r'^telebingocordobes/(\d+)/results/$', views.telebingo_results, name='telebingocordobes_results'),
    url(r'^telebingocorrentino/(\d+)/results/$', views.telebingo_results, name='telebingocorrentino_results'),
    url(r'^telebingoneuquino/(\d+)/results/$', views.telebingo_results, name='telebingoneuquino_results'),

    url(r'^telebingo_la_pampa1_results/(\d+)/results/$', views.telebingo_results, name='telebingo_la_pampa1_results'),


    url(r'^telebingo_sc_results/(\d+)/results/$', views.telebingo_results, name='telebingo_sc_results'),
    url(r'^telebingo_rebingo_sc_results/(\d+)/results/$', views.telebingo_results, name='telebingo_rebingo_sc_results'),
    url(r'^telebingo_mini_sc_results/(\d+)/results/$', views.telebingo_results, name='telebingo_minibingo_sc_results'),

    url(r'^telebingo_mibingo_ca_results/(\d+)/results/$', views.telebingo_results, name='telebingo_minibingo_sc_results'),

    url(r'^telebingo_lp_results/(\d+)/results/$', views.telebingo_results, name='telebingo_lp_results'),
    url(r'^telebingo_rebingo_lp_results/(\d+)/results/$', views.telebingo_results, name='telebingo_rebingo_lp_results'),
    url(r'^telebingo_mini_lp_results/(\d+)/results/$', views.telebingo_results, name='telebingo_minibingo_lp_results'),


    url(r'^send_extract/(\d+)/$', views.send_extract, name='send_extract'),
    url(r'^send_quiniela_extract/(\d+)/$', views.send_quiniela_extract, name='send_quiniela_extract'),

    #================================== WINNERS ======================================

    url(r'^(\d+)/winners/$', views.nonprinted_winners, name='nonprinted_winners'),
    url(r'^loteria/(\d+)/winners/$', views.loteria_winners, name='loteria_winners'),
    url(r'^telebingo/(\d+)/winners/$', views.telebingo_winners, name='telebingo_winners'),
    url(r'^quiniela/(\d+)/winners/$', views.quiniela_winners, name='quiniela_winners'),

    #url(r'^prize_requests/$', views.prize_requests, name='prize_requests'),
    #url(r'^prize_request/(\d+)/$', views.prize_request, name='prize_request'),

#================================== QUINIELA ======================================

    url(r'^quinielas/$', views.quinielas, name='quinielas'),

    url(r'^quiniela/$', views.quiniela_group, name='quiniela'),
    url(r'^quiniela/(\d+)/$', views.quiniela_group, name='quiniela'),
    url(r'^get_draws/(%s)/(?P<province_id>\d+)/(?P<group_id>\d+)/$' %DATE_REGEXP, views.get_draws, name='get_draws'),
    url(r'^get_draws/(%s)/(?P<province_id>\d+)/$' %DATE_REGEXP, views.get_draws, name='get_draws'),
    url(r'^get_draws/(?P<tipo>\d+)/(%s)/(?P<province_id>\d+)/(?P<group_id>\d+)/$' %DATE_REGEXP, views.get_draws, name='get_draws'),
    url(r'^get_draws/(?P<tipo>\d+)/(%s)/(?P<province_id>\d+)/$' %DATE_REGEXP, views.get_draws, name='get_draws'),

    url(r'^get_quinielas/$', views.get_quinielas_by_provice, name='get_quinielas_by_provice'),
    url(r'^get_quinielas/(\d+)/$', views.get_quinielas_by_provice, name='get_quinielas_by_provice'),

    url(r'^lottery_time/$', views.lottery_time, name='lottery_time'),

    url(r'^provinces/$', views.provinces, name='provinces'),

    #================================ ENDQUINIELA ======================================

    url(r'^extract/(\d+)/$', views.create_extract, name='extract'),
    url(r'^extract/(\d+)/html/$', views.extract_html, name='extract_html'),

    url(r'^extract_group/(\d+)/$', views.create_group_extract, name='extract_group'),
    url(r'^extract_group/(\d+)/html/$', views.extract_group_html, name='extract_group_html'),

    url(r'^faketicket/(\d+)/$', views.faketicket, name='faketicket'),
    url(r'^faketicket/(\d+)/html/$', views.faketicket_html, name='faketicket'),

    url(r'^fix/$', views.fix),  #TODO! DELETE
    url(r'^prod2desa/$', views.prod2desa),
    url(r'^extract_email/(\d+)/$', views.extract_email),
    url(r'^extract_email/(\d+)/email$', views.extract_email, {'email': True}),

    url(r'^android_error/$', views.android_error),

    url(r'^wsdl/$', DjangoView.as_view(application=tcargo_app, cache_wsdl=False)),
    url(r'^mp_notification/$', views.mp_notification),
    url(r'^mp_sandbox/$', views.mp_sandbox),
)

