from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class StaffAuthenticationTests(TestCase):
    def setUp(self):
        self.password = "StrongTestPassword123!"

        self.administrator = User.objects.create_superuser(
            username="test-administrator",
            password=self.password,
        )

        self.support_agent = User.objects.create_user(
            username="test-support-agent",
            password=self.password,
        )

        support_group = Group.objects.get(name="Support Agent")
        self.support_agent.groups.add(support_group)

        self.unassigned_user = User.objects.create_user(
            username="test-unassigned-user",
            password=self.password,
        )

    def test_login_page_loads(self):
        response = self.client.get(
            reverse("accounts:login")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Support team login")

    def test_portal_requires_login(self):
        response = self.client.get(
            reverse("accounts:portal")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )

    def test_administrator_can_access_portal(self):
        self.client.force_login(self.administrator)

        response = self.client.get(
            reverse("accounts:portal")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administrator")

    def test_support_agent_can_access_portal(self):
        self.client.force_login(self.support_agent)

        response = self.client.get(
            reverse("accounts:portal")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Support Agent")

    def test_unassigned_user_is_forbidden(self):
        self.client.force_login(self.unassigned_user)

        response = self.client.get(
            reverse("accounts:portal")
        )

        self.assertEqual(response.status_code, 403)

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.administrator)

        response = self.client.post(
            reverse("accounts:logout")
        )

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )