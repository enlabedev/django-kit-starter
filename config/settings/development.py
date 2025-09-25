from .base import *  # noqa
from ..tools.constance import *  # noqa


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

INSTALLED_APPS += ["debug_toolbar"]  # noqa
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa

DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.cache.CachePanel",
]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    "IS_RUNNING_TESTS": False,
}

INTERNAL_IPS = ["127.0.0.1", "localhost"]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)  # noqa
