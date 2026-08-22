from datetime import date
from decimal import Decimal

from django.test import TestCase

from catalog.models import Product
from knowledge.models import (
    FAQ,
    KnowledgeDocument,
)
from support_chat.models import (
    ChatMessage,
    ChatSession,
    UnansweredQuestion,
)
from support_chat.orchestration import (
    SAFE_FALLBACK,
    process_customer_message,
)


class ConversationalReliabilityV6AdmissionTests(TestCase):
    def setUp(self):
        FAQ.objects.update(
            is_enabled=False,
        )

        KnowledgeDocument.objects.update(
            is_indexed=False,
        )

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_product(
        self,
        sku,
        name,
    ):
        return Product.objects.create(
            sku=sku,
            product_name=name,
            category="Office",
            short_description=(
                "A practical office essential for "
                "organized everyday spaces."
            ),
            price_usd=Decimal("79.50"),
            status=Product.Status.ACTIVE,
            stock_band=Product.StockBand.HEALTHY,
            material="Acacia wood",
            color="Natural",
            dimensions="12 x 8 x 4 in",
            care_instructions=(
                "Wipe with a soft damp cloth."
            ),
            product_url=(
                "https://harborandpine.example/"
                f"products/{sku.lower()}"
            ),
            last_updated=date(
                2026,
                7,
                1,
            ),
            data_owner="Catalog Manager",
        )

    def test_bulk_pricing_information_with_product_name_is_not_stolen_by_product_route(
        self,
    ):
        FAQ.objects.filter(
            faq_id="FAQ-019",
        ).update(
            is_enabled=True,
        )

        self.create_product(
            "HPL-OFF-002",
            "Harbor Cable Box",
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "Do you offer bulk pricing for "
                "10 Harbor Cable Boxes?"
            ),
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0][
                "source_id"
            ],
            "FAQ-019",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata[
                "route"
            ],
            "product",
        )

    def test_trade_information_with_product_name_is_not_stolen_by_product_route(
        self,
    ):
        FAQ.objects.filter(
            faq_id="FAQ-020",
        ).update(
            is_enabled=True,
        )

        self.create_product(
            "HPL-OFF-002",
            "Harbor Cable Box",
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "Is there a trade program for "
                "the Harbor Cable Box?"
            ),
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0][
                "source_id"
            ],
            "FAQ-020",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata[
                "route"
            ],
            "product",
        )

    def test_wrong_family_high_overlap_faq_is_rejected(
        self,
    ):
        FAQ.objects.create(
            faq_id="TEST-V6-WRONG-FAMILY",
            category="Shipping",
            question=(
                "How do shipping notices relate "
                "to privacy policy information?"
            ),
            approved_answer=(
                "Shipping notices are operational "
                "delivery messages and are not a "
                "customer privacy policy."
            ),
            keywords=(
                "privacy policy personal data "
                "shipping notices"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "What is your privacy policy?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.UNSUPPORTED,
        )

        self.assertEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.FALLBACK,
        )

        self.assertEqual(
            UnansweredQuestion.objects.filter(
                session=self.session,
            ).count(),
            1,
        )