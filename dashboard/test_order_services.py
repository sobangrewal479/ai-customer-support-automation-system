from datetime import date
from decimal import Decimal

from django.test import TestCase

from dashboard.services import (
    get_order_lookup_attempt_records,
)
from orders.models import MockOrder, OrderLookupAttempt
from support_chat.models import ChatSession


class DashboardOrderActivityServiceTests(TestCase):
    def test_empty_database_returns_no_lookup_attempts(
        self,
    ):
        lookup_attempts = (
            get_order_lookup_attempt_records()
        )

        self.assertEqual(
            lookup_attempts.count(),
            0,
        )

    def test_service_returns_attempts_in_model_order(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        order = MockOrder.objects.create(
            order_id="HPL10002",
            billing_zip="60601",
            customer_name="Mia Brooks",
            customer_email="mia.brooks@example.com",
            order_date=date(2026, 7, 1),
            status=MockOrder.Status.SHIPPED,
            carrier="FedEx",
            tracking_reference="MOCK-FedEx-900002",
            eta_window="2026-07-22",
            items="HPL-ORG-005; HPL-ORG-014",
            order_total_usd=Decimal("83.99"),
            last_updated=date(2026, 7, 14),
        )

        first_attempt = OrderLookupAttempt.objects.create(
            session=session,
            provided_order_id="HPL99999",
            outcome=(
                OrderLookupAttempt.Outcome.NOT_FOUND
            ),
        )

        second_attempt = OrderLookupAttempt.objects.create(
            session=session,
            provided_order_id=order.order_id,
            matched_order=order,
            outcome=(
                OrderLookupAttempt.Outcome.VERIFIED
            ),
        )

        lookup_attempts = (
            get_order_lookup_attempt_records()
        )

        self.assertEqual(
            lookup_attempts.count(),
            2,
        )

        self.assertEqual(
            lookup_attempts.first(),
            second_attempt,
        )

        self.assertIn(
            first_attempt,
            lookup_attempts,
        )

        self.assertEqual(
            lookup_attempts.first().session,
            session,
        )

        self.assertEqual(
            lookup_attempts.first().matched_order,
            order,
        )