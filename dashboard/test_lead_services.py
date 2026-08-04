from django.test import TestCase

from crm_lite.models import Lead
from dashboard.services import get_lead_records
from support_chat.models import ChatSession


class DashboardLeadServiceTests(TestCase):
    def test_empty_database_returns_no_leads(self):
        leads = get_lead_records()

        self.assertEqual(
            leads.count(),
            0,
        )

    def test_service_returns_leads_in_model_order(self):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        first_lead = Lead.objects.create(
            name="Jordan Lee",
            email="jordan@example.com",
            inquiry_type=Lead.InquiryType.PRODUCT_ADVICE,
            message="I need help selecting a product.",
            consent_to_contact=True,
            source_session=session,
        )

        second_lead = Lead.objects.create(
            name="Alex Morgan",
            email="alex@example.com",
            inquiry_type=Lead.InquiryType.BULK_ORDER,
            message="I need pricing for 40 units.",
            consent_to_contact=True,
            source_session=session,
        )

        leads = get_lead_records()

        self.assertEqual(
            leads.count(),
            2,
        )

        self.assertEqual(
            leads.first(),
            second_lead,
        )

        self.assertIn(
            first_lead,
            leads,
        )

        self.assertEqual(
            leads.first().source_session,
            session,
        )