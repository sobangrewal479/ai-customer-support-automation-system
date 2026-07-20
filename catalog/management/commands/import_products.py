import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product


EXPECTED_HEADERS = [
    "sku",
    "product_name",
    "category",
    "short_description",
    "price_usd",
    "status",
    "stock_band",
    "material",
    "color",
    "dimensions",
    "care_instructions",
    "product_url",
    "last_updated",
    "data_owner",
]


class Command(BaseCommand):
    help = "Import validated Harbor & Pine products from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=str(settings.BASE_DIR / "data" / "products.csv"),
            help="CSV path. Defaults to data/products.csv.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            raise CommandError(f"CSV file was not found: {csv_path}")

        created_count = 0
        updated_count = 0
        seen_skus = set()

        with csv_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames != EXPECTED_HEADERS:
                raise CommandError(
                    "The CSV headings do not match the approved "
                    "product-data structure."
                )

            for row_number, row in enumerate(reader, start=2):
                if not any(
                    (value or "").strip()
                    for value in row.values()
                ):
                    continue

                sku = (row["sku"] or "").strip()

                if not sku:
                    raise CommandError(
                        f"Row {row_number}: SKU is required."
                    )

                if sku in seen_skus:
                    raise CommandError(
                        f"Row {row_number}: duplicate SKU {sku} "
                        "exists in the CSV file."
                    )

                seen_skus.add(sku)

                try:
                    product_values = {
                        "product_name": row["product_name"].strip(),
                        "category": row["category"].strip(),
                        "short_description": (
                            row["short_description"].strip()
                        ),
                        "price_usd": Decimal(
                            row["price_usd"].strip()
                        ),
                        "status": row["status"].strip(),
                        "stock_band": row["stock_band"].strip(),
                        "material": row["material"].strip(),
                        "color": row["color"].strip(),
                        "dimensions": row["dimensions"].strip(),
                        "care_instructions": (
                            row["care_instructions"].strip()
                        ),
                        "product_url": row["product_url"].strip(),
                        "last_updated": date.fromisoformat(
                            row["last_updated"].strip()
                        ),
                        "data_owner": row["data_owner"].strip(),
                    }
                except (ValueError, InvalidOperation) as error:
                    raise CommandError(
                        f"Row {row_number} ({sku}) contains an "
                        f"invalid price or date: {error}"
                    ) from error

                product = Product.objects.filter(sku=sku).first()
                is_new = product is None

                if is_new:
                    product = Product(sku=sku)

                for field_name, value in product_values.items():
                    setattr(product, field_name, value)

                try:
                    product.full_clean()
                except ValidationError as error:
                    raise CommandError(
                        f"Row {row_number} ({sku}) failed "
                        f"validation: {error.message_dict}"
                    ) from error

                product.save()

                if is_new:
                    created_count += 1
                else:
                    updated_count += 1

        if not seen_skus:
            raise CommandError(
                "The CSV file contains no product records."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(seen_skus)} products: "
                f"{created_count} created, "
                f"{updated_count} updated."
            )
        )