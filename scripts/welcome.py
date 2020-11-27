import pytz, datetime, logging, random
from datetime import timedelta

from django.conf import settings
from bet import models, utils
from datetime import datetime
from django.core.files import File
from bet.utils import  send_email_welcome
from django.utils import timezone


TZ = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger('agencia24_default')

def run():

    now = timezone.now()
    try:

        userp = models.UserProfile.objects.filter(user__username='ro@ro.com').first()
        
        context = {"user": userp.user}
        attachs = []
        user_email = ""

        email = send_email_welcome(None, 'emails/welcome', ["jmluque72@gmail.com", "rodrigo025@gmail.com"], context=context,
                       attachments=attachs, bcc=[user_email], send=True, imgs=None)


    except Exception as e:
        print e

