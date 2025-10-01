import logging

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """
    Application configuration for the 'core' app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = _("Core")

    def ready(self) -> None:
        try:
            import apps.core.signals  # noqa: F401
        except ImportError as e:
            logger.error(
                _("Failed to import signals module: %(error)s"),
                {"error": e},
                exc_info=True,
            )
