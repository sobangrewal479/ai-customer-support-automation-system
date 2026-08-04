from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class DashboardNavigationTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="navigation-agent",
            email="navigation@example.com",
            password="NavigationPass123!",
            is_staff=True,
        )

        self.client.force_login(
            self.staff_user
        )

    def test_dashboard_links_to_conversation_queue(self):
        response = self.client.get(
            reverse("dashboard:home")
        )

        conversation_url = reverse(
            "dashboard:conversation_list"
        )

        self.assertContains(
            response,
            f'href="{conversation_url}"',
        )

        self.assertContains(
            response,
            "Open customer conversations",
        )

    def test_dashboard_links_to_unanswered_question_queue(
        self,
    ):
        response = self.client.get(
            reverse("dashboard:home")
        )

        unanswered_question_url = reverse(
            "dashboard:unanswered_question_list"
        )

        self.assertContains(
            response,
            f'href="{unanswered_question_url}"',
        )

        self.assertContains(
            response,
            "Open unanswered questions",
        )

    def test_dashboard_links_to_lead_queue(self):
        response = self.client.get(
            reverse("dashboard:home")
        )

        lead_url = reverse(
            "dashboard:lead_list"
        )

        self.assertContains(
            response,
            f'href="{lead_url}"',
        )

        self.assertContains(
            response,
            "Open customer leads",
        )

    def test_dashboard_links_to_handoff_queue(self):
        response = self.client.get(
            reverse("dashboard:home")
        )

        handoff_url = reverse(
            "dashboard:handoff_request_list"
        )

        self.assertContains(
            response,
            f'href="{handoff_url}"',
        )

        self.assertContains(
            response,
            "Open human-support requests",
        )

    def test_dashboard_links_open_successfully(self):
        page_names = (
            "dashboard:conversation_list",
            "dashboard:unanswered_question_list",
            "dashboard:lead_list",
            "dashboard:handoff_request_list",
        )

        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.client.get(
                    reverse(page_name)
                )

                self.assertEqual(
                    response.status_code,
                    200,
                )