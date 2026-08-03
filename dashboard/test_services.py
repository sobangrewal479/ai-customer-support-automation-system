from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from crm_lite.models import HandoffRequest, Lead
from dashboard.services import (
    get_conversation_contact_records,
    get_conversation_records,
    get_dashboard_summary,
)
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
            priority=HandoffRequest.Priority.NORMAL,
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


class ConversationRecordServiceTests(TestCase):
    def test_empty_database_returns_no_conversations(self):
        conversations = get_conversation_records()

        self.assertEqual(
            conversations.count(),
            0,
        )

    def test_service_returns_stored_chat_sessions(self):
        first_session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        second_session = ChatSession.objects.create(
            privacy_acknowledged=False,
        )

        conversations = get_conversation_records()

        self.assertEqual(
            conversations.count(),
            2,
        )

        self.assertSetEqual(
            set(
                conversations.values_list(
                    "pk",
                    flat=True,
                )
            ),
            {
                first_session.pk,
                second_session.pk,
            },
        )


class ConversationContactRecordServiceTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def test_anonymous_conversation_has_no_linked_contact(self):
        contact_records = get_conversation_contact_records(
            self.session
        )

        self.assertFalse(
            contact_records["has_linked_contact"]
        )

        self.assertEqual(
            contact_records["linked_leads"].count(),
            0,
        )

        self.assertEqual(
            contact_records[
                "linked_handoff_requests"
            ].count(),
            0,
        )

    def test_service_returns_linked_lead(self):
        lead = Lead.objects.create(
            name="Alex Morgan",
            email="alex@example.com",
            phone="+1 312 555 0199",
            company="Morgan Design Studio",
            inquiry_type=Lead.InquiryType.BULK_ORDER,
            product_sku="HPL-ORG-001",
            message="I need pricing for a bulk order.",
            consent_to_contact=True,
            source_session=self.session,
        )

        contact_records = get_conversation_contact_records(
            self.session
        )

        self.assertTrue(
            contact_records["has_linked_contact"]
        )

        self.assertEqual(
            contact_records["linked_leads"].count(),
            1,
        )

        self.assertEqual(
            contact_records["linked_leads"].first(),
            lead,
        )

        self.assertEqual(
            contact_records[
                "linked_handoff_requests"
            ].count(),
            0,
        )

    def test_service_returns_linked_handoff_request(self):
        handoff = HandoffRequest.objects.create(
            session=self.session,
            contact_name="Jamie Carter",
            contact_email="jamie@example.com",
            contact_phone="+1 312 555 0188",
            category=(
                HandoffRequest.Category.HUMAN_REQUEST
            ),
            priority=HandoffRequest.Priority.NORMAL,
            reason="I need help from a support agent.",
            assigned_owner="Support Queue",
            sla_due_at=(
                timezone.now()
                + timedelta(hours=24)
            ),
        )

        contact_records = get_conversation_contact_records(
            self.session
        )

        self.assertTrue(
            contact_records["has_linked_contact"]
        )

        self.assertEqual(
            contact_records[
                "linked_handoff_requests"
            ].count(),
            1,
        )

        self.assertEqual(
            contact_records[
                "linked_handoff_requests"
            ].first(),
            handoff,
        )

        self.assertEqual(
            contact_records["linked_leads"].count(),
            0,
        )

    def test_service_excludes_records_from_other_sessions(self):
        other_session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        Lead.objects.create(
            name="Other Customer",
            email="other@example.com",
            inquiry_type=Lead.InquiryType.BULK_ORDER,
            message="This belongs to another session.",
            consent_to_contact=True,
            source_session=other_session,
        )

        HandoffRequest.objects.create(
            session=other_session,
            contact_name="Other Customer",
            contact_email="other@example.com",
            category=(
                HandoffRequest.Category.HUMAN_REQUEST
            ),
            priority=HandoffRequest.Priority.NORMAL,
            reason="This belongs to another session.",
            assigned_owner="Support Queue",
            sla_due_at=(
                timezone.now()
                + timedelta(hours=24)
            ),
        )

        contact_records = get_conversation_contact_records(
            self.session
        )

        self.assertFalse(
            contact_records["has_linked_contact"]
        )

        self.assertEqual(
            contact_records["linked_leads"].count(),
            0,
        )

        self.assertEqual(
            contact_records[
                "linked_handoff_requests"
            ].count(),
            0,
        )