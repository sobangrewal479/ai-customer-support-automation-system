from django import forms

from crm_lite.models import HandoffRequest, Lead


class LeadCaptureForm(forms.ModelForm):
    consent_to_contact = forms.BooleanField(
        required=True,
        label=(
            "I agree that Harbor & Pine may contact me "
            "about this inquiry."
        ),
    )

    class Meta:
        model = Lead

        fields = (
            "name",
            "email",
            "phone",
            "company",
            "inquiry_type",
            "product_sku",
            "message",
            "consent_to_contact",
        )

        labels = {
            "name": "Name",
            "email": "Email address",
            "phone": "Phone number",
            "company": "Company",
            "inquiry_type": "Inquiry type",
            "product_sku": "Product SKU",
            "message": "How can we help?",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Your full name",
                    "autocomplete": "name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "Optional phone number",
                    "autocomplete": "tel",
                }
            ),
            "company": forms.TextInput(
                attrs={
                    "placeholder": "Optional company name",
                    "autocomplete": "organization",
                }
            ),
            "product_sku": forms.TextInput(
                attrs={
                    "placeholder": (
                        "Optional, for example HPL-ORG-001"
                    ),
                    "autocomplete": "off",
                    "autocapitalize": "characters",
                    "spellcheck": "false",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "placeholder": (
                        "Describe the product, bulk-order, "
                        "trade, or partnership inquiry."
                    ),
                    "rows": 6,
                }
            ),
        }

    def clean_name(self):
        return " ".join(
            (
                self.cleaned_data.get("name")
                or ""
            ).split()
        )

    def clean_email(self):
        return (
            self.cleaned_data.get("email")
            or ""
        ).strip().lower()

    def clean_phone(self):
        return (
            self.cleaned_data.get("phone")
            or ""
        ).strip()

    def clean_company(self):
        return " ".join(
            (
                self.cleaned_data.get("company")
                or ""
            ).split()
        )

    def clean_product_sku(self):
        return (
            self.cleaned_data.get("product_sku")
            or ""
        ).strip().upper()

    def clean_message(self):
        return (
            self.cleaned_data.get("message")
            or ""
        ).strip()


class HandoffRequestForm(forms.ModelForm):
    class Meta:
        model = HandoffRequest

        fields = (
            "contact_name",
            "contact_email",
            "contact_phone",
            "category",
            "reason",
        )

        labels = {
            "contact_name": "Name",
            "contact_email": "Email address",
            "contact_phone": "Phone number",
            "category": "Support request type",
            "reason": "What do you need help with?",
        }

        widgets = {
            "contact_name": forms.TextInput(
                attrs={
                    "placeholder": "Your name",
                    "autocomplete": "name",
                }
            ),
            "contact_email": forms.EmailInput(
                attrs={
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                }
            ),
            "contact_phone": forms.TextInput(
                attrs={
                    "placeholder": "Phone number",
                    "autocomplete": "tel",
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "placeholder": (
                        "Explain what happened and what "
                        "you need from the support team."
                    ),
                    "rows": 6,
                }
            ),
        }

    def clean_contact_name(self):
        return " ".join(
            (
                self.cleaned_data.get("contact_name")
                or ""
            ).split()
        )

    def clean_contact_email(self):
        return (
            self.cleaned_data.get("contact_email")
            or ""
        ).strip().lower()

    def clean_contact_phone(self):
        return (
            self.cleaned_data.get("contact_phone")
            or ""
        ).strip()

    def clean_reason(self):
        return (
            self.cleaned_data.get("reason")
            or ""
        ).strip()