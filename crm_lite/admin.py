from django.contrib import admin

from crm_lite.models import HandoffRequest, Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "inquiry_type",
        "product_sku",
        "status",
        "owner",
        "duplicate_review_required",
        "created_at",
    )

    list_filter = (
        "inquiry_type",
        "status",
        "duplicate_review_required",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
        "company",
        "product_sku",
        "message",
        "owner",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    raw_id_fields = (
        "source_session",
    )

    date_hierarchy = "created_at"

    ordering = (
        "-created_at",
    )

    fieldsets = (
        (
            "Customer details",
            {
                "fields": (
                    "name",
                    "email",
                    "phone",
                    "company",
                    "consent_to_contact",
                )
            },
        ),
        (
            "Inquiry",
            {
                "fields": (
                    "inquiry_type",
                    "product_sku",
                    "message",
                    "source_session",
                )
            },
        ),
        (
            "Internal workflow",
            {
                "fields": (
                    "status",
                    "owner",
                    "duplicate_review_required",
                    "internal_notes",
                )
            },
        ),
        (
            "Record timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(HandoffRequest)
class HandoffRequestAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "priority",
        "status",
        "contact_name",
        "contact_email",
        "assigned_owner",
        "sla_due_at",
        "created_at",
    )

    list_filter = (
        "category",
        "priority",
        "status",
        "assigned_owner",
        "sla_due_at",
        "created_at",
    )

    search_fields = (
        "contact_name",
        "contact_email",
        "contact_phone",
        "reason",
        "assigned_owner",
        "notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    raw_id_fields = (
        "session",
    )

    date_hierarchy = "created_at"

    ordering = (
        "-created_at",
    )

    fieldsets = (
        (
            "Customer contact",
            {
                "fields": (
                    "contact_name",
                    "contact_email",
                    "contact_phone",
                    "session",
                )
            },
        ),
        (
            "Handoff request",
            {
                "fields": (
                    "category",
                    "priority",
                    "reason",
                    "sla_due_at",
                )
            },
        ),
        (
            "Internal workflow",
            {
                "fields": (
                    "status",
                    "assigned_owner",
                    "notes",
                )
            },
        ),
        (
            "Record timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )