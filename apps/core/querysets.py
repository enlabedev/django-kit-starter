from datetime import timedelta

from django.db import models
from django.db.models import Avg, Count, Max, Min, Q
from django.utils import timezone


class BaseQuerySet(models.QuerySet):
    """
    A base QuerySet that includes logic for soft-deletion.
    """

    def soft_delete(self, user):
        """Marks objects in the QuerySet as logically deleted."""
        return self.update(deleted_at=timezone.now(), deleted_by=user)

    def restore(self):
        """Restores objects in the QuerySet."""
        return self.update(deleted_at=None, deleted_by=None)

    def blocked(self, user):
        """
        Marks objects in the QuerySet as blocked.
        """
        return self.update(blocked_at=timezone.now(), blocked_by=user)

    def unblocked(self):
        """
        Marks objects in the QuerySet as unblocked.
        """
        return self.update(blocked_at=None, blocked_by=None)

    def hard_delete(self):
        """
        Performs a physical delete from the database.
        """
        return super().delete()

    def not_deleted(self):
        """
        Filters to include only non-deleted records.
        """
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """
        Filters to include only logically deleted records.
        """
        return self.filter(deleted_at__isnull=False)

    def created_by(self, user):
        """
        Filters to include only records created by the specified user.
        """
        return self.filter(created_by=user)

    def updated_by(self, user):
        """
        Filters to include only records updated by the specified user.
        """
        return self.filter(updated_by=user)

    def deleted_by(self, user):
        """
        Filters to include only records deleted by the specified user.
        """
        return self.filter(deleted_by=user)

    def created_after(self, date):
        """
        Filters to include only records created after the specified date.
        """
        return self.filter(created_at__gt=date)

    def created_before(self, date):
        """
        Filters to include only records created before the specified date.
        """
        return self.filter(created_at__lt=date)


class CurrencyTypeQuerySet(models.QuerySet):
    """QuerySet personalizado para CurrencyType."""

    def active(self):
        """Filtra solo monedas activas."""
        return self.filter(is_active=True)

    def base_currency(self):
        """Obtiene la moneda base del sistema."""
        return self.filter(is_base_currency=True).first()

    def cryptocurrencies(self):
        """Filtra solo criptomonedas."""
        return self.filter(is_crypto=True)

    def fiat_currencies(self):
        """Filtra solo monedas fiduciarias."""
        return self.filter(is_crypto=False)

    def with_exchange_rates(self):
        """Incluye información de tasas de cambio."""
        return self.prefetch_related("exchange_rates_from", "exchange_rates_to")

    def most_used(self, days=30):
        """
        Obtiene las monedas más utilizadas en los últimos N días.
        Basado en la cantidad de tasas de cambio registradas.
        """
        since = timezone.now() - timedelta(days=days)
        return self.annotate(
            usage_count=Count(
                "exchange_rates_from",
                filter=Q(exchange_rates_from__created_at__gte=since),
            )
            + Count(
                "exchange_rates_to",
                filter=Q(exchange_rates_to__created_at__gte=since),
            )
        ).order_by("-usage_count")

    def search(self, query):
        """Búsqueda por código, símbolo o descripción."""
        if not query:
            return self

        return self.filter(
            Q(code__icontains=query)
            | Q(symbol__icontains=query)
            | Q(description__icontains=query)
        )


class IdentityDocumentTypeQuerySet(models.QuerySet):
    """QuerySet personalizado para IdentityDocumentType."""

    def active(self):
        """Filtra solo tipos de documento activos."""
        return self.filter(is_active=True)

    def for_natural_persons(self):
        """Filtra documentos válidos para personas naturales."""
        return self.filter(is_for_natural_person=True)

    def for_legal_persons(self):
        """Filtra documentos válidos para personas jurídicas."""
        return self.filter(is_for_legal_person=True)

    def for_nationals(self):
        """Filtra documentos para nacionales."""
        from apps.core.choices import ContributorType

        return self.filter(
            contributor_type__in=[
                ContributorType.NATIONALS,
                ContributorType.NATIONALS_AND_FOREIGNERS,
            ]
        )

    def for_foreigners(self):
        """Filtra documentos para extranjeros."""
        from apps.core.choices import ContributorType

        return self.filter(
            contributor_type__in=[
                ContributorType.FOREIGNERS,
                ContributorType.NATIONALS_AND_FOREIGNERS,
            ]
        )

    def by_code(self, code):
        """Busca por código exacto."""
        return self.filter(code=code)

    def by_short_description(self, short_desc):
        """Busca por descripción corta (DNI, RUC, etc.)."""
        return self.filter(short_description__iexact=short_desc)

    def ordered_for_display(self):
        """Ordena para mostrar en formularios."""
        return self.order_by("display_order", "code")

    def search(self, query):
        """Búsqueda general."""
        if not query:
            return self

        return self.filter(
            Q(code__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
        )

    def with_stats(self):
        """Agrega estadísticas de uso."""
        from apps.peoples.models import Person

        return self.annotate(
            person_count=Count(Person, filter=Q(persons__is_active=True))
        )


class ExchangeRateQuerySet(models.QuerySet):
    """QuerySet personalizado para ExchangeRate."""

    def for_date(self, date):
        """Filtra tasas para una fecha específica."""
        return self.filter(created_at__date=date).latest("created_at")

    def for_today(self):
        """Filtra tasas de hoy."""
        return self.for_date(timezone.now().date())

    def for_currency_pair(self, from_currency, to_currency):
        """Filtra por par de monedas."""
        return self.filter(from_currency=from_currency, to_currency=to_currency)

    def latest(self):
        """Obtiene las tasas más recientes."""
        return self.order_by("-date")

    def date_range(self, start_date, end_date):
        """Filtra tasas en un rango de fechas."""
        return self.filter(date__range=[start_date, end_date])

    def official_rates(self):
        """Filtra solo tasas oficiales."""
        return self.filter(is_official=True)

    def by_source(self, source):
        """Filtra por fuente."""
        return self.filter(source=source)

    def with_currencies(self):
        """Incluye información completa de monedas."""
        return self.select_related("from_currency", "to_currency")

    def average_rates(self, start_date, end_date):
        """
        Calcula tasas promedio en un período.
        """
        return self.date_range(start_date, end_date).aggregate(
            avg_buy=Avg("buy_rate"),
            avg_sell=Avg("sell_rate"),
            avg_mid=Avg("mid_rate"),
            max_buy=Max("buy_rate"),
            min_buy=Min("buy_rate"),
            max_sell=Max("sell_rate"),
            min_sell=Min("sell_rate"),
        )
