# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
AXES_FAILURE_LIMIT=10

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'lp_agencia24',    # Or path to database file if using sqlite3.
        'USER': 'postgres',
        'PASSWORD': '',
        #'PASSWORD': 'Zz9~K*s:U6h5e+,',
        'HOST': 'localhost',    # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',             # Set to empty string for default.
        'CONN_MAX_AGE': 600
    }
}

MP_SANDBOX = False
MP_ACCESS_TOKEN = "APP_USR-c73fced8-7a3e-47d7-8e62-dce156246fe3"
MP_CLIENT_ID = "1370527506332195"
MP_SECRET_KEY = "waDU6Rlz6nnVJihLN9Jm7Dq5lzmjpXuI"

# IOS
IOS_PUSH_HEADERS = {
    "Authorization": "key=AIzaSyB2pfw5MHTe3iajal6niPsKWaRruWuQooc",
    "content-Type": "application/json"
}
ANDROID_PUSH_HEADERS_TABLET = {
    "Authorization": "key=AIzaSyCBhq_afMrGKAuPNrZ6t-FpgBlH1BPOeQM",
    "content-Type": "application/json"
}

#===============================================================================
# PDFKIT
#===============================================================================

WKHTMLTOPDF_PATH = '/usr/local/bin/wkhtmltopdf'

#===============================================================================

DESARROLLO = False# not DEBUG

SITE_ID = 6

ADMINS = [('Developer', 'developer@liricus.com.ar')]
DEBUG = True
ALLOWED_HOSTS = ['*','sc.loteriamovil.com.ar', 'admin.sc.loteriamovil.com.ar','localhost']

"""LOGGING = {
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
        },
        'logfile': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': 'agencia24/error.log'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['logfile', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'agencia24_default': {
            'handlers': ['logfile', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}"""

EMAIL_HOST_USER = "no_reply_loteriamovil"
EMAIL_HOST_PASSWORD = "noresponder"
EMAIL_HOST = 'smtp.webfaction.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = '(Loteria movil) <no_reply@loteriamovil.com.ar>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

REQUIRE_UNIQUE_EMAIL = False


PASSWORD_MIN_LENGTH = 4

PASSWORD_COMPLEXITY = { # You can omit any or all of these for no limit for that particular set
    "UPPER": 0,        # Uppercase
    "LOWER": 0,        # Lowercase
    "LETTERS": 0,      # Either uppercase or lowercase letters
    "DIGITS": 0,       # Digits
    "SPECIAL": 0,      # Not alphanumeric, space or punctuation character
    "WORDS": 0         # Words (alphanumeric sequences separated by a whitespace or punctuation character)
}

APP_CODE="LP"
URL_DOMAIN="http://lp.loteriamovil.com.ar/"
