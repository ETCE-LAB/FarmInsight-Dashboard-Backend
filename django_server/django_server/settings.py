"""
Django settings for django_server project.

Generated by 'django-admin startproject' using Django 5.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import environ
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-j_qnae2dq2!wltq1%ca7gku^ol8o7^t9-1xg5)gjw*1kcl)!d8'

# Initialize environment variables
env = environ.Env()

# Development-specific environment variables
dev_env_path = BASE_DIR / "environment" / ".env.dev"
if os.path.exists(dev_env_path):
    environ.Env.read_env(dev_env_path)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

INFLUXDB_CLIENT_SETTINGS = {
    'url': env('INFLUXDB_URL'),
    'token': env('INFLUXDB_INIT_TOKEN'),
    'org': env('DOCKER_INFLUXDB_INIT_ORG')
}

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG") == "True"

ALLOWED_HOSTS = env("ALLOWED_HOSTS").split(",")

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS").split(",")

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS").split(",")

# Camera snapshot storage config
MEDIA_URL = '/'
MEDIA_ROOT = BASE_DIR
SITE_URL = "http://localhost:8000"

# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'farminsight_dashboard_backend.apps.FarminsightDashboardBackendConfig',
    'rest_framework',
    'oauth2_provider',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "django_server.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'farminsight_dashboard_backend' / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = "django_server.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
        # "BACKEND": "channels_redis.core.RedisChannelLayer",
        # "CONFIG": {
        #    "hosts": [("127.0.0.1", 6379)],
        #},
    },
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "database" / "db.sqlite3",
    }
}

# For logging in the console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',  # Set to INFO or WARNING in production
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',  # Set to INFO in production
            'propagate': True,
        },
        'farminsight_dashboard_backend': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'farminsight_dashboard_backend.Userprofile'


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/api/login/'

OAUTH2_PROVIDER = {
    'OIDC_ENABLED': True,
    'OIDC_ISS_ENDPOINT': env('OIDC_ISS_ENDPOINT'),
    'OIDC_RSA_PRIVATE_KEY': open(os.path.join(BASE_DIR, 'rsa', 'oidc.key')).read(),
    'SCOPES': {"openid": ''},
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
    ),
    'EXCEPTION_HANDLER': 'farminsight_dashboard_backend.exceptions.exceptions.custom_exception_handler'
}

URL_PREFIX = env('URL_PREFIX', default='api/')

# 0 or negative for indefinite duration
API_KEY_VALIDATION_DURATION_DAYS = int(env('API_KEY_VALIDATION_DURATION_DAYS', default='30'))
