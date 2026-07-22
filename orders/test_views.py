from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from orders.forms import OrderLookupForm
from orders.models import MockOrder, OrderLookupAttempt
from orders.services import GENERIC_VERIFICATION_FAILURE
from support_chat.models import ChatSession
from support_chat.views import CHAT_SESSION_KEY


class OrderLookupViewTests(TestCase):
    def setUp(self):
        self.order = MockOrder.objects.create(
            order_id="HPL10002",
            billing_zip="60601",
            customer_name="Mia Brooks",
            customer_email="mia.brooks@example.com",
            order_date=date(2026, 6, 3),
            status=MockOrder.Status.SHIPPED,
            carrier="FedEx",
            tracking_reference="MOCK-FedEx-900002",
            eta_window="2026-07-22",
            items="HPL-ORG-005; HPL-ORG-014",
            order_total_usd=Decimal("83.99"),
            last_updated=date(2026, 7, 14),
        )

    def test_lookup_route_uses_expected_url(self):
        self.assertEqual(
            reverse("orders:lookup"),
            "/order-lookup/",
        )

    def test_get_request_loads_template_and_creates_session(
        self,
    ):
        response = self.client.get(
            reverse("orders:lookup")
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTemplateUsed(
            response,
            "orders/order_lookup.html",
        )
        self.assertIsInstance(
            response.context["form"],
            OrderLookupForm,
        )
        self.assertEqual(
            ChatSession.objects.count(),
            1,
        )
        self.assertIn(
            CHAT_SESSION_KEY,
            self.client.session,
        )
        self.assertContains(
            response,
            "Secure order verification",
        )

    def test_existing_browser_session_is_reused(self):
        self.client.get(
            reverse("orders:lookup")
        )

        first_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.client.get(
            reverse("orders:lookup")
        )

        second_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.assertEqual(
            first_session_id,
            second_session_id,
        )
        self.assertEqual(
            ChatSession.objects.count(),
            1,
        )

    def test_invalid_form_creates_no_lookup_attempt(self):
        response = self.client.post(
            reverse("orders:lookup"),
            {
                "order_id": "INVALID",
                "billing_zip": "6060",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "Enter an order ID in the format",
        )
        self.assertContains(
            response,
            "Enter the five-digit billing ZIP",
        )
        self.assertEqual(
            OrderLookupAttempt.objects.count(),
            0,
        )

    def test_correct_credentials_display_approved_result(self):
        response = self.client.post(
            reverse("orders:lookup"),
            {
                "order_id": "hpl10002",
                "billing_zip": "60601",
            },
        )

        attempt = OrderLookupAttempt.objects.get()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "Order HPL10002 is currently shipped.",
        )
        self.assertContains(
            response,
            "FedEx",
        )
        self.assertContains(
            response,
            "MOCK-FedEx-900002",
        )
        self.assertEqual(
            attempt.outcome,
            OrderLookupAttempt.Outcome.VERIFIED,
        )
        self.assertEqual(
            attempt.matched_order,
            self.order,
        )

    def test_verified_result_does_not_expose_private_fields(
        self,
    ):
        response = self.client.post(
            reverse("orders:lookup"),
            {
                "order_id": "HPL10002",
                "billing_zip": "60601",
            },
        )

        self.assertNotContains(
            response,
            self.order.customer_name,
        )
        self.assertNotContains(
            response,
            self.order.customer_email,
        )
        self.assertNotContains(
            response,
            self.order.items,
        )
        self.assertNotContains(
            response,
            str(self.order.order_total_usd),
        )

    def test_wrong_zip_displays_generic_failure_only(self):
        response = self.client.post(
            reverse("orders:lookup"),
            {
                "order_id": "HPL10002",
                "billing_zip": "99999",
            },
        )

        attempt = OrderLookupAttempt.objects.get()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            GENERIC_VERIFICATION_FAILURE,
        )
        self.assertNotContains(
            response,
            self.order.customer_name,
        )
        self.assertNotContains(
            response,
            self.order.customer_email,
        )
        self.assertIsNone(
            attempt.matched_order,
        )
        self.assertEqual(
            attempt.outcome,
            OrderLookupAttempt.Outcome.ZIP_MISMATCH,
        )

    def test_third_failed_attempt_requires_human_review(
        self,
    ):
        for order_id in (
            "HPL99991",
            "HPL99992",
            "HPL99993",
        ):
            response = self.client.post(
                reverse("orders:lookup"),
                {
                    "order_id": order_id,
                    "billing_zip": "60601",
                },
            )

        self.assertContains(
            response,
            "Further verification requires",
        )
        self.assertContains(
            response,
            "human-support review.",
        )
        self.assertTrue(
            OrderLookupAttempt.objects.filter(
                outcome=OrderLookupAttempt.Outcome.BLOCKED,
            ).exists()
        )