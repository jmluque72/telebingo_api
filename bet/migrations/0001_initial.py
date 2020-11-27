# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import bet.storage
import bet.modelfields
import django.core.validators
import bet.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AbstractMovement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=2, verbose_name=b'Tipo', choices=[(b'SR', b'Solicitud de retiro'), (b'PA', b'Pago de apuesta'), (b'CC', b'Carga de credito'), (b'PR', b'Premio de apuesta')])),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name=b'Fecha')),
                ('amount', bet.modelfields.RoundedDecimalField(default=0.0, max_digits=12, decimal_places=2)),
                ('state', models.PositiveIntegerField(default=0, verbose_name=b'Estado', choices=[(0, b'Pendiente'), (1, b'Acreditado'), (2, b'Cancelado')])),
                ('confirm_date', models.DateTimeField(null=True, verbose_name=b'Fecha de acreditaci\xc3\xb3n', blank=True)),
            ],
            options={
                'get_latest_by': 'confirm_date',
            },
        ),
        migrations.CreateModel(
            name='Agency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name=b'Nombre')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name=b'Fecha de alta')),
                ('is_active', models.BooleanField(default=True, verbose_name=b'Activa')),
                ('number', models.CharField(max_length=80, verbose_name='N\xfamero')),
                ('address', models.CharField(max_length=80, verbose_name='Direcci\xf3n')),
                ('city', models.CharField(max_length=80, verbose_name='Ciudad')),
                ('neighborhood', models.CharField(max_length=80, verbose_name='Barrio')),
            ],
            options={
                'verbose_name': 'Agencia',
            },
        ),
        migrations.CreateModel(
            name='AgencyCoupon',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.PositiveIntegerField(verbose_name='N\xfamero')),
                ('agency', models.ForeignKey(related_name='default_coupons_set', to='bet.Agency')),
            ],
        ),
        migrations.CreateModel(
            name='AgencyDevices',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('deviceid', models.CharField(unique=True, max_length=255, verbose_name=b'Tablet ID')),
                ('devicegsmid', models.CharField(unique=True, max_length=255, verbose_name=b'Device GSM')),
                ('agency', models.ForeignKey(related_name='device_set', to='bet.Agency')),
            ],
        ),
        migrations.CreateModel(
            name='AgenMovement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_mov', models.DateTimeField(auto_now_add=True, verbose_name=b'Fecha')),
                ('amount', bet.modelfields.RoundedDecimalField(max_digits=12, decimal_places=2)),
                ('state', models.PositiveSmallIntegerField(verbose_name=b'Estado', choices=[(0, b'Pendiente'), (1, b'Acreditado')])),
                ('code', models.PositiveSmallIntegerField(choices=[(0, b'Apuesta'), (1, b'Premio apuesta'), (2, b'Cobro'), (3, 'Comisi\xf3n de premio')])),
            ],
        ),
        migrations.CreateModel(
            name='BaseDetail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('importq', bet.modelfields.RoundedDecimalField(null=True, verbose_name=b'Importe', max_digits=12, decimal_places=2, blank=True)),
                ('state', models.PositiveIntegerField(default=0, verbose_name=b'Estado', choices=[(0, b'No Jugado'), (1, b'Jugado')])),
            ],
        ),
        migrations.CreateModel(
            name='BaseDraw',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_draw', models.DateTimeField(verbose_name=b'Fecha sorteo')),
                ('date_limit', models.DateTimeField(verbose_name='Hora l\xedmite usuario')),
                ('date_limit_agency', models.DateTimeField(verbose_name='Hora l\xedmite agencia')),
                ('number', models.CharField(max_length=20, null=True, verbose_name='N\xfamero sorteo', blank=True)),
                ('state', models.PositiveIntegerField(default=0, verbose_name=b'Estado', choices=[(1, b'Borrador'), (0, b'Publicado'), (2, b'Cargado'), (3, b'Extracto enviado')])),
                ('prize_text', models.CharField(default=b'', max_length=255, verbose_name=b'Premio Texto')),
                ('extract_file', models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.save_extract_file, null=True, verbose_name=b'Extracto', blank=True)),
            ],
            options={
                'get_latest_by': 'date_draw',
            },
        ),
        migrations.CreateModel(
            name='BaseWinner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('info', models.CharField(max_length=80, blank=True)),
                ('prize_tax', models.PositiveIntegerField(null=True, verbose_name=b'Premio con impuestos')),
                ('notif', models.BooleanField(default=False, verbose_name=b'Notificado')),
            ],
        ),
        migrations.CreateModel(
            name='Bet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_bet', models.DateTimeField(verbose_name=b'Fecha Apuesta')),
                ('code_trx', models.CharField(max_length=40, verbose_name=b'Transaccion')),
                ('agency', models.ForeignKey(related_name='bet_set', verbose_name=b'Agencia', to='bet.Agency')),
            ],
        ),
        migrations.CreateModel(
            name='BetCommission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', bet.modelfields.RoundedDecimalField(verbose_name=b'valor', max_digits=5, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)])),
            ],
        ),
        migrations.CreateModel(
            name='BrincoResults',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.CharField(max_length=40, verbose_name=b'Cupon')),
                ('fraction_sales', models.PositiveIntegerField(verbose_name=b'Fracciones compradas')),
                ('fraction_saldo', models.PositiveIntegerField(verbose_name=b'Fracciones disponibles')),
            ],
        ),
        migrations.CreateModel(
            name='CouponExtract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.CharField(max_length=40, verbose_name=b'Nro. Cup\xc3\xb3n')),
            ],
        ),
        migrations.CreateModel(
            name='DrawPromotion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('suggestion', models.CharField(max_length=255, verbose_name=b'Sugerencia', blank=True)),
                ('is_active', models.BooleanField(default=True, verbose_name=b'Activa')),
            ],
        ),
        migrations.CreateModel(
            name='DrawTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('week_day', models.PositiveSmallIntegerField(choices=[(0, b'Lunes'), (1, b'Martes'), (2, b'Miercoles'), (3, b'Jueves'), (4, b'Viernes'), (5, b'Sabado'), (6, b'Domingo')])),
                ('draw_time', models.TimeField(verbose_name=b'Hora sorteo')),
                ('agency_diff', models.PositiveIntegerField(verbose_name=b'Diferencia agencia (min)')),
                ('user_diff', models.PositiveIntegerField(verbose_name=b'Diferencia usuario (min)')),
            ],
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(unique=True, max_length=40, verbose_name=b'C\xc3\xb3digo')),
                ('name', models.CharField(max_length=255, verbose_name=b'Nombre')),
                ('type', models.PositiveIntegerField(verbose_name=b'Tipo', choices=[(0, b'Preimpreso'), (1, b'No impreso')])),
                ('order', models.PositiveIntegerField(default=0, verbose_name=b'Orden')),
            ],
        ),
        migrations.CreateModel(
            name='GameTax',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('nat_tax', bet.modelfields.RoundedDecimalField(verbose_name=b'Impuesto Nacional', max_digits=5, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)])),
                ('prov_tax', bet.modelfields.RoundedDecimalField(verbose_name=b'Impuesto Provincial', max_digits=5, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)])),
                ('min_nat', bet.modelfields.RoundedDecimalField(verbose_name=b'Minimo Nacional', max_digits=8, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('min_prov', bet.modelfields.RoundedDecimalField(verbose_name=b'Minimo Provincial', max_digits=8, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('min', bet.modelfields.RoundedDecimalField(verbose_name=b'Valor min para cobrar en Loteria.', max_digits=8, decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0)])),
                ('game', models.ForeignKey(to='bet.Game')),
            ],
        ),
        migrations.CreateModel(
            name='LoteriaPrize',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('month', models.PositiveSmallIntegerField(verbose_name=b'Mes', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)])),
                ('year', models.PositiveSmallIntegerField(verbose_name='A\xf1o', validators=[django.core.validators.MinValueValidator(2016), django.core.validators.MaxValueValidator(2099)])),
            ],
        ),
        migrations.CreateModel(
            name='LoteriaPrizeRow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.PositiveSmallIntegerField(choices=[(0, '1\xb0 PREMIO'), (1, '2\xb0 PREMIO'), (2, '3\xb0 PREMIO'), (3, '4\xb0 PREMIO'), (4, '5\xb0 PREMIO'), (5, '6\xb0 AL 10\xb0 PREMIO'), (6, '11\xb0 AL 20\xb0 PREMIO'), (7, 'ANTERIOR Y POSTERIOR DEL 1\xb0 PREMIO'), (8, 'ANTERIOR Y POSTERIOR DEL 2\xb0 PREMIO'), (9, 'ANTERIOR Y POSTERIOR DEL 3\xb0 PREMIO'), (10, '4 ULTIMAS CIFRAS DEL 1\xb0 PREMIO'), (11, '3 ULTIMAS CIFRAS DEL 1\xb0 PREMIO'), (12, '2 ULTIMAS CIFRAS DEL 1\xb0 PREMIO'), (13, '2 ULTIMAS CIFRAS DEL 2\xb0 PREMIO'), (14, '2 ULTIMAS CIFRAS DEL 3\xb0 PREMIO'), (15, 'ULTIMA CIFRA DEL 1\xb0 PREMIO'), (16, 'PROGRESION 11 EN 11')])),
                ('month', models.ForeignKey(related_name='prizes', to='bet.LoteriaPrize')),
            ],
        ),
        migrations.CreateModel(
            name='Loto5Results',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='LotoResults',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='LotteryTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.PositiveSmallIntegerField(choices=[(0, b'Primera'), (1, b'Matutina'), (2, b'Vespertina'), (3, b'Nocturna'), (4, b'Turista')])),
                ('draw_time', models.TimeField(verbose_name=b'Hora sorteo')),
                ('draw_limit', models.TimeField(verbose_name=b'Diferencia cierre')),
            ],
        ),
        migrations.CreateModel(
            name='PreprintedResults',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Prize',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.SmallIntegerField(default=0, choices=[(0, b'Dinero'), (1, 'Otro cart\xf3n'), (2, 'Otro premio')])),
                ('value', bet.modelfields.RoundedDecimalField(null=True, verbose_name=b'Premio', max_digits=12, decimal_places=2, blank=True)),
                ('text', models.CharField(max_length=100, verbose_name=b'Premio', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='PrizeRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('numbers', models.CommaSeparatedIntegerField(max_length=152, verbose_name=b'Coincidencias')),
                ('state', models.PositiveSmallIntegerField(default=0, choices=[(0, b'Pendiente'), (1, b'Aceptado'), (2, b'Rechazado')])),
                ('mode', models.CharField(max_length=12)),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Province',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code_name', models.PositiveSmallIntegerField(verbose_name=b'Nombre', choices=[(0, 'Buenos Aires'), (1, 'Catamarca'), (2, 'Chaco'), (3, 'Chubut'), (4, 'C\xf3rdoba'), (5, 'Corrientes'), (6, 'Entre R\xedos'), (7, 'Formosa'), (8, 'Jujuy'), (9, 'La Pampa'), (10, 'La Rioja'), (11, 'Mendoza'), (12, 'Misiones'), (13, 'Neuqu\xe9n'), (14, 'R\xedo Negro'), (15, 'Salta'), (16, 'San Juan'), (17, 'San Luis'), (18, 'Santa Cruz'), (19, 'Santa Fe'), (20, 'Santiago del Estero'), (21, 'Tierra del Fuego'), (22, 'Tucum\xe1n')])),
                ('quiniela_prizes', models.CommaSeparatedIntegerField(max_length=25, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Quini6Results',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Quiniela',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=35, verbose_name=b'Nombre')),
                ('code', models.PositiveSmallIntegerField(null=True, verbose_name=b'Codigo Loteria', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='QuinielaGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField(verbose_name=b'Fecha')),
                ('type', models.PositiveSmallIntegerField(verbose_name=b'Tipo', choices=[(0, b'Primera'), (1, b'Matutina'), (2, b'Vespertina'), (3, b'Nocturna'), (4, b'Turista')])),
                ('number', models.CharField(max_length=20, verbose_name='N\xfamero de sorteo')),
                ('date_draw', models.DateTimeField(null=True, blank=True)),
                ('date_limit', models.DateTimeField(null=True, verbose_name='Hora l\xedmite usuario', blank=True)),
                ('date_limit_agency', models.DateTimeField(null=True, blank=True)),
                ('extract_file', models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.save_extract_group_file, null=True, verbose_name=b'Extracto', blank=True)),
                ('state', models.PositiveIntegerField(default=0, verbose_name=b'Estado', choices=[(1, b'Borrador'), (0, b'Publicado'), (2, b'Cargado'), (3, b'Extracto enviado')])),
                ('province', models.ForeignKey(verbose_name=b'Provincia', to='bet.Province')),
            ],
            options={
                'verbose_name': 'Quiniela Group (Sorteo)',
                'verbose_name_plural': 'Quiniela Groups (Sorteos)',
            },
        ),
        migrations.CreateModel(
            name='QuinielaResults',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='QuinielaTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.PositiveSmallIntegerField(choices=[(0, b'Primera'), (1, b'Matutina'), (2, b'Vespertina'), (3, b'Nocturna'), (4, b'Turista')])),
                ('draws', models.CommaSeparatedIntegerField(max_length=250)),
                ('weekdays', models.CommaSeparatedIntegerField(max_length=13, null=True, blank=True)),
                ('province', models.ForeignKey(to='bet.Province')),
            ],
        ),
        migrations.CreateModel(
            name='ResultsSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='RowExtract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hits', models.CharField(max_length=20, verbose_name=b'Aciertos')),
                ('winners', models.PositiveIntegerField(verbose_name=b'Ganadores')),
                ('order', models.PositiveIntegerField(verbose_name=b'Orden')),
                ('prize', models.OneToOneField(null=True, blank=True, to='bet.Prize')),
            ],
        ),
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.SmallIntegerField(unique=True, choices=[(0, 'MAIL extracto enviado'), (1, 'MAIL ticket enviado'), (2, 'PUSH ticket enviado'), (3, 'MAIL apuesta jugada'), (4, 'MAIL notificacion ganador'), (5, 'PUSH notificacion ganador'), (6, 'MAIL retiro aprobado'), (7, 'PUSH retiro aprobado'), (8, 'MAIL solicitud de retiro'), (9, 'MAIL saldo acreditado'), (10, 'PUSH saldo acreditado'), (11, 'MAIL saldo rechazado'), (12, 'PUSH saldo rechazado'), (13, 'MAIL solicitud premio rechazada'), (14, 'PUSH solicitud premio rechazada')])),
                ('default', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='SingleExtract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('winners', models.PositiveIntegerField(verbose_name=b'Ganadores')),
                ('prize', models.OneToOneField(null=True, blank=True, to='bet.Prize')),
            ],
        ),
        migrations.CreateModel(
            name='TCargo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('trx', models.CharField(max_length=20, unique=True, verbose_name=b'IDUnicoTrx')),
                ('wholesaler', models.IntegerField(verbose_name=b'idMayorista')),
                ('pos', models.IntegerField(verbose_name=b'idPtoVenta')),
                ('dni', models.IntegerField(verbose_name=b'DNIbeneficiario')),
                ('amount', models.IntegerField(verbose_name=b'Importe')),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('fake', models.FileField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.picture_ticket, null=True, verbose_name=b'Pseudo-Ticket', blank=True)),
                ('real', models.ImageField(storage=bet.storage.OverwriteStorage(), upload_to=bet.models.picture_ticket, null=True, verbose_name=b'Ticket Real', blank=True)),
                ('requested', models.PositiveSmallIntegerField(default=0)),
                ('key', models.CharField(max_length=56, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('saldo', bet.modelfields.RoundedDecimalField(default=0.0, verbose_name=b'Saldo', max_digits=12, decimal_places=2, blank=True)),
                ('playtoday', bet.modelfields.RoundedDecimalField(default=0.0, verbose_name=b'Jugaste hoy', max_digits=12, decimal_places=2, blank=True)),
                ('dni', models.PositiveIntegerField(unique=True, verbose_name=b'DNI')),
                ('devicegsmid', models.CharField(max_length=255, null=True, verbose_name=b'Device GCM', blank=True)),
                ('device_os', models.PositiveSmallIntegerField(choices=[(0, b'Otro'), (1, b'Android'), (2, b'iOS')])),
                ('agency', models.ForeignKey(related_name='profile_set', verbose_name=b'Agencia', to='bet.Agency')),
                ('province', models.ForeignKey(related_name='profile_set', verbose_name=b'Provincia', to='bet.Province')),
                ('user', models.OneToOneField(related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.BooleanField()),
                ('profile', models.ForeignKey(related_name='setting_set', to='bet.UserProfile')),
                ('setting', models.ForeignKey(related_name='user_set', to='bet.Setting')),
            ],
        ),
        migrations.CreateModel(
            name='BetCommissionMov',
            fields=[
                ('agenmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AgenMovement')),
            ],
            bases=('bet.agenmovement',),
        ),
        migrations.CreateModel(
            name='BetMovement',
            fields=[
                ('abstractmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AbstractMovement')),
            ],
            bases=('bet.abstractmovement',),
        ),
        migrations.CreateModel(
            name='ChargeMovement',
            fields=[
                ('abstractmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AbstractMovement')),
                ('method', models.PositiveIntegerField(verbose_name=b'Medio de pago', choices=[(0, b'MercadoPago'), (1, b'Transferencia Bancaria'), (2, b'TCargo')])),
                ('number', models.CharField(max_length=40, verbose_name=b'N\xc3\xbamero de transacci\xc3\xb3n')),
                ('type', models.CharField(max_length=20, verbose_name=b'Tipo')),
                ('initial', bet.modelfields.RoundedDecimalField(default=0.0, max_digits=12, decimal_places=2)),
                ('external_url', models.URLField(default=b'', blank=True)),
                ('tcargo', models.ForeignKey(blank=True, to='bet.TCargo', null=True)),
            ],
            bases=('bet.abstractmovement',),
        ),
        migrations.CreateModel(
            name='Detail',
            fields=[
                ('basedetail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseDetail')),
            ],
            bases=('bet.basedetail',),
        ),
        migrations.CreateModel(
            name='DetailCoupons',
            fields=[
                ('basedetail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseDetail')),
                ('fraction_bought', models.PositiveIntegerField(verbose_name=b'Fracciones compradas')),
                ('prize_requested', models.BooleanField(default=False)),
            ],
            bases=('bet.basedetail',),
        ),
        migrations.CreateModel(
            name='DetailQuiniela',
            fields=[
                ('basedetail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseDetail')),
                ('number', models.CharField(max_length=4, verbose_name=b'Numero', validators=[django.core.validators.RegexValidator(b'^[0-9]{1,4}$', message=b'Ingrese un n\xc3\xbamero de 1 a 4 cifras')])),
                ('location', models.PositiveIntegerField(verbose_name=b'Ubicaci\xc3\xb3n', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
            ],
            bases=('bet.basedetail',),
        ),
        migrations.CreateModel(
            name='Draw',
            fields=[
                ('basedraw_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseDraw')),
                ('prize_image', models.ImageField(upload_to=bet.models.picture_prize, null=True, verbose_name=b'Avatar', blank=True)),
                ('price', bet.modelfields.RoundedDecimalField(decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0)], max_digits=12, blank=True, null=True, verbose_name=b'Precio')),
                ('price2', bet.modelfields.RoundedDecimalField(decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0)], max_digits=12, blank=True, null=True, verbose_name=b'Precio 2')),
                ('price3', bet.modelfields.RoundedDecimalField(decimal_places=2, validators=[django.core.validators.MinValueValidator(0.0)], max_digits=12, blank=True, null=True, verbose_name=b'Precio 3')),
            ],
            bases=('bet.basedraw',),
        ),
        migrations.CreateModel(
            name='DrawQuiniela',
            fields=[
                ('basedraw_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseDraw')),
                ('type', models.PositiveSmallIntegerField(verbose_name=b'Tipo', choices=[(0, b'Primera'), (1, b'Matutina'), (2, b'Vespertina'), (3, b'Nocturna'), (4, b'Turista')])),
                ('quiniela', models.ForeignKey(to='bet.Quiniela')),
            ],
            options={
                'verbose_name': 'Draw Quiniela (Concurso)',
                'verbose_name_plural': 'Draws Quiniela (Concursos)',
            },
            bases=('bet.basedraw',),
        ),
        migrations.CreateModel(
            name='LoteriaCoupon',
            fields=[
                ('coupon_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Coupon')),
                ('progresion', models.PositiveSmallIntegerField(validators=[django.core.validators.MaxValueValidator(11)])),
            ],
            bases=('bet.coupon',),
        ),
        migrations.CreateModel(
            name='LoteriaResults',
            fields=[
                ('preprintedresults_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.PreprintedResults')),
                ('progresion', models.PositiveSmallIntegerField(validators=[django.core.validators.MaxValueValidator(11)])),
            ],
            bases=('bet.preprintedresults',),
        ),
        migrations.CreateModel(
            name='NonprintedWinnerComm',
            fields=[
                ('agenmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AgenMovement')),
            ],
            bases=('bet.agenmovement',),
        ),
        migrations.CreateModel(
            name='PaymentCommissionMov',
            fields=[
                ('agenmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AgenMovement')),
                ('date_from', models.DateField()),
                ('date_to', models.DateField()),
            ],
            bases=('bet.agenmovement',),
        ),
        migrations.CreateModel(
            name='PreprintedWinnerComm',
            fields=[
                ('agenmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AgenMovement')),
                ('text', models.CharField(max_length=255, verbose_name=b'Concepto')),
            ],
            bases=('bet.agenmovement',),
        ),
        migrations.CreateModel(
            name='PrizeMovement',
            fields=[
                ('abstractmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AbstractMovement')),
            ],
            bases=('bet.abstractmovement',),
        ),
        migrations.CreateModel(
            name='ResultsSet5',
            fields=[
                ('resultsset_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet')),
                ('number1', models.PositiveIntegerField(verbose_name=b'Numero 1', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number2', models.PositiveIntegerField(verbose_name=b'Numero 2', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number3', models.PositiveIntegerField(verbose_name=b'Numero 3', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number4', models.PositiveIntegerField(verbose_name=b'Numero 4', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number5', models.PositiveIntegerField(verbose_name=b'Numero 5', validators=[django.core.validators.MaxValueValidator(99999)])),
            ],
            bases=('bet.resultsset',),
        ),
        migrations.CreateModel(
            name='ResultsSetStar',
            fields=[
                ('resultsset_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet')),
                ('star', models.PositiveIntegerField(verbose_name=b'Bolilla Estrella', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(24)])),
            ],
            bases=('bet.resultsset',),
        ),
        migrations.CreateModel(
            name='TelebingoResults',
            fields=[
                ('preprintedresults_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.PreprintedResults')),
            ],
            bases=('bet.preprintedresults',),
        ),
        migrations.CreateModel(
            name='TelekinoResults',
            fields=[
                ('preprintedresults_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.PreprintedResults')),
            ],
            bases=('bet.preprintedresults',),
        ),
        migrations.CreateModel(
            name='TotobingoResults',
            fields=[
                ('preprintedresults_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.PreprintedResults')),
            ],
            bases=('bet.preprintedresults',),
        ),
        migrations.CreateModel(
            name='VariableResultsSet',
            fields=[
                ('resultsset_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet')),
                ('numbers', models.CommaSeparatedIntegerField(max_length=152)),
            ],
            bases=('bet.resultsset',),
        ),
        migrations.CreateModel(
            name='Winner',
            fields=[
                ('basewinner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.BaseWinner')),
            ],
            bases=('bet.basewinner',),
        ),
        migrations.CreateModel(
            name='WithdrawalMovement',
            fields=[
                ('abstractmovement_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.AbstractMovement')),
                ('method', models.PositiveIntegerField(verbose_name=b'Medio de pago', choices=[(0, b'MercadoPago'), (1, b'Transferencia Bancaria'), (2, b'TCargo')])),
                ('cbu', models.CharField(max_length=22, verbose_name=b'CBU', validators=[django.core.validators.RegexValidator(b'^[0-9]{22}$', message=b'N\xc3\xbamero de CBU no v\xc3\xa1lido.')])),
            ],
            bases=('bet.abstractmovement',),
        ),
        migrations.AddField(
            model_name='rowextract',
            name='results',
            field=models.ForeignKey(related_name='extract_set', to='bet.ResultsSet'),
        ),
        migrations.AddField(
            model_name='quini6results',
            name='ext',
            field=models.OneToOneField(related_name='quini6_ext', verbose_name=b'Premio Extra', to='bet.SingleExtract'),
        ),
        migrations.AddField(
            model_name='province',
            name='quinielas',
            field=models.ManyToManyField(to='bet.Quiniela', blank=True),
        ),
        migrations.AddField(
            model_name='lotterytime',
            name='quiniela',
            field=models.ForeignKey(related_name='time_set', to='bet.Quiniela'),
        ),
        migrations.AddField(
            model_name='loteriaprizerow',
            name='prize',
            field=models.ForeignKey(to='bet.Prize'),
        ),
        migrations.AlterUniqueTogether(
            name='loteriaprize',
            unique_together=set([('month', 'year')]),
        ),
        migrations.AddField(
            model_name='gametax',
            name='province',
            field=models.ForeignKey(to='bet.Province'),
        ),
        migrations.AddField(
            model_name='drawtime',
            name='game',
            field=models.ForeignKey(to='bet.Game'),
        ),
        migrations.AddField(
            model_name='drawpromotion',
            name='draw',
            field=models.OneToOneField(related_name='promotion', verbose_name=b'Sorteo', to='bet.BaseDraw'),
        ),
        migrations.AddField(
            model_name='couponextract',
            name='prize',
            field=models.OneToOneField(to='bet.Prize'),
        ),
        migrations.AddField(
            model_name='couponextract',
            name='results',
            field=models.ForeignKey(related_name='winners_coupons_set', to='bet.PreprintedResults'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='agency',
            field=models.ForeignKey(verbose_name=b'Agencia', blank=True, to='bet.Agency', null=True),
        ),
        migrations.AddField(
            model_name='betcommission',
            name='game',
            field=models.OneToOneField(to='bet.Game'),
        ),
        migrations.AddField(
            model_name='bet',
            name='user',
            field=models.ForeignKey(related_name='bet_set', to='bet.UserProfile'),
        ),
        migrations.AddField(
            model_name='basedraw',
            name='game',
            field=models.ForeignKey(related_name='draw_set', to='bet.Game'),
        ),
        migrations.AddField(
            model_name='agenmovement',
            name='agency',
            field=models.ForeignKey(related_name='movement_set', to='bet.Agency'),
        ),
        migrations.AddField(
            model_name='agencycoupon',
            name='game',
            field=models.ForeignKey(to='bet.Game'),
        ),
        migrations.AddField(
            model_name='agency',
            name='province',
            field=models.ForeignKey(verbose_name=b'Provincia', to='bet.Province'),
        ),
        migrations.AddField(
            model_name='agency',
            name='user',
            field=models.OneToOneField(related_name='agency', verbose_name=b'Agenciero', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='abstractmovement',
            name='user',
            field=models.ForeignKey(related_name='movement_set', to='bet.UserProfile'),
        ),
        migrations.CreateModel(
            name='DetailBrinco',
            fields=[
                ('detail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Detail')),
                ('number1', models.PositiveIntegerField(verbose_name=b'Numero 1')),
                ('number2', models.PositiveIntegerField(verbose_name=b'Numero 2')),
                ('number3', models.PositiveIntegerField(verbose_name=b'Numero 3')),
                ('number4', models.PositiveIntegerField(verbose_name=b'Numero 4')),
                ('number5', models.PositiveIntegerField(verbose_name=b'Numero 5')),
                ('number6', models.PositiveIntegerField(verbose_name=b'Numero 6')),
            ],
            bases=('bet.detail',),
        ),
        migrations.CreateModel(
            name='DetailLoto',
            fields=[
                ('detail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Detail')),
                ('number1', models.PositiveIntegerField(verbose_name=b'Numero 1')),
                ('number2', models.PositiveIntegerField(verbose_name=b'Numero 2')),
                ('number3', models.PositiveIntegerField(verbose_name=b'Numero 3')),
                ('number4', models.PositiveIntegerField(verbose_name=b'Numero 4')),
                ('number5', models.PositiveIntegerField(verbose_name=b'Numero 5')),
                ('number6', models.PositiveIntegerField(verbose_name=b'Numero 6')),
                ('extra1', models.PositiveIntegerField(verbose_name=b'Extra 1')),
                ('extra2', models.PositiveIntegerField(verbose_name=b'Extra 2')),
                ('tra', models.BooleanField(default=True, verbose_name=b'Tradicional')),
                ('des', models.BooleanField(default=True, verbose_name=b'Desquite')),
                ('sos', models.BooleanField(default=True, verbose_name=b'Sale o sale')),
            ],
            bases=('bet.detail',),
        ),
        migrations.CreateModel(
            name='DetailLoto5',
            fields=[
                ('detail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Detail')),
                ('number1', models.PositiveIntegerField(verbose_name=b'Numero 1')),
                ('number2', models.PositiveIntegerField(verbose_name=b'Numero 2')),
                ('number3', models.PositiveIntegerField(verbose_name=b'Numero 3')),
                ('number4', models.PositiveIntegerField(verbose_name=b'Numero 4')),
                ('number5', models.PositiveIntegerField(verbose_name=b'Numero 5')),
            ],
            bases=('bet.detail',),
        ),
        migrations.CreateModel(
            name='DetailQuiniSeis',
            fields=[
                ('detail_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Detail')),
                ('number1', models.PositiveIntegerField(verbose_name=b'Numero 1')),
                ('number2', models.PositiveIntegerField(verbose_name=b'Numero 2')),
                ('number3', models.PositiveIntegerField(verbose_name=b'Numero 3')),
                ('number4', models.PositiveIntegerField(verbose_name=b'Numero 4')),
                ('number5', models.PositiveIntegerField(verbose_name=b'Numero 5')),
                ('number6', models.PositiveIntegerField(verbose_name=b'Numero 6')),
                ('tra', models.BooleanField(default=True)),
                ('rev', models.BooleanField(default=True)),
                ('sie', models.BooleanField(default=True)),
            ],
            bases=('bet.detail',),
        ),
        migrations.CreateModel(
            name='DrawPreprinted',
            fields=[
                ('draw_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Draw')),
                ('coupon_image', models.ImageField(upload_to=bet.models.picture_coupon, null=True, verbose_name=b'Cup\xc3\xb3n completo', blank=True)),
                ('coupon_thumbnail', models.ImageField(upload_to=bet.models.picture_coupon_th, null=True, verbose_name=b'Cup\xc3\xb3n miniatura', blank=True)),
                ('fractions', models.PositiveSmallIntegerField(default=1, verbose_name=b'Fracciones', blank=True)),
            ],
            bases=('bet.draw',),
        ),
        migrations.CreateModel(
            name='ResultsSet6',
            fields=[
                ('resultsset5_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet5')),
                ('number6', models.PositiveIntegerField(verbose_name=b'Numero 6', validators=[django.core.validators.MaxValueValidator(99999)])),
            ],
            bases=('bet.resultsset5',),
        ),
        migrations.CreateModel(
            name='WinnerExtract',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('extract', models.ForeignKey(related_name='winner_set', verbose_name=b'Fila Extracto', to='bet.RowExtract')),
            ],
            bases=('bet.winner',),
        ),
        migrations.CreateModel(
            name='WinnerLoteria',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('prize', bet.modelfields.RoundedDecimalField(verbose_name=b'Premio', max_digits=12, decimal_places=2)),
                ('type', models.PositiveSmallIntegerField(choices=[(0, 'Ubicaci\xf3n'), (1, 'Progresi\xf3n'), (2, 'Terminaci\xf3n'), (3, 'Aproximaci\xf3n')])),
            ],
            bases=('bet.winner',),
        ),
        migrations.CreateModel(
            name='WinnerQuiniela',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('prize', bet.modelfields.RoundedDecimalField(verbose_name=b'Premio', max_digits=12, decimal_places=2)),
                ('hits', models.PositiveSmallIntegerField()),
                ('winner_ticket', models.ForeignKey(to='bet.BaseWinner', null=True)),
            ],
            bases=('bet.winner',),
        ),
        migrations.CreateModel(
            name='WinnerSingleExtract',
            fields=[
                ('winner_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.Winner')),
                ('extract', models.ForeignKey(related_name='winner_set', verbose_name=b'Extracto', to='bet.SingleExtract')),
            ],
            bases=('bet.winner',),
        ),
        migrations.AddField(
            model_name='winner',
            name='detail',
            field=models.ForeignKey(verbose_name=b'Detalle', to='bet.BaseDetail'),
        ),
        migrations.AddField(
            model_name='winner',
            name='draw',
            field=models.ForeignKey(related_name='winner_set', verbose_name=b'Sorteo', to='bet.BaseDraw'),
        ),
        migrations.AlterUniqueTogether(
            name='usersetting',
            unique_together=set([('profile', 'setting')]),
        ),
        migrations.AddField(
            model_name='totobingoresults',
            name='gog',
            field=models.OneToOneField(related_name='totobingo', verbose_name='Gan\xe1 o Gan\xe1', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='totobingoresults',
            name='star',
            field=models.OneToOneField(related_name='totobingo', verbose_name=b'Bolilla Estrella', to='bet.ResultsSetStar'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='bingo1',
            field=models.ForeignKey(related_name='telebingo_bingo1_set', verbose_name='Ronda 1 - Bingo', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='bingo2',
            field=models.ForeignKey(related_name='telebingo_bingo2_set', verbose_name='Ronda 2 - Bingo', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='bingo3',
            field=models.ForeignKey(related_name='telebingo_bingo3_set', verbose_name='Ronda 3 - Bingo', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='line1',
            field=models.ForeignKey(related_name='telebingo_line1_set', verbose_name='Ronda 1 - L\xednea', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='line2',
            field=models.ForeignKey(related_name='telebingo_line2_set', verbose_name='Ronda 2 - L\xednea', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='line3',
            field=models.ForeignKey(related_name='telebingo_line3_set', verbose_name='Ronda 3 - L\xednea', to='bet.VariableResultsSet'),
        ),
        migrations.AddField(
            model_name='quinielaresults',
            name='draw',
            field=models.OneToOneField(related_name='quiniela_results', verbose_name=b'Sorteo', to='bet.DrawQuiniela'),
        ),
        migrations.AddField(
            model_name='quinielagroup',
            name='draws',
            field=models.ManyToManyField(related_name='groups', verbose_name=b'Concursos', to='bet.DrawQuiniela'),
        ),
        migrations.AddField(
            model_name='quini6results',
            name='draw',
            field=models.OneToOneField(related_name='quini6_results', verbose_name=b'Sorteo', to='bet.Draw'),
        ),
        migrations.AddField(
            model_name='prizerequest',
            name='detail',
            field=models.ForeignKey(verbose_name=b'Detalle', to='bet.DetailCoupons'),
        ),
        migrations.AddField(
            model_name='prizemovement',
            name='winner',
            field=models.OneToOneField(related_name='movement', to='bet.BaseWinner'),
        ),
        migrations.AddField(
            model_name='nonprintedwinnercomm',
            name='winner',
            field=models.ForeignKey(related_name='commission_set', to='bet.BaseWinner'),
        ),
        migrations.AlterUniqueTogether(
            name='lotterytime',
            unique_together=set([('quiniela', 'type')]),
        ),
        migrations.AddField(
            model_name='lotoresults',
            name='draw',
            field=models.OneToOneField(related_name='loto_results', verbose_name=b'Sorteo', to='bet.Draw'),
        ),
        migrations.AddField(
            model_name='loto5results',
            name='draw',
            field=models.OneToOneField(related_name='loto5_results', verbose_name=b'Sorteo', to='bet.Draw'),
        ),
        migrations.AddField(
            model_name='loto5results',
            name='tra',
            field=models.OneToOneField(related_name='loto5_results', verbose_name=b'Tradicional', to='bet.ResultsSet5'),
        ),
        migrations.AlterUniqueTogether(
            name='gametax',
            unique_together=set([('province', 'game')]),
        ),
        migrations.AlterUniqueTogether(
            name='drawtime',
            unique_together=set([('game', 'week_day')]),
        ),
        migrations.AddField(
            model_name='detailquiniela',
            name='bet',
            field=models.ForeignKey(related_name='detailquiniela_set', to='bet.Bet'),
        ),
        migrations.AddField(
            model_name='detailquiniela',
            name='draws',
            field=models.ManyToManyField(related_name='detail_set', verbose_name=b'Sorteos', to='bet.DrawQuiniela'),
        ),
        migrations.AddField(
            model_name='detailquiniela',
            name='group',
            field=models.ForeignKey(related_name='detail_set', to='bet.QuinielaGroup', null=True),
        ),
        migrations.AddField(
            model_name='detailquiniela',
            name='redoblona',
            field=models.OneToOneField(related_name='apuesta', null=True, blank=True, to='bet.DetailQuiniela'),
        ),
        migrations.AddField(
            model_name='detailquiniela',
            name='ticket',
            field=models.ForeignKey(verbose_name=b'Ticket', blank=True, to='bet.Ticket', null=True),
        ),
        migrations.AddField(
            model_name='detailcoupons',
            name='bet',
            field=models.ForeignKey(related_name='detailcoupons_set', to='bet.Bet'),
        ),
        migrations.AddField(
            model_name='detailcoupons',
            name='coupon',
            field=models.ForeignKey(related_name='detailcoupon_set', to='bet.Coupon'),
        ),
        migrations.AddField(
            model_name='detailcoupons',
            name='ticket',
            field=models.OneToOneField(null=True, blank=True, to='bet.Ticket', verbose_name=b'Cup\xc3\xb3n'),
        ),
        migrations.AddField(
            model_name='detail',
            name='bet',
            field=models.OneToOneField(related_name='detail', to='bet.Bet'),
        ),
        migrations.AddField(
            model_name='detail',
            name='draw',
            field=models.ForeignKey(related_name='detail_set', verbose_name=b'Sorteo', to='bet.Draw'),
        ),
        migrations.AddField(
            model_name='detail',
            name='ticket',
            field=models.OneToOneField(null=True, blank=True, to='bet.Ticket', verbose_name=b'Ticket'),
        ),
        migrations.AddField(
            model_name='brincoresults',
            name='draw',
            field=models.OneToOneField(related_name='brinco_results', verbose_name=b'Sorteo', to='bet.Draw'),
        ),
        migrations.AddField(
            model_name='betmovement',
            name='bet',
            field=models.OneToOneField(related_name='movement', to='bet.Bet'),
        ),
        migrations.AddField(
            model_name='betcommissionmov',
            name='bet',
            field=models.ForeignKey(related_name='commission_set', to='bet.Bet'),
        ),
        migrations.AddField(
            model_name='betcommissionmov',
            name='draw',
            field=models.ForeignKey(to='bet.BaseDraw', null=True),
        ),
        migrations.AddField(
            model_name='agenmovement',
            name='payment',
            field=models.ForeignKey(related_name='movement_set', to='bet.PaymentCommissionMov', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='agencycoupon',
            unique_together=set([('game', 'number')]),
        ),
        migrations.CreateModel(
            name='ResultsSet12',
            fields=[
                ('resultsset6_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet6')),
                ('number7', models.PositiveIntegerField(verbose_name=b'Numero 7', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number8', models.PositiveIntegerField(verbose_name=b'Numero 8', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number9', models.PositiveIntegerField(verbose_name=b'Numero 9', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number10', models.PositiveIntegerField(verbose_name=b'Numero 10', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number11', models.PositiveIntegerField(verbose_name=b'Numero 11', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number12', models.PositiveIntegerField(verbose_name=b'Numero 12', validators=[django.core.validators.MaxValueValidator(99999)])),
            ],
            bases=('bet.resultsset6',),
        ),
        migrations.CreateModel(
            name='ResultsSet6Extra',
            fields=[
                ('resultsset6_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet6')),
                ('extra1', models.PositiveIntegerField(verbose_name=b'Extra 1', validators=[django.core.validators.MaxValueValidator(9)])),
                ('extra2', models.PositiveIntegerField(verbose_name=b'Extra 2', validators=[django.core.validators.MaxValueValidator(9)])),
            ],
            bases=('bet.resultsset6',),
        ),
        migrations.AddField(
            model_name='totobingoresults',
            name='draw',
            field=models.OneToOneField(related_name='totobingo_results', verbose_name=b'Sorteo', to='bet.DrawPreprinted'),
        ),
        migrations.AddField(
            model_name='telekinoresults',
            name='draw',
            field=models.OneToOneField(related_name='telekino_results', verbose_name=b'Sorteo', to='bet.DrawPreprinted'),
        ),
        migrations.AddField(
            model_name='telebingoresults',
            name='draw',
            field=models.OneToOneField(related_name='telebingo_results', verbose_name=b'Sorteo', to='bet.DrawPreprinted'),
        ),
        migrations.AlterUniqueTogether(
            name='quinielagroup',
            unique_together=set([('date', 'province', 'type')]),
        ),
        migrations.AddField(
            model_name='quini6results',
            name='rev',
            field=models.OneToOneField(related_name='quini6_rev', verbose_name=b'Revancha', to='bet.ResultsSet6'),
        ),
        migrations.AddField(
            model_name='quini6results',
            name='sie',
            field=models.OneToOneField(related_name='quini6_sie', verbose_name=b'Siempre Sale', to='bet.ResultsSet6'),
        ),
        migrations.AddField(
            model_name='quini6results',
            name='tra',
            field=models.OneToOneField(related_name='quini6_tra', verbose_name=b'Tradicional 1', to='bet.ResultsSet6'),
        ),
        migrations.AddField(
            model_name='quini6results',
            name='tra2',
            field=models.OneToOneField(related_name='quini6_tra2', verbose_name=b'Tradicional 2', to='bet.ResultsSet6'),
        ),
        migrations.AddField(
            model_name='preprintedwinnercomm',
            name='draw',
            field=models.ForeignKey(to='bet.DrawPreprinted'),
        ),
        migrations.AddField(
            model_name='lotoresults',
            name='des',
            field=models.OneToOneField(related_name='loto_des', verbose_name=b'Desquite', to='bet.ResultsSet6'),
        ),
        migrations.AddField(
            model_name='lotoresults',
            name='sos',
            field=models.OneToOneField(related_name='loto_sos', verbose_name=b'Sale o Sale', to='bet.ResultsSet6'),
        ),
        migrations.AddField(
            model_name='loteriaresults',
            name='draw',
            field=models.OneToOneField(related_name='loteria_results', verbose_name=b'Sorteo', to='bet.DrawPreprinted'),
        ),
        migrations.AddField(
            model_name='coupon',
            name='draw',
            field=models.ForeignKey(related_name='coupon_set', verbose_name=b'Sorteo', to='bet.DrawPreprinted'),
        ),
        migrations.AddField(
            model_name='brincoresults',
            name='tra',
            field=models.OneToOneField(related_name='brinco_results', verbose_name=b'Tradicional', to='bet.ResultsSet6'),
        ),
        migrations.CreateModel(
            name='ResultsSet15',
            fields=[
                ('resultsset12_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet12')),
                ('number13', models.PositiveIntegerField(verbose_name=b'Numero 13', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number14', models.PositiveIntegerField(verbose_name=b'Numero 14', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number15', models.PositiveIntegerField(verbose_name=b'Numero 15', validators=[django.core.validators.MaxValueValidator(99999)])),
            ],
            bases=('bet.resultsset12',),
        ),
        migrations.AddField(
            model_name='totobingoresults',
            name='poz',
            field=models.OneToOneField(related_name='totobingo', verbose_name=b'Pozo Millonario', to='bet.ResultsSet12'),
        ),
        migrations.AddField(
            model_name='lotoresults',
            name='tra',
            field=models.OneToOneField(related_name='loto_tra', verbose_name=b'Tradicional', to='bet.ResultsSet6Extra'),
        ),
        migrations.CreateModel(
            name='ResultsSet20',
            fields=[
                ('resultsset15_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='bet.ResultsSet15')),
                ('number16', models.PositiveIntegerField(verbose_name=b'Numero 16', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number17', models.PositiveIntegerField(verbose_name=b'Numero 17', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number18', models.PositiveIntegerField(verbose_name=b'Numero 18', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number19', models.PositiveIntegerField(verbose_name=b'Numero 19', validators=[django.core.validators.MaxValueValidator(99999)])),
                ('number20', models.PositiveIntegerField(verbose_name=b'Numero 20', validators=[django.core.validators.MaxValueValidator(99999)])),
            ],
            bases=('bet.resultsset15',),
        ),
        migrations.AddField(
            model_name='telekinoresults',
            name='rek',
            field=models.OneToOneField(related_name='telekino_rek', verbose_name=b'Rekino', to='bet.ResultsSet15'),
        ),
        migrations.AddField(
            model_name='telekinoresults',
            name='tel',
            field=models.OneToOneField(related_name='telekino_tel', verbose_name=b'Telekino', to='bet.ResultsSet15'),
        ),
        migrations.AddField(
            model_name='quinielaresults',
            name='res',
            field=models.OneToOneField(related_name='quiniela', verbose_name=b'Quiniela', to='bet.ResultsSet20'),
        ),
        migrations.AddField(
            model_name='loteriaresults',
            name='ord',
            field=models.OneToOneField(related_name='loteria_ord', verbose_name=b'Ordinaria', to='bet.ResultsSet20'),
        ),
    ]
