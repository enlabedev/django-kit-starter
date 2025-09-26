from decimal import Decimal

from django.db import models

from apps.core.managers import BaseManager

from .querysets import CategoryQuerySet, OrderQuerySet, ProductQuerySet


class CategoryManager(BaseManager):
    """
    Custom manager for Category model with optimized queries.
    """

    def get_queryset(self):
        """Return the custom QuerySet for this manager."""
        return CategoryQuerySet(self.model, using=self._db)

    def active(self):
        """Return only active categories."""
        return self.get_queryset().active()

    def get_by_natural_key(self, slug: str):
        """Get category by its natural key (slug)."""
        return self.get_queryset().get_by_natural_key(slug)

    def search(self, query: str):
        """Search categories by name or description."""
        return self.get_queryset().search(query)


class ProductManager(BaseManager):
    """
    Custom manager for Product model with optimized queries and business logic.
    """

    def get_queryset(self):
        """Return the custom QuerySet for this manager."""
        return ProductQuerySet(self.model, using=self._db)

    def active(self):
        """Return only active products."""
        return self.get_queryset().active()

    def in_stock(self):
        """Return only products that are in stock."""
        return self.get_queryset().in_stock()

    def low_stock(self):
        """Return products with low stock (less than 10 units)."""
        return self.get_queryset().low_stock()

    def by_category(self, category_slug: str):
        """Get products by category slug."""
        return self.get_queryset().by_category(category_slug)

    def search(self, query: str):
        """Search products by name or description."""
        return self.get_queryset().search(query)


class OrderManager(BaseManager):
    """
    Custom manager for Order model with business logic queries.
    """

    def get_queryset(self):
        """Return the custom QuerySet for this manager."""
        return OrderQuerySet(self.model, using=self._db)

    def paid(self):
        """Return only paid orders."""
        return self.get_queryset().paid()

    def within_date_range(self, start_date=None, end_date=None):
        """Get orders within a specific date range."""
        return self.get_queryset().within_date_range(start_date, end_date)

    def unpaid(self):
        """Return only unpaid orders."""
        return self.get_queryset().unpaid()

    def total_sales(self, start_date=None, end_date=None):
        """Calculate total sales amount for a date range."""

        queryset = self.get_queryset().paid()
        if start_date:
            queryset = queryset.within_date_range(start_date=start_date)
        if end_date:
            queryset = queryset.within_date_range(end_date=end_date)
        return queryset.aggregate(total=models.Sum("items__cost"))[
            "total"
        ] or Decimal("0.00")

    def order_count(self, status=None):
        """Get order count, optionally filtered by status."""
        return self.get_queryset().order_count(status=status)
