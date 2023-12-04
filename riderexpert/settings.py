"""
Django settings for riderexpert project.

Generated by 'django-admin startproject' using Django 4.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
from pathlib import Path
from datetime import timedelta


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE_PATH = os.path.join(BASE_DIR, "logs", "logfile.log")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-q--wp)4sq%ly16dr1&0(+71jihbdwxsg#%o7qk7o67(qru1-+&"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_extensions",
    "rest_framework_simplejwt",
    "accounts",
    "order",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "riderexpert.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "riderexpert.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "custom": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "riderexpert",
        "USER": "riderexpert",
        "PASSWORD": "testdatabase",
        "HOST": "db",
        "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
    },
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DJANGO_DB_NAME", "default_db_name"),
        "USER": os.environ.get("DJANGO_DB_USER", "default_db_user"),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", "default_db_password"),
        "HOST": os.environ.get("DJANGO_DB_HOST", "localhost"),
        "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
    },
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Custom User settings
AUTH_USER_MODEL = "accounts.CustomUser"

# Email settings
EMAIL_HOST = "sandbox.smtp.mailtrap.io"
EMAIL_HOST_USER = "a1b94a501906b4"
EMAIL_HOST_PASSWORD = "8fcd935d4f88a6"
EMAIL_PORT = "2525"
DEFAULT_FROM_EMAIL = "info@emjay.dev"
EMAIL_USE_TLS = True


# Authentication settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # Other authentication classes as needed
    ),
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",  # Set the desired minimum log level for the console handler (INFO includes ERROR and WARNING)
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",  # Set the root logger level to INFO
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",  # Set the Django logger level to INFO
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",  # Set the Django request logger level to INFO
            "propagate": True,
        },
        "rest_framework": {
            "handlers": ["console"],
            "level": "INFO",  # Set the Django REST framework logger level to INFO
            "propagate": True,
        },
    },
}
