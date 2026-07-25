from django.core.exceptions import ValidationError
from django.db import models


class Lead(models.Model):
    class InquiryType(models.TextChoices):
        PRODUCT_ADVICE = (
            "product_advice",
            "Product advice",
        )
        BULK_ORDER = (
            "bulk_order",
            "Bulk order",
        )
        TRADE_PROGRAM = (
            "trade_program",
            "Trade program",
        )
        PARTNERSHIP = (
            "partnership",
            "Partnership",
        )
        OTHER = (
            "other",
            "Other",
        )

    class Status(models.TextChoices):
        NEW = (
            "new",
            "New",
        )
        CONTACTED = (
            "contacted",
            "Contacted",
        )
        QUALIFIED = (
            "qualified",
            "Qualified",
        )
        CLOSED = (
            "closed",
            "Closed",
        )

    name = models.CharField(
        max_length=120,
    )
    email = models.EmailField(
        max_length=254,
    )
    phone = models.CharField(
        max_length=40,
        blank=True,
    )
    company = models.CharField(
        max_length=160,
        blank=True,
    )
    inquiry_type = models.CharField(
        max_length=30,
        choices=InquiryType.choices,
        db_index=True,
    )
    product_sku = models.CharField(
        max_length=30,
        blank=True,
    )
    message = models.TextField(
        max_length=2000,
    )
    consent_to_contact = models.BooleanField(
        default=False,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    owner = models.CharField(
        max_length=120,
        default="Support Queue",
        blank=True,
        db_index=True,
    )
    source_session = models.ForeignKey(
        "support_chat.ChatSession",
        on_delete=models.SET_NULL,
        related_name="leads",
        null=True,
        blank=True,
    )
    duplicate_review_required = models.BooleanField(
        default=False,
        db_index=True,
    )
    internal_notes = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "inquiry_type",
                    "status",
                ],
                name="crm_lead_type_stat_idx",
            ),
            models.Index(
                fields=[
                    "owner",
                    "status",
                ],
                name="crm_lead_owner_stat_idx",
            ),
        ]

    def clean(self):
        super().clean()

        self.name = " ".join(
            (self.name or "").split()
        )
        self.email = (
            self.email or ""
        ).strip().lower()
        self.phone = (
            self.phone or ""
        ).strip()
        self.company = " ".join(
            (self.company or "").split()
        )
        self.product_sku = (
            self.product_sku or ""
        ).strip().upper()
        self.message = (
            self.message or ""
        ).strip()
        self.owner = (
            self.owner or "Support Queue"
        ).strip()

        errors = {}

        if not self.name:
            errors["name"] = (
                "Enter the customer's name."
            )

        if not self.email:
            errors["email"] = (
                "Enter the customer's email address."
            )

        if not self.message:
            errors["message"] = (
                "Enter the customer's inquiry or request."
            )

        if not self.consent_to_contact:
            errors["consent_to_contact"] = (
                "Consent is required before saving "
                "a contact request."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = " ".join(
            (self.name or "").split()
        )
        self.email = (
            self.email or ""
        ).strip().lower()
        self.phone = (
            self.phone or ""
        ).strip()
        self.company = " ".join(
            (self.company or "").split()
        )
        self.product_sku = (
            self.product_sku or ""
        ).strip().upper()
        self.message = (
            self.message or ""
        ).strip()
        self.owner = (
            self.owner or "Support Queue"
        ).strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.name} — "
            f"{self.get_inquiry_type_display()}"
        )


class HandoffRequest(models.Model):
    class Category(models.TextChoices):
        HUMAN_REQUEST = (
            "human_request",
            "Customer requested a person",
        )
        UNSUPPORTED = (
            "unsupported",
            "Unsupported or uncertain request",
        )
        COMPLAINT = (
            "complaint",
            "Complaint or angry customer",
        )
        PAYMENT_REFUND = (
            "payment_refund",
            "Payment or refund dispute",
        )
        SAFETY_LEGAL = (
            "safety_legal",
            "Safety, injury, or legal concern",
        )
        PRIVACY_REQUEST = (
            "privacy_request",
            "Privacy or data request",
        )
        HIGH_VALUE_SALES = (
            "high_value_sales",
            "High-value sales inquiry",
        )
        OTHER = (
            "other",
            "Other",
        )

    class Priority(models.TextChoices):
        LOW = (
            "low",
            "Low",
        )
        NORMAL = (
            "normal",
            "Normal",
        )
        HIGH = (
            "high",
            "High",
        )
        URGENT = (
            "urgent",
            "Urgent",
        )

    class Status(models.TextChoices):
        NEW = (
            "new",
            "New",
        )
        ASSIGNED = (
            "assigned",
            "Assigned",
        )
        IN_PROGRESS = (
            "in_progress",
            "In progress",
        )
        WAITING_FOR_CUSTOMER = (
            "waiting_for_customer",
            "Waiting for customer",
        )
        RESOLVED = (
            "resolved",
            "Resolved",
        )
        CLOSED = (
            "closed",
            "Closed",
        )

    session = models.ForeignKey(
        "support_chat.ChatSession",
        on_delete=models.SET_NULL,
        related_name="handoff_requests",
        null=True,
        blank=True,
    )
    contact_name = models.CharField(
        max_length=120,
        blank=True,
    )
    contact_email = models.EmailField(
        max_length=254,
        blank=True,
    )
    contact_phone = models.CharField(
        max_length=40,
        blank=True,
    )
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
        db_index=True,
    )
    reason = models.TextField(
        max_length=2000,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    assigned_owner = models.CharField(
        max_length=120,
        default="Support Queue",
        blank=True,
        db_index=True,
    )
    sla_due_at = models.DateTimeField(
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]
        indexes = [
            models.Index(
                fields=[
                    "priority",
                    "status",
                ],
                name="crm_hand_pri_stat_idx",
            ),
            models.Index(
                fields=[
                    "assigned_owner",
                    "status",
                ],
                name="crm_hand_owner_stat_idx",
            ),
        ]

    def clean(self):
        super().clean()

        self.contact_name = " ".join(
            (self.contact_name or "").split()
        )
        self.contact_email = (
            self.contact_email or ""
        ).strip().lower()
        self.contact_phone = (
            self.contact_phone or ""
        ).strip()
        self.reason = (
            self.reason or ""
        ).strip()
        self.assigned_owner = (
            self.assigned_owner or "Support Queue"
        ).strip()

        errors = {}

        if (
            not self.contact_email
            and not self.contact_phone
        ):
            contact_error = (
                "Provide an email address or phone number "
                "for the human-support request."
            )

            errors["contact_email"] = contact_error
            errors["contact_phone"] = contact_error

        if not self.reason:
            errors["reason"] = (
                "Enter the reason for the human handoff."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.contact_name = " ".join(
            (self.contact_name or "").split()
        )
        self.contact_email = (
            self.contact_email or ""
        ).strip().lower()
        self.contact_phone = (
            self.contact_phone or ""
        ).strip()
        self.reason = (
            self.reason or ""
        ).strip()
        self.assigned_owner = (
            self.assigned_owner or "Support Queue"
        ).strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_category_display()} — "
            f"{self.get_status_display()}"
        )