from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from crm_lite.models import HandoffRequest
from support_chat.models import ChatSession


User = get_user_model()


class DashboardHandoffRequestTests(TestCase):
    def setUp(self):
        self.handoff_list_url = reverse(
            "dashboard:handoff_request_list"
        )

        self.staff_user = User.objects.create_user(
            username="handoff-reviewer",
            email="handoff-reviewer@example.com",
            password="HandoffReviewerPass123!",
            is_staff=True,
        )

    def test_handoff_list_uses_expected_url(self):
        self.assertEqual(
            self.handoff_list_url,
            "/dashboard/human-support-requests/",
        )

    def test_logged_out_user_cannot_access_handoff_list(
        self,
    ):
        response = self.client.get(
            self.handoff_list_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                "?next=/dashboard/human-support-requests/"
            ),
            fetch_redirect_response=False,
        )

    def test_authenticated_staff_user_can_access_page(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.handoff_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/handoff_request_list.html",
        )

        self.assertContains(
            response,
            "Human-support requests",
        )

        self.assertContains(
            response,
            "Human-support queue",
        )

        self.assertContains(
            response,
            "handoff-reviewer",
        )

    def test_empty_page_displays_expected_message(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.handoff_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "handoff_requests"
            ].count(),
            0,
        )

        self.assertContains(
            response,
            "No human-support requests found",
        )

    def test_page_displays_stored_handoff_request(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        handoff_request = HandoffRequest.objects.create(
            session=session,
            contact_name="Alex Morgan",
            contact_email=(
                "alex.morgan.test@example.com"
            ),
            contact_phone="+1 555 0199",
            category=HandoffRequest.Category.COMPLAINT,
            priority=HandoffRequest.Priority.HIGH,
            reason=(
                "I received a damaged product and need "
                "help resolving the issue."
            ),
            status=HandoffRequest.Status.NEW,
            assigned_owner="Priority Support Queue",
            sla_due_at=(
                timezone.now()
                + timedelta(hours=4)
            ),
            notes="Review the damaged-product claim.",
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
            self.handoff_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "handoff_requests"
            ].count(),
            1,
        )

        self.assertEqual(
            response.context[
                "handoff_requests"
            ].first(),
            handoff_request,
        )

        expected_content = (
            "Complaint or angry customer",
            "New",
            "Alex Morgan",
            "alex.morgan.test@example.com",
            "+1 555 0199",
            "Priority Support Queue",
            "Review the damaged-product claim.",
        )

        for content in expected_content:
            with self.subTest(content=content):
                self.assertContains(
                    response,
                    content,
                )

        self.assertContains(
            response,
            (
                '<p class="dashboard-eyebrow">'
                "High priority"
                "</p>"
            ),
            html=True,
        )

        self.assertContains(
            response,
            f'href="{conversation_detail_url}"',
        )

        self.assertContains(
            response,
            "Review conversation",
        )