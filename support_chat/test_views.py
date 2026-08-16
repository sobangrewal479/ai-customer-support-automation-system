from django.test import TestCase
from django.urls import reverse

from support_chat.models import (
    ChatMessage,
    ChatSession,
)
from support_chat.views import (
    CHAT_SESSION_KEY,
    MAX_MESSAGE_LENGTH,
)


class ChatPageViewTests(TestCase):
    def test_chat_route_uses_expected_url(self):
        self.assertEqual(
            reverse("support_chat:chat"),
            "/support/",
        )

    def test_get_request_creates_session_and_loads_template(self):
        response = self.client.get(
            reverse("support_chat:chat")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "support_chat/chat.html",
        )

        self.assertEqual(
            ChatSession.objects.count(),
            1,
        )

        self.assertContains(
            response,
            "How can we help?",
        )

        self.assertIn(
            CHAT_SESSION_KEY,
            self.client.session,
        )

    def test_refresh_starts_new_chat_session(self):
        self.client.get(
            reverse("support_chat:chat")
        )

        first_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.client.get(
            reverse("support_chat:chat")
        )

        second_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        self.assertNotEqual(
            first_session_id,
            second_session_id,
        )

        self.assertEqual(
            ChatSession.objects.count(),
            2,
        )

    def test_privacy_acknowledgement_is_required(self):
        response = self.client.post(
            reverse("support_chat:chat"),
            {
                "message": "Hello",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Please acknowledge the privacy notice",
        )

        self.assertEqual(
            ChatMessage.objects.count(),
            0,
        )

    def test_empty_message_is_rejected(self):
        response = self.client.post(
            reverse("support_chat:chat"),
            {
                "privacy_acknowledged": "yes",
                "message": "   ",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Please enter a support question.",
        )

        self.assertEqual(
            ChatMessage.objects.count(),
            0,
        )

    def test_message_above_limit_is_rejected(self):
        response = self.client.post(
            reverse("support_chat:chat"),
            {
                "privacy_acknowledged": "yes",
                "message": "x" * (
                    MAX_MESSAGE_LENGTH + 1
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            (
                f"Your message must not exceed "
                f"{MAX_MESSAGE_LENGTH} characters."
            ),
        )

        self.assertEqual(
            ChatMessage.objects.count(),
            0,
        )

    def test_valid_message_is_processed_and_redirected(self):
        response = self.client.post(
            reverse("support_chat:chat"),
            {
                "privacy_acknowledged": "yes",
                "message": "Hello",
            },
        )

        self.assertRedirects(
            response,
            reverse("support_chat:chat"),
        )

        chat_session = ChatSession.objects.get()

        self.assertTrue(
            chat_session.privacy_acknowledged
        )

        self.assertEqual(
            chat_session.messages.count(),
            2,
        )

        self.assertEqual(
            list(
                chat_session.messages.values_list(
                    "sender_type",
                    flat=True,
                )
            ),
            [
                ChatMessage.SenderType.CUSTOMER,
                ChatMessage.SenderType.ASSISTANT,
            ],
        )

    def test_post_redirect_keeps_chat_before_refresh(self):
        self.client.get(
            reverse("support_chat:chat")
        )

        original_session_id = self.client.session[
            CHAT_SESSION_KEY
        ]

        response = self.client.post(
            reverse("support_chat:chat"),
            {
                "privacy_acknowledged": "yes",
                "message": "Hello",
            },
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self.client.session[
                CHAT_SESSION_KEY
            ],
            original_session_id,
        )

        chat_session = ChatSession.objects.get(
            session_id=original_session_id
        )

        self.assertEqual(
            chat_session.messages.count(),
            2,
        )

    def test_widget_mode_loads_compact_chat(self):
        response = self.client.get(
            reverse("support_chat:chat"),
            {
                "widget": "1",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response.context["widget_mode"]
        )

        self.assertContains(
            response,
            'class="widget-mode"',
        )

        self.assertNotContains(
            response,
            "Approved support",
        )

    def test_standalone_chat_does_not_use_widget_mode(self):
        response = self.client.get(
            reverse("support_chat:chat")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.context["widget_mode"]
        )

        self.assertContains(
            response,
            "Approved support",
        )

    def test_widget_message_redirect_preserves_widget_mode(self):
        response = self.client.post(
            (
                f'{reverse("support_chat:chat")}'
                "?widget=1"
            ),
            {
                "privacy_acknowledged": "yes",
                "message": "Hello",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            (
                f'{reverse("support_chat:chat")}'
                "?widget=1"
            ),
        )

    def test_chat_can_be_embedded_from_same_origin(self):
        response = self.client.get(
            reverse("support_chat:chat"),
            {
                "widget": "1",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.headers["X-Frame-Options"],
            "SAMEORIGIN",
        )