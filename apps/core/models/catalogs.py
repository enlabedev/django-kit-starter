from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.choices import (
    ContributorType,
    DocumentDataType,
    DocumentLengthType,
)
from apps.core.validators import (
    currency_code_validator,
    document_type_code_validator,
)

from ..managers import (
    CurrencyTypeManager,
    ExchangeRateManager,
    IdentityDocumentTypeManager,
)
from .base import AuditModel, SimpleModel


class CurrencyType(SimpleModel):
    """
    Represents currency types for financial operations.
    """

    code = models.CharField(
        _("Code"),
        primary_key=True,
        max_length=3,
        validators=[currency_code_validator],
        help_text=_("ISO 4217 currency code (e.g., USD, EUR, PEN)."),
        db_index=True,
    )

    symbol = models.CharField(
        _("Symbol"),
        max_length=10,
        blank=True,
        null=True,
        help_text=_("Currency symbol for display (e.g., S/, $, €, ¥)."),
    )

    decimal_places = models.PositiveSmallIntegerField(
        _("Decimal Places"),
        default=2,
        help_text=_(
            "Number of decimal places for this currency (usually 2, but 0 for JPY, 3 for some currencies)."
        ),
    )

    exchange_rate_multiplier = models.DecimalField(
        _("Exchange Rate Multiplier"),
        max_digits=10,
        decimal_places=6,
        default=Decimal("1.000000"),
        help_text=_(
            "Multiplier for exchange rate calculations (e.g., 100 for Japanese Yen)."
        ),
    )

    is_base_currency = models.BooleanField(
        _("Is Base Currency"),
        default=False,
        help_text=_(
            "Mark if this is the system's base currency for conversions."
        ),
    )

    is_crypto = models.BooleanField(
        _("Is Cryptocurrency"),
        default=False,
        help_text=_("Mark if this is a cryptocurrency."),
    )

    @property
    def display_name(self):
        """Returns formatted display name with symbol."""
        if self.symbol:
            return f"{self.symbol} ({self.code})"
        return self.code

    def format_amount(self, amount):
        """Format an amount with the currency symbol and appropriate decimals."""
        if self.symbol:
            formatted = f"{self.symbol} {amount:,.{self.decimal_places}f}"
        else:
            formatted = f"{amount:,.{self.decimal_places}f} {self.code}"
        return formatted

    def get_latest_exchange_rate(self, to_currency=None):
        """Get the latest exchange rate for this currency."""
        if to_currency is None:
            to_currency = CurrencyType.objects.get_base_currency()

        if self == to_currency:
            return Decimal("1.0")

        try:
            return ExchangeRate.objects.get_latest_rate(self, to_currency)
        except ExchangeRate.DoesNotExist:
            return None

    def clean(self):
        """Validate currency data before saving."""
        super().clean()

        if self.is_base_currency:
            existing_base = CurrencyType.objects.filter(
                is_base_currency=True
            ).exclude(code=self.code)
            if existing_base.exists():
                raise ValidationError(
                    {
                        "is_base_currency": _(
                            "Only one currency can be marked as base currency."
                        )
                    }
                )

        if self.decimal_places > 6:
            raise ValidationError(
                {"decimal_places": _("Decimal places cannot exceed 6.")}
            )

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency."""
        self.code = self.code.upper() if self.code else self.code
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.description}"

    class Meta:
        verbose_name = _("Currency Type")
        verbose_name_plural = _("Currency Types")
        ordering = ["code"]
        indexes = [
            models.Index(fields=["is_active", "code"]),
            models.Index(fields=["is_base_currency"]),
        ]

    objects = CurrencyTypeManager()


class IdentityDocumentType(SimpleModel):
    """
    Model for identity document types, based on SUNAT Table 6.
    """

    code = models.CharField(
        _("Code"),
        primary_key=True,
        max_length=2,
        validators=[document_type_code_validator],
        help_text=_(
            "Document type code based on SUNAT (e.g., 01 for DNI, 06 for RUC)."
        ),
    )

    short_description = models.CharField(
        _("Short Description"),
        max_length=20,
        blank=True,
        help_text=_("Short description or acronym (e.g., DNI, RUC, CE)."),
        db_index=True,
    )
    length = models.PositiveSmallIntegerField(
        _("Length"),
        help_text=_("Exact or maximum length of the document number."),
    )

    length_type = models.CharField(
        _("Length Type"),
        max_length=1,
        choices=DocumentLengthType.choices,
        default=DocumentLengthType.EXACT,
        help_text=_("Indicates if the length is exact or a maximum."),
    )

    data_type = models.CharField(
        _("Data Type"),
        max_length=3,
        choices=DocumentDataType.choices,
        default=DocumentDataType.NUMERIC,
        help_text=_("Type of characters allowed for the document number."),
    )

    contributor_type = models.CharField(
        _("Contributor Type"),
        max_length=1,
        choices=ContributorType.choices,
        default=ContributorType.NATIONALS_AND_FOREIGNERS,
        help_text=_(
            "Indicates if it applies to nationals, foreigners, or both."
        ),
    )

    is_for_natural_person = models.BooleanField(
        _("For Natural Person"),
        default=True,
        help_text=_(
            "Indicates if this document type is valid for individuals."
        ),
    )

    is_for_legal_person = models.BooleanField(
        _("For Legal Person"),
        default=False,
        help_text=_("Indicates if this document type is valid for companies."),
    )

    requires_verification_digit = models.BooleanField(
        _("Requires Verification Digit"),
        default=False,
        help_text=_(
            "Indicates if the document requires a verification digit (like RUC)."
        ),
    )
    display_order = models.PositiveSmallIntegerField(
        _("Display Order"),
        default=100,
        help_text=_("Order for displaying in forms and lists."),
    )

    @property
    def display_name(self):
        """Returns the best display name available."""
        return self.short_description or self.description

    @property
    def validation_pattern(self):
        """Returns a regex pattern for basic validation."""
        if self.data_type == DocumentDataType.NUMERIC:
            if self.length_type == DocumentLengthType.EXACT:
                return f"^[0-9]{{{self.length}}}$"
            else:
                return f"^[0-9]{{1,{self.length}}}$"
        elif self.data_type == DocumentDataType.ALPHANUMERIC:
            if self.length_type == DocumentLengthType.EXACT:
                return f"^[A-Za-z0-9]{{{self.length}}}$"
            else:
                return f"^[A-Za-z0-9]{{1,{self.length}}}$"
        return None

    def __str__(self):
        return f"{self.code} - {self.display_name}"

    class Meta:
        verbose_name = _("Identity Document Type")
        verbose_name_plural = _("Identity Document Types")
        ordering = ["display_order", "code"]
        indexes = [
            models.Index(fields=["is_active", "code"]),
            models.Index(
                fields=["is_for_natural_person", "is_for_legal_person"]
            ),
            models.Index(fields=["display_order", "is_active"]),
        ]

    objects = IdentityDocumentTypeManager()


class ExchangeRate(AuditModel):
    """
    Stores currency exchange rates for financial operations.
    """

    from_currency = models.ForeignKey(
        CurrencyType,
        on_delete=models.PROTECT,
        related_name="exchange_rates_from",
        verbose_name=_("From Currency"),
        help_text=_("Source currency for the exchange rate."),
    )

    to_currency = models.ForeignKey(
        CurrencyType,
        on_delete=models.PROTECT,
        related_name="exchange_rates_to",
        verbose_name=_("To Currency"),
        help_text=_("Target currency for the exchange rate."),
    )
    buy_rate = models.DecimalField(
        _("Buy Rate"),
        max_digits=12,
        decimal_places=6,
        help_text=_("Rate at which the bank/exchange buys the currency."),
    )

    sell_rate = models.DecimalField(
        _("Sell Rate"),
        max_digits=12,
        decimal_places=6,
        help_text=_("Rate at which the bank/exchange sells the currency."),
    )

    mid_rate = models.DecimalField(
        _("Mid Rate"),
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Average of buy and sell rates, calculated automatically."),
    )

    source = models.CharField(
        _("Source"),
        max_length=100,
        blank=True,
        help_text=_(
            "Source of the exchange rate (e.g., Central Bank, API provider)."
        ),
    )

    is_official = models.BooleanField(
        _("Is Official Rate"),
        default=False,
        help_text=_(
            "Indicates if this is an official rate from a central bank."
        ),
    )

    @property
    def spread(self):
        """Calculate the spread between buy and sell rates."""
        return self.sell_rate - self.buy_rate

    @property
    def spread_percentage(self):
        """Calculate the spread as a percentage of the mid rate."""
        if self.mid_rate and self.mid_rate != 0:
            return (self.spread / self.mid_rate) * 100
        return Decimal("0")

    def calculate_mid_rate(self):
        """Calculate and return the mid-point between buy and sell rates."""
        return (self.buy_rate + self.sell_rate) / 2

    def convert(self, amount, use_buy_rate=True):
        """
        Convert an amount from one currency to another.
        """
        rate = self.buy_rate if use_buy_rate else self.sell_rate
        return Decimal(str(amount)) * rate

    def inverse_rate(self):
        """
        Get or create the inverse exchange rate.
        """
        try:
            return ExchangeRate.objects.get(
                from_currency=self.to_currency,
                to_currency=self.from_currency,
                date=self.date,
            )
        except ExchangeRate.DoesNotExist:
            return ExchangeRate.objects.create(
                from_currency=self.to_currency,
                to_currency=self.from_currency,
                buy_rate=1 / self.sell_rate if self.sell_rate else 0,
                sell_rate=1 / self.buy_rate if self.buy_rate else 0,
                date=self.date,
                source=self.source,
                is_official=self.is_official,
            )

    def clean(self):
        """Validate exchange rate data before saving."""
        super().clean()
        errors = {}

        if self.from_currency == self.to_currency:
            errors["to_currency"] = _(
                "From and To currencies must be different."
            )

        if self.buy_rate and self.sell_rate:
            if self.sell_rate < self.buy_rate:
                errors["sell_rate"] = _(
                    "Sell rate must be higher than buy rate."
                )

        if self.buy_rate and self.buy_rate <= 0:
            errors["buy_rate"] = _("Buy rate must be positive.")

        if self.sell_rate and self.sell_rate <= 0:
            errors["sell_rate"] = _("Sell rate must be positive.")

        if self.date and self.date > timezone.now().date():
            errors["date"] = _("Exchange rate date cannot be in the future.")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to calculate mid rate automatically."""
        if not self.mid_rate and self.buy_rate and self.sell_rate:
            self.mid_rate = self.calculate_mid_rate()

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.date}: {self.from_currency.code} → {self.to_currency.code} "
            f"Buy: {self.buy_rate:.4f} / Sell: {self.sell_rate:.4f}"
        )

    class Meta:
        verbose_name = _("Exchange Rate")
        verbose_name_plural = _("Exchange Rates")
        ordering = ["-created_at", "from_currency", "to_currency"]
        unique_together = [["created_at", "from_currency", "to_currency"]]
        indexes = [
            models.Index(
                fields=["-created_at", "from_currency", "to_currency"]
            ),
            models.Index(
                fields=["from_currency", "to_currency", "-created_at"]
            ),
            models.Index(fields=["is_official", "-created_at"]),
        ]
        permissions = [
            (
                "import_exchange_rates",
                "Can import exchange rates from external sources",
            ),
            ("approve_exchange_rates", "Can approve exchange rates"),
        ]

    objects = ExchangeRateManager()
