# -*- coding: utf-8 -*-
import logging
from django.db.models.signals import post_save, pre_save, post_delete, m2m_changed
from django.dispatch import receiver

from bet import models

# Get an instance of a logger
#logging.basicConfig()
logger = logging.getLogger('agencia24_default')


# Al guardar la imagen el objeto todavia no tiene pk
# Es necesario guardar la imagen en un atributo temporal (_UNSAVED_FILEFIELD)
# antes de que se guarde el draw, y pasar la imagen al campo original una vez
# que el draw se guardó y el objeto ya tiene pk.
_UNSAVED_FILEFIELD = 'unsaved_filefield'

@receiver(pre_save, sender=models.Draw)
@receiver(pre_save, sender=models.DrawPreprinted)
def skip_saving_file(sender, instance, **kwargs):
    if not instance.pk and not hasattr(instance, _UNSAVED_FILEFIELD):
        setattr(instance, _UNSAVED_FILEFIELD, instance.prize_image)
        instance.prize_image = None

@receiver(post_save, sender=models.Draw)
@receiver(post_save, sender=models.DrawPreprinted)
def save_file(sender, instance, created, **kwargs):
    if created and hasattr(instance, _UNSAVED_FILEFIELD):
        instance.prize_image = getattr(instance, _UNSAVED_FILEFIELD)
        instance.save()
        instance.__dict__.pop(_UNSAVED_FILEFIELD)


@receiver(pre_save, sender=models.Ticket)
def skip_saving_file(sender, instance, **kwargs):
    if not instance.pk and not hasattr(instance, _UNSAVED_FILEFIELD):
        setattr(instance, _UNSAVED_FILEFIELD, instance.real)
        instance.real = None

@receiver(post_save, sender=models.Ticket)
def save_file(sender, instance, created, **kwargs):
    if created and hasattr(instance, _UNSAVED_FILEFIELD):
        instance.real = getattr(instance, _UNSAVED_FILEFIELD)
        instance.save()
        instance.__dict__.pop(_UNSAVED_FILEFIELD)

################## date_draw in QuinielaGroup ##################
def on_draws_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if not reverse and action == 'post_add':
        try:
            earliest_draw = models.DrawQuiniela.objects.filter(pk__in=pk_set, state=models.BaseDraw.STATE.ACTIVE).earliest('date_limit')
        except models.DrawQuiniela.DoesNotExist:
            pass
        else:
            instance.date_draw = earliest_draw.date_draw
            instance.date_limit = earliest_draw.date_limit
            instance.date_limit_agency = earliest_draw.date_limit_agency
            instance.save()

m2m_changed.connect(on_draws_changed, sender=models.QuinielaGroup.draws.through)

# Actualizar date_draw de QuinielaGroup cuando cambia el concurso
def on_drawquiniela_changed(sender, instance, created, update_fields, **kwargs):
    if update_fields is None or 'date_limit' in update_fields or 'state' in update_fields:
        # Para cada grupo al que pertenece el draw modificado
        for group in instance.groups.all():
            try:
                earliest_draw = group.active_draws.earliest('date_limit')
            except models.DrawQuiniela.DoesNotExist:
                pass
            else:
                group.date_draw = earliest_draw.date_draw
                group.date_limit = earliest_draw.date_limit
                group.date_limit_agency = earliest_draw.date_limit_agency
                group.save()

post_save.connect(on_drawquiniela_changed, sender=models.DrawQuiniela)


@receiver(post_save, sender=models.UserProfile)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        for setting in models.Setting.objects.all():
            models.UserSetting.objects.create(
                profile=instance, setting=setting, value=setting.default
            )


@receiver(post_delete, sender=models.Detail)
@receiver(post_delete, sender=models.DetailCoupons)
@receiver(post_delete, sender=models.DetailQuiniela)
def save_file(sender, instance, using, **kwargs):
    if hasattr(instance, 'ticket') and not instance.ticket is None:
        instance.ticket.delete()

    if not hasattr(instance, 'bet'):
        return

    if isinstance(instance, models.Detail):
        instance.bet.delete()
    elif isinstance(instance, models.DetailCoupons):
        if not instance.bet.detailcoupons_set.exclude(id=instance.id).exists():
            instance.bet.delete()
    elif isinstance(instance, models.DetailQuiniela):
        if not instance.bet.detailquiniela_set.exclude(id=instance.id).exists():
            instance.bet.delete()


@receiver(pre_save, sender=models.BetCommissionMov)
@receiver(pre_save, sender=models.PaymentCommissionMov)
@receiver(pre_save, sender=models.WinnerCommissionMov)
def on_change_agenmovement(sender, instance, update_fields, **kwargs):
    if update_fields is not None and 'amount' not in update_fields:
        return

    if instance.pk:
        old = models.AgenMovement.objects.get(id=instance.pk)
        instance.agency.balance -= old.amount

    instance.agency.balance += instance.amount
    instance.agency.save(update_fields=('balance',))

@receiver(post_delete, sender=models.BetCommissionMov)
@receiver(post_delete, sender=models.PaymentCommissionMov)
@receiver(post_delete, sender=models.WinnerCommissionMov)
def on_delete_agenmovement(sender, instance, using, **kwargs):
    instance.agency.balance -= instance.amount
    instance.agency.save(update_fields=('balance',))


@receiver(post_save, sender=models.Game)
def create_gamebet_commission(sender, instance, created, **kwargs):
    if created:
        models.BetCommission.objects.create(game=instance)


########################################
# Delete ResultsSet's on <game>Result deletion
########################################

@receiver(post_delete, sender=models.Quini6Results)
def delete_quini6_results_set(sender, instance, **kwargs):
    if instance.tra:
        instance.tra.delete()
    if instance.tra2:
        instance.tra2.delete()
    if instance.rev:
        instance.rev.delete()
    if instance.sie:
        instance.sie.delete()
    if instance.ext:
        instance.ext.delete()

@receiver(post_delete, sender=models.LotoResults)
def delete_loto_results_set(sender, instance, **kwargs):
    if instance.tra:
        instance.tra.delete()
    if instance.des:
        instance.des.delete()
    if instance.sos:
        instance.sos.delete()

@receiver(post_delete, sender=models.BrincoResults)
@receiver(post_delete, sender=models.Loto5Results)
def delete_brinco_results_set(sender, instance, **kwargs):
    if instance.tra:
        instance.tra.delete()

@receiver(post_delete, sender=models.TelekinoResults)
def delete_telekino_results_set(sender, instance, **kwargs):
    if instance.tel:
        instance.tel.delete()
    if instance.rek:
        instance.rek.delete()

@receiver(post_delete, sender=models.LoteriaResults)
def delete_loteria_results_set(sender, instance, **kwargs):
    if instance.ord:
        instance.ord.delete()

@receiver(post_delete, sender=models.TotobingoResults)
def delete_totobingo_results_set(sender, instance, **kwargs):
    if instance.gog:
        instance.gog.delete()
    if instance.poz:
        instance.poz.delete()
    if instance.star:
        instance.star.delete()

"""@receiver(post_delete, sender=models.TelebingoOldResults)
def delete_telebingo_results_set(sender, instance, **kwargs):
    if instance.line1:
        instance.line1.delete()
    if instance.line2:
        instance.line2.delete()
    if instance.line3:
        instance.line3.delete()
    if instance.bingo1:
        instance.bingo1.delete()
    if instance.bingo2:
        instance.bingo2.delete()
    if instance.bingo3:
        instance.bingo3.delete()"""

@receiver(post_delete, sender=models.QuinielaResults)
def delete_quiniela_results_set(sender, instance, **kwargs):
    if instance.res:
        instance.res.delete()
