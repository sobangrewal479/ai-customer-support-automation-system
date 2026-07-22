from datetime import date
from decimal import Decimal

from django.test import TestCase

from orders.models import MockOrder, OrderLookupAttempt
from orders.services import (
    GENERIC_VERIFICATION_FAILURE,
    REPEATED_FAILURE_RESPONSE,
    lookup_order,
)
from support_chat.models import ChatSession


class OrderLookupServiceTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        self.order = MockOrder.objects.create(
            order_id="HPL10001",
            billing_zip="78701",
            customer_name="Jordan Lee",
            customer_email="jordan@example.com",
            order_date=date(2026, 7, 1),
            status=MockOrder.Status.SHIPPED,
            carrier="UPS",
            tracking_reference="1ZTEST10001",
            eta_window="July 8-10, 2026",
            items="HPL-ORG-001 x 1",
            order_total_usd=Decimal("49.99"),
            last_updated=date(2026, 7, 2),
        )

    def test_missing_verification_data_returns_safe_response(self):
        result = lookup_order(
            "",
            "78701",
            session=self.session,
        )

        self.assertFalse(result.verified)
        self.assertEqual(
            result.outcome,
            OrderLookupAttempt.Outcome.MISSING_DATA,
        )
        self.assertEqual(
            result.message,
            GENERIC_VERIFICATION_FAILURE,
        )
        self.assertEqual(result.approved_data, {})

    def test_unknown_order_returns_safe_generic_response(self):
        result = lookup_order(
            "HPL99999",
            "78701",
            session=self.session,
        )

        self.assertFalse(result.verified)
        self.assertEqual(
            result.outcome,
            OrderLookupAttempt.Outcome.NOT_FOUND,
        )
        self.assertEqual(
            result.message,
            GENERIC_VERIFICATION_FAILURE,
        )
        self.assertNotIn(
            self.order.customer_name,
            result.message,
        )

    def test_zip_mismatch_reveals_no_order_details(self):
        result = lookup_order(
            "HPL10001",
            "99999",
            session=self.session,
        )

        attempt = OrderLookupAttempt.objects.get()

        self.assertFalse(result.verified)
        self.assertEqual(
            result.outcome,
            OrderLookupAttempt.Outcome.ZIP_MISMATCH,
        )
        self.assertEqual(result.approved_data, {})
        self.assertIsNone(attempt.matched_order)

    def test_verified_lookup_returns_only_approved_fields(self):
        result = lookup_order(
            "hpl10001",
            "78701",
            session=self.session,
        )

        attempt = OrderLookupAttempt.objects.get()

        self.assertTrue(result.verified)
        self.assertEqual(
            result.outcome,
            OrderLookupAttempt.Outcome.VERIFIED,
        )
        self.assertEqual(
            result.approved_data["status"],
            "Shipped",
        )
        self.assertEqual(
            result.approved_data["carrier"],
            "UPS",
        )
        self.assertEqual(
            result.approved_data[
                "tracking_reference"
            ],
            "1ZTEST10001",
        )
        self.assertEqual(
            attempt.matched_order,
            self.order,
        )

        prohibited_fields = {
            "customer_name",
            "customer_email",
            "items",
            "order_total_usd",
            "billing_zip",
        }

        self.assertTrue(
            prohibited_fields.isdisjoint(
                result.approved_data.keys()
            )
        )

    def test_verified_message_excludes_private_order_data(self):
        result = lookup_order(
            "HPL10001",
            "78701",
            session=self.session,
        )

        self.assertNotIn(
            self.order.customer_name,
            result.message,
        )
        self.assertNotIn(
            self.order.customer_email,
            result.message,
        )
        self.assertNotIn(
            self.order.items,
            result.message,
        )
        self.assertNotIn(
            str(self.order.order_total_usd),
            result.message,
        )

    def test_third_consecutive_failure_blocks_lookup(self):
        lookup_order(
            "HPL99991",
            "78701",
            session=self.session,
        )
        lookup_order(
            "HPL99992",
            "78701",
            session=self.session,
        )
        result = lookup_order(
            "HPL99993",
            "78701",
            session=self.session,
        )

        outcomes = list(
            OrderLookupAttempt.objects.filter(
                session=self.session
            )
            .order_by("created_at")
            .values_list(
                "outcome",
                flat=True,
            )
        )

        self.assertEqual(
            outcomes,
            [
                OrderLookupAttempt.Outcome.NOT_FOUND,
                OrderLookupAttempt.Outcome.NOT_FOUND,
                OrderLookupAttempt.Outcome.BLOCKED,
            ],
        )
        self.assertFalse(result.verified)
        self.assertTrue(
            result.requires_security_handoff
        )
        self.assertEqual(
            result.message,
            REPEATED_FAILURE_RESPONSE,
        )

    def test_blocked_session_cannot_verify_an_order(self):
        for order_number in (
            "HPL99991",
            "HPL99992",
            "HPL99993",
        ):
            lookup_order(
                order_number,
                "78701",
                session=self.session,
            )

        result = lookup_order(
            "HPL10001",
            "78701",
            session=self.session,
        )

        self.assertFalse(result.verified)
        self.assertEqual(
            result.outcome,
            OrderLookupAttempt.Outcome.BLOCKED,
        )
        self.assertTrue(
            result.requires_security_handoff
        )

    def test_processing_order_omits_carrier_and_tracking(self):
        processing_order = MockOrder.objects.create(
            order_id="HPL10002",
            billing_zip="78702",
            customer_name="Taylor Morgan",
            customer_email="taylor@example.com",
            order_date=date(2026, 7, 2),
            status=MockOrder.Status.PROCESSING,
            carrier="",
            tracking_reference="",
            eta_window="July 10-12, 2026",
            items="HPL-KIT-001 x 1",
            order_total_usd=Decimal("67.00"),
            last_updated=date(2026, 7, 3),
        )

        result = lookup_order(
            processing_order.order_id,
            processing_order.billing_zip,
            session=self.session,
        )

        self.assertTrue(result.verified)
        self.assertNotIn(
            "carrier",
            result.approved_data,
        )
        self.assertNotIn(
            "tracking_reference",
            result.approved_data,
        )