#from datetime import datetime

#from django.core.mail import send_mail
from django_extensions.management.jobs import DailyJob

from bet import models

class Job(DailyJob):
    help = "Set userprofile's playtoday attr to 0"

    def execute(self):
        rows = models.UserProfile.objects.filter(playtoday__gt=0).update(playtoday=0)
        """try:
            p = models.UserProfile.objects.get(user__username='luciano')
            message = 'Cron executed at {} localtime - {} utctime. ' \
                      '{} profile/s updated.'.format(datetime.now().strftime('%Y-%m-%d %H:%M'),
                                                     datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
                                                     rows)

            send_mail('Reset PlayToday', message, 'from@example.com',
                [p.user.email], fail_silently=True)
        except models.UserProfile.DoesNotExist:
            pass"""
