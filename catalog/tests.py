from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalog.models import Product


class ProductModelTests(TestCase):
    def create_product(self, **overrides):
        product_data = {
            "sku": "HP-HO-001",
            "product_name": "Bamboo Entryway Organizer",
            "category": Product.Category.HOME_ORGANIZATION,
            "short_description": (
                "A compact bamboo organizer for entryway essentials."
            ),
            "price_usd": Decimal("49.99"),
            "status": Product.Status.ACTIVE,
            "stock_band": Product.StockBand.HEALTHY,
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
            "last_updated": date(2026, 7, 1),
            "data_owner": "Catalog Manager",
        }
        product_data.update(overrides)

        return Product(**product_data)

    def test_valid_product_passes_validation_and_saves(self):
        product = self.create_product()

        product.full_clean()
        product.save()

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(str(product), "HP-HO-001 — Bamboo Entryway Organizer")

    def test_duplicate_sku_is_rejected(self):
        first_product = self.create_product()
        first_product.full_clean()
        first_product.save()

        duplicate_product = self.create_product(
            product_name="Different Product Name",
        )

        with self.assertRaises(ValidationError):
            duplicate_product.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                duplicate_product.save()

    def test_negative_price_is_rejected(self):
        product = self.create_product(
            price_usd=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError) as error:
            product.full_clean()

        self.assertIn("price_usd", error.exception.message_dict)

    def test_invalid_category_is_rejected(self):
        product = self.create_product(
            category="Invalid Category",
        )

        with self.assertRaises(ValidationError) as error:
            product.full_clean()

        self.assertIn("category", error.exception.message_dict)

    def test_active_product_accepts_moderate_stock(self):
        product = self.create_product(
            status=Product.Status.ACTIVE,
            stock_band=Product.StockBand.MODERATE,
        )

        product.full_clean()

    def test_low_stock_product_requires_low_stock_band(self):
        product = self.create_product(
            status=Product.Status.LOW_STOCK,
            stock_band=Product.StockBand.HEALTHY,
        )

        with self.assertRaises(ValidationError) as error:
            product.full_clean()

        self.assertIn("stock_band", error.exception.message_dict)

    def test_out_of_stock_product_requires_out_of_stock_band(self):
        product = self.create_product(
            status=Product.Status.OUT_OF_STOCK,
            stock_band=Product.StockBand.LOW_STOCK,
        )

        with self.assertRaises(ValidationError) as error:
            product.full_clean()

        self.assertIn("stock_band", error.exception.message_dict)

    def test_discontinued_product_requires_discontinued_band(self):
        product = self.create_product(
            status=Product.Status.DISCONTINUED,
            stock_band=Product.StockBand.OUT_OF_STOCK,
        )

        with self.assertRaises(ValidationError) as error:
            product.full_clean()

        self.assertIn("stock_band", error.exception.message_dict)