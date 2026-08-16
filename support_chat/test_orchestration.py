from datetime import date
from decimal import Decimal

from django.test import TestCase

from catalog.models import Product
from knowledge.models import (
    FAQ,
    KnowledgeChunk,
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


class ChatOrchestrationTests(TestCase):
    def setUp(self):
        FAQ.objects.update(is_enabled=False)

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_product(self, sku, name, **overrides):
        values = {
            "category": Product.Category.HOME_ORGANIZATION,
            "short_description": "A practical home organizer.",
            "price_usd": Decimal("49.99"),
            "status": Product.Status.ACTIVE,
            "stock_band": Product.StockBand.HEALTHY,
            "material": "Bamboo",
            "color": "Natural",
            "dimensions": "18 x 8 x 6 in",
            "care_instructions": "Wipe with a damp cloth.",
            "product_url": (
                "https://harborandpine.example/products/"
                f"{sku.lower()}"
            ),
            "last_updated": date(2026, 7, 1),
            "data_owner": "Catalog Manager",
        }
        values.update(overrides)

        return Product.objects.create(
            sku=sku,
            product_name=name,
            **values,
        )

    def test_greeting_is_stored_and_resolved(self):
        customer_message, assistant_message = (
            process_customer_message(
                self.session,
                "Hello",
            )
        )

        self.session.refresh_from_db()

        self.assertEqual(
            customer_message.sender_type,
            ChatMessage.SenderType.CUSTOMER,
        )
        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.GREETING,
        )
        self.assertEqual(
            self.session.outcome,
            ChatSession.Outcome.RESOLVED,
        )
        self.assertEqual(
            self.session.messages.count(),
            2,
        )

    def test_faq_answer_uses_approved_source(self):
        FAQ.objects.create(
            faq_id="TEST-FAQ-001",
            category="Shipping",
            question="How long does shipping take?",
            approved_answer=(
                "Standard shipping normally takes 3-7 "
                "business days after processing."
            ),
            keywords="shipping time delivery",
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "How long does shipping take?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )
        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.FAQ,
        )
        self.assertEqual(
            assistant_message.source_references[0][
                "source_id"
            ],
            "TEST-FAQ-001",
        )

        def test_paraphrased_return_window_question_uses_return_faq(
        self,
    ):
            FAQ.objects.create(
            faq_id="TEST-FAQ-SHIPPING",
            category="Shipping",
            question="How long does standard shipping take?",
            approved_answer=(
                "In-stock orders normally process in 1-2 "
                "business days, followed by an estimated "
                "3-7 business days in transit."
            ),
            keywords="how long standard shipping transit",
            is_enabled=True,
        )

        FAQ.objects.create(
            faq_id="TEST-FAQ-RETURN",
            category="Returns",
            question="What is the return window?",
            approved_answer=(
                "Most unused items may be requested for "
                "return within 30 calendar days of delivery."
            ),
            keywords="return window 30 days return eligibility",
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "how long after receiving the order i can return it?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )
        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "TEST-FAQ-RETURN",
        )
        self.assertIn(
            "30 calendar days",
            assistant_message.message,
        )
    
    def test_document_answer_uses_indexed_active_chunk(self):
        document = KnowledgeDocument.objects.create(
            title="Test Support Guide",
            version="1.0",
            file="knowledge_documents/test-guide.pdf",
            status=KnowledgeDocument.Status.ACTIVE,
            is_indexed=True,
        )

        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            page_number=4,
            section_title="Tracking delays",
            content=(
                "A first carrier scan can take up to "
                "24 hours."
            ),
        )

        _, assistant_message = process_customer_message(
            self.session,
            "How long can a carrier scan take?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.DOCUMENT,
        )
        self.assertEqual(
            assistant_message.source_references[0][
                "source_type"
            ],
            "document",
        )
        self.assertEqual(
            assistant_message.source_references[0][
                "page_number"
            ],
            4,
        )

    def test_unique_product_answer_uses_product_record(self):
        product = self.create_product(
            "HPL-ORG-001",
            "Cove Entryway Tray",
        )

        _, assistant_message = process_customer_message(
            self.session,
            "Tell me about HPL-ORG-001",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )
        self.assertIn(
            product.product_name,
            assistant_message.message,
        )
        self.assertEqual(
            assistant_message.source_references[0][
                "source_id"
            ],
            product.sku,
        )

    def test_ambiguous_product_query_requests_sku(self):
        self.create_product(
            "HPL-ORG-001",
            "Cove Storage Basket",
        )
        self.create_product(
            "HPL-ORG-002",
            "Harbor Storage Basket",
        )

        _, assistant_message = process_customer_message(
            self.session,
            "storage basket",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )
        self.assertIn(
            "provide the SKU",
            assistant_message.message,
        )
        self.assertEqual(
            self.session.messages.count(),
            2,
        )

    def test_order_status_question_requests_secure_verification(
        self,
    ):
        _, assistant_message = process_customer_message(
            self.session,
            "Where is my order?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.ORDER,
        )
        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.ORDER,
        )
        self.assertIn(
            "exact order ID",
            assistant_message.message,
        )
        self.assertIn(
            "billing ZIP",
            assistant_message.message,
        )
        self.assertEqual(
            self.session.outcome,
            ChatSession.Outcome.IN_PROGRESS,
        )
        self.assertEqual(
            UnansweredQuestion.objects.count(),
            0,
        )

    def test_load_rating_question_falls_back_even_if_document_mentions_it(
        self,
    ):
        document = KnowledgeDocument.objects.create(
            title="Product Support Guide",
            version="1.0",
            file=(
                "knowledge_documents/"
                "product-support-guide.pdf"
            ),
            status=KnowledgeDocument.Status.ACTIVE,
            is_indexed=True,
        )

        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            page_number=7,
            section_title="Unsupported specifications",
            content=(
                "If asked whether a shelf safely holds "
                "80 pounds and no approved load rating "
                "exists, do not estimate."
            ),
        )

        _, assistant_message = process_customer_message(
            self.session,
            "Does this shelf safely hold 80 pounds?",
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
            self.session.outcome,
            ChatSession.Outcome.FALLBACK,
        )
        self.assertEqual(
            UnansweredQuestion.objects.count(),
            1,
        )

    def test_unknown_question_creates_fallback_record(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Does this shelf safely hold 80 pounds?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )
        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.UNSUPPORTED,
        )
        self.assertEqual(
            self.session.outcome,
            ChatSession.Outcome.FALLBACK,
        )
        self.assertEqual(
            UnansweredQuestion.objects.count(),
            1,
        )

    def test_repeated_unknown_question_increments_count(self):
        question = "Does this shelf safely hold 80 pounds?"

        process_customer_message(
            self.session,
            question,
        )

        second_session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

        process_customer_message(
            second_session,
            question,
        )

        unanswered = UnansweredQuestion.objects.get()

        self.assertEqual(
            unanswered.occurrence_count,
            2,
        )
        self.assertEqual(
            unanswered.session,
            second_session,
        )