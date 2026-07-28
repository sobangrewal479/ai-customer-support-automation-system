from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class DashboardAuthenticationTests(TestCase):
    def setUp(self):
        self.dashboard_url = reverse(
            "dashboard:home"
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
            (
                "/staff/login/"
                "?next=/dashboard/"
            ),
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