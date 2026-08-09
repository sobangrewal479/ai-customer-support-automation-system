from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from orders.models import MockOrder, OrderLookupAttempt
from support_chat.models import ChatSession


User = get_user_model()


class DashboardOrderActivityTests(TestCase):
    def setUp(self):
        self.order_activity_url = reverse(
            "dashboard:order_activity_list"
        )

        self.staff_user = User.objects.create_user(
            username="order-reviewer",
            email="order-reviewer@example.com",
            password="OrderReviewerPass123!",
            is_staff=True,
        )

    def create_mock_order(self):
        return MockOrder.objects.create(
            order_id="HPL10002",
            billing_zip="60601",
            customer_name="Mia Brooks",
            customer_email="mia.brooks@example.com",
            order_date=date(2026, 7, 1),
            status=MockOrder.Status.SHIPPED,
            carrier="FedEx",
            tracking_reference="MOCK-FedEx-900002",
            eta_window="2026-07-22",
            items="HPL-ORG-005; HPL-ORG-014",
            order_total_usd=Decimal("83.99"),
            last_updated=date(2026, 7, 14),
        )

    def test_order_activity_uses_expected_url(self):
        self.assertEqual(
            self.order_activity_url,
            "/dashboard/order-activity/",
        )

    def test_logged_out_user_cannot_access_order_activity(
        self,
    ):
        response = self.client.get(
            self.order_activity_url
        )

        self.assertRedirects(
            response,
            (
                "/staff/login/"
                "?next=/dashboard/order-activity/"
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
            self.order_activity_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/order_activity_list.html",
        )

        self.assertContains(
            response,
            "Order activity",
        )

        self.assertContains(
            response,
            "Order lookup activity",
        )

        self.assertContains(
            response,
            "order-reviewer",
        )

    def test_empty_page_displays_expected_message(
        self,
    ):
        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.order_activity_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "order_lookup_attempts"
            ].count(),
            0,
        )

        self.assertContains(
            response,
            "No order lookup activity found",
        )

    def test_verified_attempt_displays_only_approved_data(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        order = self.create_mock_order()

        attempt = OrderLookupAttempt.objects.create(
            session=session,
            provided_order_id=order.order_id,
            matched_order=order,
            outcome=OrderLookupAttempt.Outcome.VERIFIED,
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
            self.order_activity_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "order_lookup_attempts"
            ].count(),
            1,
        )

        self.assertEqual(
            response.context[
                "order_lookup_attempts"
            ].first(),
            attempt,
        )

        approved_content = (
            "Verified",
            "HPL10002",
            "Shipped",
            "FedEx",
            "MOCK-FedEx-900002",
            "2026-07-22",
        )

        for content in approved_content:
            with self.subTest(content=content):
                self.assertContains(
                    response,
                    content,
                )

        private_content = (
            "60601",
            "Mia Brooks",
            "mia.brooks@example.com",
            "HPL-ORG-005; HPL-ORG-014",
            "83.99",
        )

        for content in private_content:
            with self.subTest(content=content):
                self.assertNotContains(
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

    def test_failed_and_blocked_attempts_reveal_no_order(
        self,
    ):
        OrderLookupAttempt.objects.create(
            provided_order_id="HPL99998",
            outcome=(
                OrderLookupAttempt.Outcome.ZIP_MISMATCH
            ),
        )

        OrderLookupAttempt.objects.create(
            provided_order_id="HPL99999",
            outcome=OrderLookupAttempt.Outcome.BLOCKED,
        )

        self.client.force_login(
            self.staff_user
        )

        response = self.client.get(
            self.order_activity_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            "Billing ZIP mismatch",
        )

        self.assertContains(
            response,
            "Blocked after repeated failures",
        )

        self.assertContains(
            response,
            "No verified order linked",
            count=2,
        )

        self.assertContains(
            response,
            "Further verification requires",
        )

        self.assertContains(
            response,
            "human-support review.",
        )