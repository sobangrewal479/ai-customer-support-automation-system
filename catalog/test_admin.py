from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.admin import ProductAdmin
from catalog.models import Product


class ProductAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.admin_user = user_model.objects.create_superuser(
            username="catalog-admin",
            email="catalog-admin@harborandpine.example",
            password="SafeTestPassword123!",
        )

    def test_product_is_registered_in_admin(self):
        self.assertIn(Product, admin.site._registry)

    def test_product_uses_expected_admin_configuration(self):
        product_admin = admin.site._registry[Product]

        self.assertIsInstance(product_admin, ProductAdmin)
        self.assertIn("sku", product_admin.list_display)
        self.assertIn("product_name", product_admin.list_display)
        self.assertIn("status", product_admin.list_display)
        self.assertIn("category", product_admin.list_filter)
        self.assertIn("sku", product_admin.search_fields)

    def test_superuser_can_access_product_admin_page(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:catalog_product_changelist")
        )

        self.assertEqual(response.status_code, 200)