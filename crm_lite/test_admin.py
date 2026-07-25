from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from crm_lite.admin import (
    HandoffRequestAdmin,
    LeadAdmin,
)
from crm_lite.models import HandoffRequest, Lead


User = get_user_model()


class CrmLiteAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="crm-admin",
            email="crm-admin@example.com",
            password="AdminPass123!",
        )

    def test_models_use_expected_admin_classes(self):
        self.assertIsInstance(
            admin.site._registry[Lead],
            LeadAdmin,
        )

        self.assertIsInstance(
            admin.site._registry[HandoffRequest],
            HandoffRequestAdmin,
        )

    def test_lead_admin_configuration(self):
        lead_admin = admin.site._registry[Lead]

        self.assertIn(
            "inquiry_type",
            lead_admin.list_filter,
        )
        self.assertIn(
            "status",
            lead_admin.list_filter,
        )
        self.assertIn(
            "email",
            lead_admin.search_fields,
        )
        self.assertIn(
            "source_session",
            lead_admin.raw_id_fields,
        )

    def test_handoff_admin_configuration(self):
        handoff_admin = admin.site._registry[
            HandoffRequest
        ]

        self.assertIn(
            "priority",
            handoff_admin.list_filter,
        )
        self.assertIn(
            "status",
            handoff_admin.list_filter,
        )
        self.assertIn(
            "contact_email",
            handoff_admin.search_fields,
        )
        self.assertIn(
            "session",
            handoff_admin.raw_id_fields,
        )

    def test_superuser_can_access_lead_admin_page(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("admin:crm_lite_lead_changelist")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_superuser_can_access_handoff_admin_page(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                "admin:crm_lite_handoffrequest_changelist"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )