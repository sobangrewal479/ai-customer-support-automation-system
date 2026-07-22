import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


ORDER_ID_PATTERN = re.compile(r"^HPL\d{5}$")
BILLING_ZIP_PATTERN = re.compile(r"^\d{5}$")


class MockOrder(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        OUT_FOR_DELIVERY = (
            "out_for_delivery",
            "Out for delivery",
        )
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order_id = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
    )
    billing_zip = models.CharField(
        max_length=10,
    )
    customer_name = models.CharField(
        max_length=150,
    )
    customer_email = models.EmailField()
    order_date = models.DateField()
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        db_index=True,
    )
    carrier = models.CharField(
        max_length=50,
        blank=True,
    )
    tracking_reference = models.CharField(
        max_length=100,
        blank=True,
    )
    eta_window = models.CharField(
        max_length=100,
    )
    items = models.TextField()
    order_total_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )
    last_updated = models.DateField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["order_id"]
        indexes = [
            models.Index(
                fields=["status", "order_date"],
                name="orders_status_date_idx",
            ),
        ]

    def clean(self):
        super().clean()

        field_errors = {}

        normalized_order_id = (
            self.order_id or ""
        ).strip().upper()

        if not ORDER_ID_PATTERN.fullmatch(
            normalized_order_id
        ):
            field_errors["order_id"] = (
                "Order ID must use the format HPL followed "
                "by exactly five digits."
            )

        normalized_zip = (
            self.billing_zip or ""
        ).strip()

        if not BILLING_ZIP_PATTERN.fullmatch(
            normalized_zip
        ):
            field_errors["billing_zip"] = (
                "Billing ZIP must contain exactly five digits."
            )

        statuses_requiring_tracking = {
            self.Status.PACKED,
            self.Status.SHIPPED,
            self.Status.OUT_FOR_DELIVERY,
            self.Status.DELIVERED,
        }

        if self.status in statuses_requiring_tracking:
            if not self.carrier.strip():
                field_errors["carrier"] = (
                    "Carrier is required for this order status."
                )

            if not self.tracking_reference.strip():
                field_errors["tracking_reference"] = (
                    "Tracking reference is required for this "
                    "order status."
                )

        if field_errors:
            raise ValidationError(field_errors)

    def save(self, *args, **kwargs):
        self.order_id = self.order_id.strip().upper()
        self.billing_zip = self.billing_zip.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_id} — {self.get_status_display()}"


class OrderLookupAttempt(models.Model):
    class Outcome(models.TextChoices):
        VERIFIED = "verified", "Verified"
        NOT_FOUND = "not_found", "Order not found"
        ZIP_MISMATCH = "zip_mismatch", "Billing ZIP mismatch"
        MISSING_DATA = "missing_data", "Missing verification data"
        BLOCKED = "blocked", "Blocked after repeated failures"

    session = models.ForeignKey(
        "support_chat.ChatSession",
        on_delete=models.SET_NULL,
        related_name="order_lookup_attempts",
        null=True,
        blank=True,
    )
    provided_order_id = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
    )
    matched_order = models.ForeignKey(
        MockOrder,
        on_delete=models.SET_NULL,
        related_name="lookup_attempts",
        null=True,
        blank=True,
    )
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.provided_order_id or 'Missing order ID'} "
            f"— {self.get_outcome_display()}"
        )