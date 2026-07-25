from django.test import TestCase
from django.urls import reverse

from crm_lite.forms import (
    HandoffRequestForm,
    LeadCaptureForm,
)
from crm_lite.models import HandoffRequest, Lead
from support_chat.models import ChatSession
from support_chat.views import CHAT_SESSION_KEY


class CrmLiteViewTests(TestCase):
    def valid_lead_data(self, **overrides):
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

        return values

    def valid_handoff_data(self, **overrides):
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

        return values

    def test_crm_routes_use_expected_urls(self):
        self.assertEqual(
            reverse("crm_lite:lead_capture"),
            "/contact/lead/",
        )
        self.assertEqual(
            reverse("crm_lite:human_handoff"),
            "/contact/human-support/",
        )

    def test_lead_page_loads_form_and_creates_session(self):
        response = self.client.get(
            reverse("crm_lite:lead_capture")
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTemplateUsed(
            response,
            "crm_lite/lead_capture.html",
        )
        self.assertIsInstance(
            response.context["form"],
            LeadCaptureForm,
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
            "Submit an inquiry",
        )

    def test_valid_lead_submission_creates_linked_record(self):
        response = self.client.post(
            reverse("crm_lite:lead_capture"),
            self.valid_lead_data(
                name="  Jordan   Lee  ",
                email="  JORDAN@EXAMPLE.COM  ",
                product_sku="  hpl-org-001  ",
            ),
            follow=True,
        )

        lead = Lead.objects.get()
        session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.assertRedirects(
            response,
            reverse("crm_lite:lead_capture"),
        )
        self.assertEqual(
            lead.name,
            "Jordan Lee",
        )
        self.assertEqual(
            lead.email,
            "jordan@example.com",
        )
        self.assertEqual(
            lead.product_sku,
            "HPL-ORG-001",
        )
        self.assertEqual(
            str(lead.source_session_id),
            session_id,
        )
        self.assertContains(
            response,
            "Your inquiry has been saved",
        )

    def test_invalid_lead_submission_creates_no_record(self):
        response = self.client.post(
            reverse("crm_lite:lead_capture"),
            self.valid_lead_data(
                consent_to_contact=False,
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            Lead.objects.count(),
            0,
        )
        self.assertContains(
            response,
            "This field is required.",
        )

    def test_repeated_lead_submission_is_flagged(self):
        self.client.post(
            reverse("crm_lite:lead_capture"),
            self.valid_lead_data(),
        )

        self.client.post(
            reverse("crm_lite:lead_capture"),
            self.valid_lead_data(
                message=(
                    "I am following up about the same inquiry."
                ),
            ),
        )

        leads = Lead.objects.order_by(
            "created_at"
        )

        self.assertEqual(
            leads.count(),
            2,
        )
        self.assertFalse(
            leads[0].duplicate_review_required,
        )
        self.assertTrue(
            leads[1].duplicate_review_required,
        )

    def test_handoff_page_loads_form_and_reuses_session(self):
        self.client.get(
            reverse("crm_lite:lead_capture")
        )

        first_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        response = self.client.get(
            reverse("crm_lite:human_handoff")
        )

        second_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTemplateUsed(
            response,
            "crm_lite/human_handoff.html",
        )
        self.assertIsInstance(
            response.context["form"],
            HandoffRequestForm,
        )
        self.assertEqual(
            first_session_id,
            second_session_id,
        )
        self.assertEqual(
            ChatSession.objects.count(),
            1,
        )
        self.assertContains(
            response,
            "Human-support request",
        )

    def test_valid_handoff_submission_creates_request(self):
        response = self.client.post(
            reverse("crm_lite:human_handoff"),
            self.valid_handoff_data(
                category=(
                    HandoffRequest.Category.COMPLAINT
                ),
                reason=(
                    "I need help resolving a complaint."
                ),
            ),
            follow=True,
        )

        handoff = HandoffRequest.objects.get()
        session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.assertRedirects(
            response,
            reverse("crm_lite:human_handoff"),
        )
        self.assertEqual(
            str(handoff.session_id),
            session_id,
        )
        self.assertEqual(
            handoff.priority,
            HandoffRequest.Priority.HIGH,
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Priority Support Queue",
        )
        self.assertContains(
            response,
            "Your human-support request has been created",
        )

    def test_safety_handoff_uses_escalation_queue(self):
        self.client.post(
            reverse("crm_lite:human_handoff"),
            self.valid_handoff_data(
                category=(
                    HandoffRequest.Category.SAFETY_LEGAL
                ),
                reason=(
                    "The product may have caused an injury."
                ),
            ),
        )

        handoff = HandoffRequest.objects.get()

        self.assertEqual(
            handoff.priority,
            HandoffRequest.Priority.URGENT,
        )
        self.assertEqual(
            handoff.assigned_owner,
            "Escalation Queue",
        )

    def test_handoff_accepts_phone_without_email(self):
        response = self.client.post(
            reverse("crm_lite:human_handoff"),
            self.valid_handoff_data(
                contact_email="",
                contact_phone="+1 555 0100",
            ),
        )

        handoff = HandoffRequest.objects.get()

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertEqual(
            handoff.contact_email,
            "",
        )
        self.assertEqual(
            handoff.contact_phone,
            "+1 555 0100",
        )

    def test_invalid_handoff_creates_no_request(self):
        response = self.client.post(
            reverse("crm_lite:human_handoff"),
            self.valid_handoff_data(
                contact_email="",
                contact_phone="",
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            HandoffRequest.objects.count(),
            0,
        )
        self.assertContains(
            response,
            "Provide an email address or phone number",
            count=2,
        )