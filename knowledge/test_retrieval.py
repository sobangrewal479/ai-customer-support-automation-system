from django.test import TestCase

from .models import FAQ, KnowledgeChunk, KnowledgeDocument
from .retrieval import (
    retrieve_knowledge,
    search_document_chunks,
    search_faqs,
)


class KnowledgeRetrievalTests(TestCase):
    def setUp(self):
        FAQ.objects.update(is_enabled=False)

        self.shipping_faq = FAQ.objects.create(
            faq_id="FAQ-SEARCH-001",
            category="Shipping",
            question="How long does standard shipping take?",
            approved_answer=(
                "Standard shipping normally takes "
                "3-7 business days after processing."
            ),
            keywords=(
                "shipping, delivery, transit, timeframe"
            ),
            is_enabled=True,
        )

        self.disabled_faq = FAQ.objects.create(
            faq_id="FAQ-SEARCH-002",
            category="Testing",
            question="What is the mooncrate policy?",
            approved_answer=(
                "This disabled answer must not be returned."
            ),
            keywords="mooncrate",
            is_enabled=False,
        )

        self.document = KnowledgeDocument.objects.create(
            title="Test Knowledge Base",
            version="1.0",
            file="knowledge_documents/test.pdf",
            status=KnowledgeDocument.Status.ACTIVE,
            is_indexed=True,
        )

        self.chunk = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=0,
            page_number=4,
            section_title="Privacy Requests",
            content=(
                "Personal data deletion requests require "
                "an authorized privacy handoff."
            ),
        )

    def test_relevant_enabled_faq_is_returned(self):
        results = search_faqs(
            "How long does shipping take?"
        )

        self.assertTrue(results)
        self.assertEqual(
            results[0].source_id,
            "FAQ-SEARCH-001",
        )
        self.assertEqual(
            results[0].source_type,
            "faq",
        )

    def test_disabled_faq_is_not_returned(self):
        results = search_faqs(
            "mooncrate policy"
        )

        self.assertEqual(results, [])

    def test_active_indexed_document_is_returned(self):
        results = search_document_chunks(
            "delete personal data privacy"
        )

        self.assertTrue(results)
        self.assertEqual(
            results[0].source_type,
            "document",
        )
        self.assertEqual(
            results[0].page_number,
            4,
        )
        self.assertIn(
            "Privacy Requests",
            results[0].source_label,
        )

    def test_unindexed_document_is_excluded(self):
        self.document.is_indexed = False
        self.document.save(
            update_fields=["is_indexed"]
        )

        results = search_document_chunks(
            "delete personal data privacy"
        )

        self.assertEqual(results, [])

    def test_combined_retrieval_contains_sources(self):
        results = retrieve_knowledge(
            "shipping and privacy"
        )

        source_types = {
            result.source_type
            for result in results
        }

        self.assertIn("faq", source_types)
        self.assertIn("document", source_types)

    def test_empty_query_returns_no_results(self):
        self.assertEqual(search_faqs(""), [])
        self.assertEqual(
            search_document_chunks(""),
            [],
        )
        self.assertEqual(
            retrieve_knowledge(""),
            [],
        )