from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Product


User = get_user_model()


class DashboardProductTests(TestCase):
    def setUp(self):
        self.product_list_url = reverse(
            "dashboard:product_list"
        )

        self.staff_user = User.objects.create_user(
            username="catalog-reviewer",
            email="catalog-reviewer@example.com",
            password="CatalogReviewerPass123!",
            is_staff=True,
        )

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

    def test_product_list_uses_expected_url(self):
        self.assertEqual(
            self.product_list_url,
            "/dashboard/products/",
        )

    def test_logged_out_user_cannot_access_product_list(
        self,
    ):
        response = self.client.get(
            self.product_list_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                "?next=/dashboard/products/"
            ),
            fetch_redirect_response=False,
        )

    def test_authenticated_staff_user_can_access_page(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.product_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/product_list.html",
        )

        self.assertContains(
            response,
            "Product catalogue",
        )

        self.assertContains(
            response,
            "Approved catalogue",
        )

        self.assertContains(
            response,
            "catalog-reviewer",
        )

    def test_empty_page_displays_expected_message(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.product_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["products"].count(),
            0,
        )

        self.assertContains(
            response,
            "No approved products found",
        )

    def test_page_displays_stored_product(self):
        product = self.create_product()

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.product_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["products"].count(),
            1,
        )

        self.assertEqual(
            response.context["products"].first(),
            product,
        )

        expected_content = (
            "HPL-BTH-001",
            "Cove Cotton Bath Mat",
            "Bath",
            "28.00",
            "Active",
            "Healthy",
            "Cotton",
            "Ivory",
            "24 x 16 in",
            "Machine wash cold and air dry.",
            "Catalog Manager",
            "Open product page",
        )

        for content in expected_content:
            with self.subTest(content=content):
                self.assertContains(
                    response,
                    content,
                )

    def test_discontinued_product_displays_correct_status(
        self,
    ):
        self.create_product(
            sku="HPL-OUT-001",
            product_name="Canvas Outdoor Basket",
            category=Product.Category.OUTDOOR,
            status=Product.Status.DISCONTINUED,
            stock_band=(
                Product.StockBand.DISCONTINUED
            ),
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.product_list_url
        )

        self.assertContains(
            response,
            "Canvas Outdoor Basket",
        )

        self.assertContains(
            response,
            "Discontinued",
        )