from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    class Category(models.TextChoices):
        HOME_ORGANIZATION = "Home Organization", "Home Organization"
        KITCHEN = "Kitchen", "Kitchen"
        BATH = "Bath", "Bath"
        OFFICE = "Office", "Office"
        OUTDOOR = "Outdoor", "Outdoor"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        LOW_STOCK = "low_stock", "Low stock"
        OUT_OF_STOCK = "out_of_stock", "Out of stock"
        DISCONTINUED = "discontinued", "Discontinued"

    class StockBand(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        MODERATE = "moderate", "Moderate"
        LOW_STOCK = "low_stock", "Low stock"
        OUT_OF_STOCK = "out_of_stock", "Out of stock"
        DISCONTINUED = "discontinued", "Discontinued"

    sku = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )
    product_name = models.CharField(
        max_length=150,
        db_index=True,
    )
    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        db_index=True,
    )
    short_description = models.TextField()
    price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True,
    )
    stock_band = models.CharField(
        max_length=20,
        choices=StockBand.choices,
    )
    material = models.CharField(
        max_length=100,
        blank=True,
    )
    color = models.CharField(
        max_length=80,
        blank=True,
    )
    dimensions = models.CharField(
        max_length=120,
        blank=True,
    )
    care_instructions = models.TextField(
        blank=True,
    )
    product_url = models.URLField(
        max_length=300,
        blank=True,
    )
    last_updated = models.DateField()
    data_owner = models.CharField(
        max_length=120,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["sku"]
        indexes = [
            models.Index(
                fields=["category", "status"],
                name="catalog_cat_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        valid_stock_bands = {
            self.Status.ACTIVE: {
                self.StockBand.HEALTHY,
                self.StockBand.MODERATE,
            },
            self.Status.LOW_STOCK: {
                self.StockBand.LOW_STOCK,
            },
            self.Status.OUT_OF_STOCK: {
                self.StockBand.OUT_OF_STOCK,
            },
            self.Status.DISCONTINUED: {
                self.StockBand.DISCONTINUED,
            },
        }

        allowed_bands = valid_stock_bands.get(self.status, set())

        if self.stock_band and self.stock_band not in allowed_bands:
            raise ValidationError(
                {
                    "stock_band": (
                        "The selected stock band does not match "
                        "the product status."
                    )
                }
            )

    def __str__(self):
        return f"{self.sku} — {self.product_name}"