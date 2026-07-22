from django.contrib import admin

from orders.models import MockOrder, OrderLookupAttempt


@admin.register(MockOrder)
class MockOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "customer_name",
        "order_date",
        "status",
        "carrier",
        "eta_window",
        "last_updated",
    )
    list_filter = (
        "status",
        "carrier",
        "order_date",
        "last_updated",
    )
    search_fields = (
        "order_id",
        "customer_name",
        "customer_email",
        "billing_zip",
        "tracking_reference",
        "items",
    )
    ordering = ("order_id",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_per_page = 50

    fieldsets = (
        (
            "Order identity",
            {
                "fields": (
                    "order_id",
                    "order_date",
                    "status",
                )
            },
        ),
        (
            "Verification information",
            {
                "fields": (
                    "billing_zip",
                    "customer_name",
                    "customer_email",
                )
            },
        ),
        (
            "Delivery information",
            {
                "fields": (
                    "carrier",
                    "tracking_reference",
                    "eta_window",
                    "last_updated",
                )
            },
        ),
        (
            "Order details",
            {
                "fields": (
                    "items",
                    "order_total_usd",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(OrderLookupAttempt)
class OrderLookupAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "provided_order_id",
        "outcome",
        "session",
        "matched_order",
        "created_at",
    )
    list_filter = (
        "outcome",
        "created_at",
    )
    search_fields = (
        "provided_order_id",
        "session__session_id",
        "matched_order__order_id",
    )
    readonly_fields = (
        "session",
        "provided_order_id",
        "matched_order",
        "outcome",
        "created_at",
    )
    ordering = ("-created_at",)
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False