from django.test import SimpleTestCase

from orders.forms import OrderLookupForm


class OrderLookupFormTests(SimpleTestCase):
    def test_valid_values_are_normalized(self):
        form = OrderLookupForm(
            data={
                "order_id": "  hpl10002  ",
                "billing_zip": " 60601 ",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["order_id"],
            "HPL10002",
        )
        self.assertEqual(
            form.cleaned_data["billing_zip"],
            "60601",
        )

    def test_invalid_order_id_is_rejected(self):
        form = OrderLookupForm(
            data={
                "order_id": "ORDER-10002",
                "billing_zip": "60601",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "order_id",
            form.errors,
        )

    def test_invalid_billing_zip_is_rejected(self):
        form = OrderLookupForm(
            data={
                "order_id": "HPL10002",
                "billing_zip": "6060",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "billing_zip",
            form.errors,
        )

    def test_leading_zero_zip_is_preserved(self):
        form = OrderLookupForm(
            data={
                "order_id": "HPL10006",
                "billing_zip": "02108",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["billing_zip"],
            "02108",
        )