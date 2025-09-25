import logging
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from .managers import BaseManager

logger = logging.getLogger(__name__)


class User(AbstractUser):
    id = models.UUIDField(
        _("ID"), primary_key=True, default=uuid.uuid4, editable=False
    )
    last_login_ip = models.GenericIPAddressField(
        _("Last login IP"), null=True, blank=True, protocol="both"
    )
    password_change_required = models.BooleanField(
        _("Password change required"), default=True
    )
    last_password_change_at = models.DateTimeField(
        _("Last password change at"), default=timezone.now
    )
    failed_login_attempts = models.PositiveSmallIntegerField(
        _("Failed login attempts"), default=0, validators=[MaxValueValidator(3)]
    )
    locked_until = models.DateTimeField(
        _("Locked until"), null=True, blank=True
    )
    is_temporary = models.BooleanField(_("Is temporary"), default=False)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["last_login"]),
        ]

    def __str__(self):
        return self.username


class BaseModel(models.Model):
    """
    Abstract base model for entities belonging to a specific tenant.
    """

    id = models.UUIDField(
        _("ID"), primary_key=True, default=uuid.uuid4, editable=False
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)

    objects = BaseManager()
    history = HistoricalRecords(inherit=True)

    def is_deleted(self):
        """
        Returns True if the object is soft-deleted, False otherwise.
        """
        return self.deleted_at is not None

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AuditModel(BaseModel):
    """
    Abstract model that adds audit fields to derived models.
    User fields are limited to staff for increased security in critical operations.
    """

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="%(class)s_created",
        limit_choices_to={"is_staff": True},
        null=True,
        blank=True,
        verbose_name=_("Created by"),
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
        limit_choices_to={"is_staff": True},
        verbose_name=_("Updated by"),
    )
    deleted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_deleted",
        limit_choices_to={"is_staff": True},
        verbose_name=_("Deleted by"),
    )
    blocked_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Blocked at")
    )
    blocked_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_blocked",
        verbose_name=_("Blocked by"),
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SimpleAuditModel(models.Model):
    """
    Abstract model that adds simple audit fields to derived models.
    Includes auto-incremental ID, automatic creation and update timestamps.
    Useful for models that require basic change tracking without soft delete.
    """

    id = models.BigAutoField(_("ID"), primary_key=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)
    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SimpleModel(models.Model):
    """
    Abstract model that adds basic description and active status fields to derived models.
    Useful for catalogs and simple entities that require activation/deactivation.
    """

    description = models.CharField(_("Description"), max_length=250)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    deleted_at = models.DateTimeField(_("Deleted at"), null=True, blank=True)
    history = HistoricalRecords(inherit=True)

    def __str__(self):
        return self.description

    class Meta:
        abstract = True
        ordering = ["description"]


class Profile(AuditModel):
    """
    One-to-one profile model to store extra user data.
    This is preferred over adding many fields to the User model directly.
    """

    user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="profile"
    )
    bio = models.TextField(blank=True, null=True)
    avatar = models.ImageField(
        upload_to="images/avatars/", null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"
