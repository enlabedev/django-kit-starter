# Import signals to ensure they are loaded when the app starts
from . import signals  # noqa

default_app_config = "apps.core.apps.CoreConfig"
