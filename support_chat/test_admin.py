from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from support_chat.models import (
    ChatMessage,
    ChatSession,
    UnansweredQuestion,
)


class SupportChatAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()

        self.admin_user = user_model.objects.create_superuser(
            username="support-chat-admin",
            email="support-chat-admin@harborandpine.example",
            password="SafeTestPassword123!",
        )

    def test_support_chat_models_are_registered(self):
        self.assertIn(ChatSession, admin.site._registry)
        self.assertIn(ChatMessage, admin.site._registry)
        self.assertIn(UnansweredQuestion, admin.site._registry)

    def test_admin_can_access_chat_session_list(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:support_chat_chatsession_changelist")
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_chat_message_list(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:support_chat_chatmessage_changelist")
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_unanswered_question_list(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "admin:support_chat_unansweredquestion_changelist"
            )
        )

        self.assertEqual(response.status_code, 200)