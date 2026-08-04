import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from crm_lite.models import HandoffRequest, Lead
from support_chat.models import (
    ChatMessage,
    ChatSession,
    UnansweredQuestion,
)


User = get_user_model()


class DashboardAuthenticationTests(TestCase):
    def setUp(self):
        self.dashboard_url = reverse(
            "dashboard:home"
        )

        self.conversation_list_url = reverse(
            "dashboard:conversation_list"
        )

        self.staff_user = User.objects.create_user(
            username="dashboard-agent",
            email="dashboard-agent@example.com",
            password="AgentPass123!",
            is_staff=True,
        )

    def test_dashboard_uses_expected_url(self):
        self.assertEqual(
            self.dashboard_url,
            "/dashboard/",
        )

    def test_logged_out_user_is_redirected_to_staff_login(
        self,
    ):
        response = self.client.get(
            self.dashboard_url
        )

        self.assertRedirects(
            response,
            "/staff/login/?next=/dashboard/",
            fetch_redirect_response=False,
        )

    def test_authenticated_staff_user_can_access_dashboard(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.dashboard_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/home.html",
        )

        self.assertContains(
            response,
            "Harbor &amp; Pine Support Dashboard",
        )

        self.assertContains(
            response,
            "dashboard-agent",
        )

    def test_dashboard_lists_required_operational_areas(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.dashboard_url
        )

        expected_sections = (
            "Customer conversations",
            "Unanswered questions",
            "Leads",
            "Human-support requests",
            "Order activity",
            "Product catalogue",
        )

        for section in expected_sections:
            with self.subTest(section=section):
                self.assertContains(
                    response,
                    section,
                )

    def test_dashboard_receives_summary_metrics(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.dashboard_url
        )

        summary = response.context["summary"]

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

        self.assertContains(
            response,
            "Operational summary",
        )

    def test_conversation_list_uses_expected_url(self):
        self.assertEqual(
            self.conversation_list_url,
            "/dashboard/conversations/",
        )

    def test_logged_out_user_cannot_access_conversation_list(
        self,
    ):
        response = self.client.get(
            self.conversation_list_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                "?next=/dashboard/conversations/"
            ),
            fetch_redirect_response=False,
        )

    def test_authenticated_staff_user_can_access_conversation_list(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.conversation_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/conversation_list.html",
        )

        self.assertContains(
            response,
            "Customer conversations",
        )

        self.assertContains(
            response,
            "Conversation queue",
        )

        self.assertContains(
            response,
            "dashboard-agent",
        )

    def test_conversation_list_displays_stored_session(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.conversation_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["conversations"].count(),
            1,
        )

        self.assertContains(
            response,
            f"Session {session.pk}",
        )

        self.assertContains(
            response,
            "1 stored conversation",
        )

        self.assertContains(
            response,
            "Privacy acknowledged:",
        )

        self.assertContains(
            response,
            "Yes",
        )

        self.assertContains(
            response,
            "Messages:",
        )

    def test_conversation_list_links_to_session_detail(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.conversation_list_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            f'href="{detail_url}"',
        )

        self.assertContains(
            response,
            "Review conversation details",
        )

    def test_conversation_detail_uses_expected_url(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.assertEqual(
            detail_url,
            (
                "/dashboard/conversations/"
                f"{session.pk}/"
            ),
        )

    def test_logged_out_user_cannot_access_conversation_detail(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        response = self.client.get(
            detail_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                f"?next={detail_url}"
            ),
            fetch_redirect_response=False,
        )

    def test_authenticated_staff_user_can_access_conversation_detail(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/conversation_detail.html",
        )

        self.assertEqual(
            response.context["conversation"],
            session,
        )

        self.assertContains(
            response,
            "Conversation details",
        )

        self.assertContains(
            response,
            "Conversation transcript",
        )

        self.assertContains(
            response,
            str(session.pk),
        )

    def test_conversation_detail_displays_stored_messages(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        ChatMessage.objects.create(
            session=session,
            sender_type=ChatMessage.SenderType.CUSTOMER,
            message="Where is my order?",
        )

        ChatMessage.objects.create(
            session=session,
            sender_type=ChatMessage.SenderType.ASSISTANT,
            message=(
                "I can help you securely verify your order."
            ),
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Where is my order?",
        )

        self.assertContains(
            response,
            (
                "I can help you securely verify "
                "your order."
            ),
        )

        self.assertContains(
            response,
            "Message 1",
        )

        self.assertContains(
            response,
            "Message 2",
        )

        self.assertContains(
            response,
            "Messages",
        )

        self.assertContains(
            response,
            "2",
        )

    def test_anonymous_conversation_shows_no_contact_message(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.context["has_linked_contact"]
        )

        self.assertContains(
            response,
            "Linked customer/contact details",
        )

        self.assertContains(
            response,
            "Anonymous conversation",
        )

        self.assertContains(
            response,
            (
                "No lead-capture submission or "
                "human-support request is linked"
            ),
        )

    def test_conversation_detail_displays_linked_lead(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        Lead.objects.create(
            name="Alex Morgan",
            email="alex@example.com",
            phone="+1 312 555 0199",
            company="Morgan Design Studio",
            inquiry_type=Lead.InquiryType.BULK_ORDER,
            product_sku="HPL-ORG-001",
            message="I need pricing for a bulk order.",
            consent_to_contact=True,
            source_session=session,
        )

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.context["has_linked_contact"]
        )

        self.assertEqual(
            response.context["linked_leads"].count(),
            1,
        )

        self.assertContains(
            response,
            "Lead record",
        )

        self.assertContains(
            response,
            "Alex Morgan",
        )

        self.assertContains(
            response,
            "alex@example.com",
        )

        self.assertContains(
            response,
            "+1 312 555 0199",
        )

        self.assertContains(
            response,
            "Morgan Design Studio",
        )

        self.assertContains(
            response,
            "I need pricing for a bulk order.",
        )

    def test_conversation_detail_displays_linked_handoff_request(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        HandoffRequest.objects.create(
            session=session,
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

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": session.pk,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.context["has_linked_contact"]
        )

        self.assertEqual(
            response.context[
                "linked_handoff_requests"
            ].count(),
            1,
        )

        self.assertContains(
            response,
            "Human-support request",
        )

        self.assertContains(
            response,
            "Jamie Carter",
        )

        self.assertContains(
            response,
            "jamie@example.com",
        )

        self.assertContains(
            response,
            "+1 312 555 0188",
        )

        self.assertContains(
            response,
            "I need help from a support agent.",
        )

        self.assertContains(
            response,
            "Support Queue",
        )

    def test_missing_conversation_detail_returns_404(
        self,
    ):
        missing_session_id = uuid.uuid4()

        detail_url = reverse(
            "dashboard:conversation_detail",
            kwargs={
                "session_id": missing_session_id,
            },
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            404,
        )


class DashboardUnansweredQuestionTests(TestCase):
    def setUp(self):
        self.unanswered_question_url = reverse(
            "dashboard:unanswered_question_list"
        )

        self.staff_user = User.objects.create_user(
            username="knowledge-reviewer",
            email="reviewer@example.com",
            password="ReviewerPass123!",
            is_staff=True,
        )

    def test_unanswered_question_list_uses_expected_url(
        self,
    ):
        self.assertEqual(
            self.unanswered_question_url,
            "/dashboard/unanswered-questions/",
        )

    def test_logged_out_user_cannot_access_unanswered_questions(
        self,
    ):
        response = self.client.get(
            self.unanswered_question_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                "?next=/dashboard/unanswered-questions/"
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
            self.unanswered_question_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/unanswered_question_list.html",
        )

        self.assertContains(
            response,
            "Unanswered questions",
        )

        self.assertContains(
            response,
            "Unanswered-question queue",
        )

        self.assertContains(
            response,
            "knowledge-reviewer",
        )

    def test_empty_page_displays_expected_message(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.unanswered_question_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "No unanswered questions found",
        )

        self.assertEqual(
            response.context[
                "unanswered_questions"
            ].count(),
            0,
        )

    def test_page_displays_stored_unanswered_question(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        unanswered_question = (
            UnansweredQuestion.objects.create(
                question=(
                    "Can this organizer be used outdoors?"
                ),
                normalized_topic=(
                    "can this organizer be used outdoors"
                ),
                session=session,
                occurrence_count=3,
                status=(
                    UnansweredQuestion.Status.REVIEWING
                ),
                review_notes=(
                    "Confirm approved outdoor-use guidance."
                ),
            )
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
            self.unanswered_question_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "unanswered_questions"
            ].count(),
            1,
        )

        self.assertEqual(
            response.context[
                "unanswered_questions"
            ].first(),
            unanswered_question,
        )

        self.assertContains(
            response,
            "can this organizer be used outdoors",
        )

        self.assertContains(
            response,
            "Can this organizer be used outdoors?",
        )

        self.assertContains(
            response,
            "Reviewing",
        )

        self.assertContains(
            response,
            "Confirm approved outdoor-use guidance.",
        )

        self.assertContains(
            response,
            "Occurrences:",
        )

        self.assertContains(
            response,
            "3",
        )

        self.assertContains(
            response,
            f'href="{conversation_detail_url}"',
        )

        self.assertContains(
            response,
            "Review conversation",
        )