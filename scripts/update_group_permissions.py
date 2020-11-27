from django.contrib.auth.models import Group, Permission
from bet.perms import GlobalPermission

def update_permissions():
    perms = {
        ('Can view draw', 'view_draw'),
        ('Can edit draw', 'edit_draw'),
        ('Can edit draw', 'edit_draw'),

        ('Can edit agencies', 'edit_agency'),
    }

    for name, codename in perms:
        perm, created = GlobalPermission.objects.get_or_create(name=name,
                                                               codename=codename)
        if created:
            print 'creating permission {0}'.format(name)


# admin is just a dump from [p.codename for p in Permission.objects.all()] for now
group_perms = {
    u'admin': {
        'perms': tuple([p.codename for p in Permission.objects.all()])
    },
    u'agenciero': {
        'perms': (u'view_draw',)
    },
    u'user': {
        'perms': ()
    },
}

def run():
    update_permissions()

    for group_name in group_perms.keys():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print 'creating group {0}'.format(group_name)
        print 'adding permissions for {0}'.format(group_name)
        for perm_codename in group_perms[group_name]['perms']:
            perm = Permission.objects.get(codename=perm_codename)
            group.permissions.add(perm)
        group.save()
