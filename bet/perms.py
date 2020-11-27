from django.db import models
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# PARA CREAR PERMISOS QUE NO DEPENDEN DE UN MODELO
#
# from bet.perms import GlobalPermission
# gp = GlobalPermission.objects.create(codename='can_do_it', name='Can do it')
# Once this is run you can add that permission to users/group like any other permission.

class GlobalPermissionManager(models.Manager):

    def get_query_set(self):
        return super(GlobalPermissionManager, self).\
            get_query_set().filter(content_type__name='global_permission')


class GlobalPermission(Permission):
    """A global permission, not attached to a model"""

    objects = GlobalPermissionManager()

    class Meta:
        proxy = True
        verbose_name = "global_permission"


    def save(self, *args, **kwargs):
        ct, created = ContentType.objects.get_or_create(
            model=self._meta.verbose_name, app_label=self._meta.app_label,
        )
        self.content_type = ct
        super(GlobalPermission, self).save(*args)

