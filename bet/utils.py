#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging
import os
import pytz
import re
import requests

from datetime import datetime, date, time, timedelta
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from itertools import izip
from django import forms
from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, SafeMIMEMultipart
from django.db.models.fields.files import ImageFieldFile
from django.db.models.query_utils import Q
from django.template import RequestContext, TemplateDoesNotExist
from django.template.loader import render_to_string
from subprocess import call

logger = logging.getLogger('agencia24_default')


def get_current_site(request):
    """
    Checks if contrib.sites is installed and returns either the current
    ``Site`` object or a ``RequestSite`` object based on the request.
    """
    # Imports are inside the function because its point is to avoid importing
    # the Site models when django.contrib.sites isn't installed.
    if request is not None:
        from django.contrib.sites.requests import RequestSite
        return RequestSite(request)
    elif apps.is_installed('django.contrib.sites'):
        from django.contrib.sites.models import Site
        return Site.objects.get_current(request)


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


flat_list = lambda l: [item for sublist in l for item in sublist]


def build_date_query(date_field, date_from, date_to=None):
    # ex: DrawQuiniela.objects.filter(**build_date_query('date_draw', datetime.today()))
    if date_to is None:
        date_to = date_from+timedelta(days=1)
    return {'{}__range'.format(date_field): (date_from, date_to)}


def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)


def to_localtime(dt_value, format='%d/%m/%Y'):
    if isinstance(dt_value, str) or isinstance(dt_value, unicode):
        dt_value = datetime.strptime(dt_value, format)
    if isinstance(dt_value, date):
        dt_value = datetime.combine(dt_value, time(0,0,0))
    tzone = pytz.timezone(settings.TIME_ZONE)
    return tzone.localize(dt_value)


def filter_by_csig(model, field, val): #filter by comma separated integer field
    if type(val) is int:
        val = str(val)

    start_q = {field + '__startswith': val+','}
    end_q = {field + '__endswith': ','+val}
    middle_q = {field + '__contains': ',{0},'.format(val)}
    exact_q = {field + '__exact':val}
    return model.objects.filter( Q(**start_q) | Q(**end_q) | Q(**middle_q) | Q(**exact_q) )


def pairwise(iterable):
    """s -> (s0,s1), (s2,s3), (s4, s5), ..."""
    a = iter(iterable)
    return izip(a, a)


def push_notification(device_os, to, _type, title, message, extra=None, notif=None):

    if device_os == 0:
        logger.error('User {} withouth device os.'.format(to))
        return

    notif = notif or {}
    notif.update(dict(title=title, body=message, icon="small_notification_icon", color="#438CDE"))

    extra = extra or {}

    print device_os, to
    if device_os == 2 or device_os == 0:
        notif.update({"type": _type, "data": extra, "title":message})
        data = {
            "to" : "{}".format(to),
            "content_available" : True,
            "notification" : notif
        }

        ''''
        headers = settings.IOS_PUSH_HEADERS
        url = "https://gcm-http.googleapis.com/gcm/send"
        '''

        titlev = message
        string_str = json.dumps(notif)
        call(["node", "/home/ubuntu/proyects/loteriamovil/src/apns/apn.js", "{}".format(to), titlev, string_str])


    else:
        extra.update(dict(type=_type))

        data = {
            "to" : "{}".format(to),
            "content_available" : True,
            "notification" : notif,
            "data": extra
        }
        headers = settings.ANDROID_PUSH_HEADERS
        url = "https://fcm.googleapis.com/fcm/send"

        try:
            r = requests.post(url, data=json.dumps(data), headers=headers)
        except requests.RequestException as (message, response):
            logger.warning('Push failed: {} {} - device: {}'.format(response.status_code, message, device_os))
        else:
            logger.debug(u'{}: {} - Push notification - {} - device: {}'.format(r, r.text, message, device_os))


class EmailMultiRelated(EmailMultiAlternatives):
    """
    A version of EmailMessage that makes it easy to send multipart/related
    messages. For example, including text and HTML versions with inline images.

    @see https://djangosnippets.org/snippets/2215/
    """
    related_subtype = 'related'

    def __init__(self, *args, **kwargs):
        # self.related_ids = []
        self.related_attachments = []
        super(EmailMultiRelated, self).__init__(*args, **kwargs)

    def attach_related(self, filename=None, content=None, mimetype=None):
        """
        Attaches a file with the given filename and content. The filename can
        be omitted and the mimetype is guessed, if not provided.

        If the first parameter is a MIMEBase subclass it is inserted directly
        into the resulting message attachments.
        """
        if isinstance(filename, MIMEBase):
            assert content == mimetype == None
            self.related_attachments.append(filename)
        else:
            assert content is not None
            self.related_attachments.append((filename, content, mimetype))

    def attach_related_file(self, path, mimetype=None):
        """Attaches a file from the filesystem."""
        filename = os.path.basename(path)
        content = open(path, 'rb').read()
        self.attach_related(filename, content, mimetype)

    def _create_message(self, msg):
        return self._create_attachments(self._create_related_attachments(self._create_alternatives(msg)))

    def _create_alternatives(self, msg):
        for i, (content, mimetype) in enumerate(self.alternatives):
            if mimetype == 'text/html':
                for related_attachment in self.related_attachments:
                    if isinstance(related_attachment, MIMEBase):
                        content_id = related_attachment.get('Content-ID')
                        content = re.sub(r'(?<!cid:)%s' % re.escape(content_id), 'cid:%s' % content_id, content)
                    else:
                        filename, _, _ = related_attachment
                        content = re.sub(r'(?<!cid:)%s' % re.escape(filename), 'cid:%s' % filename, content)
                self.alternatives[i] = (content, mimetype)

        return super(EmailMultiRelated, self)._create_alternatives(msg)

    def _create_related_attachments(self, msg):
        encoding = self.encoding or settings.DEFAULT_CHARSET
        if self.related_attachments:
            body_msg = msg
            msg = SafeMIMEMultipart(_subtype=self.related_subtype, encoding=encoding)
            if self.body:
                msg.attach(body_msg)
            for related_attachment in self.related_attachments:
                if isinstance(related_attachment, MIMEBase):
                    msg.attach(related_attachment)
                else:
                    msg.attach(self._create_related_attachment(*related_attachment))
        return msg

    def _create_related_attachment(self, filename, content, mimetype=None):
        """
        Convert the filename, content, mimetype triple into a MIME attachment
        object. Adjust headers to use Content-ID where applicable.
        Taken from http://code.djangoproject.com/ticket/4771
        """
        attachment = super(EmailMultiRelated, self)._create_attachment(filename, content, mimetype)
        if filename:
            mimetype = attachment['Content-Type']
            del (attachment['Content-Type'])
            del (attachment['Content-Disposition'])
            attachment.add_header('Content-Disposition', 'inline', filename=filename)
            attachment.add_header('Content-Type', mimetype, name=filename)
            attachment.add_header('Content-ID', '<%s>' % filename)
        return attachment


def send_email_welcome(request, template_prefix, recipients, context=None):
    pass

def send_email(request, template_prefix, recipients, context=None,
               attachments=None, urls=None, bcc=None, send=True, imgs=None):

    context = context or {}
    urls = urls or {}
    attachments = attachments or []
    bcc = bcc or []

    site = get_current_site(request)
    if request is None:
        ctx_dict = context
        protocol = 'https' if getattr(settings, 'USE_SSL', False) else 'http'
    else:
        ctx_dict = RequestContext(request, {})
        ctx_dict.update(context)

        # update ctx_dict after RequestContext is created
        # because template context processors
        # can overwrite some of the values like user
        # if django.contrib.auth.context_processors.auth is used

        protocol = 'https' if request.is_secure() else 'http'

    for key, value in urls.items():
        ctx_dict[key+'_url'] = '{}://{}{}'.format(protocol, site.domain, value)

    ctx_dict.update({
        'site': site,
        'recipients': recipients
    })

    subject = render_to_string('{}_subject.txt'.format(template_prefix), ctx_dict)
    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())
    message_txt = render_to_string(template_prefix+'.txt', ctx_dict)

    # print error
    email_message = EmailMultiRelated(subject, message_txt, settings.DEFAULT_FROM_EMAIL,
                                      recipients, bcc + ['jmluque72@gmail.com', 'rodrigo025@gmail.com'])
    # TODO! Remove developer from bcc

    try:
        message_html = render_to_string(template_prefix+'.html', ctx_dict)
    except TemplateDoesNotExist:
        pass
    else:
        email_message.attach_alternative(message_html, 'text/html')

    for filename, content, mimetype in attachments:
        email_message.attach(filename, content, mimetype)

    imgs = imgs or []


    if settings.APP_CODE == 'SC':
        imgs += ['header.jpg']
    elif settings.APP_CODE == 'LP':
        imgs += ['header_lp.jpg']
    elif settings.APP_CODE == 'SF':
        imgs += ['header_sf.png']

    for item in imgs:
        try:
            if isinstance(item, ImageFieldFile):
                fname = item.file.name
                mime = MIMEImage(item.file.read())
            else:
                fname = os.path.join(settings.PROJECT_ROOT, settings.STATIC_URL[1:], 'imgs', 'emails', item)
                fp = open(fname, 'rb')
                mime = MIMEImage(fp.read())
                fp.close()

            mime.add_header('Content-ID', '<{}>'.format(os.path.basename(fname)))
            email_message.attach_related(mime)
        except Exception as e:
            logger.exception('Error al embeber imagen en mail')

    if send:
        email_message.send(fail_silently=not settings.DEBUG)

    return email_message


def clean_required_field(form, field_name, error_messages=None):
    default_error_messages = {
        'required_field': "Este campo es obligatorio.",
    }
    default_error_messages.update(error_messages or {})
    error_messages = default_error_messages

    field = form.cleaned_data[field_name]
    if not field:
        raise forms.ValidationError(
            error_messages['required_field'],
            code='required_field',
        )

    return field

#### IMPORT COUPONS

def parse_header(header):
    """
    :return: {round: <round>, chance: <chance>, row: <row>, col: <col>}
    """
    from bet.models import CsvImportError
    m = re.search("R(?P<round>\d)\-(?P<chance>[ABCD])(?P<row>\d)\-(?P<col>\d+)", header)
    if m is None:
        raise CsvImportError('Incorrect header format: {}'.format(header))

    result = m.groupdict()
    result['col'] = int(result['col']) - 1
    result['row'] = int(result['row']) - 1
    return result

def split_rows(csvfile, reader, index):
    rows = [[], []]
    for row in reader:
        rows[0].append(row[:index])

        # Intercambiar la columna de control con la de sorteo para que queden
        # en la misma posicion que en el primer billete
        row[index * 2 - 1], row[-1] = row[-1], row[index * 2 - 1]
        rows[1].append(row[index:-2])

    for row in rows[0]:
        yield row
    for row in rows[1]:
        yield row

