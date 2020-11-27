"""
Django settings for agencia24 project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = BASE_DIR

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'i1)hxlju1t0i0-7kq&!&usy*2^xvx2fn4d!oa(vbdfbf1f3hs8'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
	# 3rd party apps I added:
    'axes',
    'bootstrap3_datetime',
    'corsheaders',
    'django_extensions',
    'django_modalview',
    #'debug_toolbar',
    'django_unused_media',
    'django_user_agents',
    'fixture_magic',
    'longerusernameandemail',
    'mathfilters',
    'oauth2_provider', # add 'WSGIPassAuthorization On' to httpd.conf file
	'pagination',
    'passwords',
	'registration',
    'widget_tweaks',
	# My apps
    'bet',
    'simple_webservice',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pagination.middleware.PaginationMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'axes.middleware.FailedLoginMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
)

ROOT_URLCONF = 'agencia24.urls'

WSGI_APPLICATION = 'agencia24.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_ROOT, "templates"),
        ],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.core.context_processors.request',
                'bet.context_processors.debug',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.eggs.Loader',
            ],
            #'debug': False,
        },
    },
]
from django.template.loaders import eggs

if not DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        'django.template.loaders.eggs.Loader',
    )),
)


SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'es-ar'

TIME_ZONE = 'America/Argentina/Cordoba'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
MEDIA_URL = "/site_media/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "site_media", "_media")

STATIC_URL = '/site_media/static/'
STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, "site_media", "static"),
)

LOCALE_PATHS = (
    os.path.join(PROJECT_ROOT, 'locale').replace('\\', '/'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': 'A24 %(levelname)s [%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'agencia24_default': {
            'handlers': ['console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

#===============================================================================
# REGISTRATION!
#===============================================================================

ACCOUNT_ACTIVATION_DAYS = 5
SEND_ACTIVATION_EMAIL = False

EMAIL_HOST_USER = "no_reply_agencia24"
EMAIL_HOST_PASSWORD = "noresponder"
EMAIL_HOST = 'smtp.webfaction.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = '(Agencia24) <no_reply@agencia24.com.ar>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

REQUIRE_UNIQUE_EMAIL = False

#===============================================================================


LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login'


#===============================================================================
# MERCADOPAGO
#===============================================================================

MP_ACCESS_TOKEN = "TEST-2692549476916264-012507-3c26394260b30dfc3c78a004094cf36d__LA_LB__-162591608"

MP_CLIENT_ID = "2692549476916264"
MP_SECRET_KEY = "oB4gYLQz5lNhFRWOuXt0WNW4umSW2mvj"

#===============================================================================
# PDFKIT
#===============================================================================

WKHTMLTOPDF_PATH = ''

#===============================================================================
# PUSH
#===============================================================================

# IOS
IOS_PUSH_HEADERS = {
    "Authorization": "key=AIzaSyAuMBsR2J-i1Ne9gHH_1DL8jbHEBYJ5IgU",
    "content-Type": "application/json"
}

ANDROID_PUSH_HEADERS = {
    "Authorization": "key=AIzaSyD-dcMsjsQsWbJ1tPwjsnMdwym79mE8xDU",
    #"Authorization": "key=AIzaSyA-D9yqibGabnUb_5bqQZptdQFxBQndGuc",
    "content-Type": "application/json"
}

#===============================================================================
# DJANGO OAUTH TOOLKIT
#===============================================================================

OAUTH2_PROVIDER = {
    'ACCESS_TOKEN_EXPIRE_SECONDS': 600, # Seconds
    'REFRESH_TOKEN_EXPIRE_SECONDS': 6*3600,
}

CORS_ORIGIN_ALLOW_ALL = True

AUTHENTICATION_BACKENDS = (
    'oauth2_provider.backends.OAuth2Backend',
    # Uncomment following if you want to access the admin
    'django.contrib.auth.backends.ModelBackend'
)

#===============================================================================
# DJANGO-PASSWORDS!
#===============================================================================

PASSWORD_MIN_LENGTH = 4

PASSWORD_COMPLEXITY = { # You can omit any or all of these for no limit for that particular set
    "UPPER": 0,        # Uppercase
    "LOWER": 0,        # Lowercase
    "LETTERS": 0,      # Either uppercase or lowercase letters
    "DIGITS": 0,       # Digits
    "SPECIAL": 0,      # Not alphanumeric, space or punctuation character
    "WORDS": 0         # Words (alphanumeric sequences separated by a whitespace or punctuation character)
}

#===============================================================================
#===============================================================================

QUINI6_MAX_NUMBER = 45
LOTO_MAX_NUMBER = 41
LOTO_MAX_EXTRA = 9
LOTO5_MAX_NUMBER = 36
BRINCO_MAX_NUMBER = 39

#===============================================================================
# DJANGO USER AGENT
#===============================================================================

# TODO!
# Cache backend is optional, but recommended to speed up user agent parsing
#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
#        'LOCATION': '127.0.0.1:11211',
#    }
#}

# Name of cache backend to cache user agents. If it not specified default
# cache alias will be used. Set to `None` to disable caching.
#USER_AGENTS_CACHE = 'default'

#===============================================================================
# DJANGO AXES
#===============================================================================

from django.utils.timezone import timedelta
AXES_COOLOFF_TIME =  timedelta(minutes=20) # Hours
AXES_LOCKOUT_TEMPLATE = 'registration/login.html'
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True

"""
AXES_LOGIN_FAILURE_LIMIT: The number of login attempts allowed before a record is created for the failed logins. Default: 3
AXES_LOCK_OUT_AT_FAILURE: After the number of allowed login attempts are exceeded, should we lock out this IP (and optional user agent)? Default: True
AXES_USE_USER_AGENT: If True, lock out / log based on an IP address AND a user agent. This means requests from different user agents but from the same IP are treated differently. Default: False
AXES_COOLOFF_TIME: If set, defines a period of inactivity after which old failed login attempts will be forgotten. Can be set to a python timedelta object or an integer. If an integer, will be interpreted as a number of hours. Default: None
AXES_LOGGER: If set, specifies a logging mechanism for axes to use. Default: 'axes.watch_login'
AXES_LOCKOUT_TEMPLATE: If set, specifies a template to render when a user is locked out. Template receives cooloff_time and failure_limit as context variables. Default: None
AXES_LOCKOUT_URL: If set, specifies a URL to redirect to on lockout. If both AXES_LOCKOUT_TEMPLATE and AXES_LOCKOUT_URL are set, the template will be used. Default: None
AXES_VERBOSE: If True, you'll see slightly more logging for Axes. Default: True
AXES_USERNAME_FORM_FIELD: the name of the form field that contains your users usernames. Default: username
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP: If True prevents to login from IP under particular user if attempts limit exceed, otherwise lock out based on IP. Default: False
"""

#===============================================================================

ADMINS = [('Developer', 'developer@liricus.com.ar')]
#DEBUG = False
#ALLOWED_HOSTS = ['*']

SUPPORTED_IMPORT_EXT = ('.csv',)
EXTRACT_SEPARATOR = '*'

from local_settings_sf import *
