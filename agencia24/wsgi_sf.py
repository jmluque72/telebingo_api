"""
WSGI config for loteriamovil project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""
import os, sys, site

# Add the site-packages of the chosen virtualenv to work with
site.addsitedir('/home/ubuntu/proyects/loteriamovil/lib/python2.7/site-packages')

# Add the app's directory to the PYTHONPATH
sys.path.append('/home/ubuntu/proyects/loteriamovil/lib/python2.7')
sys.path.append('/home/ubuntu/proyects/loteriamovil')
sys.path.append('/home/ubuntu/proyects/loteriamovil/src')

os.environ['DJANGO_SETTINGS_MODULE'] = "agencia24.settings_sf"

if os.getenv('HOME') == '/home/ubuntu':
    # Activate your virtual env
    activate_env = "/home/ubuntu/proyects/loteriamovil/bin/activate_this.py"

    execfile(activate_env, dict(__file__=activate_env))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
#import django.core.handlers.wsgi
#application = django.core.handlers.wsgi.WSGIHandler()
