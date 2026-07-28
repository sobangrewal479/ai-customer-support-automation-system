from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from crm_lite.models import HandoffRequest, Lead
from dashboard.services import get_dashboard_summary
from support_chat.models import ChatSession


class DashboardSummaryServiceTests(TestCase):
    def test_empty_database_returns_zero_counts(self):
        summary = get_dashboard_summary()

        self.assertEqual(
            summary["chat_sessions"],
            0,
        )
        self.assertEqual(
            summary["unanswered_questions"],
            0,
        )
        self.assertEqual(
            summary["leads"],
            0,
        )
        self.assertEqual(
            summary["handoff_requests"],
            0,
        )
        self.assertEqual(
            summary["order_lookup_attempts"],
            0,
        )
        self.assertEqual(
            summary["products"],
            0,
        )

    def test_summary_counts_existing_records(self):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        Lead.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            inquiry_type=Lead.InquiryType.BULK_ORDER,
            product_sku="HPL-ORG-001",
            message="I need pricing for 25 units.",
            consent_to_contact=True,
            source_session=session,
        )

        HandoffRequest.objects.create(
            session=session,
            contact_name="Jordan Lee",
            contact_email="jordan@example.com",
            category=(
                HandoffRequest.Category.HUMAN_REQUEST
            ),
            priority=(
                HandoffRequest.Priority.NORMAL
            ),
            reason="The customer requested human support.",
            assigned_owner="Support Queue",
            sla_due_at=(
                timezone.now()
                + timedelta(hours=24)
            ),
        )

        summary = get_dashboard_summary()

        self.assertEqual(
            summary["chat_sessions"],
            1,
        )
        self.assertEqual(
            summary["leads"],
            1,
        )
        self.assertEqual(
            summary["handoff_requests"],
            1,
        )
        self.assertEqual(
            summary["unanswered_questions"],
            0,
        )
        self.assertEqual(
            summary["order_lookup_attempts"],
            0,
        )
        self.assertEqual(
            summary["products"],
            0,
        )