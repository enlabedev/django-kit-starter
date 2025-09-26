from decimal import Decimal
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models.base import AuditModel

from .choices import OrderStatus
from .managers import CategoryManager, OrderManager, ProductManager

User = settings.AUTH_USER_MODEL


class Category(AuditModel):
    """
    Model representing product categories in the e-commerce store.
    """

    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("Category display name (max 100 characters)"),
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Optional category description"),
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL-friendly identifier for the category"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether the category is visible to customers"),
    )
    parent = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name=_("Parent Category"),
        help_text=_("Parent category for hierarchical organization"),
    )
    image = models.ImageField(
        upload_to="categories/%Y/%m",
        blank=True,
        null=True,
        verbose_name=_("Image"),
        help_text=_("Optional category image"),
    )

    objects = CategoryManager()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["parent", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "slug"],
                name="unique_category_parent_slug",
            ),
        ]

    def __str__(self):
        """Return the category name as string representation."""
        return self.name

    def clean(self):
        """Validate the category data."""
        super().clean()
        if self.parent and self.parent.id == self.id:
            raise ValidationError(_("Category cannot be its own parent."))

    @property
    def is_root_category(self) -> bool:
        """Return True if this is a root category (no parent)."""
        return self.parent is None

    def all_products(self):
        """
        Get all products in this category and its subcategories.
        """
        if self.is_root_category:
            return Product.objects.filter(
                models.Q(category=self)
                | models.Q(category__parent__isnull=False)
                & models.Q(category__parent__parent=self)
            )
        return self.products.all()

    def ancestors(self, include_self: bool = False):
        """
        Get all ancestor categories.
        """
        ancestors = []
        if include_self:
            ancestors.append(self)

        parent = self.parent
        while parent is not None:
            ancestors.insert(0, parent)
            parent = parent.parent

        return Category.objects.filter(id__in=[cat.id for cat in ancestors])

    def descendants(self, include_self: bool = False):
        """
        Get all descendant categories.
        """
        descendants = []
        if include_self:
            descendants.append(self)

        children = list(self.children.all())
        descendants.extend(children)

        for child in children:
            descendants.extend(child.get_descendants())

        return Category.objects.filter(id__in=[cat.id for cat in descendants])


class Tag(AuditModel):
    """
    Model representing product tags for filtering and organization.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Tag name"),
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL-friendly identifier"),
    )
    description = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Optional tag description"),
    )
    color = models.CharField(
        max_length=7,
        default="#007bff",
        verbose_name=_("Color"),
        help_text=_("Hex color code for tag display"),
    )

    class Meta:
        verbose_name = _("Product Tag")
        verbose_name_plural = _("Product Tags")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        """Return the tag name as string representation."""
        return self.name

    def clean(self):
        """Validate the tag data."""
        super().clean()
        if self.color and not self.color.startswith("#"):
            raise ValidationError(
                {
                    "color": _(
                        "Color must be a valid hex color code starting with #."
                    )
                }
            )


class Product(AuditModel):
    """
    Model representing products in the e-commerce store.
    """

    name = models.CharField(
        max_length=200,
        verbose_name=_("Name"),
        help_text=_("Product display name (max 200 characters)"),
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Detailed product description"),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Price"),
        help_text=_("Current selling price"),
    )
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Compare at Price"),
        help_text=_("Original price for comparison display"),
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Cost Price"),
        help_text=_("Actual cost for profit calculations"),
    )
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Stock"),
        help_text=_("Available quantity in inventory"),
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Low Stock Threshold"),
        help_text=_("Stock level considered low"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("Category"),
        help_text=_("Product category"),
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("URL-friendly identifier"),
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_("SKU"),
        help_text=_("Stock Keeping Unit"),
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_("Weight"),
        help_text=_("Product weight in kg"),
    )
    dimensions = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Dimensions"),
        help_text=_("Product dimensions (L x W x H)"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether product is available for purchase"),
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured"),
        help_text=_("Whether product should be highlighted"),
    )
    is_digital = models.BooleanField(
        default=False,
        verbose_name=_("Digital Product"),
        help_text=_("Whether this is a digital product"),
    )
    requires_shipping = models.BooleanField(
        default=True,
        verbose_name=_("Requires Shipping"),
        help_text=_("Whether product requires physical shipping"),
    )
    image = models.ImageField(
        upload_to="products/%Y/%m",
        blank=True,
        null=True,
        verbose_name=_("Main Image"),
        help_text=_("Primary product image"),
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="products",
        verbose_name=_("Tags"),
        help_text=_("Product tags for filtering and search"),
    )

    objects = ProductManager()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["id", "slug"]),
            models.Index(fields=["category", "name"]),
            models.Index(fields=["price"]),
            models.Index(fields=["is_active", "stock"]),
            models.Index(fields=["is_featured"]),
            models.Index(fields=["sku"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name="product_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(stock__gte=0),
                name="product_stock_non_negative",
            ),
        ]

    def __str__(self):
        """Return the product name as string representation."""
        return self.name

    def clean(self):
        """Validate the product data."""
        super().clean()

        if self.compare_at_price and self.price >= self.compare_at_price:
            raise ValidationError(
                {
                    "compare_at_price": _(
                        "Compare at price must be higher than selling price."
                    )
                }
            )

        if self.cost_price and self.price <= self.cost_price:
            raise ValidationError(
                {"price": _("Selling price must be higher than cost price.")}
            )

        if self.sku and not self.sku.strip():
            raise ValidationError(
                {"sku": _("SKU cannot be empty if provided.")}
            )

    @property
    def is_in_stock(self) -> bool:
        """Return True if the product is in stock."""
        return self.stock > 0

    @property
    def is_low_stock(self) -> bool:
        """Return True if the product has low stock."""
        return 0 < self.stock < self.low_stock_threshold

    @property
    def is_out_of_stock(self) -> bool:
        """Return True if the product is out of stock."""
        return self.stock == 0

    @property
    def stock_status(self) -> str:
        """Return a human-readable stock status."""
        if self.is_out_of_stock:
            return _("Out of Stock")
        elif self.is_low_stock:
            return _("Low Stock")
        else:
            return _("In Stock")

    @property
    def discount_percentage(self) -> Optional[Decimal]:
        """Calculate discount percentage if compare_at_price exists."""
        if self.compare_at_price and self.compare_at_price > self.price:
            return (
                (self.compare_at_price - self.price) / self.compare_at_price
            ) * 100
        return None

    @property
    def profit_margin(self) -> Optional[Decimal]:
        """Calculate profit margin percentage."""
        if self.cost_price and self.price > self.cost_price:
            return ((self.price - self.cost_price) / self.price) * 100
        return None

    def reduce_stock(self, quantity: int, save: bool = True) -> bool:
        """
        Reduce product stock by the specified quantity.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError(_("Quantity must be a positive integer."))

        if self.stock >= quantity:
            self.stock -= quantity
            if save:
                self.save(update_fields=["stock"])
            return True
        return False

    def increase_stock(self, quantity: int, save: bool = True) -> bool:
        """
        Increase product stock by the specified quantity.
        """
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError(_("Quantity must be a positive integer."))

        self.stock += quantity
        if save:
            self.save(update_fields=["stock"])
        return True

    def set_stock(self, quantity: int, save: bool = True) -> bool:
        """
        Set product stock to a specific quantity.
        """
        if not isinstance(quantity, int) or quantity < 0:
            raise ValidationError(
                _("Stock quantity must be a non-negative integer.")
            )

        self.stock = quantity
        if save:
            self.save(update_fields=["stock"])
        return True

    def similar_products(self, limit: int = 5):
        """
        Get similar products based on category and tags.
        """
        return (
            Product.objects.filter(
                models.Q(category=self.category)
                | models.Q(tags__in=self.tags.all()),
                is_active=True,
                stock__gt=0,
            )
            .exclude(id=self.id)
            .distinct()[:limit]
        )


class Order(AuditModel):
    """
    Model representing customer orders in the e-commerce system.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("User"),
        help_text=_("Customer who placed the order"),
    )
    first_name = models.CharField(
        max_length=50,
        verbose_name=_("First Name"),
        help_text=_("Customer's first name"),
    )
    last_name = models.CharField(
        max_length=50,
        verbose_name=_("Last Name"),
        help_text=_("Customer's last name"),
    )
    email = models.EmailField(
        verbose_name=_("Email"),
        help_text=_("Customer's email address"),
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Phone"),
        help_text=_("Customer's phone number"),
    )
    address = models.CharField(
        max_length=250,
        verbose_name=_("Address"),
        help_text=_("Primary shipping address"),
    )
    address_line_2 = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name=_("Address Line 2"),
        help_text=_("Additional address information"),
    )
    postal_code = models.CharField(
        max_length=20,
        verbose_name=_("Postal Code"),
        help_text=_("Shipping postal code"),
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_("City"),
        help_text=_("Shipping city"),
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("State"),
        help_text=_("Shipping state or province"),
    )
    country = models.CharField(
        max_length=100,
        default="US",
        verbose_name=_("Country"),
        help_text=_("Shipping country"),
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created"),
        help_text=_("Order creation date"),
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated"),
        help_text=_("Last update date"),
    )
    paid = models.BooleanField(
        default=False,
        verbose_name=_("Paid"),
        help_text=_("Payment status"),
    )
    payment_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Payment Date"),
        help_text=_("When payment was completed"),
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name=_("Status"),
        help_text=_("Current order status"),
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Notes"),
        help_text=_("Internal order notes"),
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Tracking Number"),
        help_text=_("Shipping tracking number"),
    )
    shipped_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Shipped Date"),
        help_text=_("When order was shipped"),
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Subtotal"),
        help_text=_("Order subtotal before taxes and shipping"),
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Tax Amount"),
        help_text=_("Calculated tax amount"),
    )
    shipping_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Shipping Amount"),
        help_text=_("Shipping cost"),
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Discount Amount"),
        help_text=_("Applied discount amount"),
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("Total Amount"),
        help_text=_("Final order total including all charges"),
    )

    objects = OrderManager()

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["user", "-created"]),
            models.Index(fields=["status"]),
            models.Index(fields=["paid"]),
            models.Index(fields=["email"]),
            models.Index(fields=["created"]),
            models.Index(fields=["user", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name="order_subtotal_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name="order_total_non_negative",
            ),
        ]

    def __str__(self):
        """Return formatted order identifier."""
        return f"Order #{self.id}"

    @property
    def full_name(self) -> str:
        """Return the customer's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def shipping_address(self) -> str:
        """Return the formatted shipping address."""
        lines = [self.address]
        if self.address_line_2:
            lines.append(self.address_line_2)
        lines.append(
            f"{self.city}, {self.state or ''} {self.postal_code}".strip(", ")
        )
        lines.append(self.country)
        return "\n".join(lines)

    @property
    def billing_address(self) -> str:
        """Return the billing address (same as shipping for now)."""
        return self.shipping_address

    @property
    def total_cost(self) -> Decimal:
        """Calculate the total cost of all items in the order."""
        return self.items.aggregate(
            total=models.Sum(models.F("price") * models.F("quantity"))
        )["total"] or Decimal("0.00")

    @property
    def total_items(self) -> int:
        """Return the total number of items in the order."""
        return self.items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def total_weight(self) -> Decimal:
        """Calculate the total weight of all items in the order."""
        return self.items.aggregate(
            total=models.Sum(models.F("product__weight") * models.F("quantity"))
        )["total"] or Decimal("0.00")

    @property
    def is_pending(self) -> bool:
        """Return True if order is in pending status."""
        return self.status == OrderStatus.PENDING

    @property
    def is_processing(self) -> bool:
        """Return True if order is being processed."""
        return self.status == OrderStatus.PROCESSING

    @property
    def is_completed(self) -> bool:
        """Return True if order is completed."""
        return self.status == OrderStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """Return True if order is cancelled."""
        return self.status == OrderStatus.CANCELLED

    @property
    def can_be_modified(self) -> bool:
        """Return True if the order can still be modified."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]

    @property
    def can_be_cancelled(self) -> bool:
        """Return True if the order can be cancelled."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PROCESSING]

    @property
    def can_be_shipped(self) -> bool:
        """Return True if the order can be shipped."""
        return self.paid and self.status == OrderStatus.PROCESSING

    @property
    def days_since_creation(self) -> int:
        """Return the number of days since the order was created."""
        return (timezone.now().date() - self.created.date()).days

    @property
    def is_overdue(self) -> bool:
        """Return True if the order is overdue for processing."""
        return self.is_pending and self.days_since_creation > 7

    def get_status_display_with_date(self) -> str:
        """Return status with relevant date information."""
        status_display = self.get_status_display()

        if self.status == OrderStatus.COMPLETED and self.payment_date:
            status_display += (
                f" ({_('paid on')} {self.payment_date.strftime('%Y-%m-%d')})"
            )
        elif self.status == OrderStatus.CANCELLED and self.updated:
            status_display += (
                f" ({_('cancelled on')} {self.updated.strftime('%Y-%m-%d')})"
            )

        return status_display

    def calculate_totals(self, save: bool = True) -> Dict[str, Decimal]:
        """
        Calculate and update all order totals.
        """
        subtotal = self.total_cost
        total = (
            subtotal
            + self.shipping_amount
            + self.tax_amount
            - self.discount_amount
        )

        if save:
            Order.objects.filter(id=self.id).update(
                subtotal=subtotal,
                total_amount=total,
            )
            self.refresh_from_db()

        return {
            "subtotal": subtotal,
            "total": total,
            "tax": self.tax_amount,
            "shipping": self.shipping_amount,
            "discount": self.discount_amount,
        }

    def apply_coupon(self, coupon_code: str) -> bool:
        """
        Apply a coupon to the order.
        """
        from apps.store.models import Coupon

        try:
            coupon = Coupon.objects.get(code=coupon_code, active=True)
            if coupon.is_valid():
                totals = self.calculate_totals(save=False)
                discount_amount = coupon.get_discount_amount(totals["subtotal"])

                self.discount_amount = discount_amount
                self.save(update_fields=["discount_amount"])
                return True
        except Coupon.DoesNotExist:
            pass
        return False

    def mark_as_paid(
        self, payment_date: Optional[timezone.datetime] = None
    ) -> None:
        """
        Mark the order as paid and update relevant timestamps.
        """
        if not self.paid:
            self.paid = True
            self.payment_date = payment_date or timezone.now()
            self.save(update_fields=["paid", "payment_date"])

    def mark_as_shipped(self, tracking_number: str = None) -> None:
        """
        Mark the order as shipped.
        """
        if self.can_be_shipped:
            with transaction.atomic():
                self.status = OrderStatus.COMPLETED
                self.shipped_date = timezone.now()
                if tracking_number:
                    self.tracking_number = tracking_number
                self.save(
                    update_fields=["status", "shipped_date", "tracking_number"]
                )

    def cancel_order(self, reason: str = None) -> bool:
        """
        Cancel the order and restore product stock.
        """
        if not self.can_be_cancelled:
            return False

        with transaction.atomic():
            for item in self.items.all():
                item.product.increase_stock(item.quantity, save=False)
                item.product.save()

            self.status = OrderStatus.CANCELLED
            if reason:
                self.notes = reason
            self.save(update_fields=["status", "notes"])

        return True


class OrderItem(AuditModel):
    """
    Model representing individual items within an order.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Order"),
        help_text=_("Order this item belongs to"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("Product"),
        help_text=_("Product in this order item"),
    )
    product_name = models.CharField(
        max_length=200,
        verbose_name=_("Product Name"),
        help_text=_("Product name at time of purchase"),
    )
    product_sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Product SKU"),
        help_text=_("Product SKU at time of purchase"),
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price"),
        help_text=_("Price per unit at time of purchase"),
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity"),
        help_text=_("Number of units ordered"),
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_("Weight"),
        help_text=_("Total weight for this item"),
    )

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")
        unique_together = (("order", "product"),)
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
            models.Index(fields=["order", "product"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gte=0),
                name="order_item_price_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gte=1),
                name="order_item_quantity_positive",
            ),
        ]

    def __str__(self):
        """Return formatted item description."""
        return f"{self.product_name} (x{self.quantity})"

    def clean(self):
        """Validate the order item data."""
        super().clean()

        if self.price <= 0:
            raise ValidationError(
                {"price": _("Price must be greater than zero.")}
            )

        if self.quantity < 1:
            raise ValidationError(
                {"quantity": _("Quantity must be at least 1.")}
            )

    @property
    def cost(self) -> Decimal:
        """Calculate the total cost for this order item."""
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        """Override save to capture product state and calculate totals."""
        if not self.created_at:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            if not self.price:
                self.price = self.product.price
            if not self.weight and self.product.weight:
                self.weight = self.product.weight * self.quantity

        super().save(*args, **kwargs)


class CouponManager(models.Manager):
    """
    Custom manager for Coupon model with validation queries.
    """

    def active(self):
        """Return only active coupons."""
        return self.filter(active=True)

    def valid(self):
        """Return only currently valid coupons."""
        now = timezone.now()
        return self.filter(active=True, valid_from__lte=now, valid_to__gte=now)


class Coupon(AuditModel):
    """
    Model representing discount coupons for the e-commerce system.
    """

    PERCENTAGE = "percentage"
    FIXED = "fixed"

    DISCOUNT_TYPE_CHOICES = [
        (PERCENTAGE, _("Percentage")),
        (FIXED, _("Fixed Amount")),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Code"),
        help_text=_("Unique coupon code"),
    )
    description = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name=_("Description"),
        help_text=_("Coupon description"),
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default=PERCENTAGE,
        verbose_name=_("Discount Type"),
        help_text=_("Type of discount"),
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Discount Value"),
        help_text=_("Discount amount or percentage"),
    )
    valid_from = models.DateTimeField(
        verbose_name=_("Valid From"),
        help_text=_("Coupon validity start date"),
    )
    valid_to = models.DateTimeField(
        verbose_name=_("Valid To"),
        help_text=_("Coupon validity end date"),
    )
    active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        help_text=_("Whether the coupon is active"),
    )
    usage_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Usage Limit"),
        help_text=_("Maximum number of uses (blank for unlimited)"),
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Usage Count"),
        help_text=_("Number of times coupon has been used"),
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name=_("Minimum Order Amount"),
        help_text=_("Minimum order total required"),
    )
    maximum_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_("Maximum Discount"),
        help_text=_("Maximum discount amount allowed"),
    )
    applicable_categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="coupons",
        verbose_name=_("Applicable Categories"),
        help_text=_("Categories this coupon applies to"),
    )
    applicable_products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="coupons",
        verbose_name=_("Applicable Products"),
        help_text=_("Specific products this coupon applies to"),
    )
    single_use_per_customer = models.BooleanField(
        default=False,
        verbose_name=_("Single Use Per Customer"),
        help_text=_("Whether each customer can use this coupon only once"),
    )

    objects = CouponManager()

    class Meta:
        verbose_name = _("Coupon")
        verbose_name_plural = _("Coupons")
        ordering = ["-valid_to", "code"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["valid_from", "valid_to"]),
            models.Index(fields=["active"]),
            models.Index(fields=["discount_type"]),
            models.Index(fields=["valid_from", "valid_to", "active"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_value__gte=0),
                name="coupon_discount_value_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(valid_from__lte=models.F("valid_to")),
                name="coupon_valid_dates_order",
            ),
        ]

    def __str__(self):
        """Return the coupon code as string representation."""
        return self.code

    def clean(self):
        """Validate the coupon data."""
        super().clean()
        if self.discount_type == self.PERCENTAGE:
            if self.discount_value > 100:
                raise ValidationError(
                    {
                        "discount_value": _(
                            "Percentage discount cannot exceed 100%."
                        )
                    }
                )
        if (
            self.discount_type == self.PERCENTAGE
            and self.maximum_discount_amount is not None
        ):
            raise ValidationError(
                {
                    "maximum_discount_amount": _(
                        "Maximum discount is only valid for fixed amount discounts."
                    )
                }
            )

    def is_valid(self, order: Optional[Order] = None) -> bool:
        """
        Check if the coupon is currently valid.
        """
        now = timezone.now()
        if not self.active:
            return False

        if not (self.valid_from <= now <= self.valid_to):
            return False

        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False

        if order and order.total_amount < self.minimum_order_amount:
            return False
        if order and self.applicable_categories.exists():
            if not order.items.filter(
                product__category__in=self.applicable_categories.all()
            ).exists():
                return False

        if order and self.applicable_products.exists():
            if not order.items.filter(
                product__in=self.applicable_products.all()
            ).exists():
                return False

        return True

    def get_discount_amount(self, order_total: Decimal) -> Decimal:
        """
        Calculate the discount amount for a given order total.
        """
        if not self.is_valid():
            return Decimal("0.00")

        if self.discount_type == self.PERCENTAGE:
            discount = (order_total * self.discount_value) / 100
        else:
            discount = self.discount_value

        if (
            self.discount_type == self.FIXED
            and self.maximum_discount_amount
            and discount > self.maximum_discount_amount
        ):
            discount = self.maximum_discount_amount

        return discount

    def apply_discount(self, order_total: Decimal) -> Dict[str, Any]:
        """
        Apply the coupon discount to an order total.
        """
        discount_amount = self.get_discount_amount(order_total)
        discounted_total = max(order_total - discount_amount, Decimal("0.00"))

        return {
            "discounted_total": discounted_total,
            "discount_amount": discount_amount,
        }

    def increment_usage(self) -> None:
        """Increment the usage count for this coupon."""
        self.usage_count += 1
        self.save(update_fields=["usage_count"])

    def can_be_used_by_customer(self, user: User) -> bool:
        """
        Check if the coupon can be used by a specific customer.
        """
        if not self.single_use_per_customer:
            return True

        return not self.order_set.filter(
            user=user,
            items__product__in=self.applicable_products.all()
            if self.applicable_products.exists()
            else [],
        ).exists()
