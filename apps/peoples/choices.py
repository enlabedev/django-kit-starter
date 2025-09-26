from django.db import models
from django.utils.translation import gettext_lazy as _


class PersonType(models.TextChoices):
    CUSTOMER = "CUSTOMER", _("Customer")
    SUPPLIER = "SUPPLIER", _("Supplier")
    EMPLOYEE = "EMPLOYEE", _("Employee")
    OTHER = "OTHER", _("Other")
    BUSINESS = "BUSINESS", _("Business")


class Gender(models.TextChoices):
    MALE = "M", _("Male")
    FEMALE = "F", _("Female")
    OTHER = "O", _("Other")
