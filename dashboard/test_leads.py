from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crm_lite.models import Lead
from support_chat.models import ChatSession


User = get_user_model()


class DashboardLeadTests(TestCase):
    def setUp(self):
        self.lead_list_url = reverse(
            "dashboard:lead_list"
        )

        self.staff_user = User.objects.create_user(
            username="lead-reviewer",
            email="lead-reviewer@example.com",
            password="LeadReviewerPass123!",
            is_staff=True,
        )

    def test_lead_list_uses_expected_url(self):
        self.assertEqual(
            self.lead_list_url,
            "/dashboard/leads/",
        )

    def test_logged_out_user_cannot_access_lead_list(
        self,
    ):
        response = self.client.get(
            self.lead_list_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                "?next=/dashboard/leads/"
            ),
            fetch_redirect_response=False,
        )

    def test_authenticated_staff_user_can_access_lead_list(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.lead_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/lead_list.html",
        )

        self.assertContains(
            response,
            "Customer leads",
        )

        self.assertContains(
            response,
            "Lead queue",
        )

        self.assertContains(
            response,
            "lead-reviewer",
        )

    def test_empty_lead_list_displays_expected_message(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.lead_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["leads"].count(),
            0,
        )

        self.assertContains(
            response,
            "No customer leads found",
        )

    def test_lead_list_displays_stored_lead(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        lead = Lead.objects.create(
            name="Alex Morgan",
            email="alex.morgan.test@example.com",
            phone="+1 555 0199",
            company="Morgan Home Studio",
            inquiry_type=Lead.InquiryType.BULK_ORDER,
            product_sku="HPL-ORG-001",
            message=(
                "I would like pricing and delivery "
                "information for 40 units."
            ),
            consent_to_contact=True,
            status=Lead.Status.NEW,
            owner="Support Queue",
            duplicate_review_required=True,
            internal_notes="Review bulk pricing request.",
            source_session=session,
        )

        conversation_detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.lead_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["leads"].count(),
            1,
        )

        self.assertEqual(
            response.context["leads"].first(),
            lead,
        )

        expected_content = (
            "Alex Morgan",
            "alex.morgan.test@example.com",
            "+1 555 0199",
            "Morgan Home Studio",
            "Bulk order",
            "HPL-ORG-001",
            "Support Queue",
            "Review bulk pricing request.",
            "Yes — staff review required",
        )

        for content in expected_content:
            with self.subTest(content=content):
                self.assertContains(
                    response,
                    content,
                )

        self.assertContains(
            response,
            f'href="{conversation_detail_url}"',
        )

        self.assertContains(
            response,
            "Review conversation",
        )