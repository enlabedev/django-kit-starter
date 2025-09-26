from django.db import models

from .querysets import (
    BaseQuerySet,
    CurrencyTypeQuerySet,
    ExchangeRateQuerySet,
    IdentityDocumentTypeQuerySet,
)


class BaseManager(models.Manager):
    """
    Manager that uses the BaseQuerySet to enforce soft-delete logic by default.
    """

    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db).not_deleted()

    def all_with_deleted(self):
        """
        Returns all objects, including logically deleted ones.
        """
        return BaseQuerySet(self.model, using=self._db)

    def restore(self):
        """
        Restores logically deleted objects in the QuerySet.
        """
        return self.get_queryset().restore()

    def deleted(self):
        """
        Returns only logically deleted objects.
        """
        return BaseQuerySet(self.model, using=self._db).deleted()

    def hard_delete(self):
        """
        Performs a physical delete from the database.
        """
        return self.get_queryset().hard_delete()

    def soft_delete(self, user):
        """
        Marks objects in the QuerySet as logically deleted.
        """
        return self.get_queryset().soft_delete(user)

    def blocked(self, user):
        """
        Marks objects in the QuerySet as blocked.
        """
        return self.get_queryset().blocked(user)

    def unblocked(self):
        """
        Marks objects in the QuerySet as unblocked.
        """
        return self.get_queryset().unblocked()


class CurrencyTypeManager(models.Manager):
    """Manager personalizado para CurrencyType."""

    def get_queryset(self):
        return CurrencyTypeQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def get_base_currency(self):
        """Obtiene la moneda base del sistema."""
        return self.get_queryset().base_currency()


class IdentityDocumentTypeManager(models.Manager):
    """Manager personalizado para IdentityDocumentType."""

    def get_queryset(self):
        return IdentityDocumentTypeQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def for_natural_persons(self):
        return self.get_queryset().for_natural_persons()

    def for_legal_persons(self):
        return self.get_queryset().for_legal_persons()

    def get_dni(self):
        """Obtiene el tipo DNI (código 01 en SUNAT)."""
        return self.get_queryset().filter(code="01").first()

    def get_ruc(self):
        """Obtiene el tipo RUC (código 06 en SUNAT)."""
        return self.get_queryset().filter(code="06").first()

    def get_ce(self):
        """Obtiene el tipo Carnet de Extranjería (código 04 en SUNAT)."""
        return self.get_queryset().filter(code="04").first()

    def get_passport(self):
        """Obtiene el tipo Pasaporte (código 07 en SUNAT)."""
        return self.get_queryset().filter(code="07").first()

    def get_default_for_person_type(self, is_natural=True):
        """
        Obtiene el documento por defecto según el tipo de persona.
        """
        if is_natural:
            return self.get_dni() or self.for_natural_persons().first()
        else:
            return self.get_ruc() or self.for_legal_persons().first()


class ExchangeRateManager(BaseManager):
    """
    Custom Manager for the ExchangeRate model.
    """

    def get_queryset(self):
        return ExchangeRateQuerySet(self.model, using=self._db)

    def for_date(self, date):
        """
        Returns exchange rates for a specific date.
        """
        return self.get_queryset().for_date(date)

    def for_today(self):
        """
        Returns exchange rates for today.
        """
        return self.get_queryset().for_today()

    def for_currency_pair(self, from_currency, to_currency):
        """
        Returns exchange rates for a specific currency pair.
        """
        return self.get_queryset().for_currency_pair(from_currency, to_currency)

    def latest(self):
        """
        Returns the latest exchange rates.
        """
        return self.get_queryset().latest()

    def date_range(self, start_date, end_date):
        """
        Returns exchange rates within a specific date range.
        """
        return self.get_queryset().filter(date__range=(start_date, end_date))

    def official_rates(self):
        """
        Returns only official exchange rates.
        """
        return self.get_queryset().filter(is_official=True)

    def by_source(self, source):
        """
        Returns exchange rates from a specific source.
        """
        return self.get_queryset().filter(source=source)

    def with_currencies(self):
        """
        Returns exchange rates with related currency data.
        """
        return self.get_queryset().with_currencies()

    def average_rates(self, start_date, end_date):
        """
        Returns average exchange rates over a date range.
        """
        return self.get_queryset().average_rates(start_date, end_date)
