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
    normalize_customer_knowledge_voice,
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

    def create_internal_product_document(self):
        document = KnowledgeDocument.objects.create(
            title="Internal Product Guide",
            version="1.0",
            file=(
                "knowledge_documents/"
                "internal-product-guide.pdf"
            ),
            status=KnowledgeDocument.Status.ACTIVE,
            is_indexed=True,
        )

        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            page_number=7,
            section_title="Product information",
            content=(
                "H&P Harbor & Pine Living Mock Knowledge "
                "Base v1.0 Fictional practice document - "
                "not a real company policy Page 7 SECTION 06 "
                "Product information. The structured product "
                "catalog contains Home Organization, Kitchen, "
                "Bath, Office, and Outdoor products."
            ),
        )

        return document

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

    def test_support_capabilities_handles_natural_question(
        self,
    ):
        _, assistant_message = process_customer_message(
            self.session,
            "hey, what can you help me with?",
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "support_capabilities",
        )

        self.assertIn(
            "product discovery",
            assistant_message.message,
        )

        self.assertNotEqual(
            assistant_message.message,
            SAFE_FALLBACK,
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

    def test_document_internal_header_is_not_exposed(
        self,
    ):
        document = KnowledgeDocument.objects.create(
            title="Internal Bamboo Guide",
            version="1.0",
            file=(
                "knowledge_documents/"
                "internal-bamboo-guide.pdf"
            ),
            status=KnowledgeDocument.Status.ACTIVE,
            is_indexed=True,
        )

        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            page_number=7,
            section_title="General bamboo care",
            content=(
                "H&P Harbor & Pine Living Mock Knowledge "
                "Base v1.0 Fictional practice document - "
                "not a real company policy Page 7 SECTION 06 "
                "General bamboo care. Wipe bamboo with a soft "
                "damp cloth and avoid abrasive cleaners."
            ),
        )

        _, assistant_message = process_customer_message(
            self.session,
            "What is the general bamboo care?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.DOCUMENT,
        )

        self.assertIn(
            "Wipe bamboo",
            assistant_message.message,
        )

        self.assertNotIn(
            "Mock Knowledge Base",
            assistant_message.message,
        )

        self.assertNotIn(
            "Fictional practice document",
            assistant_message.message,
        )

        self.assertNotIn(
            "not a real company policy",
            assistant_message.message,
        )

        self.assertEqual(
            assistant_message.source_references[0][
                "source_label"
            ],
            "Approved Harbor & Pine support guide",
        )

    def test_generic_product_help_does_not_route_to_safety_faq(
        self,
    ):
        FAQ.objects.create(
            faq_id="TEST-FAQ-SAFETY",
            category="Safety",
            question=(
                "What should I do if a product appears unsafe?"
            ),
            approved_answer=(
                "Stop using the product and request urgent "
                "human support."
            ),
            keywords=(
                "product safety urgent human support"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "can u guide me about a certain product?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.PRODUCT,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "generic_product_help",
        )

        self.assertIn(
            "product name",
            assistant_message.message,
        )

        self.assertNotIn(
            "Stop using the product",
            assistant_message.message,
        )

    def test_product_overview_does_not_expose_internal_document_text(
        self,
    ):
        self.create_internal_product_document()

        _, assistant_message = process_customer_message(
            self.session,
            (
                "what kind of products harbor and pine "
                "can offer?"
            ),
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "product_overview",
        )

        self.assertIn(
            "Home Organization",
            assistant_message.message,
        )

        self.assertIn(
            "Kitchen",
            assistant_message.message,
        )

        self.assertIn(
            "Bath",
            assistant_message.message,
        )

        self.assertIn(
            "Office",
            assistant_message.message,
        )

        self.assertIn(
            "Outdoor",
            assistant_message.message,
        )

        self.assertNotIn(
            "Fictional practice document",
            assistant_message.message,
        )

        self.assertEqual(
            assistant_message.source_references[0][
                "source_label"
            ],
            "Approved product catalog",
        )

    def test_what_do_you_guys_sell_uses_product_overview(
        self,
    ):
        self.create_internal_product_document()

        _, assistant_message = process_customer_message(
            self.session,
            "what do you guys sell?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "product_overview",
        )

        self.assertIn(
            "Home Organization",
            assistant_message.message,
        )

        self.assertIn(
            "Kitchen",
            assistant_message.message,
        )

        self.assertNotIn(
            "Mock Knowledge Base",
            assistant_message.message,
        )

    def test_office_browse_uses_products_before_document(
        self,
    ):
        self.create_internal_product_document()

        self.create_product(
            "HPL-OFF-001",
            "Cove Desk Shelf",
            category="Office",
        )

        self.create_product(
            "HPL-OFF-002",
            "Harbor Cable Box",
            category="Office",
        )

        self.create_product(
            "HPL-OFF-003",
            "Pine Ridge Document Tray",
            category="Office",
        )

        _, assistant_message = process_customer_message(
            self.session,
            "can u help me find something for my office?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.PRODUCT,
        )

        self.assertNotIn(
            "Mock Knowledge Base",
            assistant_message.message,
        )

        self.assertNotIn(
            "Fictional practice document",
            assistant_message.message,
        )

        self.assertTrue(
            (
                "Cove Desk Shelf"
                in assistant_message.message
            )
            or (
                assistant_message.decision_metadata[
                    "route"
                ]
                == "product_category_browse"
            )
        )

    def test_kitchen_browse_uses_product_catalog(
        self,
    ):
        self.create_product(
            "HPL-KIT-001",
            "Cove Utensil Caddy",
            category="Kitchen",
        )

        self.create_product(
            "HPL-KIT-002",
            "Harbor Glass Canister",
            category="Kitchen",
        )

        self.create_product(
            "HPL-KIT-003",
            "Pine Ridge Cutting Board",
            category="Kitchen",
        )

        _, assistant_message = process_customer_message(
            self.session,
            "do you have anything for the kitchen?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertNotEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )

        self.assertNotIn(
            "Mock Knowledge Base",
            assistant_message.message,
        )

    def test_specific_product_without_sku_requests_details(
        self,
    ):
        self.create_internal_product_document()

        _, assistant_message = process_customer_message(
            self.session,
            (
                "I need a specific product but I don't "
                "know the SKU"
            ),
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "generic_product_help",
        )

        self.assertIn(
            "product name",
            assistant_message.message,
        )

        self.assertNotIn(
            "Mock Knowledge Base",
            assistant_message.message,
        )

        self.assertNotIn(
            "Fictional practice document",
            assistant_message.message,
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
            keywords=(
                "return window 30 days return eligibility"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "how long after receiving the order "
                "i can return it?"
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
            "TEST-FAQ-RETURN",
        )

        self.assertIn(
            "30 calendar days",
            assistant_message.message,
        )

    def test_shipping_time_paraphrase_uses_shipping_faq(
        self,
    ):
        FAQ.objects.create(
            faq_id="TEST-FAQ-SHIPPING-DURATION",
            category="Shipping",
            question="How long does standard shipping take?",
            approved_answer=(
                "In-stock orders normally process in 1-2 "
                "business days, followed by an estimated "
                "3-7 business days in transit within the "
                "contiguous United States. Carrier estimates "
                "are not guarantees."
            ),
            keywords=(
                "how long standard shipping transit"
            ),
            is_enabled=True,
        )

        FAQ.objects.create(
            faq_id="TEST-FAQ-ORDER-EDIT",
            category="Orders",
            question="Can I add an item to my order?",
            approved_answer=(
                "The assistant cannot edit an order. "
                "It can create a handoff for review, but "
                "fulfillment status may prevent changes."
            ),
            keywords=(
                "add item edit order fulfillment order change"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "how long will it take for my order "
                "to get to me?"
            ),
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
            "TEST-FAQ-SHIPPING-DURATION",
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "targeted_shipping_time_faq",
        )

        self.assertIn(
            "1-2 business days",
            assistant_message.message,
        )

        self.assertIn(
            "3-7 business days",
            assistant_message.message,
        )

        self.assertNotIn(
            "cannot edit an order",
            assistant_message.message,
        )

    def test_used_item_return_question_uses_return_eligibility_faq(
        self,
    ):
        FAQ.objects.create(
            faq_id="TEST-FAQ-RETURN-ELIGIBILITY",
            category="Returns",
            question="What is the return window?",
            approved_answer=(
                "Most unused, unwashed, non-personalized "
                "items in original condition may be "
                "requested for return within 30 calendar "
                "days of recorded delivery, subject to "
                "review."
            ),
            keywords=(
                "return window 30 days return eligibility"
            ),
            is_enabled=True,
        )

        FAQ.objects.create(
            faq_id="TEST-FAQ-RETURN-SHIPPING",
            category="Returns",
            question="Who pays return shipping?",
            approved_answer=(
                "Customers normally pay return shipping for "
                "preference-based returns. Wrong-item or "
                "verified-damage claims require human review "
                "before a resolution is approved."
            ),
            keywords=(
                "return shipping return cost wrong item damage"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "can i return an item after i have used it?",
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
            "TEST-FAQ-RETURN-ELIGIBILITY",
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "targeted_return_eligibility_faq",
        )

        self.assertIn(
            "unused",
            assistant_message.message,
        )

        self.assertIn(
            "30 calendar days",
            assistant_message.message,
        )

        self.assertNotIn(
            "pay return shipping",
            assistant_message.message,
        )

    def test_safe_for_80_pounds_question_falls_back(self):
        _, assistant_message = process_customer_message(
            self.session,
            "is the Shoreline Desk Shelf safe for 80 pounds?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.UNSUPPORTED,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.FALLBACK,
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


class CustomerKnowledgeSanitizationTests(TestCase):
    def setUp(self):
        FAQ.objects.update(is_enabled=False)

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def test_trade_program_removes_mock_wording(self):
        FAQ.objects.create(
            faq_id="TEST-FAQ-TRADE",
            category="Trade",
            question="Can I join the trade program?",
            approved_answer=(
                "The mock trade program is reviewed case by case. "
                "The assistant can capture interest but cannot "
                "promise approval, terms, or discounts."
            ),
            keywords=(
                "trade program join trade approval terms discounts"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "can i join your trade program?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertIn(
            "trade program is reviewed case by case",
            assistant_message.message.lower(),
        )

        self.assertNotIn(
            "mock trade program",
            assistant_message.message.lower(),
        )

        self.assertNotIn(
            "mock",
            assistant_message.message.lower(),
        )


class CustomerVoiceNormalizationTests(TestCase):
    def setUp(self):
        FAQ.objects.update(is_enabled=False)

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def test_address_change_uses_first_person_voice(self):
        FAQ.objects.create(
            faq_id="TEST-FAQ-ADDRESS-VOICE",
            category="Shipping",
            question="Can I change my delivery address?",
            approved_answer=(
                "The assistant cannot change an address. "
                "If fulfillment has not started, a support "
                "specialist may review the request, but a "
                "change is not guaranteed."
            ),
            keywords=(
                "change delivery address shipping fulfillment"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "can you change the delivery address on my order for me?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "address_change_handoff",
        )

        self.assertIn(
            "I can't change a delivery address directly.",
            assistant_message.message,
        )

        self.assertNotIn(
            "The assistant",
            assistant_message.message,
        )

    def test_tracking_delay_uses_customer_facing_voice(self):
        FAQ.objects.create(
            faq_id="TEST-FAQ-TRACKING-VOICE",
            category="Shipping",
            question=(
                "My tracking has not updated. Is my package lost?"
            ),
            approved_answer=(
                "A first carrier scan can take up to 24 hours. "
                "The assistant should not declare a package lost; "
                "it can create a support request if the delay "
                "continues or the customer is concerned."
            ),
            keywords=(
                "tracking delayed scan package lost carrier"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "my tracking hasnt updated since yesterday, "
                "does that mean my package is lost?"
            ),
        )

        self.assertIn(
            "up to 24 hours",
            assistant_message.message,
        )

        self.assertIn(
            "your package is lost",
            assistant_message.message,
        )

        self.assertIn(
            "I can help you request support",
            assistant_message.message,
        )

        self.assertNotIn(
            "The assistant",
            assistant_message.message,
        )

        self.assertNotIn(
            "the customer",
            assistant_message.message.lower(),
        )

        self.assertNotIn(
            "it can create",
            assistant_message.message.lower(),
        )

    def test_refund_timing_uses_your_financial_institution(self):
        FAQ.objects.create(
            faq_id="TEST-FAQ-REFUND-VOICE",
            category="Returns",
            question="How long do refunds take?",
            approved_answer=(
                "After an approved return is received and "
                "inspected, a refund is normally initiated "
                "within 5-10 business days. The financial "
                "institution may need additional time."
            ),
            keywords=(
                "refund timing return financial institution"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "after you receive my return, "
                "how long should the refund take?"
            ),
        )

        self.assertIn(
            "5-10 business days",
            assistant_message.message,
        )

        self.assertIn(
            "Your financial institution may need additional time.",
            assistant_message.message,
        )

        self.assertNotIn(
            "The financial institution may need additional time.",
            assistant_message.message,
        )

    def test_discount_code_known_it_phrase_becomes_first_person(
        self,
    ):
        FAQ.objects.create(
            faq_id="TEST-FAQ-DISCOUNT-VOICE",
            category="Discounts",
            question="Can the bot create a discount code?",
            approved_answer=(
                "No. It can explain an approved active code but "
                "cannot create a code, override restrictions, or "
                "promise a manual discount."
            ),
            keywords=(
                "discount code promotion create override"
            ),
            is_enabled=True,
        )

        _, assistant_message = process_customer_message(
            self.session,
            "can you make a discount code for me?",
        )

        self.assertIn(
            "I can explain an approved active code",
            assistant_message.message,
        )

        self.assertIn(
            "I can't create a code",
            assistant_message.message,
        )

        self.assertNotIn(
            "It can explain",
            assistant_message.message,
        )

    def test_unrelated_it_pronouns_are_not_changed(self):
        original_text = (
            "It is made from bamboo. Keep it dry and do not "
            "place it near direct heat."
        )

        normalized_text = normalize_customer_knowledge_voice(
            original_text
        )

        self.assertEqual(
            normalized_text,
            original_text,
        )


class UnsupportedProductSpecificationTests(TestCase):
    def setUp(self):
        FAQ.objects.update(is_enabled=False)

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_product(self, sku, name, **overrides):
        values = {
            "category": "Office",
            "short_description": (
                "A practical office essential designed for "
                "calm, organized everyday spaces."
            ),
            "price_usd": Decimal("72.00"),
            "status": Product.Status.ACTIVE,
            "stock_band": Product.StockBand.HEALTHY,
            "material": "Bamboo",
            "color": "Slate",
            "dimensions": "9 x 12 x 4 in",
            "care_instructions": (
                "Wipe with a soft damp cloth; do not soak "
                "or use abrasives."
            ),
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

    def test_product_warranty_question_falls_back(self):
        self.create_product(
            "HPL-OFF-002",
            "Harbor Cable Box",
            material="Acacia wood",
            price_usd=Decimal("79.50"),
        )

        _, assistant_message = process_customer_message(
            self.session,
            "how long is the warranty on the Harbor Cable Box?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.UNSUPPORTED,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.FALLBACK,
        )

        self.assertEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "unsupported_product_specification",
        )

        self.assertEqual(
            self.session.outcome,
            ChatSession.Outcome.FALLBACK,
        )

        self.assertEqual(
            UnansweredQuestion.objects.count(),
            1,
        )

    def test_product_restock_timing_question_falls_back(self):
        self.create_product(
            "HPL-OFF-001",
            "Cove Desk Shelf",
        )

        _, assistant_message = process_customer_message(
            self.session,
            "when will the Cove Desk Shelf be restocked?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.UNSUPPORTED,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.FALLBACK,
        )

        self.assertEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "unsupported_product_specification",
        )

        self.assertEqual(
            self.session.outcome,
            ChatSession.Outcome.FALLBACK,
        )

        self.assertEqual(
            UnansweredQuestion.objects.count(),
            1,
        )

    def test_current_stock_question_is_not_blocked(self):
        product = self.create_product(
            "HPL-OFF-001",
            "Cove Desk Shelf",
        )

        _, assistant_message = process_customer_message(
            self.session,
            "is the Cove Desk Shelf in stock?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.PRODUCT,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.PRODUCT,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "product",
        )

        self.assertIn(
            product.product_name,
            assistant_message.message,
        )

        self.assertNotEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )

        self.assertNotEqual(
            assistant_message.decision_metadata["route"],
            "unsupported_product_specification",
        )


class CustomerRoutingSafetyV5Tests(TestCase):
    BASE_FAQ_IDS = tuple(
        f"FAQ-{number:03d}"
        for number in range(1, 21)
    )

    def setUp(self):
        FAQ.objects.filter(
            faq_id__in=self.BASE_FAQ_IDS,
        ).update(
            is_enabled=True,
        )

        KnowledgeDocument.objects.update(
            is_indexed=False,
        )

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def create_product(self, sku, name, **overrides):
        values = {
            "category": "Office",
            "short_description": (
                "A practical office essential for organized "
                "everyday spaces."
            ),
            "price_usd": Decimal("72.00"),
            "status": Product.Status.ACTIVE,
            "stock_band": Product.StockBand.HEALTHY,
            "material": "Bamboo",
            "color": "Natural",
            "dimensions": "24 x 8 x 4 in",
            "care_instructions": (
                "Wipe with a soft damp cloth; do not soak."
            ),
            "product_url": (
                "https://harborandpine.example/products/"
                f"{sku.lower()}"
            ),
            "last_updated": date(2026, 7, 1),
            "data_owner": "Catalog Manager",
        }

        values.update(overrides)

        product, _ = Product.objects.update_or_create(
            sku=sku,
            defaults={
                "product_name": name,
                **values,
            },
        )

        return product

    def test_all_twenty_enabled_base_faqs_resolve_to_their_own_records(
        self,
    ):
        faqs = list(
            FAQ.objects.filter(
                faq_id__in=self.BASE_FAQ_IDS,
                is_enabled=True,
            ).order_by("faq_id")
        )

        self.assertEqual(
            len(faqs),
            20,
        )

        self.assertEqual(
            tuple(faq.faq_id for faq in faqs),
            self.BASE_FAQ_IDS,
        )

        for faq in faqs:
            with self.subTest(faq_id=faq.faq_id):
                session = ChatSession.objects.create(
                    privacy_acknowledged=True,
                )

                _, assistant_message = process_customer_message(
                    session,
                    faq.question,
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
                    faq.faq_id,
                )

                self.assertEqual(
                    assistant_message.decision_metadata["route"],
                    "exact_enabled_faq",
                )

                self.assertNotEqual(
                    assistant_message.message,
                    SAFE_FALLBACK,
                )

    def test_support_hours_returns_compact_customer_answer(self):
        document = KnowledgeDocument.objects.create(
            title="Harbor & Pine Support Guide",
            version="1.0",
            file="knowledge_documents/support-hours.pdf",
            status=KnowledgeDocument.Status.ACTIVE,
            is_indexed=True,
        )

        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            page_number=3,
            section_title="Company and support profile",
            content=(
                "H&P Harbor & Pine Living Mock Knowledge Base "
                "v1.0 Fictional practice document - not a real "
                "company policy Page 3 SECTION 02 Company and "
                "support profile. Business hours Mon-Fri 9 AM-6 "
                "PM CT; Sat 10 AM-2 PM CT. Human response target "
                "within one business day. Brand promise calm, "
                "practical home essentials with dependable support."
            ),
        )

        _, assistant_message = process_customer_message(
            self.session,
            "What are your customer support hours?",
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "support_hours",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.DOCUMENT,
        )

        self.assertIn(
            "Mon-Fri 9 AM-6 PM CT",
            assistant_message.message,
        )

        self.assertIn(
            "Sat 10 AM-2 PM CT",
            assistant_message.message,
        )

        self.assertNotIn(
            "Brand promise",
            assistant_message.message,
        )

        self.assertLessEqual(
            len(assistant_message.message.split()),
            25,
        )

    def test_explicit_human_request_routes_before_support_faq(self):
        _, assistant_message = process_customer_message(
            self.session,
            "can you point me to human support?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "explicit_human_handoff",
        )

        self.assertIn(
            "human-support",
            assistant_message.decision_metadata["next_url"],
        )

        self.assertEqual(
            assistant_message.source_references,
            [],
        )

    def test_human_response_time_paraphrase_stays_informational(self):
        _, assistant_message = process_customer_message(
            self.session,
            "How long before a person replies to my support request?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "FAQ-018",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata["route"],
            "explicit_human_handoff",
        )

    def test_bulk_quote_routes_to_lead_before_exact_product_match(self):
        self.create_product(
            "HPL-OFF-001",
            "Cove Desk Shelf",
        )

        _, assistant_message = process_customer_message(
            self.session,
            (
                "I want to get a bulk quote for 60 Cove Desk "
                "Shelves for my business."
            ),
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.LEAD,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.LEAD,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "bulk_quote_lead",
        )

        self.assertEqual(
            assistant_message.decision_metadata["inquiry_type"],
            "bulk_order",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata["route"],
            "product",
        )

    def test_bulk_pricing_paraphrase_stays_informational(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Do you offer bulk pricing for larger orders?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "FAQ-019",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata["route"],
            "bulk_quote_lead",
        )

    def test_trade_program_information_stays_faq(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Is there a trade program I can join?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "FAQ-020",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata["route"],
            "trade_program_lead",
        )

    def test_trade_application_routes_to_lead_workflow(self):
        _, assistant_message = process_customer_message(
            self.session,
            "I want to apply for the trade program.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.LEAD,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "trade_program_lead",
        )

        self.assertEqual(
            assistant_message.decision_metadata["inquiry_type"],
            "trade_program",
        )

    def test_cancellation_information_paraphrase_stays_faq(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Is order cancellation possible?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "FAQ-009",
        )

        self.assertNotEqual(
            assistant_message.decision_metadata["route"],
            "order_cancellation_handoff",
        )

    def test_cancellation_action_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Please cancel my order.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "order_cancellation_handoff",
        )

    def test_order_edit_action_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Can you add an item to my order?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "order_edit_handoff",
        )

    def test_damage_event_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            "My item arrived damaged.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "damage_handoff",
        )

        self.assertEqual(
            assistant_message.decision_metadata["handoff_category"],
            "complaint",
        )

    def test_safety_event_routes_to_urgent_handoff_path(self):
        _, assistant_message = process_customer_message(
            self.session,
            "The product overheated and burned me.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "urgent_safety_handoff",
        )

        self.assertEqual(
            assistant_message.decision_metadata["handoff_category"],
            "safety_legal",
        )

        self.assertIn(
            "stop using",
            assistant_message.message.lower(),
        )

    def test_privacy_action_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Please delete my personal data.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "privacy_request_handoff",
        )

        self.assertEqual(
            assistant_message.decision_metadata["handoff_category"],
            "privacy_request",
        )

    def test_payment_dispute_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            "I was charged twice and need help.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "payment_refund_handoff",
        )

        self.assertEqual(
            assistant_message.decision_metadata["handoff_category"],
            "payment_refund",
        )

    def test_complaint_request_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            "I want to file a complaint.",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "complaint_handoff",
        )

    def test_policy_exception_request_routes_to_handoff(self):
        _, assistant_message = process_customer_message(
            self.session,
            (
                "Can you make an exception to the final-sale "
                "return policy?"
            ),
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.HANDOFF,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "policy_exception_handoff",
        )

    def test_weak_unrelated_faq_overlap_falls_back(self):
        _, assistant_message = process_customer_message(
            self.session,
            "Do you have a loyalty rewards points program?",
        )

        self.session.refresh_from_db()

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.UNSUPPORTED,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.FALLBACK,
        )

        self.assertEqual(
            assistant_message.message,
            SAFE_FALLBACK,
        )

        self.assertEqual(
            UnansweredQuestion.objects.filter(
                session=self.session,
            ).count(),
            1,
        )

    def test_exact_human_reply_faq_is_not_stolen_by_handoff_route(self):
        faq = FAQ.objects.get(
            faq_id="FAQ-018",
        )

        _, assistant_message = process_customer_message(
            self.session,
            faq.question,
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "FAQ-018",
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "exact_enabled_faq",
        )

    def test_exact_bulk_pricing_faq_is_not_stolen_by_lead_route(self):
        faq = FAQ.objects.get(
            faq_id="FAQ-019",
        )

        _, assistant_message = process_customer_message(
            self.session,
            faq.question,
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.FAQ,
        )

        self.assertEqual(
            assistant_message.source_references[0]["source_id"],
            "FAQ-019",
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "exact_enabled_faq",
        )

class ConversationalReliabilityV6RegressionTests(TestCase):
    BASE_FAQ_IDS = tuple(
        f"FAQ-{number:03d}"
        for number in range(1, 21)
    )

    def setUp(self):
        FAQ.objects.filter(
            faq_id__in=self.BASE_FAQ_IDS,
        ).update(
            is_enabled=True,
        )

        KnowledgeDocument.objects.update(
            is_indexed=False,
        )

        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def test_order_status_of_my_order_requires_secure_verification(
        self,
    ):
        _, assistant_message = process_customer_message(
            self.session,
            "what is the status of my order?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.ORDER,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.ORDER,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "order_verification_required",
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
            assistant_message.source_references,
            [],
        )

    def test_lookup_my_order_requires_secure_verification(
        self,
    ):
        _, assistant_message = process_customer_message(
            self.session,
            "can u lookup my order?",
        )

        self.assertEqual(
            assistant_message.detected_intent,
            ChatMessage.Intent.ORDER,
        )

        self.assertEqual(
            assistant_message.resolution_path,
            ChatSession.ResolutionPath.ORDER,
        )

        self.assertEqual(
            assistant_message.decision_metadata["route"],
            "order_verification_required",
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
            assistant_message.source_references,
            [],
        )

    def test_natural_order_lookup_paraphrases_require_verification(
        self,
    ):
        queries = (
            "can you check my order status?",
            "could u look up my order for me?",
            "i want to track my order",
            "where can i check the status of my order?",
            "order lookup please",
            "can u chek my order status?",
            "can u lokup my order?",
        )

        for query in queries:
            with self.subTest(query=query):
                session = ChatSession.objects.create(
                    privacy_acknowledged=True,
                )

                _, assistant_message = process_customer_message(
                    session,
                    query,
                )

                self.assertEqual(
                    assistant_message.detected_intent,
                    ChatMessage.Intent.ORDER,
                )

                self.assertEqual(
                    assistant_message.resolution_path,
                    ChatSession.ResolutionPath.ORDER,
                )

                self.assertEqual(
                    assistant_message.decision_metadata["route"],
                    "order_verification_required",
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
                    assistant_message.source_references,
                    [],
                )

    def test_order_policy_questions_are_not_stolen_by_lookup_route(
        self,
    ):
        queries = (
            "Is order cancellation possible?",
            "Can I add an item to my order?",
            "Can I change my delivery address?",
            "How long does standard shipping take?",
        )

        for query in queries:
            with self.subTest(query=query):
                session = ChatSession.objects.create(
                    privacy_acknowledged=True,
                )

                _, assistant_message = process_customer_message(
                    session,
                    query,
                )

                self.assertNotEqual(
                    assistant_message.detected_intent,
                    ChatMessage.Intent.ORDER,
                )

                self.assertNotEqual(
                    assistant_message.decision_metadata["route"],
                    "order_verification_required",
                )