from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from crm_lite.models import HandoffRequest, Lead
from support_chat.models import ChatSession


class LeadModelTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_valid_lead(self, **overrides):
        values = {
            "name": "Jordan Lee",
            "email": "jordan@example.com",
            "phone": "+1 555 0100",
            "company": "North Harbor Studio",
            "inquiry_type": Lead.InquiryType.BULK_ORDER,
            "product_sku": "HPL-ORG-001",
            "message": "I need pricing for 25 units.",
            "consent_to_contact": True,
            "source_session": self.session,
        }
        values.update(overrides)

        return Lead(**values)

    def test_valid_lead_passes_validation(self):
        lead = self.create_valid_lead()

        lead.full_clean()

    def test_lead_requires_contact_consent(self):
        lead = self.create_valid_lead(
            consent_to_contact=False,
        )

        with self.assertRaises(ValidationError) as error:
            lead.full_clean()

        self.assertIn(
            "consent_to_contact",
            error.exception.message_dict,
        )

    def test_lead_requires_name_email_and_message(self):
        lead = self.create_valid_lead(
            name="",
            email="",
            message="",
        )

        with self.assertRaises(ValidationError) as error:
            lead.full_clean()

        self.assertIn(
            "name",
            error.exception.message_dict,
        )
        self.assertIn(
            "email",
            error.exception.message_dict,
        )
        self.assertIn(
            "message",
            error.exception.message_dict,
        )

    def test_lead_values_are_normalized_when_saved(self):
        lead = self.create_valid_lead(
            name="  Jordan   Lee  ",
            email="  JORDAN@EXAMPLE.COM  ",
            company="  North   Harbor   Studio  ",
            product_sku="  hpl-org-001  ",
            message="  I need pricing for 25 units.  ",
            owner="  Sales Queue  ",
        )

        lead.save()
        lead.refresh_from_db()

        self.assertEqual(
            lead.name,
            "Jordan Lee",
        )
        self.assertEqual(
            lead.email,
            "jordan@example.com",
        )
        self.assertEqual(
            lead.company,
            "North Harbor Studio",
        )
        self.assertEqual(
            lead.product_sku,
            "HPL-ORG-001",
        )
        self.assertEqual(
            lead.message,
            "I need pricing for 25 units.",
        )
        self.assertEqual(
            lead.owner,
            "Sales Queue",
        )

    def test_lead_uses_expected_defaults(self):
        lead = self.create_valid_lead(
            owner="",
        )
        lead.save()

        self.assertEqual(
            lead.status,
            Lead.Status.NEW,
        )
        self.assertEqual(
            lead.owner,
            "Support Queue",
        )
        self.assertFalse(
            lead.duplicate_review_required,
        )

    def test_lead_string_uses_name_and_inquiry_type(self):
        lead = self.create_valid_lead()
        lead.save()

        self.assertEqual(
            str(lead),
            "Jordan Lee — Bulk order",
        )


class HandoffRequestModelTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_valid_handoff(self, **overrides):
        values = {
            "session": self.session,
            "contact_name": "Jordan Lee",
            "contact_email": "jordan@example.com",
            "contact_phone": "",
            "category": HandoffRequest.Category.HUMAN_REQUEST,
            "priority": HandoffRequest.Priority.NORMAL,
            "reason": "The customer requested a support agent.",
            "sla_due_at": (
                timezone.now()
                + timedelta(hours=24)
            ),
        }
        values.update(overrides)

        return HandoffRequest(**values)

    def test_valid_handoff_passes_validation(self):
        handoff = self.create_valid_handoff()

        handoff.full_clean()

    def test_handoff_accepts_phone_without_email(self):
        handoff = self.create_valid_handoff(
            contact_email="",
            contact_phone="+1 555 0100",
        )

        handoff.full_clean()

    def test_handoff_requires_email_or_phone(self):
        handoff = self.create_valid_handoff(
            contact_email="",
            contact_phone="",
        )

        with self.assertRaises(ValidationError) as error:
            handoff.full_clean()

        self.assertIn(
            "contact_email",
            error.exception.message_dict,
        )
        self.assertIn(
            "contact_phone",
            error.exception.message_dict,
        )

    def test_handoff_requires_reason(self):
        handoff = self.create_valid_handoff(
            reason="",
        )

        with self.assertRaises(ValidationError) as error:
            handoff.full_clean()

        self.assertIn(
            "reason",
            error.exception.message_dict,
        )

    def test_handoff_values_are_normalized_when_saved(self):
        handoff = self.create_valid_handoff(
            contact_name="  Jordan   Lee  ",
            contact_email="  JORDAN@EXAMPLE.COM  ",
            contact_phone="  +1 555 0100  ",
            reason="  Customer requested a person.  ",
            assigned_owner="  Escalation Queue  ",
        )

        handoff.save()
        handoff.refresh_from_db()

        self.assertEqual(
            handoff.contact_name,
            "Jordan Lee",
        )
        self.assertEqual(
            handoff.contact_email,
            "jordan@example.com",
        )
        self.assertEqual(
            handoff.contact_phone,
            "+1 555 0100",
        )
        self.assertEqual(
            handoff.reason,
            "Customer requested a person.",
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Escalation Queue",
        )

    def test_handoff_uses_expected_defaults(self):
        handoff = self.create_valid_handoff(
            assigned_owner="",
        )
        handoff.save()

        self.assertEqual(
            handoff.status,
            HandoffRequest.Status.NEW,
        )
        self.assertEqual(
            handoff.priority,
            HandoffRequest.Priority.NORMAL,
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Support Queue",
        )

    def test_handoff_string_uses_category_and_status(self):
        handoff = self.create_valid_handoff()
        handoff.save()

        self.assertEqual(
            str(handoff),
            "Customer requested a person — New",
        )