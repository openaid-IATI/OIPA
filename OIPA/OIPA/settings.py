# Django settings for OIPA project.

import os
import sys
from ast import literal_eval
from os import environ as env

from celery.schedules import crontab

# from tzlocal import get_localzone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DEBUG = literal_eval(env.get('OIPA_DEBUG', 'True'))
FTS_ENABLED = literal_eval(env.get('OIPA_FTS_ENABLED', 'True'))

LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_URL = '/logout'
DATA_UPLOAD_MAX_NUMBER_FIELDS = 3000

SECRET_KEY = env.get('OIPA_SECRET_KEY', 'PXwlMOpfNJTgIdQeH5zk39jKfUMZPOUK')

DATABASES = {
    'default': {
        'ENGINE': env.get(
            'OIPA_DB_ENGINE', 'django.contrib.gis.db.backends.postgis'
        ),
        'HOST': os.getenv('OIPA_DB_HOST', 'localhost'),
        'PORT': os.getenv('OIPA_DB_PORT', 5432),
        'NAME': os.getenv('OIPA_DB_NAME', 'oipa'),
        'USER': os.getenv('OIPA_DB_USER', 'oipa'),
        'PASSWORD': os.getenv('OIPA_DB_PASSWORD', 'oipa'),
        'CONN_MAX_AGE': int(os.getenv('OIPA_DB_CONN_MAX_AGE', 500))
    },
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (os.path.join(BASE_DIR, 'templates'),),
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            # 'loaders': [
            #    ('django.template.loaders.cached.Loader', [
            #        'django.template.loaders.filesystem.Loader',
            #        'django.template.loaders.app_directories.Loader',
            #    ]),
            # ],
        },
    },
]


def rel(*x):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)


sys.path.insert(0, rel('..', 'lib'))

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.get('OIPA_ALLOWED_HOSTS', '*').split()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.


# Celery is needed UTC
# TIME_ZONE = get_localzone().zone

TIME_ZONE = 'UTC'


# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

APPEND_SLASH = True

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# URL for static files
STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get(
    'OIPA_STATIC_ROOT',
    os.path.join(
        os.path.dirname(BASE_DIR),
        'public/static'))

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get(
    'OIPA_MEDIA_ROOT',
    os.path.join(
        os.path.dirname(BASE_DIR),
        'public/media'))

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static/'),
)

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'OIPA.wsgi.application'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.FileExportMiddleware',
]

ROOT_URLCONF = 'OIPA.urls'

INSTALLED_APPS = [
    # 'django_rq',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # 'grappelli',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.gis',
    'corsheaders',
    'common',
    'iati.apps.IatiConfig',
    'iati_organisation.apps.IatiOrganisationConfig',
    'iati_synchroniser.apps.IatiSynchroniserConfig',
    'geodata.apps.GeodataConfig',
    'currency_convert.apps.CurrencyConvertConfig',
    'traceability.apps.TraceabilityConfig',
    'api',
    'task_queue',
    'djsupervisor',
    'rest_framework',
    'rest_framework_csv',
    'django_extensions',
    'iati_vocabulary.apps.IatiVocabularyConfig',
    'iati_codelists.apps.IatiCodelistsConfig',
    'test_without_migrations',
    'rest_framework.authtoken',
    'iati.permissions',
    'rest_auth',
    'rest_auth.registration',
    'django_filters',
    'markdownify',
    'solr',
    'django_celery_beat'
]


RQ_SHOW_ADMIN_LINK = True

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.CustomPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'api.renderers.PaginatedCSVRenderer',
        'api.renderers.XlsRenderer',
        'api.renderers.IATIXMLRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    )
}

RQ_REDIS_URL = env.get('OIPA_RQ_REDIS_URL', 'redis://localhost:6379/0')

RQ_QUEUES = {
    'default': {
        'URL': RQ_REDIS_URL,
        'DEFAULT_TIMEOUT': 10800,  # 3 hours
    },
    'parser': {
        'URL': RQ_REDIS_URL,
        'DEFAULT_TIMEOUT': 5400,
    },
    'export': {
        'URL': RQ_REDIS_URL,
        'DEFAULT_TIMEOUT': 5400,
    },
    'document_collector': {
        'URL': RQ_REDIS_URL,
        'DEFAULT_TIMEOUT': 5400,
    },
    'solr': {
        'URL': RQ_REDIS_URL,
        'DEFAULT_TIMEOUT': 10800,
    }
}

GRAPPELLI_ADMIN_TITLE = 'OIPA admin'
ADMINFILES_UPLOAD_TO = 'csv_files'

CORS_ORIGIN_ALLOW_ALL = True
CORS_URLS_REGEX = r'^/api/.*$'
CORS_ALLOW_METHODS = ('GET',)

IATI_PARSER_DISABLED = False
CONVERT_CURRENCIES = True
ROOT_ORGANISATIONS = []

ERROR_LOGS_ENABLED = literal_eval(env.get('OIPA_ERROR_LOGS_ENABLED', 'True'))

DEFAULT_LANG = 'en'
# django-all-auth
ACCOUNT_EMAIL_VERIFICATION = 'none'

# django-rest-auth
REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'api.permissions.serializers.UserSerializer',
}

REST_AUTH_REGISTER_SERIALIZERS = {
    'REGISTER_SERIALIZER': 'api.permissions.serializers.RegistrationSerializer'
}

# EXPORT_COMMENT = 'Published with tools developed by Zimmerman & Zimmerman'

FIXTURE_DIRS = (
    os.path.join(BASE_DIR, '../fixtures/'),
)

CKAN_URL = env.get('OIPA_CKAN_URL', 'https://iati-staging.ckan.io')

API_CACHE_SECONDS = int(env.get('OIPA_API_CACHE_SECONDS', 0))

CACHES = {
    'default': {
        'BACKEND': env.get(
            'OIPA_CACHES_DEFAULT_BACKEND', 'redis_cache.RedisCache'
        ),
        'LOCATION': env.get('OIPA_CACHES_DEFAULT_LOCATION', 'localhost:6379'),
    },
    'api': {
        'BACKEND': env.get(
            'OIPA_CACHES_DEFAULT_BACKEND', 'redis_cache.RedisCache'
        ),
        'LOCATION': env.get('OIPA_CACHES_DEFAULT_LOCATION', 'localhost:6379'),
    }
}

OIPA_LOG_LEVEL = env.get('OIPA_LOG_LEVEL', 'ERROR')

# These settings are overriden in development_settings and
# produduction_settings modules:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        # Useful for local development:
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        # All other errors:
        '': {
            'handlers': ['console'],
            'level': OIPA_LOG_LEVEL,
            'propagate': False,
        },
        # IATI Parser related errors:
        'iati.parser': {
            'handlers': ['console'],
            'level': OIPA_LOG_LEVEL,
            'propagate': False,
        },
        # Django-related errors:
        'django': {
            'handlers': ['console'],
            'level': OIPA_LOG_LEVEL,
            'propagate': False,
        },
    },
}

REST_FRAMEWORK_EXTENSIONS = {
    'DEFAULT_USE_CACHE': 'api',
    # reset cache every x seconds:
    'DEFAULT_CACHE_RESPONSE_TIMEOUT': 1 * 60 * 60 * 24 * 7,  # 1 week
}

# DATA PLUGINS is a dict with data which is not related to the IATI data.
# For example, for M49 Regions import, add such code block it in the
# local_settings.py:

# import os
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
# DATA_PLUGINS = {
#     'codelist': {
#        'm49_region_file': '{base_dir}/plugins/data/{filename}'.format(
#             base_dir=BASE_DIR, filename='regions.json')
#     }
# }
DATA_PLUGINS = {}

# A setting indicating whether to save XML datasets (files) to local machine or
# not:
DOWNLOAD_DATASETS = False

# CELERY CONFIG
CELERY_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # limiting the number of reserved tasks.
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_ROUTES = {'task_queue.tasks.revoke_all_tasks': {'queue':
                                                               'revoke_queue'}}
CELERY_BROKER_URL = 'amqp://localhost'
CELERY_RESULT_BACKEND = 'rpc://localhost'
# 'db+postgresql://oipa:oipa@localhost/oipa'
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_IMPORTS = 'iati.PostmanJsonImport.tasks'
CELERY_BEAT_SCHEDULE = {
    'getting_postman-api': {
        'task': 'iati.PostmanJsonImport.tasks.get_postman_api',
        'schedule': crontab(minute=0, hour=0),
    },
}

SOLR = {
    'indexing': False,
    'url': 'http://localhost:8983/solr',
    'cores': {
        'activity': 'activity',
        'budget': 'budget',
        'codelist': {
            'country': 'codelist-country',
            'region': 'codelist-region'
        },
        'dataset': 'dataset',
        'datasetnote': 'datasetnote',
        'organisation': 'organisation',
        'publisher': 'publisher',
        'result': 'result',
        'transaction': 'transaction'
    }
}

VALIDATION = {
    'host': 'https://test-validator.iatistandard.org',
    'api': {
        'root': '/api',
        'version': '/v1',
        'urls': {
            'post_file': '/iati-testfiles/file/source',
            'start_validation': '/iati-testdatasets/{validation_id}',
            'get_json_file': '/iati-files/file/json/{json_file}',
            'get_json_file_ad_hoc': '/iati-testfiles/file/json/{json_file}',
        },
        'max_loop_process': 50,
        'sleep_second_process': 5,
        'valid_status': 'success',
        'retry': {
            'max_retries': 5,
        }
    }
}

try:
    from .local_settings import *  # noqa: F401, F403
except ImportError:
    pass
