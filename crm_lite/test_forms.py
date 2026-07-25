from django.test import SimpleTestCase

from crm_lite.forms import (
    HandoffRequestForm,
    LeadCaptureForm,
)
from crm_lite.models import HandoffRequest, Lead


class LeadCaptureFormTests(SimpleTestCase):
    def valid_data(self, **overrides):
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

    def test_valid_lead_form_normalizes_values(self):
        form = LeadCaptureForm(
            data=self.valid_data(
                name="  Jordan   Lee  ",
                email="  JORDAN@EXAMPLE.COM  ",
                company="  North   Harbor   Studio  ",
                product_sku="  hpl-org-001  ",
                message="  I need pricing for 25 units.  ",
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )
        self.assertEqual(
            form.cleaned_data["name"],
            "Jordan Lee",
        )
        self.assertEqual(
            form.cleaned_data["email"],
            "jordan@example.com",
        )
        self.assertEqual(
            form.cleaned_data["company"],
            "North Harbor Studio",
        )
        self.assertEqual(
            form.cleaned_data["product_sku"],
            "HPL-ORG-001",
        )
        self.assertEqual(
            form.cleaned_data["message"],
            "I need pricing for 25 units.",
        )

    def test_lead_form_requires_contact_consent(self):
        form = LeadCaptureForm(
            data=self.valid_data(
                consent_to_contact=False,
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "consent_to_contact",
            form.errors,
        )

    def test_lead_form_rejects_invalid_email(self):
        form = LeadCaptureForm(
            data=self.valid_data(
                email="not-an-email",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "email",
            form.errors,
        )

    def test_optional_lead_fields_can_be_blank(self):
        form = LeadCaptureForm(
            data=self.valid_data(
                phone="",
                company="",
                product_sku="",
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )


class HandoffRequestFormTests(SimpleTestCase):
    def valid_data(self, **overrides):
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

    def test_handoff_form_accepts_email_contact(self):
        form = HandoffRequestForm(
            data=self.valid_data()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_handoff_form_accepts_phone_without_email(self):
        form = HandoffRequestForm(
            data=self.valid_data(
                contact_email="",
                contact_phone="+1 555 0100",
            )
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_handoff_form_requires_contact_method(self):
        form = HandoffRequestForm(
            data=self.valid_data(
                contact_email="",
                contact_phone="",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "contact_email",
            form.errors,
        )
        self.assertIn(
            "contact_phone",
            form.errors,
        )

    def test_handoff_form_requires_reason(self):
        form = HandoffRequestForm(
            data=self.valid_data(
                reason="",
            )
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "reason",
            form.errors,
        )