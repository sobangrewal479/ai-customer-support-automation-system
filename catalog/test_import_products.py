import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalog.management.commands.import_products import EXPECTED_HEADERS
from catalog.models import Product


class ImportProductsCommandTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.csv_path = (
            Path(self.temporary_directory.name) / "products.csv"
        )

    def valid_row(self, **overrides):
        row = {
            "sku": "HP-HO-001",
            "product_name": "Bamboo Entryway Organizer",
            "category": "Home Organization",
            "short_description": (
                "A compact organizer for entryway essentials."
            ),
            "price_usd": "49.99",
            "status": "active",
            "stock_band": "healthy",
            "material": "Bamboo",
            "color": "Natural",
            "dimensions": "18 x 8 x 6 in",
            "care_instructions": (
                "Wipe with a soft damp cloth. Do not soak."
            ),
            "product_url": (
                "https://harborandpine.example/products/"
                "bamboo-entryway-organizer"
            ),
            "last_updated": "2026-07-01",
            "data_owner": "Catalog Manager",
        }
        row.update(overrides)
        return row

    def write_csv(self, rows, headers=None):
        selected_headers = headers or EXPECTED_HEADERS

        with self.csv_path.open(
            mode="w",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=selected_headers,
            )
            writer.writeheader()

            for row in rows:
                filtered_row = {
                    header: row.get(header, "")
                    for header in selected_headers
                }
                writer.writerow(filtered_row)

        return self.csv_path

    def test_valid_csv_creates_product(self):
        self.write_csv([self.valid_row()])
        output = StringIO()

        call_command(
            "import_products",
            str(self.csv_path),
            stdout=output,
        )

        product = Product.objects.get(sku="HP-HO-001")

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(
            product.product_name,
            "Bamboo Entryway Organizer",
        )
        self.assertEqual(
            product.price_usd,
            Decimal("49.99"),
        )
        self.assertEqual(
            product.last_updated,
            date(2026, 7, 1),
        )
        self.assertIn(
            "1 created, 0 updated",
            output.getvalue(),
        )

    def test_existing_product_is_updated_without_duplicate(self):
        self.write_csv([self.valid_row()])
        call_command(
            "import_products",
            str(self.csv_path),
            stdout=StringIO(),
        )

        updated_row = self.valid_row(
            product_name="Updated Bamboo Organizer",
            price_usd="59.99",
        )
        self.write_csv([updated_row])
        output = StringIO()

        call_command(
            "import_products",
            str(self.csv_path),
            stdout=output,
        )

        product = Product.objects.get(sku="HP-HO-001")

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(
            product.product_name,
            "Updated Bamboo Organizer",
        )
        self.assertEqual(
            product.price_usd,
            Decimal("59.99"),
        )
        self.assertIn(
            "0 created, 1 updated",
            output.getvalue(),
        )

    def test_duplicate_sku_in_csv_is_rejected_and_rolled_back(self):
        duplicate_row = self.valid_row(
            product_name="Duplicate Product",
        )
        self.write_csv(
            [
                self.valid_row(),
                duplicate_row,
            ]
        )

        with self.assertRaises(CommandError):
            call_command(
                "import_products",
                str(self.csv_path),
                stdout=StringIO(),
            )

        self.assertEqual(Product.objects.count(), 0)

    def test_incorrect_headers_are_rejected(self):
        invalid_headers = EXPECTED_HEADERS[:-1]

        self.write_csv(
            [self.valid_row()],
            headers=invalid_headers,
        )

        with self.assertRaises(CommandError):
            call_command(
                "import_products",
                str(self.csv_path),
                stdout=StringIO(),
            )

        self.assertEqual(Product.objects.count(), 0)

    def test_invalid_status_and_stock_band_are_rolled_back(self):
        invalid_row = self.valid_row(
            status="low_stock",
            stock_band="healthy",
        )
        self.write_csv([invalid_row])

        with self.assertRaises(CommandError):
            call_command(
                "import_products",
                str(self.csv_path),
                stdout=StringIO(),
            )

        self.assertEqual(Product.objects.count(), 0)