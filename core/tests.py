from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_homepage_loads_successfully(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")

    def test_homepage_contains_storefront_content(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(
            response,
            "Essentials designed for",
        )
        self.assertContains(
            response,
            "Home Organization",
        )
        self.assertContains(
            response,
            "Kitchen",
        )
        self.assertContains(
            response,
            "Bath",
        )
        self.assertContains(
            response,
            "Office",
        )
        self.assertContains(
            response,
            "Outdoor",
        )

    def test_homepage_contains_category_images(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(
            response,
            "images/categories/home-organization.png",
        )
        self.assertContains(
            response,
            "images/categories/kitchen.png",
        )
        self.assertContains(
            response,
            "images/categories/bath.png",
        )
        self.assertContains(
            response,
            "images/categories/office.png",
        )
        self.assertContains(
            response,
            "images/categories/outdoor.png",
        )

    def test_homepage_keeps_standalone_support_link(self):
        response = self.client.get(reverse("core:home"))

        self.assertContains(
            response,
            'href="/support/"',
        )