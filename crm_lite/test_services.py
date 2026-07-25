from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from crm_lite.forms import (
    HandoffRequestForm,
    LeadCaptureForm,
)
from crm_lite.models import HandoffRequest, Lead
from crm_lite.services import (
    create_handoff_from_form,
    create_lead_from_form,
)
from support_chat.models import ChatSession


class LeadCaptureServiceTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_form(self, **overrides):
        values = {
            "name": "Jordan Lee",
            "email": "jordan@example.com",
            "phone": "+1 555 0100",
            "company": "North Harbor Studio",
            "inquiry_type": Lead.InquiryType.BULK_ORDER,
            "product_sku": "HPL-ORG-001",
            "message": "I need pricing for 25 units.",
            "consent_to_contact": True,
        }
        values.update(overrides)

        return LeadCaptureForm(data=values)

    def test_service_creates_lead_and_links_session(self):
        form = self.create_form()

        lead = create_lead_from_form(
            form,
            session=self.session,
        )

        self.assertEqual(
            Lead.objects.count(),
            1,
        )
        self.assertEqual(
            lead.source_session,
            self.session,
        )
        self.assertEqual(
            lead.status,
            Lead.Status.NEW,
        )
        self.assertFalse(
            lead.duplicate_review_required,
        )

    def test_repeated_email_and_inquiry_is_flagged(self):
        create_lead_from_form(
            self.create_form(),
            session=self.session,
        )

        second_lead = create_lead_from_form(
            self.create_form(
                message=(
                    "Following up about the same order."
                ),
            ),
            session=self.session,
        )

        self.assertEqual(
            Lead.objects.count(),
            2,
        )
        self.assertTrue(
            second_lead.duplicate_review_required,
        )

    def test_different_inquiry_type_is_not_duplicate(self):
        create_lead_from_form(
            self.create_form(),
            session=self.session,
        )

        second_lead = create_lead_from_form(
            self.create_form(
                inquiry_type=(
                    Lead.InquiryType.PARTNERSHIP
                ),
            ),
            session=self.session,
        )

        self.assertFalse(
            second_lead.duplicate_review_required,
        )

    def test_invalid_lead_form_is_rejected(self):
        form = self.create_form(
            consent_to_contact=False,
        )

        with self.assertRaises(ValueError):
            create_lead_from_form(
                form,
                session=self.session,
            )

        self.assertEqual(
            Lead.objects.count(),
            0,
        )


class HandoffServiceTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_form(self, **overrides):
        values = {
            "contact_name": "Jordan Lee",
            "contact_email": "jordan@example.com",
            "contact_phone": "",
            "category": (
                HandoffRequest.Category.HUMAN_REQUEST
            ),
            "reason": (
                "I need help from a support agent."
            ),
        }
        values.update(overrides)

        return HandoffRequestForm(data=values)

    def test_human_request_uses_normal_priority(self):
        before_creation = timezone.now()

        handoff = create_handoff_from_form(
            self.create_form(),
            session=self.session,
        )

        expected_minimum = (
            before_creation
            + timedelta(hours=24)
        )
        expected_maximum = (
            timezone.now()
            + timedelta(hours=24, seconds=5)
        )

        self.assertEqual(
            handoff.session,
            self.session,
        )
        self.assertEqual(
            handoff.priority,
            HandoffRequest.Priority.NORMAL,
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Support Queue",
        )
        self.assertGreaterEqual(
            handoff.sla_due_at,
            expected_minimum,
        )
        self.assertLessEqual(
            handoff.sla_due_at,
            expected_maximum,
        )

    def test_safety_request_uses_urgent_priority(self):
        before_creation = timezone.now()

        handoff = create_handoff_from_form(
            self.create_form(
                category=(
                    HandoffRequest.Category.SAFETY_LEGAL
                ),
                reason=(
                    "The product may have caused an injury."
                ),
            ),
            session=self.session,
        )

        expected_minimum = (
            before_creation
            + timedelta(hours=1)
        )
        expected_maximum = (
            timezone.now()
            + timedelta(hours=1, seconds=5)
        )

        self.assertEqual(
            handoff.priority,
            HandoffRequest.Priority.URGENT,
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Escalation Queue",
        )
        self.assertGreaterEqual(
            handoff.sla_due_at,
            expected_minimum,
        )
        self.assertLessEqual(
            handoff.sla_due_at,
            expected_maximum,
        )

    def test_complaint_uses_high_priority(self):
        handoff = create_handoff_from_form(
            self.create_form(
                category=(
                    HandoffRequest.Category.COMPLAINT
                ),
                reason=(
                    "I need help resolving a complaint."
                ),
            ),
            session=self.session,
        )

        self.assertEqual(
            handoff.priority,
            HandoffRequest.Priority.HIGH,
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Priority Support Queue",
        )

    def test_invalid_handoff_form_is_rejected(self):
        form = self.create_form(
            contact_email="",
            contact_phone="",
        )

        with self.assertRaises(ValueError):
            create_handoff_from_form(
                form,
                session=self.session,
            )

        self.assertEqual(
            HandoffRequest.objects.count(),
            0,
        )