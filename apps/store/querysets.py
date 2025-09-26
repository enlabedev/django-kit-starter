from core.querysets import BaseQuerySet
from django.db import models


class CategoryQuerySet(BaseQuerySet):
    """
    Custom QuerySet for Category model with additional filtering methods.
    """

    def active(self):
        """Return only active categories."""
        return self.filter(is_active=True)

    def get_by_natural_key(self, slug: str):
        """Get category by its natural key (slug)."""
        return self.get(slug=slug)

    def search(self, query: str):
        """Search categories by name or description."""
        return self.filter(
            models.Q(name__icontains=query)
            | models.Q(description__icontains=query),
            is_active=True,
        )


class ProductQuerySet(BaseQuerySet):
    """
    Custom QuerySet for Product model with additional filtering methods.
    """

    def active(self):
        """Return only active products."""
        return self.filter(is_active=True)

    def in_stock(self):
        """Return only products that are in stock."""
        return self.filter(stock__gt=0)

    def low_stock(self):
        """Return products with low stock (less than 10 units)."""
        return self.filter(stock__lt=10, stock__gt=0)

    def by_category(self, category_slug: str):
        """Get products by category slug."""
        return self.filter(category__slug=category_slug, is_active=True)

    def search(self, query: str):
        """Search products by name or description."""
        return self.filter(
            models.Q(name__icontains=query)
            | models.Q(description__icontains=query),
            is_active=True,
        )


class OrderQuerySet(BaseQuerySet):
    """
    Custom QuerySet for Order model with business logic queries.
    """

    def paid(self):
        """Return only paid orders."""
        return self.filter(paid=True)

    def unpaid(self):
        """Return only unpaid orders."""
        return self.filter(paid=False)

    def by_customer(self, user_id: int):
        """Get orders by customer user ID."""
        return self.filter(customer_id=user_id)

    def within_date_range(self, start_date, end_date):
        """Get orders within a specific date range."""
        return self.filter(created_at__gte=start_date, created_at__lte=end_date)

    def order_count(self, status=None):
        """Get order count, optionally filtered by status."""
        return self.filter(status=status).count() if status else self.count()


class CouponQuerySet(BaseQuerySet):
    """
    Custom QuerySet for Coupon model with additional filtering methods.
    """

    def active(self):
        """Return only active coupons."""
        return self.filter(active=True)

    def valid(self):
        """Return only currently valid coupons."""
        now = models.functions.Now()
        return self.filter(active=True, valid_from__lte=now, valid_to__gte=now)
