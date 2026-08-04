from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from crm_lite.models import HandoffRequest
from dashboard.services import (
    get_handoff_request_records,
)
from support_chat.models import ChatSession


class DashboardHandoffServiceTests(TestCase):
    def test_empty_database_returns_no_handoff_requests(
        self,
    ):
        handoff_requests = (
            get_handoff_request_records()
        )

        self.assertEqual(
            handoff_requests.count(),
            0,
        )

    def test_service_returns_requests_in_model_order(
        self,
    ):
        session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        first_request = HandoffRequest.objects.create(
            session=session,
            contact_name="Jordan Lee",
            contact_email="jordan@example.com",
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

        second_request = HandoffRequest.objects.create(
            session=session,
            contact_name="Alex Morgan",
            contact_email="alex@example.com",
            category=HandoffRequest.Category.COMPLAINT,
            priority=HandoffRequest.Priority.HIGH,
            reason="I need help resolving a complaint.",
            assigned_owner="Priority Support Queue",
            sla_due_at=(
                timezone.now()
                + timedelta(hours=4)
            ),
        )

        handoff_requests = (
            get_handoff_request_records()
        )

        self.assertEqual(
            handoff_requests.count(),
            2,
        )

        self.assertEqual(
            handoff_requests.first(),
            second_request,
        )

        self.assertIn(
            first_request,
            handoff_requests,
        )

        self.assertEqual(
            handoff_requests.first().session,
            session,
        )