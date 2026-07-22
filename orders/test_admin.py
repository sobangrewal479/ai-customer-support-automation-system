from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.admin import (
    MockOrderAdmin,
    OrderLookupAttemptAdmin,
)
from orders.models import MockOrder, OrderLookupAttempt


class OrderAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.admin_user = user_model.objects.create_superuser(
            username="orders-admin",
            email="orders-admin@harborandpine.example",
            password="SafeTestPassword123!",
        )

    def test_order_models_are_registered(self):
        self.assertIn(
            MockOrder,
            admin.site._registry,
        )
        self.assertIn(
            OrderLookupAttempt,
            admin.site._registry,
        )

    def test_mock_order_uses_expected_admin_class(self):
        model_admin = admin.site._registry[
            MockOrder
        ]

        self.assertIsInstance(
            model_admin,
            MockOrderAdmin,
        )
        self.assertIn(
            "order_id",
            model_admin.list_display,
        )
        self.assertIn(
            "status",
            model_admin.list_filter,
        )
        self.assertIn(
            "tracking_reference",
            model_admin.search_fields,
        )

    def test_lookup_attempt_uses_expected_admin_class(self):
        model_admin = admin.site._registry[
            OrderLookupAttempt
        ]

        self.assertIsInstance(
            model_admin,
            OrderLookupAttemptAdmin,
        )
        self.assertIn(
            "outcome",
            model_admin.list_display,
        )
        self.assertIn(
            "provided_order_id",
            model_admin.search_fields,
        )

    def test_superuser_can_access_order_admin_pages(self):
        self.client.force_login(self.admin_user)

        order_response = self.client.get(
            reverse(
                "admin:orders_mockorder_changelist"
            )
        )
        attempt_response = self.client.get(
            reverse(
                "admin:orders_orderlookupattempt_changelist"
            )
        )

        self.assertEqual(
            order_response.status_code,
            200,
        )
        self.assertEqual(
            attempt_response.status_code,
            200,
        )