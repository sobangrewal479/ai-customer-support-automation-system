from django import forms

from orders.models import (
    BILLING_ZIP_PATTERN,
    ORDER_ID_PATTERN,
)


class OrderLookupForm(forms.Form):
    order_id = forms.CharField(
        label="Order ID",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Example: HPL10002",
                "autocomplete": "off",
                "autocapitalize": "characters",
                "spellcheck": "false",
            }
        ),
    )

    billing_zip = forms.CharField(
        label="Billing ZIP",
        max_length=5,
        widget=forms.TextInput(
            attrs={
                "placeholder": "5-digit billing ZIP",
                "inputmode": "numeric",
                "autocomplete": "postal-code",
                "spellcheck": "false",
            }
        ),
    )

    def clean_order_id(self):
        order_id = (
            self.cleaned_data.get("order_id") or ""
        ).strip().upper()

        if not ORDER_ID_PATTERN.fullmatch(order_id):
            raise forms.ValidationError(
                "Enter an order ID in the format HPL followed "
                "by exactly five digits."
            )

        return order_id

    def clean_billing_zip(self):
        billing_zip = (
            self.cleaned_data.get("billing_zip") or ""
        ).strip()

        if not BILLING_ZIP_PATTERN.fullmatch(
            billing_zip
        ):
            raise forms.ValidationError(
                "Enter the five-digit billing ZIP associated "
                "with the order."
            )

        return billing_zip