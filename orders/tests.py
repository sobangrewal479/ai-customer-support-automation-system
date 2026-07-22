from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from orders.models import MockOrder, OrderLookupAttempt
from support_chat.models import ChatSession


class MockOrderModelTests(TestCase):
    def create_order(self, **overrides):
        order_data = {
            "order_id": "HPL10001",
            "billing_zip": "78701",
            "customer_name": "Jordan Lee",
            "customer_email": "jordan@example.com",
            "order_date": date(2026, 7, 1),
            "status": MockOrder.Status.PROCESSING,
            "carrier": "",
            "tracking_reference": "",
            "eta_window": "July 8-10, 2026",
            "items": "HPL-ORG-001 x 1",
            "order_total_usd": Decimal("49.99"),
            "last_updated": date(2026, 7, 2),
        }
        order_data.update(overrides)

        return MockOrder(**order_data)

    def test_valid_order_passes_validation_and_saves(self):
        order = self.create_order()

        order.full_clean()
        order.save()

        self.assertEqual(MockOrder.objects.count(), 1)
        self.assertEqual(
            str(order),
            "HPL10001 — Processing",
        )

    def test_order_id_and_zip_are_normalized_on_save(self):
        order = self.create_order(
            order_id="  hpl10002  ",
            billing_zip=" 78702 ",
        )

        order.full_clean()
        order.save()

        self.assertEqual(order.order_id, "HPL10002")
        self.assertEqual(order.billing_zip, "78702")

    def test_invalid_order_id_is_rejected(self):
        order = self.create_order(
            order_id="ORDER-10001",
        )

        with self.assertRaises(ValidationError) as error:
            order.full_clean()

        self.assertIn(
            "order_id",
            error.exception.message_dict,
        )

    def test_invalid_billing_zip_is_rejected(self):
        order = self.create_order(
            billing_zip="7870",
        )

        with self.assertRaises(ValidationError) as error:
            order.full_clean()

        self.assertIn(
            "billing_zip",
            error.exception.message_dict,
        )

    def test_negative_order_total_is_rejected(self):
        order = self.create_order(
            order_total_usd=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError) as error:
            order.full_clean()

        self.assertIn(
            "order_total_usd",
            error.exception.message_dict,
        )

    def test_shipped_order_requires_carrier_and_tracking(self):
        order = self.create_order(
            status=MockOrder.Status.SHIPPED,
            carrier="",
            tracking_reference="",
        )

        with self.assertRaises(ValidationError) as error:
            order.full_clean()

        self.assertIn(
            "carrier",
            error.exception.message_dict,
        )
        self.assertIn(
            "tracking_reference",
            error.exception.message_dict,
        )

    def test_processing_order_can_have_no_tracking(self):
        order = self.create_order(
            status=MockOrder.Status.PROCESSING,
            carrier="",
            tracking_reference="",
        )

        order.full_clean()


class OrderLookupAttemptModelTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        self.order = MockOrder.objects.create(
            order_id="HPL10003",
            billing_zip="78703",
            customer_name="Taylor Morgan",
            customer_email="taylor@example.com",
            order_date=date(2026, 7, 3),
            status=MockOrder.Status.SHIPPED,
            carrier="UPS",
            tracking_reference="1ZTEST10003",
            eta_window="July 9-11, 2026",
            items="HPL-KIT-001 x 1",
            order_total_usd=Decimal("67.00"),
            last_updated=date(2026, 7, 4),
        )

    def test_verified_attempt_stores_session_and_order(self):
        attempt = OrderLookupAttempt.objects.create(
            session=self.session,
            provided_order_id="HPL10003",
            matched_order=self.order,
            outcome=OrderLookupAttempt.Outcome.VERIFIED,
        )

        self.assertEqual(
            attempt.session,
            self.session,
        )
        self.assertEqual(
            attempt.matched_order,
            self.order,
        )
        self.assertEqual(
            attempt.outcome,
            OrderLookupAttempt.Outcome.VERIFIED,
        )

    def test_lookup_attempt_string_uses_outcome(self):
        attempt = OrderLookupAttempt.objects.create(
            session=self.session,
            provided_order_id="HPL99999",
            outcome=OrderLookupAttempt.Outcome.NOT_FOUND,
        )

        self.assertEqual(
            str(attempt),
            "HPL99999 — Order not found",
        )