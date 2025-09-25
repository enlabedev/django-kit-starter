from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        try:
            import apps.core.signals  # noqa: F401
        except ImportError as e:
            logger = self.get_logger()
            logger.error(f"Failed to import signals module: {e}", exc_info=True)
