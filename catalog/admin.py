from django.contrib import admin

from catalog.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product_name",
        "category",
        "price_usd",
        "status",
        "stock_band",
        "last_updated",
    )
    list_filter = (
        "category",
        "status",
        "stock_band",
        "last_updated",
    )
    search_fields = (
        "sku",
        "product_name",
        "short_description",
        "material",
        "color",
    )
    ordering = ("sku",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_per_page = 50

    fieldsets = (
        (
            "Product identity",
            {
                "fields": (
                    "sku",
                    "product_name",
                    "category",
                    "short_description",
                )
            },
        ),
        (
            "Price and availability",
            {
                "fields": (
                    "price_usd",
                    "status",
                    "stock_band",
                )
            },
        ),
        (
            "Product details",
            {
                "fields": (
                    "material",
                    "color",
                    "dimensions",
                    "care_instructions",
                    "product_url",
                )
            },
        ),
        (
            "Data management",
            {
                "fields": (
                    "last_updated",
                    "data_owner",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )