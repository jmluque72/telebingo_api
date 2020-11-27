# scripts/delete_all_questions.py
from bet import models
import requests
import json
import datetime
from django.core.mail import EmailMultiAlternatives
from subprocess import call
from bet.utils import enum, push_notification, send_email, get_current_site, split_rows, parse_header
from django.conf import settings

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

def run():

    pendings = models.Messages.objects.filter(startprocess=False,finished=False)
    for p in pendings:

        p.startprocess = True
        p.save()
        data = {}
        messages = models.MessagesSend.objects.filter(message=p,send=False)
        for m in messages:
            
            try:
                #push_notification(self.device_os, self.devicegsmid, _type, title, message, data, notif)
                #if m.userprofile.devicegsmid != 'fwZGdUTf2XU:APA91bEAFi9pQPfl8kAzzwX3NwkHctCdQKrrVOK6cRM-Qu4KZVxUM9MSUzE9QBbjEcQpY09W4mqq9mwDfo0A_poJRQTXnBmQ1jm_svXOHdpmWv2-4nL_ZVRBCOgqRpvKjE-aVFWudLQ8vhRa4I5JE0NgpL7wsaWx7A':
                #    continue

                if settings.APP_CODE == 'SC':
                    push_notification(m.userprofile.device_os, m.userprofile.devicegsmid, None, "Loteriamovil Santa Cruz", p.text, data, data)
                else:
                    push_notification(m.userprofile.device_os, m.userprofile.devicegsmid, None, "Agencia24 Notifiacion", p.text, data, data)

                m.send = True
                #m.save()
                p.process = p.process + 1
                #p.save()

            except Exception as e:
                print e
                pass

        p.startprocess = False
        p.finished = True
        p.save()

