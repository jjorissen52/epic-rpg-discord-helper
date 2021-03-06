"""
Django settings for epic_reminder project.

Generated by 'django-admin startproject' using Django 3.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from epic_reminder import utils

BASE_DIR = str(Path(__file__).resolve().parent.parent)
# { start } generated using python manage.py populate_settings

environment_defaults = {
    "DEBUG": "1",
    "SECRET_KEY": "n8s0=e-jypoxyoe1+)n^u^kwl&=y2g9_-j9-f^@qw33i9v+ax0",
    "INITIAL_ADMIN_USERNAME": "admin",
    "INITIAL_ADMIN_EMAIL": "example@email.com",
    "INITIAL_ADMIN_PASSWORD": "password123",
    "ALLOWED_HOSTS": ["*"],
    "USE_SQLITE": "1",
    "DATABASE_NAME": "epic",
    "DATABASE_USER": "postgres",
    "DATABASE_PASSWORD": "superstrongpassword123",
    "DATABASE_HOST": "127.0.0.1",
    "DATABASE_PORT": "5432",
    "DISCORD_TOKEN": "TOKEN",
}

ENV = utils.get_runtime_parameters(environment_defaults)

DEBUG = ENV.DEBUG
SECRET_KEY = ENV.SECRET_KEY
INITIAL_ADMIN_USERNAME = ENV.INITIAL_ADMIN_USERNAME
INITIAL_ADMIN_EMAIL = ENV.INITIAL_ADMIN_EMAIL
INITIAL_ADMIN_PASSWORD = ENV.INITIAL_ADMIN_PASSWORD
ALLOWED_HOSTS = ENV.ALLOWED_HOSTS
USE_SQLITE = ENV.USE_SQLITE
DATABASE_NAME = ENV.DATABASE_NAME
DATABASE_USER = ENV.DATABASE_USER
DATABASE_PASSWORD = ENV.DATABASE_PASSWORD
DATABASE_HOST = ENV.DATABASE_HOST
DATABASE_PORT = ENV.DATABASE_PORT
DISCORD_TOKEN = ENV.DISCORD_TOKEN


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = (
    [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "epic",
    ]
    + ["django_extensions"]
    if DEBUG
    else []
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "epic_reminder.urls"

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

WSGI_APPLICATION = "epic_reminder.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases


if ENV.USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, f"{ENV.DATABASE_NAME}.sqlite3"),
        }
    }
else:
    DATABASE_HOST = ENV.DATABASE_HOST
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": ENV.DATABASE_NAME,
            "USER": ENV.DATABASE_USER,
            "PASSWORD": ENV.DATABASE_PASSWORD,
            "HOST": DATABASE_HOST,
            "PORT": ENV.DATABASE_PORT,
        }
    }


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",  # Change to DEBUG for SQL logging
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        # Custom handler which we will use with logger 'django'.
        # We want errors/warnings to be logged when DEBUG=False
        "console_on_not_debug": {
            "level": "WARNING",
            "filters": ["require_debug_false"],
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins", "console_on_not_debug"],
            "level": "DEBUG",
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
