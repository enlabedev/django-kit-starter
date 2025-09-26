from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import SimpleModel


class Department(SimpleModel):
    def __str__(self):
        return self.description

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = ("description", "is_active")
        ordering = ["description"]


class Province(SimpleModel):
    department = models.ForeignKey(
        Department,
        on_delete=models.RESTRICT,
        verbose_name=_("Department"),
    )

    def __str__(self):
        return f"{self.description} ({self.department.description})"

    def clean(self):
        super().clean()
        if self.department and not self.department.active:
            raise ValidationError(
                _("Cannot create a province for an inactive department.")
            )

    class Meta:
        verbose_name = _("Province")
        verbose_name_plural = _("Provinces")
        unique_together = ("department", "description")
        ordering = ["description"]
        indexes = [
            models.Index(fields=["department", "is_active"]),
        ]


class District(SimpleModel):
    province = models.ForeignKey(
        Province,
        on_delete=models.RESTRICT,
        verbose_name=_("Province"),
    )

    @property
    def department(self):
        return self.province.department

    def __str__(self):
        return f"{self.description} ({self.province.description})"

    def clean(self):
        super().clean()
        if self.department and not self.department.active:
            raise ValidationError(
                _("Cannot create a district for an inactive department.")
            )
        if not self.province:
            raise ValidationError(_("Province is required."))
        if self.province and not self.province.active:
            raise ValidationError(
                _("Cannot create a district for an inactive province.")
            )

    class Meta:
        verbose_name = _("District")
        verbose_name_plural = _("Districts")
        ordering = ["description"]
        unique_together = ("province", "description")
        indexes = [
            models.Index(fields=["province", "is_active"]),
        ]


class LocationMixin(models.Model):
    """
    Represents a geographic area, which can be a department, province, or district.
    """

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="%(class)s_department",
    )
    province = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        related_name="%(class)s_province",
    )
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="%(class)s_district",
    )
    address = models.CharField(max_length=200)
    reference = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = _("Geographic Area")
        verbose_name_plural = _("Geographic Areas")
        unique_together = ("description", "active")
        abstract = True

    def get_full_address(self):
        parts = [
            self.address,
            self.district.description,
            self.province.description,
            self.department.description,
        ]
        if self.reference:
            parts.append(f"Ref: {self.reference}")
        return ", ".join(parts)
