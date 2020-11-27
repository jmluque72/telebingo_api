#!/usr/bin/env python
# -*- coding: utf-8 -*-
from copy import copy
import datetime, pytz
from functools import partial, wraps
import os
import re

from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm as PassResetForm, SetPasswordForm as SetPassForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db.models.aggregates import Count
from django.forms.formsets import formset_factory
from django.forms.models import inlineformset_factory, modelformset_factory, BaseInlineFormSet
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from bootstrap3_datetime.widgets import DateTimePicker
from passwords.validators import ComplexityValidator as _ComplexityValidator
from passwords.fields import PasswordField

from bet import models, utils
from bet.utils import clean_required_field



#===============================================================================
# REGISTER & LOGIN
#===============================================================================


class ComplexityValidator(_ComplexityValidator):

    def __call__(self, value):
        if self.complexities is None:
            return

        uppercase, lowercase, letters = set(), set(), set()
        digits, special = set(), set()

        for character in value:
            if character.isupper():
                uppercase.add(character)
                letters.add(character)
            elif character.islower():
                lowercase.add(character)
                letters.add(character)
            elif character.isdigit():
                digits.add(character)
            elif not character.isspace():
                special.add(character)

        words = set(re.findall(r'\b\w+', value, re.UNICODE))

        errors = []
        if len(uppercase) < self.complexities.get("UPPER", 0):
            errors.append(
                u"%(UPPER)s letra/s mayúscula/s" %
                self.complexities)
        if len(lowercase) < self.complexities.get("LOWER", 0):
            errors.append(
                u"%(LOWER)s letra/s minúscula/s" %
                self.complexities)
        if len(letters) < self.complexities.get("LETTERS", 0):
            errors.append(
                u"%(LETTERS)s letra/s distinta/s" %
                self.complexities)
        if len(digits) < self.complexities.get("DIGITS", 0):
            errors.append(
                u"%(DIGITS)s dígito/s" %
                self.complexities)
        if len(special) < self.complexities.get("SPECIAL", 0):
            errors.append(
                u"%(SPECIAL)s caracter/es special/es" %
                self.complexities)
        if len(words) < self.complexities.get("WORDS", 0):
            errors.append(
                u"%(WORDS)s or more unique words" %
                self.complexities)

        if errors:
            raise ValidationError(self.message % (u'debe contener al menos: ' + u', '.join(errors),),
                                  code=self.code)


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = models.UserProfile
        exclude = ['user', 'saldo', 'playtoday', 'devicegsmid']


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']


# Formulario para usar registro de django-registration en webservices
class UserRegistrationForm(forms.ModelForm):

    password = PasswordField(label="Password")

    class Meta:
        model = User
        fields = ['username', 'email', 'password']


class PasswordResetForm(PassResetForm):

    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):

        urls = {'reset': '/accounts/password/reset/confirm/{}/{}/'.format(context['uid'], context['token'])}
        utils.send_email(None, 'registration/password_reset_email', [to_email], context, urls=urls)


class SetPasswordForm(SetPassForm):

    new_password1 = PasswordField(label=u"Contraseña nueva")



class MessagesForm(forms.ModelForm):

    text = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = models.Messages
        fields = ["text", "users", "type"]

    def __init__(self, *a, **kw):
        super(MessagesForm, self).__init__(*a, **kw)




class UserChoiceField(forms.ChoiceField):
    """users = models.UserProfile.objects.values_list('pk','user__first_name','user__last_name')
    USER_CHOICES = map(lambda (x,y,z): (x,u' '.join([y,z])), users)
    USER_CHOICES = [(None, '')] + USER_CHOICES
    return forms.ChoiceField(label='Usuario', choices=USER_CHOICES,
                                            required=False,
                                            widget=forms.Select(attrs = {'title': '',
                                                                         'data-live-search': 'True',
                                                                         'data-width':'auto'}))"""

    def __init__(self, *args, **kwargs):
        super(UserChoiceField, self).__init__(*args, **kwargs)

        self.label = 'Usuario'
        self.required = False
        self.widget = forms.Select(attrs = {'title': '',
                                             'data-live-search': 'True',
                                             'data-width':'auto'})

        users = models.UserProfile.objects.values_list('pk','user__first_name','user__last_name')
        USER_CHOICES = map(lambda (x,y,z): (x,u' '.join([y,z])), users)
        USER_CHOICES = [(None, '')] + USER_CHOICES
        self.choices = USER_CHOICES

class NonprintedForm(forms.ModelForm):

    class Meta:
        model = models.Draw
        exclude = ('game',)

        labels = {'date_draw': 'Fecha de sorteo:',
                  'date_limit': u'Fecha límite usuario:',
                  'date_limit_agency': u'Fecha límite agencia:',
                  'prize_text': 'Monto',
                  'prize_image': 'Adjuntar imagen',
                  'price': 'Precio en $:',
                  'number': u'Número de sorteo:'
                  }

        widgets = {
            'date_draw': DateTimePicker(options={"format": "DD/MM/YYYY HH:mm",
                                       "pickSeconds": False}, attrs={'readonly':''}),
            'date_limit': DateTimePicker(options={"format": "DD/MM/YYYY HH:mm",
                                       "pickSeconds": False}, attrs={'readonly':''}),
            'date_limit_agency': DateTimePicker(options={"format": "DD/MM/YYYY HH:mm",
                                       "pickSeconds": False}, attrs={'readonly':''}),
            'number': forms.TextInput(attrs={'required': True})
        }

    def __init__(self, game_code, *args, **kwargs):
        self.game_code = game_code
        readonly = kwargs.pop('readonly', False)
        super(NonprintedForm, self).__init__(*args, **kwargs)
        #instance = getattr(self, 'instance', None)

        STATE_CHOICES = models.Draw.STATE_CHOICES[:2]
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))

        start = (timezone.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        self.fields['date_draw'].widget.options['startDate'] = start
        self.fields['date_limit'].widget.options['startDate'] = start
        self.fields['date_limit_agency'].widget.options['startDate'] = start

        if readonly:
            for field in self.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = 'disabled'

        self.fields['price'].required = True
        if self.game_code == models.Game.CODE.QUINI6:
            self.fields['price'].label = 'Precio en $ (Trad.):'
            self.fields['price2'].label = 'Precio en $ (Rev.):'
            self.fields['price3'].label = 'Precio en $ (Sal.):'
            self.fields['price2'].required = True
            self.fields['price3'].required = True
        elif self.game_code == models.Game.CODE.LOTO:
            self.fields['price'].label = 'Precio en $ (Trad.):'
            self.fields['price2'].label = 'Precio en $ (Des.):'
            self.fields['price3'].label = 'Precio en $ (Sie.):'
            self.fields['price2'].required = True
            self.fields['price3'].required = True
        else:
            self.fields['price2'].label = ''
            self.fields['price3'].label = ''

    def clean_number(self):
        return clean_required_field(self, 'number')

    def clean(self):
        cleaned_data = super(NonprintedForm, self).clean()
        date_draw = cleaned_data.get("date_draw")
        date_limit = cleaned_data.get("date_limit")

        if date_draw and date_limit:
            # Only do something if both fields are valid so far.
            if date_draw < date_limit:
                raise forms.ValidationError(
                    "La fecha límite del usuario debe ser anterior"
                    " a la fecha del sorteo."
                )

        return cleaned_data

class QuinielaForm(forms.ModelForm):

    """date = forms.DateField(label="Fecha de sorteo:", required=True,
                           widget=DateTimePicker(options={"format": "DD/MM/YYYY",
                                    "startDate": timezone.now().strftime("%Y-%m-%d"),
                                    "pickTime": False}))

    limit = forms.DateField(label="Fecha límite usuario:", required=True,
                           widget=DateTimePicker(options={"format": "DD/MM/YYYY",
                                    "startDate": timezone.now().strftime("%Y-%m-%d"),
                                    "pickTime": False}))"""

    province = forms.ModelChoiceField(queryset=models.Province.objects.all(), label="Provincia", required=False, empty_label='')


    class Meta:
        model = models.DrawQuiniela
        exclude = ('game', 'prize_text')

        labels = {'number': u'Número concurso',
                  'date_draw': 'Fecha de concurso:',
                  'date_limit': u'Fecha límite usuario:',
                  'date_limit_agency': u'Fecha límite agencia:',
                  }

        widgets = {
            'date_draw': DateTimePicker(options={
                                    "format": "DD/MM/YYYY HH:mm",
                                    "pickSeconds": False,
                                        }, attrs={'readonly':''}),
            'date_limit': DateTimePicker(options={
                                    "format": "DD/MM/YYYY HH:mm",
                                    "pickSeconds": False}, attrs={'readonly':''}),
            'date_limit_agency': DateTimePicker(options={"format": "DD/MM/YYYY HH:mm",
                                       "pickSeconds": False}, attrs={'readonly':''}),
        }

    def __init__(self, *args, **kwargs):
        readonly = kwargs.pop('readonly', False)
        super(QuinielaForm, self).__init__(*args, **kwargs)

        if self.instance.pk is None:
            self.fields['quiniela'] = forms.ModelMultipleChoiceField(
                queryset=models.Quiniela.objects.all().order_by('code'),
                label='Quinielas',
                required=True,
                widget=forms.SelectMultiple(attrs = {'title': ''})
            )

        self.fields['number'].widget.attrs['required'] = False

        STATE_CHOICES = models.Draw.STATE_CHOICES[:2]
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))

        start = (timezone.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
        self.fields['date_draw'].widget.options['startDate'] = start
        self.fields['date_limit'].widget.options['startDate'] = start
        self.fields['date_limit_agency'].widget.options['startDate'] = start

        if readonly:
            for field in self.fields.values():
                field.widget.attrs['readonly'] = True
                field.widget.attrs['disabled'] = 'disabled'

    def clean_number(self):
        return self.cleaned_data['number']

    def clean(self):
        # Si esta creando puede seleccionar muchas quinielas, validar cada una
        if self.instance.pk is None:
            self.quinielas = self.cleaned_data['quiniela']
            for quiniela in self.cleaned_data['quiniela']:
                self.instance.quiniela = quiniela
                super(QuinielaForm, self).clean()
            self.cleaned_data['quiniela'] = self.quinielas[0]
            return self.cleaned_data
        else:
            return super(QuinielaForm, self).clean()

    def save(self, commit=True):
        instance = super(QuinielaForm, self).save(commit=False)

        if self.instance.pk is None:
            instances = []
            for quiniela in self.quinielas:
                instance.quiniela = quiniela
                instances.append(copy(instance))
        else:
            instances = [instance]

        if commit:
            map(models.DrawQuiniela.save, instances)
        return instances


class QuinielaGroupForm(forms.ModelForm):
    class Meta:
        model = models.QuinielaGroup
        exclude = ('state',)

        widgets = {
            'date': DateTimePicker(options={
                                    "format": "DD/MM/YYYY",
                                    "pickTime": False,
                                    'readonly':''}),
            'province': forms.Select(attrs = {'title': '',
                                              'data-live-search': 'True',
                                              'data-width':'auto'}),
            'number': forms.TextInput(attrs={'required': True}),
            'draws': forms.SelectMultiple(attrs = {'title': ''})
        }

    refine = forms.BooleanField(label="Filtrar por tipo", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(QuinielaGroupForm, self).__init__(*args, **kwargs)

        #self.fields['draws'].queryset = models.DrawQuiniela.objects.none()
        self.fields['type'].empty_label = ''
        self.fields['province'].empty_label = ''


class PreprintedForm(NonprintedForm):
    class Meta(NonprintedForm.Meta):
        model = models.DrawPreprinted
        exclude = ('game', 'tbg_state')

    def __init__(self, *args, **kwargs):
        super(PreprintedForm, self).__init__(*args, **kwargs)
        if self.game_code == models.Game.CODE.LOTERIA:
            self.fields['fractions'].widget.attrs['required'] = True
        if self.game_code.startswith('telebingo'):
            self.fields['rounds'].widget.attrs['required'] = True
            self.fields['chances'].widget.attrs['required'] = True
            self.fields['rounds'].widget.attrs['min'] = 1
            self.fields['chances'].widget.attrs['min'] = 1

    def clean_fractions(self):
        if self.instance is not None and self.game_code == models.Game.CODE.LOTERIA:
            return clean_required_field(self, 'fractions')
        elif self.instance is not None:
            return 1
        else:
            return self.cleaned_data['fractions']

    def clean_rounds(self):
        if self.instance is not None and self.game_code.startswith('telebingo'):
            return clean_required_field(self, 'rounds')
        else:
            return None

    def clean_chances(self):
        if self.instance is not None and self.game_code.startswith('telebingo'):
            return clean_required_field(self, 'chances')
        else:
            return None


class DateFilterForm(forms.Form):
    date_from = forms.DateTimeField(label='Desde',
                                    required=False,
                                    input_formats=['%d/%m/%Y'],
                                    widget=DateTimePicker(
                                        options={"format": "DD/MM/YYYY",
                                                 "pickTime": False},
                                        attrs={'readonly':''}
                                    ))
    date_to = forms.DateTimeField(label='Hasta',
                                  required=False,
                                  input_formats=['%d/%m/%Y'],
                                  widget=DateTimePicker(
                                      options={"format": "DD/MM/YYYY",
                                               "pickTime": False},
                                        attrs={'readonly':''}
                                  ))

    """def __init__(self, *args, **kwargs):
        from_min_value = kwargs.pop('from_min_value', None)
        from_max_value = kwargs.pop('from_max_value', None)
        to_min_value = kwargs.pop('to_min_value', None)
        to_max_value = kwargs.pop('to_max_value', None)
        super(DateFilterForm, self).__init__(*args, **kwargs)

        if from_min_value is not None:
            self.fields['date_from'].widget.options['startDate'] = from_min_value.strftime("%Y-%m-%d %H:%M")
        if from_max_value is not None:
            self.fields['date_from'].widget.options['endDate'] = from_max_value.strftime("%Y-%m-%d %H:%M")
        if to_min_value is not None:
            self.fields['date_to'].widget.options['startDate'] = to_min_value.strftime("%Y-%m-%d %H:%M")
        if to_max_value is not None:
            self.fields['date_to'].widget.options['endDate'] = to_max_value.strftime("%Y-%m-%d %H:%M")"""


class FilterDrawsForm(DateFilterForm):

    def __init__(self, *args, **kwargs):
        is_old = kwargs.pop('is_old', False)
        agenciero = kwargs.pop('agenciero', False)
        super(FilterDrawsForm, self).__init__(*args, **kwargs)

        games = models.Game.objects.exclude(code=models.Game.CODE.QUINIELA)
        if agenciero:
            games = games.exclude(type=models.Game.TYPE.NONPRINTED)
        CODE_CHOICES = list(games.values_list('code','name'))
        CODE_CHOICES = [(None, '')] + CODE_CHOICES
        self.fields['code'] = forms.ChoiceField(label='Juego', choices=CODE_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        if is_old:
            STATE_CHOICES = ((None, ''),) + models.Draw.STATE_CHOICES[models.BaseDraw.STATE.DRAFT:]
        else:
            STATE_CHOICES = ((None, ''),) + models.Draw.STATE_CHOICES[:models.BaseDraw.STATE.LOADED]
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))


class FilterDrawsQuinielaForm(FilterDrawsForm):
    def __init__(self, *args, **kwargs):
        super(FilterDrawsQuinielaForm, self).__init__(*args, **kwargs)
        del self.fields['code']

        self.fields['quiniela'] = forms.ModelChoiceField(
            label='Quiniela',required = False,
            queryset=models.Quiniela.objects.all(),
            empty_label='',
            widget = forms.Select(attrs = {'title': '',
                                           'data-live-search': 'True',
                                           'data-width':'auto'})
        )

        TYPE_CHOICES = ((None, ''),) + models.TYPE_CHOICES
        self.fields['type'] = forms.ChoiceField(label='Tipo', choices=TYPE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))


class FilterQuinielaForm(FilterDrawsQuinielaForm):

    def __init__(self, *args, **kwargs):
        super(FilterQuinielaForm, self).__init__(*args, **kwargs)
        del self.fields['quiniela']

        self.fields['province'] = forms.ModelChoiceField(
            queryset=models.Province.objects.all(),
            empty_label='',
            label='Provincia', required=False,
            widget=forms.Select(attrs={'title': ''})
        )

        TYPE_CHOICES = ((None, ''),) + models.TYPE_CHOICES
        self.fields['type'] = forms.ChoiceField(label='Tipo', choices=TYPE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))


class FilterPromotionsForm(DateFilterForm):

    def __init__(self, *args, **kwargs):
        super(FilterPromotionsForm, self).__init__(*args, **kwargs)

        CODE_CHOICES = list(models.Game.objects.exclude(code=models.Game.CODE.QUINIELA).values_list('code','name'))
        CODE_CHOICES = [(None, '')] + CODE_CHOICES
        self.fields['code'] = forms.ChoiceField(label='Juego', choices=CODE_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        STATE_CHOICES = ((None, ''),(1, 'Activa'),(0, 'Inactiva'))
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))

#===============================================================================
# CUPONES DRAW
#===============================================================================


class FilterCouponsForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(FilterCouponsForm, self).__init__(*args, **kwargs)

        AGENCY_CHOICES = list(models.Agency.objects.values_list('pk', 'name'))
        AGENCY_CHOICES = [(None, '')] + AGENCY_CHOICES
        self.fields['agency'] = forms.ChoiceField(label='Agencia', choices=AGENCY_CHOICES,
                                                  required=False,
                                                  widget=forms.Select(attrs={'title': '',
                                                                             'data-live-search': 'True'}))

        STATE_CHOICES = ((None, ''), (0, 'Disponible'), (1, 'Vendido'))
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs={'title': ''}))


class ImportFileForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.supported_ext = kwargs.pop('supported_ext', settings.SUPPORTED_IMPORT_EXT)
        super(ImportFileForm, self).__init__(*args, **kwargs)

        self.fields['file'] = forms.FileField(label='Archivo', required=True,
                                              widget=forms.FileInput(attrs={'accept': ','.join(self.supported_ext)}))

    def clean_file(self):
        _file = clean_required_field(self, 'file')
        if _file and os.path.splitext(_file.name)[1] not in self.supported_ext:
            raise forms.ValidationError(
                "Extensión de archivo no permitida."
            )

        return _file


class CouponForm(forms.ModelForm):

    class Meta:
        model = models.Coupon
        exclude = ['fraction_saldo', 'fraction_sales']

        labels = {'number': 'Billete Nro.'}

        widgets = {
            'draw': forms.HiddenInput(),
            'agency': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('fractions', None)
        self.game = kwargs.pop('game', None)
        super(CouponForm, self).__init__(*args, **kwargs)

        if not hasattr(self, 'instance'):
            return

        if self.game and self.game.code.startswith('telebingo'):
            self.fields['number'].widget.attrs['class'] = 'autocomplete-field'

        if self.instance.pk:
            if self.instance.draw.is_old:
                for field in self.fields.values():
                    field.widget.attrs['readonly'] = True
            else:
                self.fields['number'].widget.attrs['readonly'] = True

    def clean_number(self):
        if hasattr(self, 'instance') and self.instance.pk:
            return self.instance.number
        else:
            return self.cleaned_data['number']

    def save(self, commit=True):
        instance = super(CouponForm, self).save(commit=False)
        instance.fraction_sales = 1
        instance.fraction_saldo = instance.fraction_sales - instance.fractions_bought

        if commit:
            instance.save()
        return instance


class LotteryCouponForm(CouponForm):

    class Meta(CouponForm.Meta):
        model = models.LoteriaCoupon
        exclude = ('fraction_saldo',)

        CouponForm.Meta.labels.update({'fraction_sales': 'Fracciones compradas'})

        widgets = {
            'fraction_sales': forms.NumberInput(attrs={'min':'1'}),
            'progresion': forms.NumberInput(attrs={'max':'11'})
        }

    def __init__(self, *args, **kwargs):
        fractions = kwargs.pop('fractions', None)
        super(LotteryCouponForm, self).__init__(*args, **kwargs)

        if fractions is not None:
            self.fields['fraction_sales'].widget.attrs['max'] = str(fractions)

        if hasattr(self, 'instance') and self.instance.pk:

            fractions_bought = self.instance.fractions_bought
            if fractions_bought == 0:
                # Si no fue comprado, se puede modificar
                return

            self.fields['fraction_sales'].widget.attrs['min'] = fractions_bought

    def clean_number(self):
        number = super(LotteryCouponForm, self).clean_number()

        if models.LOTERIA_MIN_COUPON > int(number):
            raise forms.ValidationError(
                u"El numero de billete debe ser mayor a {}".format(models.LOTERIA_MIN_COUPON)
            )
        if models.LOTERIA_MAX_COUPON < int(number):
            raise forms.ValidationError(
                u"El numero de billete debe ser menor a {}".format(models.LOTERIA_MAX_COUPON)
            )
        return number


    def save(self, commit=True):
        instance = super(CouponForm, self).save(commit=False)
        instance.fraction_saldo = instance.fraction_sales - instance.fractions_bought

        if commit:
            instance.save()
        return instance


class BaseCouponFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        self.fractions = kwargs.pop('fractions', 1)
        self.game = kwargs.pop('game', None)
        super(BaseCouponFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs.update({'fractions': self.fractions})
        kwargs.update({'game': self.game})
        return super(BaseCouponFormSet, self)._construct_form(i, **kwargs)

    def clean(self):
        super(BaseCouponFormSet, self).clean()

        """Checks that no two coupons have the same number."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        numbers = []
        for form in self.forms:
            if not 'number' in form.cleaned_data or form in self.deleted_forms:
                continue

            number = form.cleaned_data['number']
            if number in numbers:
                raise forms.ValidationError(u"Billete número {} repetido.".format(number))

            existing = models.Coupon.objects.filter(draw=form.instance.draw, number=number)
            if self.game.code.startswith('telebingo'):
                if not existing.exists():
                    raise forms.ValidationError(u"El billete número {} no pertenece a este sorteo.".format(number))
                existing = existing.filter(agency__isnull=False)

            if existing.exclude(id=form.instance.id).exists():
                raise forms.ValidationError(u"El billete número {} ya fue cargado en el sistema.".format(number))

            numbers.append(number)


def createCouponFormSet(game_code=None, readonly=False):

    if game_code == models.Game.CODE.LOTERIA:
        form_model = LotteryCouponForm
        model = models.LoteriaCoupon
    else:
        form_model = CouponForm
        model = models.Coupon

    if readonly:
        extra = 0
    else:
        extra = 5

    return inlineformset_factory(models.DrawPreprinted,
                                 model,
                                 form=form_model,
                                 formset=BaseCouponFormSet,
                                 extra=extra)

#===============================================================================
# AGENCIAS
#===============================================================================

class AgencyUserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super(AgencyUserForm, self).__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs['required'] = True
        self.fields['last_name'].widget.attrs['required'] = True
        self.fields['email'].widget.attrs['required'] = True

    def save(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        creating = kwargs.pop('creating', False)
        self.instance.username = self.instance.email
        user = super(AgencyUserForm, self).save(*args, **kwargs)

        if creating:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            urls = {
                'reset': '/accounts/password/reset/confirm/{}/{}/'.format(uid, token)
            }

            utils.send_email(request, 'emails/agency_pass_reset_email', [user.email],
                             {'user': user}, urls=urls)
        return user

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                u"El email {} no está disponible.".format(email),
            )

        return email


class AgencyForm(forms.ModelForm):

    class Meta:
        model = models.Agency
        exclude = ('user', 'balance')

        widgets = {
            'province': forms.Select(attrs = {'title': '',
                                              'data-live-search': 'True',
                                              'data-width':'auto'})
        }

    def __init__(self, *args, **kwargs):
        super(AgencyForm, self).__init__(*args, **kwargs)

        games = models.Game.objects.count()
        #provinces = models.Province.objects.annotate(taxes_count=Count('gametax'))\
        #     .filter(taxes_count__gte=games)
        provinces = models.Province.objects.all()
        self.fields['province'].queryset = provinces

        for field in self.fields:
            if field == 'is_active' or field == 'province':
                continue
            self.fields[field].widget.attrs['required'] = True


class FilterAgencyMovsForm(DateFilterForm):

    number = forms.IntegerField(min_value=0, label='N° ref. pago', required=False)

    def __init__(self, *args, **kwargs):
        super(FilterAgencyMovsForm, self).__init__(*args, **kwargs)

        self.fields['date_from'].widget.options['endDate'] = timezone.now().strftime("%Y-%m-%d")
        self.fields['date_to'].widget.options['endDate'] = timezone.now().strftime("%Y-%m-%d")

        GAME_CHOICES = list(models.Game.objects.values_list('code','name'))
        GAME_CHOICES = [(None, '')] + GAME_CHOICES
        self.fields['game'] = forms.ChoiceField(label='Juego', choices=GAME_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

    def is_completed(self):
        result =  bool(self.cleaned_data.has_key('game') and self.cleaned_data['game'])
        result &= bool(self.cleaned_data.has_key('date_from') and self.cleaned_data['date_from'])
        result &= bool(self.cleaned_data.has_key('date_to') and self.cleaned_data['date_to'])
        return result


    """def clean(self):
        cleaned_data = super(FilterAgencyMovsForm, self).clean()
        date_from = cleaned_data.get("date_from")
        game = cleaned_data.get("game")

        if (date_from and not game) or (not date_from and game):
            raise forms.ValidationError(
                    u"Complete todos los campos"
                )

        return cleaned_data"""

#===============================================================================
# RESULTADOS
#===============================================================================


class PrizeExtractForm(forms.ModelForm):

    prize_type = forms.ChoiceField(choices=models.Prize.TYPE_CHOICES, label="Tipo de Premio", required=False)
    value = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2,
                               label="Premio", required=False)
    text = forms.CharField(max_length=100, label="Premio", required=False)
    coupon = forms.CharField(max_length=100, label="Premio", required=False,
                             initial=u"Otro Billete")

    class Meta:
        model = models.RowExtract
        exclude = ('order', 'prize')

        widgets = {
            'coupon': forms.TextInput(attrs={'readonly': 'readonly'})
        }

    def __init__(self, *args, **kwargs):
        hidden_hits = kwargs.pop('hidden_hits', False)
        self.prize_type = kwargs.pop('prize_type', models.Prize.TYPE.CASH)
        readonly = kwargs.pop('readonly', True)
        self.draw = kwargs.pop('draw', None)
        super(PrizeExtractForm, self).__init__(*args, **kwargs)

        if 'hits' in self.fields:
            if hidden_hits:
                self.fields['hits'].widget = forms.HiddenInput()
            if readonly:
                self.fields['hits'].widget.attrs['readonly'] = True

        if not self.instance is None and not self.instance.prize_id is None:
            self.fields['value'].initial = self.instance.prize.value
            self.fields['text'].initial = self.instance.prize.text
            self.fields['prize_type'].initial = self.instance.prize.type
        elif not self.empty_permitted:
            self.fields['prize_type'].initial = self.prize_type

        if self.prize_type != models.Prize.TYPE.COUPON:
            self.fields.pop('coupon')

        if self.prize_type == models.Prize.TYPE.CASH:
            self.fields['value'].widget.attrs['required'] = 'required'
            self.fields['prize_type'].widget = forms.HiddenInput()
            self.fields.pop('text')
        elif self.prize_type == models.Prize.TYPE.COUPON:
            self.fields['prize_type'].widget = forms.HiddenInput()
            self.fields.pop('text')
            self.fields.pop('value')
        elif self.prize_type == models.Prize.TYPE.OTHER:
            self.fields['text'].widget.attrs['required'] = 'required'
            self.fields['prize_type'].widget = forms.HiddenInput()
            self.fields.pop('value')
        else:
            self.fields['prize_type'].widget.attrs['data-prize'] = 'type'
            self.fields['prize_type'].widget.attrs['required'] = 'required'
            self.fields['value'].widget.attrs['data-prize'] = 'value'
            self.fields['text'].widget.attrs['data-prize'] = 'text'

    def clean(self):
        cleaned_data = super(PrizeExtractForm, self).clean()

        if self.prize_type is None:
            self.prize_type = cleaned_data.get('prize_type')

        if self.prize_type == models.Prize.TYPE.CASH:
            if 'value' in cleaned_data and cleaned_data['value'] is None:
                raise forms.ValidationError(
                        u"El campo Premio es obligatorio."
                    )

        if self.prize_type == models.Prize.TYPE.OTHER:
            if 'text' in cleaned_data and cleaned_data['text'] is None:
                raise forms.ValidationError(
                        u"El campo Premio es obligatorio."
                    )

        return cleaned_data

    def save(self, commit=True):
        instance = super(PrizeExtractForm, self).save(commit=False)

        prize = instance.prize if hasattr(instance, 'prize') and instance.prize else models.Prize()

        prize.value = self.cleaned_data.get('value', None)
        prize.text = self.cleaned_data.get('text', "")
        prize.type = self.cleaned_data.get('prize_type', self.prize_type)
        #print '.{}.{}.{}.'.format(prize.value, prize.text, prize.type)

        prize.save()
        instance.prize = prize

        if commit:
            instance.save()

        return instance


class RowExtractForm(PrizeExtractForm):

    class Meta(PrizeExtractForm.Meta):
        model = models.RowExtract
        exclude = ('order', 'prize')


class TbgRowExtractForm(PrizeExtractForm):

    number = forms.CharField(label='Billete',
                             widget=forms.TextInput(attrs={
                                 'class': 'autocomplete-field',
                                 'required': 'required',
                             }))

    class Meta(PrizeExtractForm.Meta):
        model = models.TbgRowExtract
        exclude = ('order', 'prize', 'coupon')

    def clean_winners(self):
        return 1

    def clean_number(self):
        number = self.cleaned_data['number']
        if not self.draw.coupon_set.filter(number=number).exists():
            raise forms.ValidationError(
                u"El billete número {} no pertenece a este sorteo.".format(number)
            )
        return number


class SinlgeExtractForm(PrizeExtractForm):

    class Meta(PrizeExtractForm.Meta):
        model = models.SingleExtract
        exclude = ()


class PreprintedExtractForm(RowExtractForm):

    class Meta(RowExtractForm.Meta):
        exclude = ('results', 'order', 'prize')

        widgets = {
            'hits': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(PreprintedExtractForm, self).__init__(*args, **kwargs)
        self.fields['winners'].widget.attrs['required'] = 'required'

        #for field in self.fields.values():
        #    field.widget.attrs['required'] = 'required'


class PrizeFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.readonly = kwargs.pop('readonly', True)
        self.prize_type = kwargs.pop('prize_type', models.Prize.TYPE.CASH)
        self.hidden_hits = kwargs.pop('hidden_hits', False)
        self.draw = kwargs.pop('draw', None)
        super(PrizeFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs.update({'prize_type': self.prize_type,
                       'readonly': self.readonly,
                       'hidden_hits': self.hidden_hits,
                       'draw': self.draw})
        return super(PrizeFormSet, self)._construct_form(i, **kwargs)


def createExtractFormSet(min_num, numbers=None):

    if numbers == 0:
        model = models.VariableResultsSet
    elif numbers == 1:
        model = models.ResultsSetStar
    elif numbers == 5:
        model = models.ResultsSet5
    elif numbers == 6:
        model = models.ResultsSet6
    elif numbers == 15:
        model = models.ResultsSet15
    else:
        model = models.ResultsSet6Extra

    return inlineformset_factory(model,
                                 models.RowExtract,
                                 form=RowExtractForm,
                                 formset=PrizeFormSet,
                                 min_num=min_num,
                                 extra=0,
                                 can_delete=False)


TbgExtractFormSet = inlineformset_factory(
    models.VariableResultsSet,
    models.TbgRowExtract,
    form=TbgRowExtractForm,
    formset=PrizeFormSet,
    min_num=1,
    extra=0,
    can_delete=False
)


class ResultsSetForm(forms.ModelForm):
    numbers = 5
    max_value = 36
    min_value = 0

    class Meta:
        model = models.ResultsSet
        exclude = []

    def __init__(self, *args, **kwargs):
        min_value = kwargs.pop('min_value', self.min_value)
        max_value = kwargs.pop('max_value', self.max_value)
        super(ResultsSetForm, self).__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['min'] = min_value
            field.widget.attrs['max'] = max_value
            field.widget.attrs['required'] = 'required'

    def save(self, commit=True):
        numbers = [self.cleaned_data.get("number"+str(i)) for i in range(1, self.numbers+1)]
        numbers.sort()

        results = super(ResultsSetForm, self).save(commit=False)
        for i in range(1, self.numbers+1):
            setattr(results, "number"+str(i),numbers[i-1])

        if commit:
            results = results.save()

        return results

class ResultsSetStarForm(ResultsSetForm):
    max_value = 24
    min_value = 1

    class Meta:
        model = models.ResultsSetStar
        exclude = ()

class ResultsSet5Form(ResultsSetForm):
    numbers = 5
    max_value = 36
    min_value = 0

    class Meta:
        model = models.ResultsSet5
        exclude = ()

    def clean(self):
        cleaned_data = super(ResultsSet5Form, self).clean()

        numbers = [cleaned_data.get("number"+str(i)) for i in range(1, self.numbers+1)]
        if all(isinstance(number, int) for number in numbers):
            # Only do something if all fields are valid so far.
            duplicates = list(set([x for x in numbers if numbers.count(x) > 1]))
            if duplicates:
                raise forms.ValidationError(
                    u"Números repetidos ({}).".format(', '.join(map(str, duplicates)))
                )

        return cleaned_data

class ResultsSet6Form(ResultsSet5Form):
    numbers = 6
    max_value = 45

    class Meta(ResultsSet5Form.Meta):
        model = models.ResultsSet6

class ResultsSet6ExtraForm(ResultsSet6Form):
    max_value = 41
    max_value_extra = 9

    class Meta(ResultsSet6Form.Meta):
        model = models.ResultsSet6Extra

    def __init__(self, *args, **kwargs):
        max_value_extra = kwargs.pop('max_value_extra', self.max_value_extra)
        super(ResultsSet6ExtraForm, self).__init__(*args, **kwargs)

        self.fields['extra1'].widget.attrs['max'] = max_value_extra
        self.fields['extra1'].widget.attrs['required'] = 'required'

        self.fields['extra2'].widget.attrs['max'] = max_value_extra
        self.fields['extra2'].widget.attrs['required'] = 'required'


    def clean(self):
        cleaned_data = super(ResultsSet6ExtraForm, self).clean()

        if cleaned_data.get("extra1") == cleaned_data.get("extra2"):
            raise forms.ValidationError(
                u"Números repetidos ({}).".format(cleaned_data.get("extra1"))
            )

        return cleaned_data

    def save(self, commit=True):
        results = super(ResultsSet6ExtraForm, self).save(commit=False)
        if results.extra1 > results.extra2:
            swap = results.extra1
            results.extra1 = results.extra2
            results.extra2 = swap

        if commit:
            results = results.save()

        return results


class ResultsSet12Form(ResultsSet5Form):
    numbers = 12
    max_value = 25
    min_value = 1

    class Meta:
        model = models.ResultsSet12
        exclude = []

class ResultsSet15Form(ResultsSet5Form):
    numbers = 15
    max_value = 25
    min_value = 1

    class Meta:
        model = models.ResultsSet15
        exclude = ()

class ResultsSet20Form(ResultsSet5Form):
    numbers = 20
    max_value = 99999
    min_value = 0

    class Meta:
        model = models.ResultsSet20
        exclude = ()

    def clean(self):
        return forms.ModelForm.clean(self)

    def save(self, commit=True):
        return forms.ModelForm.save(self, commit)


class ProgresionLotteryForm(forms.ModelForm):

    class Meta:
        model = models.LoteriaResults
        exclude = ('ord',)

        widgets = {
            'draw': forms.HiddenInput(),
            'progresion': forms.NumberInput(attrs={'min': 1, 'max': 11})
        }

class ResultsSetLotteryForm(ResultsSet5Form):
    numbers = 20
    max_value = 99999
    min_value = 0

    class Meta:
        model = models.ResultsSet20
        exclude = ()

    def clean(self):
        return forms.ModelForm.clean(self)

    def save(self, commit=True):
        return forms.ModelForm.save(self, commit)

class BaseNumberFormSet(forms.BaseFormSet):

    def __init__(self, *args, **kwargs):
        min_num = kwargs.pop('min_num', 0)
        super(BaseNumberFormSet, self).__init__(*args, **kwargs)
        for form in self.forms[:min_num]:
            form.fields['number'].widget.attrs['required'] = 'required'
            form.empty_permitted = False

    def clean(self):
        """
        Add validation to check that no two equal numbers
        """
        if any(self.errors):
            return

        numbers = []
        duplicates = []

        for form in self.forms:
            if form.cleaned_data:
                number = form.cleaned_data['number']

                if number:
                    if number in numbers and not number in duplicates:
                        duplicates.append(number)
                    numbers.append(number)

                if duplicates:
                    raise forms.ValidationError(
                        u'Números repetidos ({}).'.format(', '.join(map(str, duplicates)))
                    )


class NumberForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.min_value = kwargs.pop('min_value', 1)
        self.max_value = kwargs.pop('max_value', 54)
        self.readonly = kwargs.pop('readonly', False)
        super(NumberForm, self).__init__(*args, **kwargs)

        self.fields['number'] = forms.IntegerField(min_value=self.min_value,
                                                   max_value=self.max_value,
                                                   required=False)
        self.fields['number'].widget.attrs['class'] = 'number-comma'

        if self.readonly:
            self.fields['number'].widget.attrs['readonly'] = True


def createVariableResultsFormSet(max_value, extra, min_value=1, readonly=False):

    form = wraps(NumberForm)(partial(NumberForm, min_value=min_value,
                                     max_value=max_value, readonly=readonly))

    return formset_factory(form, extra=extra, formset=BaseNumberFormSet)


class VariableResultsForm(forms.ModelForm):
    class Meta:
        model = models.VariableResultsSet
        fields = ('numbers',)

        widgets = {
            'numbers': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        self.sort_numbers = kwargs.pop('sort_numbers', False)
        super(VariableResultsForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(VariableResultsForm, self).clean()

        if not "numbers" in cleaned_data:
            raise forms.ValidationError(
                u"Faltan datos."
            )

        numbers = map(int, cleaned_data["numbers"].split(','))
        duplicates = list(set([x for x in numbers if numbers.count(x) > 1]))
        if duplicates:
            raise forms.ValidationError(
                u"Números repetidos ({}).".format(', '.join(map(str, duplicates)))
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super(VariableResultsForm, self).save(commit=False)

        if 'numbers' in self.changed_data:
            if not instance.numbers:
                return instance

            numbers = map(int, instance.numbers.split(','))
            if self.sort_numbers:
                numbers.sort()
            instance.numbers = ",".join(map(str, numbers))

        if commit:
            instance.save()

        return instance


class QuinielaResultsForm(forms.Form):

    error_messages = {
        'required_field': "Este campo es obligatorio.",
    }

    lottery = forms.ModelChoiceField(
        queryset=models.Quiniela.objects.all(),
        widget=forms.RadioSelect(), empty_label=None,
        label='Quiniela', required=True
    )
    type = forms.ChoiceField(
        choices=models.TYPE_CHOICES,
        widget=forms.RadioSelect(),
        label='Tipo', required=True
    )

    def __init__(self, *args, **kwargs):
        readonly = kwargs.pop('readonly', False)
        super(QuinielaResultsForm, self).__init__(*args, **kwargs)

        if readonly:
            for field in self.fields.values():
                field.widget.attrs['readonly'] = True

    def clean_type(self):
        _type = self.cleaned_data["type"]
        if not _type:
            raise forms.ValidationError(
            self.error_messages['required_field'],
            code='required_field',
        )

        return _type

    def clean_date(self):
        date = self.cleaned_data["date"]
        if not date:
            raise forms.ValidationError(
            self.error_messages['required_field'],
            code='required_field',
        )

        return date

#===============================================================================
# CUPONES RESULTADOS
#===============================================================================

class CouponExtractForm(PrizeExtractForm):
    class Meta(PrizeExtractForm.Meta):
        model = models.CouponExtract
        exclude = ('prize',)
        labels = {'number': 'Billete Nro.'}

    def __init__(self, *args, **kwargs):
        kwargs.update({'readonly': False})
        kwargs.update({'prize_type': models.Prize.TYPE.OTHER})
        super(CouponExtractForm, self).__init__(*args, **kwargs)

        self.fields['text'].widget.attrs.pop('required', None)

    def clean(self):
        cleaned_data = super(PrizeExtractForm, self).clean()

        if self.prize_type is None:
            self.prize_type = cleaned_data.get('prize_type')

        if self.prize_type == models.Prize.TYPE.CASH:
            if 'value' in cleaned_data and cleaned_data['value'] is None:
                raise forms.ValidationError(
                        u"El campo Premio es obligatorio."
                    )

        if self.prize_type == models.Prize.TYPE.OTHER:
            if 'text' in cleaned_data and cleaned_data['text'] is None:
                raise forms.ValidationError(
                        u"El campo Premio es obligatorio."
                    )

        return cleaned_data

def createCouponResultsFormSet(min_num, max_num, extra=0):

    return inlineformset_factory(models.PreprintedResults,
                            models.CouponExtract,
                            min_num=min_num,
                            max_num=max_num,
                            extra=extra,
                            form=CouponExtractForm,
                            formset=PrizeFormSet,
                            can_delete=False)


"""class TbgCouponExtractForm(CouponExtractForm):
    class Meta(CouponExtractForm.Meta):
        model = models.TbgCouponExtract

TbgCouponResultsFormSet = inlineformset_factory(
    models.DrawPreprinted,
    models.TbgCouponExtract,
    min_num=2,
    max_num=5,
    extra=0,
    form=TbgCouponExtractForm,
    formset=PrizeFormSet,
    can_delete=False
)"""

#===============================================================================
# PAGOS
#===============================================================================

class PaymentForm(forms.ModelForm):

    class Meta:
        model = models.AbstractMovement
        fields = ('state', 'amount')

        widgets = {
            'amount': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)

        if self.instance.code == 'CC':
            self.fields['amount'].widget.attrs['initial'] = self.instance.chargemovement.initial
        self.original_state = self.instance.state

    def save(self, commit=True):
        profile = self.instance.user
        if self.instance.code == 'CC' and self.instance.amount > self.instance.chargemovement.initial:
            raise forms.ValidationError("")

        # Si estaba confirmado
        if self.original_state == models.AbstractMovement.STATE.CONFIRMED:
            profile.saldo -= self.instance.amount

        if self.instance.state == models.AbstractMovement.STATE.CONFIRMED:
            profile.saldo += self.instance.amount

        self.instance.confirm_date = timezone.now()
        profile.save()

        return super(PaymentForm, self).save(commit)

PaymentFormSet = modelformset_factory(models.AbstractMovement, PaymentForm, fields=('state','amount'), extra=0)

class FilterPaymentsForm(DateFilterForm):

    def __init__(self, *args, **kwargs):
        super(FilterPaymentsForm, self).__init__(*args, **kwargs)

        self.fields['date_to'].widget.options['endDate'] = timezone.now().strftime("%Y-%m-%d")
        self.fields['date_to'].widget.options['showClear'] = True

        CODE_CHOICES = list((a,b) for a,b in models.AbstractMovement.CODE_CHOICES if a in ['CC','SR'])
        CODE_CHOICES = [(None, '')] + CODE_CHOICES
        self.fields['code'] = forms.ChoiceField(label='Tipo', choices=CODE_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        METHOD_CHOICES = list(models.AbstractMovement.PAYMENT_CHOICES)
        METHOD_CHOICES = [(None, '')] + METHOD_CHOICES
        self.fields['method'] = forms.ChoiceField(label='Método', choices=METHOD_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        STATE_CHOICES = ((-1, 'Todos'),) + models.AbstractMovement.STATE_CHOICES
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))

        self.fields['user'] = UserChoiceField()


class FilterMovementsForm(DateFilterForm):

    def __init__(self, *args, **kwargs):
        super(FilterMovementsForm, self).__init__(*args, **kwargs)

        self.fields['date_to'].widget.options['endDate'] = timezone.now().strftime("%Y-%m-%d")
        self.fields['date_to'].widget.options['showClear'] = True

        CODE_CHOICES = list((a,b) for a,b in models.AbstractMovement.CODE_CHOICES if a in ['PA', 'PR', 'CC','SR'])
        CODE_CHOICES = [(None, '')] + CODE_CHOICES
        self.fields['code'] = forms.ChoiceField(label='Tipo', choices=CODE_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        DRAW_CHOISES = list(models.DrawPreprinted.objects.values_list('pk','number'))
        DRAW_CHOISES = [(None, '')] + DRAW_CHOISES
        self.fields['draw'] = forms.ChoiceField(label='Sorteo', choices=DRAW_CHOISES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        self.fields['user'] = UserChoiceField()

#===============================================================================
# APUESTAS
#===============================================================================

class FilterBetsForm(DateFilterForm):

    def __init__(self, *args, **kwargs):
        super(FilterBetsForm, self).__init__(*args, **kwargs)

        self.fields['date_to'].widget.options['endDate'] = timezone.now().strftime("%Y-%m-%d")

        AGENCY_CHOICES = list(models.Agency.objects.values_list('pk','name'))
        AGENCY_CHOICES = [(None, '')] + AGENCY_CHOICES
        self.fields['agency'] = forms.ChoiceField(label='Agencia', choices=AGENCY_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        STATE_CHOICES = ((None, ''),) + models.BaseDetail.STATE_CHOICES
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))

        GAME_CHOICES = list(models.Game.objects.values_list('code','name'))
        GAME_CHOICES = [(None, '')] + GAME_CHOICES
        self.fields['game'] = forms.ChoiceField(label='Juego', choices=GAME_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))

        self.fields['user'] = UserChoiceField()

class FilterUsersForm(DateFilterForm):

    def __init__(self, *args, **kwargs):
        super(FilterUsersForm, self).__init__(*args, **kwargs)

        STATE_CHOICES = ((None, ''), (0, 'Inactivo'), (1, 'Activo'))
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))

        self.fields['user'] = UserChoiceField()

class QuinielasProvinceForm(forms.Form):

    province = forms.ChoiceField(
        choices=((None,''),)+models.Province.PROVINCE_CHOICES,
        label='Provincia', required=True,
        widget=forms.Select(attrs = {'title': ''})
    )

    quinielas = forms.ModelMultipleChoiceField(
        queryset=models.Quiniela.objects.all(),
        widget=forms.SelectMultiple(attrs = {'title': ''}),
        label='Quinielas'
    )


WinnerFormSet = modelformset_factory(models.Winner, fields=('notif', 'id'), extra=0)

BaseWinnerFormSet = modelformset_factory(models.BaseWinner, fields=('notif', 'id'), extra=0)


class FilterPrizeRequestForm(FilterPaymentsForm):

    def __init__(self, *args, **kwargs):
        super(FilterPrizeRequestForm, self).__init__(*args, **kwargs)

        self.fields.pop('code')
        self.fields.pop('user')
        self.fields.pop('method')

        GAME_CHOICES = list(models.Game.objects.filter(
            type=models.Game.TYPE.PREPRINTED
        ).exclude(code='loteria').values_list('pk','name'))
        GAME_CHOICES = [(None, '')] + GAME_CHOICES
        self.fields['game'] = forms.ChoiceField(label='Juego', choices=GAME_CHOICES,
                                                required=False,
                                                widget=forms.Select(attrs = {'title': ''}))


        STATE_CHOICES = ((-1, ''),) + models.PrizeRequest.STATE_CHOICES
        self.fields['state'] = forms.ChoiceField(label='Estado', choices=STATE_CHOICES,
                                                 required=False,
                                                 widget=forms.Select(attrs = {'title': ''}))


#===============================================================================
# CONFIGURACION
#===============================================================================

class MonthForm(forms.Form):

    month = forms.DateField(widget=DateTimePicker(options={'format': 'MM/YYYY',
                                                           'pickTime': False,
                                                           'viewMode': 'months',
                                                           'minViewMode': 'months'},
                                                  attrs={'readonly':''}))

class LoteriaPrizeRowForm(PrizeExtractForm):

    class Meta(PrizeExtractForm.Meta):
        model = models.LoteriaPrizeRow
        exclude = ('prize',)

        widgets = {
            'code': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(LoteriaPrizeRowForm, self).__init__(*args, **kwargs)

    def get_code_display(self):
        try:
            return dict(models.LoteriaPrizeRow.CODE_CHOICES)[self.initial['code']]
        except KeyError:
            return None


LoteriaPrizeFormSet = inlineformset_factory(models.LoteriaPrize,
                                 models.LoteriaPrizeRow,
                                 form=LoteriaPrizeRowForm,
                                 min_num=len(models.LoteriaPrizeRow.CODE_CHOICES),
                                 extra=0,
                                 can_delete=False)


class GameTaxForm(forms.ModelForm):

    class Meta:
        model = models.GameTax
        exclude = ('province',)

        widgets = {
            'game': forms.HiddenInput()
        }

        labels = {'game': 'Juego'}

    def __init__(self, *args, **kwargs):
        super(GameTaxForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['required'] = True

    def get_name_display(self):
        try:
            return models.Game.objects.get(id=self.initial['game']).name
        except KeyError, models.Game.DoesNotExist:
            return None


class GameTaxFilter(forms.Form):

    province = forms.ModelChoiceField(
        queryset=models.Province.objects.all(),
        empty_label='', label='Provincia', required=False,
        widget=forms.Select(attrs={'title': ''})
    )


class PromotionModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):

        date = obj.date_draw.astimezone(pytz.timezone(settings.TIME_ZONE))
        date = date.strftime("%d/%m/%y")

        if isinstance(obj.parent, models.DrawQuiniela):
            return u'{} - {} {}'.format(date, obj.parent.quiniela.name, obj.parent.get_type_display())

        return u'{} - {}'.format(date, obj.number)


class DrawPromotionForm(forms.ModelForm):

    game = forms.ModelChoiceField(queryset=models.Game.objects.all(), label="Juego", required=False,
                                  empty_label='', widget=forms.Select(attrs={'title': '', 'data-width':'auto'}))

    """province = forms.ModelChoiceField(queryset=models.Province.objects.all(),
                                      widget=forms.Select(attrs={'title': ''}),
                                      label="Provincia", required=False, empty_label='')

    type = forms.ChoiceField(queryset=models.Province.objects.all(),
                                      widget=forms.Select(attrs={'title': ''}),
                                      label="Quiniela", required=False, empty_label='')"""

    class Meta:
        model = models.DrawPromotion
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(DrawPromotionForm, self).__init__(*args, **kwargs)

        now = datetime.datetime.now()
        draws = models.BaseDraw.objects.filter(date_limit__gt=now)
        self.fields['draw'] = PromotionModelChoiceField(queryset=draws, empty_label='',
                                                        widget=forms.Select(attrs={'title': '',
                                                                                   'data-width':'auto'})
                                                        )


class BetCommissionForm(forms.ModelForm):

    class Meta:
        model = models.BetCommission
        exclude = ()

        widgets = {
            'game': forms.HiddenInput()
        }

        labels = {'game': 'Juego'}

    def __init__(self, *args, **kwargs):
        super(BetCommissionForm, self).__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs['required'] = True

    def get_name_display(self):
        try:
            return models.Game.objects.get(id=self.initial['game']).name
        except KeyError, models.Game.DoesNotExist:
            return None


def telebingo_forms_are_valid(round_list):
    result = True

    for round_dict in round_list:
        #result &= all(map(PreprintedExtractForm.is_valid, round_dict['line']['extractForms']))
        result &= round_dict['line']['extractForms'].is_valid()
        result &= round_dict['line']['resultsForm'].is_valid()
        result &= round_dict['line']['formSet'].is_valid()

        #result &= all(map(PreprintedExtractForm.is_valid, round_dict['bingo']['extractForms']))
        result &= round_dict['bingo']['extractForms'].is_valid()
        result &= round_dict['bingo']['resultsForm'].is_valid()
        result &= round_dict['bingo']['formSet'].is_valid()

    return result

