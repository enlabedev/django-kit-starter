from pathlib import Path

import dj_database_url
from decouple import Csv, config
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

from ..tools.constance import *  # noqa

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DOTENV_PATH = BASE_DIR / ".env"
load_dotenv(DOTENV_PATH)

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", cast=Csv(), default="localhost,127.0.0.1"
)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://127.0.0.1,http://localhost,https://localhost",
    cast=Csv(),
)

DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    "unfold.contrib.simple_history",
    "unfold.contrib.constance",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = []

THIRD_PARTY_APPS = [
    "simple_history",
    "constance",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "apps/templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default="sqlite:///db.sqlite3")
    )
}
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

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_L10N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "apps/static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "apps/media"
MEDIA_URL = "/media/"

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

LANGUAGES = (
    ("en", _("English")),
    ("es", _("Spanish")),
)
LOCALE_PATHS = [BASE_DIR / "apps/locale"]

UNFOLD = {
    "SITE_TITLE": _("TRITON"),
    "SITE_HEADER": _("Data Control Panel"),
    "SITE_URL": "/",
    "SITE_ICON": lambda request: static("images/logo.svg"),
    "SITE_LOGO": lambda request: static("images/logo.svg"),
    "SITE_SYMBOL": "analytics",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "ENVIRONMENT": None,
    "LOGIN": {
        "image": lambda request: static("images/login.png"),
    },
    "SCRIPTS": [],
    "COLORS": {
        "primary": {
            "50": "239 246 255",
            "100": "219 234 254",
            "200": "191 219 254",
            "300": "147 197 253",
            "400": "96 165 250",
            "500": "59 130 246",
            "600": "37 99 235",
            "700": "29 78 216",
            "800": "30 64 175",
            "900": "30 58 138",
            "950": "23 37 84",
        },
    },
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "🇬🇧",
                "es": "🇪🇸",
            },
        },
    },
}
