from datetime import date
from decimal import Decimal

from django.test import TestCase

from catalog.models import Product
from catalog.retrieval import (
    get_availability_message,
    resolve_product,
    search_products,
)


class ProductRetrievalTests(TestCase):
    def create_product(self, sku, name, **overrides):
        values = {
            "category": Product.Category.KITCHEN,
            "short_description": "A practical home product.",
            "price_usd": Decimal("39.99"),
            "status": Product.Status.ACTIVE,
            "stock_band": Product.StockBand.HEALTHY,
            "material": "Bamboo",
            "color": "Natural",
            "dimensions": "12 x 8 x 4 in",
            "care_instructions": "Wipe with a damp cloth.",
            "product_url": (
                f"https://harborandpine.example/products/{sku.lower()}"
            ),
            "last_updated": date(2026, 7, 1),
            "data_owner": "Catalog Manager",
        }
        values.update(overrides)

        return Product.objects.create(
            sku=sku,
            product_name=name,
            **values,
        )

    def test_exact_sku_returns_product(self):
        product = self.create_product(
            "HP-KI-001",
            "Bamboo Counter Organizer",
        )

        resolution = resolve_product("HP-KI-001")

        self.assertEqual(resolution.status, "found")
        self.assertEqual(
            resolution.best_match.product,
            product,
        )
        self.assertEqual(resolution.best_match.score, 100)

    def test_exact_product_name_returns_product(self):
        product = self.create_product(
            "HP-KI-002",
            "Stoneware Utensil Holder",
        )

        resolution = resolve_product(
            "Stoneware Utensil Holder"
        )

        self.assertEqual(resolution.status, "found")
        self.assertEqual(
            resolution.best_match.product,
            product,
        )

    def test_partial_unique_name_returns_product(self):
        product = self.create_product(
            "HP-KI-003",
            "Expandable Bamboo Drawer Tray",
        )
        self.create_product(
            "HP-KI-004",
            "Cotton Kitchen Towel Set",
        )

        resolution = resolve_product(
            "expandable bamboo tray"
        )

        self.assertEqual(resolution.status, "found")
        self.assertEqual(
            resolution.best_match.product,
            product,
        )

    def test_broad_category_query_is_ambiguous(self):
        self.create_product(
            "HP-KI-005",
            "Glass Pantry Jar",
            material="Glass",
        )
        self.create_product(
            "HP-KI-006",
            "Metal Dish Rack",
            material="Metal",
        )

        resolution = resolve_product("Kitchen")

        self.assertEqual(resolution.status, "ambiguous")
        self.assertEqual(len(resolution.matches), 2)

    def test_unknown_product_returns_not_found(self):
        self.create_product(
            "HP-KI-007",
            "Bamboo Spice Rack",
        )

        resolution = resolve_product(
            "electric coffee machine"
        )

        self.assertEqual(resolution.status, "not_found")
        self.assertEqual(resolution.matches, ())

    def test_empty_query_returns_no_results(self):
        self.create_product(
            "HP-KI-008",
            "Wood Serving Board",
        )

        self.assertEqual(search_products(""), [])
        self.assertEqual(search_products("   "), [])

    def test_equal_scores_are_ordered_by_sku(self):
        self.create_product(
            "HP-KI-010",
            "Large Storage Basket",
        )
        self.create_product(
            "HP-KI-009",
            "Small Storage Basket",
        )

        results = search_products("storage basket")

        self.assertEqual(
            [result.product.sku for result in results],
            ["HP-KI-009", "HP-KI-010"],
        )

    def test_availability_messages_cover_all_statuses(self):
        cases = (
            (
                Product.Status.ACTIVE,
                Product.StockBand.HEALTHY,
                "active",
            ),
            (
                Product.Status.LOW_STOCK,
                Product.StockBand.LOW_STOCK,
                "low stock",
            ),
            (
                Product.Status.OUT_OF_STOCK,
                Product.StockBand.OUT_OF_STOCK,
                "out of stock",
            ),
            (
                Product.Status.DISCONTINUED,
                Product.StockBand.DISCONTINUED,
                "discontinued",
            ),
        )

        for index, (status, stock_band, wording) in enumerate(cases):
            with self.subTest(status=status):
                product = self.create_product(
                    f"HP-KI-{20 + index}",
                    f"Test Product {index}",
                    status=status,
                    stock_band=stock_band,
                )

                message = get_availability_message(product)

                self.assertIn(wording, message.lower())