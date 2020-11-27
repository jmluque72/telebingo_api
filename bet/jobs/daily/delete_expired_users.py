from django_extensions.management.jobs import DailyJob

from registration.models import RegistrationProfile

class Job(DailyJob):
    help = "Delete users who didn't activate their account."

    def execute(self):
        RegistrationProfile.objects.delete_expired_users()
