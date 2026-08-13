from datetime import date
from decimal import Decimal

from django.test import TestCase

from catalog.models import Product
from dashboard.services import get_product_records


class DashboardProductServiceTests(TestCase):
    def create_product(self, **overrides):
        product_data = {
            "sku": "HPL-BTH-001",
            "product_name": "Cove Cotton Bath Mat",
            "category": Product.Category.BATH,
            "short_description": (
                "A practical bath essential designed "
                "for calm, organized everyday spaces."
            ),
            "price_usd": Decimal("28.00"),
            "status": Product.Status.ACTIVE,
            "stock_band": Product.StockBand.HEALTHY,
            "material": "Cotton",
            "color": "Ivory",
            "dimensions": "24 x 16 in",
            "care_instructions": (
                "Machine wash cold and air dry."
            ),
            "product_url": (
                "https://harborandpine.example/"
                "products/cove-cotton-bath-mat"
            ),
            "last_updated": date(2026, 7, 1),
            "data_owner": "Catalog Manager",
        }

        product_data.update(overrides)

        return Product.objects.create(
            **product_data
        )

    def test_empty_database_returns_no_products(self):
        products = get_product_records()

        self.assertEqual(
            products.count(),
            0,
        )

    def test_service_returns_products_in_model_order(
        self,
    ):
        second_product = self.create_product(
            sku="HPL-KIT-002",
            product_name="Bamboo Kitchen Tray",
            category=Product.Category.KITCHEN,
        )

        first_product = self.create_product(
            sku="HPL-BTH-001",
            product_name="Cove Cotton Bath Mat",
        )

        products = get_product_records()

        self.assertEqual(
            products.count(),
            2,
        )

        self.assertEqual(
            products.first(),
            first_product,
        )

        self.assertIn(
            second_product,
            products,
        )