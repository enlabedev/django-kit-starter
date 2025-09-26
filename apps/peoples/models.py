from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models.base import AuditModel
from apps.core.models.catalogs import IdentityDocumentType
from apps.core.models.location import LocationMixin
from apps.core.validators import (
    DocumentNumberValidator,
    PhoneNumberValidator,
    image_validator,
    validate_district_in_province,
    validate_province_in_department,
)

from .choices import Gender, PersonType
from .managers import AddressManager, PersonManager


def avatar_upload_to(instance, filename):
    """Genera la ruta de almacenamiento para avatares."""
    identifier = instance.id if instance.id else instance.number
    return f"avatars/{identifier}/{filename}"


User = get_user_model()


class Person(AuditModel):
    """
    Represents a natural or legal person (customer, supplier, etc.).
    """

    objects = PersonManager()

    type = models.CharField(
        _("Person Type"),
        max_length=20,
        choices=PersonType.choices,
        default=PersonType.CUSTOMER,
        db_index=True,
        help_text=_(
            "Specifies if this is a customer, supplier, or other type."
        ),
    )

    identity_document_type = models.ForeignKey(
        IdentityDocumentType,
        on_delete=models.PROTECT,
        verbose_name=_("Identity Document Type"),
        related_name="persons",
        help_text=_("Type of identification document (DNI, RUC, etc.)."),
    )

    number = models.CharField(
        _("Document Number"),
        max_length=20,
        help_text=_("Document number (e.g., DNI, RUC)."),
        db_index=True,
    )
    first_name = models.CharField(
        _("First Name"),
        max_length=250,
        blank=True,
        null=True,
        help_text=_("Required for natural persons."),
    )

    last_name = models.CharField(
        _("Last Name"),
        max_length=250,
        blank=True,
        null=True,
        help_text=_("Required for natural persons."),
    )

    business_name = models.CharField(
        _("Business Name"),
        max_length=250,
        blank=True,
        null=True,
        help_text=_("Required for legal persons (companies)."),
    )

    birth_date = models.DateField(
        _("Birth Date"),
        null=True,
        blank=True,
        help_text=_("Only for natural persons."),
    )

    gender = models.CharField(
        _("Gender"),
        max_length=1,
        choices=Gender.choices,
        blank=True,
        null=True,
        help_text=_("Only for natural persons."),
    )
    email = models.EmailField(
        _("Email"),
        max_length=250,
        db_index=True,
        help_text=_("Primary email address for communications."),
    )

    telephone = models.CharField(
        _("Telephone"),
        max_length=20,
        null=True,
        blank=True,
        validators=[PhoneNumberValidator(allow_international=True)],
        help_text=_("Landline phone number."),
    )

    mobile = models.CharField(
        _("Mobile"),
        max_length=20,
        null=True,
        blank=True,
        validators=[PhoneNumberValidator(require_mobile=True)],
        help_text=_("Mobile phone number."),
    )
    avatar = models.ImageField(
        _("Avatar"),
        upload_to=avatar_upload_to,
        validators=[image_validator],
        blank=True,
        null=True,
        help_text=_(
            "Profile image. Max size: 500KB. Formats: JPEG, PNG, GIF, WebP."
        ),
    )

    approved_at = models.DateTimeField(
        _("Approved At"),
        null=True,
        blank=True,
        editable=False,
        help_text=_("Timestamp when the person was approved."),
    )

    rejected_at = models.DateTimeField(
        _("Rejected At"),
        null=True,
        blank=True,
        editable=False,
        help_text=_("Timestamp when the person was rejected."),
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("Approved By"),
        related_name="approved_persons",
        null=True,
        blank=True,
        editable=False,
    )

    rejected_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("Rejected By"),
        related_name="rejected_persons",
        null=True,
        blank=True,
        editable=False,
    )

    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("User"),
        related_name="person",
        null=True,
        blank=True,
        help_text=_("Associated user account for authentication."),
    )

    @property
    def full_name(self):
        """Returns the complete name for display."""
        if self.business_name:
            return self.business_name
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or _(
            "(No name)"
        )

    @property
    def is_natural_person(self):
        """Check if this is a natural person (individual)."""
        return bool(self.first_name or self.last_name)

    @property
    def is_legal_person(self):
        """Check if this is a legal person (company)."""
        return bool(self.business_name)

    @property
    def is_approved(self):
        """Check if the person has been approved."""
        return self.approved_at is not None

    @property
    def is_rejected(self):
        """Check if the person has been rejected."""
        return self.rejected_at is not None

    @property
    def approval_status(self):
        """Get the current approval status."""
        if self.is_approved:
            return "approved"
        elif self.is_rejected:
            return "rejected"
        return "pending"

    def __str__(self):
        return f"{self.full_name} ({self.number})"

    def clean(self):
        """Validate model data before saving."""
        super().clean()
        errors = {}

        if self.identity_document_type and self.number:
            try:
                validator = DocumentNumberValidator(self.identity_document_type)
                validator(self.number)
            except ValidationError as e:
                errors["number"] = e.messages

        if not self.business_name and not (self.first_name and self.last_name):
            errors["business_name"] = [
                _(
                    "You must provide a business name OR both first and last name."
                )
            ]

        if self.approved_at and self.rejected_at:
            errors["__all__"] = [
                _("A person cannot be both approved and rejected.")
            ]

        if self.birth_date:
            from django.utils import timezone

            if self.birth_date > timezone.now().date():
                errors["birth_date"] = [
                    _("Birth date cannot be in the future.")
                ]

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        if self.business_name:
            self.gender = None
            self.birth_date = None

        self.full_clean()
        super().save(*args, **kwargs)

    def approve(self, user):
        """Approve this person."""
        from django.utils import timezone

        if self.is_approved:
            raise ValidationError(_("This person is already approved."))

        self.approved_at = timezone.now()
        self.approved_by = user
        self.rejected_at = None
        self.rejected_by = None
        self.save(
            update_fields=[
                "approved_at",
                "approved_by",
                "rejected_at",
                "rejected_by",
            ]
        )

    def reject(self, user, reason=None):
        """Reject this person."""
        from django.utils import timezone

        if self.is_rejected:
            raise ValidationError(_("This person is already rejected."))

        self.rejected_at = timezone.now()
        self.rejected_by = user
        self.approved_at = None
        self.approved_by = None
        self.save(
            update_fields=[
                "rejected_at",
                "rejected_by",
                "approved_at",
                "approved_by",
            ]
        )

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("Persons")
        ordering = ["-created_at"]
        unique_together = [["identity_document_type", "number"]]
        indexes = [
            models.Index(fields=["type", "created_at"]),
            models.Index(fields=["number"]),
            models.Index(fields=["email"]),
            models.Index(fields=["approved_at", "rejected_at"]),
        ]
        permissions = [
            ("approve_person", "Can approve person"),
            ("reject_person", "Can reject person"),
        ]


class Address(AuditModel, LocationMixin):
    """
    Stores multiple addresses associated with a Person.
    """

    objects = AddressManager()

    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="addresses",
        verbose_name=_("Person"),
    )
    label = models.CharField(
        _("Label"),
        max_length=100,
        default=_("Main"),
        help_text=_("Descriptive name: Home, Office, Warehouse, etc."),
    )

    telephone = models.CharField(
        _("Contact Phone"),
        max_length=20,
        validators=[PhoneNumberValidator(allow_international=True)],
        blank=True,
        null=True,
        help_text=_("Contact phone for this specific address."),
    )

    is_default = models.BooleanField(
        _("Default Address"),
        default=False,
        help_text=_("Mark as the primary address for this person."),
    )

    is_billing = models.BooleanField(
        _("Billing Address"),
        default=False,
        help_text=_("Use this address for billing purposes."),
    )

    is_shipping = models.BooleanField(
        _("Shipping Address"),
        default=False,
        help_text=_("Use this address for shipping purposes."),
    )

    def __str__(self):
        return f"{self.label}: {self.get_full_address()}"

    def clean(self):
        """Validate address data before saving."""
        super().clean()

        try:
            validate_province_in_department(self.province, self.department)
            validate_district_in_province(self.district, self.province)

        except ValidationError as e:
            raise e

    def save(self, *args, **kwargs):
        """Override save to ensure only one default address per person."""
        if self.is_default:
            Address.objects.filter(person=self.person, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)

        super().save(*args, **kwargs)

    def set_as_default(self):
        """Convenience method to set this as the default address."""
        self.is_default = True
        self.save()

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["person", "is_default"]),
            models.Index(fields=["person", "is_billing"]),
            models.Index(fields=["person", "is_shipping"]),
        ]
