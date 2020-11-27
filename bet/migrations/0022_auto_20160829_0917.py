# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def migrate_tbg_results(apps, schema_editor):
    TelebingoOldResults = apps.get_model("bet", "TelebingoOldResults")
    TelebingoResults = apps.get_model("bet", "TelebingoResults")
    TbgCouponExtract = apps.get_model("bet", "TbgCouponExtract")
    CouponExtract = apps.get_model("bet", "CouponExtract")
    Round = apps.get_model("bet", "Round")
    old_results = TelebingoOldResults.objects.all()
    for old in old_results:
        round1 = Round.objects.create(draw=old.draw, number=1)
        round2 = Round.objects.create(draw=old.draw, number=2)
        round3 = Round.objects.create(draw=old.draw, number=3)

        TelebingoResults.objects.create(round=round1, line=old.line1, bingo=old.bingo1)
        TelebingoResults.objects.create(round=round2, line=old.line2, bingo=old.bingo2)
        TelebingoResults.objects.create(round=round3, line=old.line3, bingo=old.bingo3)

    for old in CouponExtract.objects.filter(results__telebingooldresults__isnull=False):
        TbgCouponExtract.objects.create(number=old.number, prize=old.prize,
                                        draw=old.results.telebingooldresults.draw)
        old.prize = None
        old.save(update_fields=('prize',))

    old_results.delete()


def migrate_tbg_results_back(apps, schema_editor):
    TelebingoOldResults = apps.get_model("bet", "TelebingoOldResults")
    TelebingoResults = apps.get_model("bet", "TelebingoResults")
    CouponExtract = apps.get_model("bet", "CouponExtract")
    DrawPreprinted = apps.get_model("bet", "DrawPreprinted")
    for draw in DrawPreprinted.objects.filter(state__gte=2, game__code='telebingocordobes'):
        results = TelebingoResults.objects.filter(round__draw=draw)
        if not results.exists():
            continue

        old = TelebingoOldResults.objects.create(
            draw=draw,
            line1=results[0].line,
            line2=results[1].line,
            line3=results[2].line,
            bingo1=results[0].bingo,
            bingo2=results[1].bingo,
            bingo3=results[2].bingo,
        )

        for extract in draw.winners_coupons_set.all():
            CouponExtract.objects.create(number=extract.number, prize=extract.prize, results=old)


class Migration(migrations.Migration):

    dependencies = [
        ('bet', '0021_auto_20160825_1414'),
    ]

    operations = [
        migrations.RunPython(migrate_tbg_results, reverse_code=migrate_tbg_results_back),
    ]
