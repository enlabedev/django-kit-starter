from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", _("Administrator")
    CUSTOMER = "CUSTOMER", _("Customer")
    GUEST = "GUEST", _("Guest")


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    SUSPENDED = "SUSPENDED", _("Suspended")


class DocumentDataType(models.TextChoices):
    ALPHANUMERIC = "ALN", _("Alphanumeric")
    NUMERIC = "NUM", _("Numeric")


class ContributorType(models.TextChoices):
    NATIONALS_ONLY = "N", _("Nationals only")
    FOREIGNERS_ONLY = "F", _("Foreigners only")
    NATIONALS_AND_FOREIGNERS = "B", _("Nationals and Foreigners")


class DocumentLengthType(models.TextChoices):
    EXACT = "E", _("Exact")
    MAXIMUM = "M", _("Maximum")
