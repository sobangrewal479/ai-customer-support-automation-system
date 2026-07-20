import hashlib
from datetime import date
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    MAX_DOCUMENT_SIZE,
    FAQ,
    KnowledgeChunk,
    KnowledgeDocument,
    validate_document_size,
)


class KnowledgeModelTests(TestCase):
    def test_faq_can_be_created(self):
        faq = FAQ.objects.create(
            faq_id="FAQ-TEST-001",
            category="Shipping",
            question="How long does shipping take?",
            approved_answer="Shipping normally takes several days.",
            is_enabled=True,
        )

        self.assertEqual(
            str(faq),
            "FAQ-TEST-001 - How long does shipping take?",
        )
        self.assertTrue(faq.is_enabled)

    def test_faq_id_must_be_unique(self):
        FAQ.objects.create(
            faq_id="FAQ-TEST-002",
            category="Returns",
            question="First question",
            approved_answer="First answer",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FAQ.objects.create(
                    faq_id="FAQ-TEST-002",
                    category="Returns",
                    question="Second question",
                    approved_answer="Second answer",
                )

    def test_faq_review_date_cannot_be_too_early(self):
        faq = FAQ(
            faq_id="FAQ-TEST-003",
            category="Returns",
            question="What is the return window?",
            approved_answer="The approved return guidance.",
            effective_date=date(2026, 7, 1),
            review_date=date(2026, 6, 1),
        )

        with self.assertRaises(ValidationError):
            faq.full_clean()

    def test_document_title_and_version_are_unique(self):
        KnowledgeDocument.objects.create(
            title="Customer Support Knowledge Base",
            version="1.0",
            file="knowledge_documents/test.pdf",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                KnowledgeDocument.objects.create(
                    title="Customer Support Knowledge Base",
                    version="1.0",
                    file="knowledge_documents/test-copy.pdf",
                )

    def test_non_pdf_extension_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "knowledge.txt",
            b"Not a PDF",
            content_type="text/plain",
        )

        document = KnowledgeDocument(
            title="Invalid Document",
            version="1.0",
            file=uploaded_file,
        )

        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_oversized_document_is_rejected(self):
        oversized_file = SimpleNamespace(
            size=MAX_DOCUMENT_SIZE + 1
        )

        with self.assertRaises(ValidationError):
            validate_document_size(oversized_file)

    def test_document_deletion_removes_chunks(self):
        document = KnowledgeDocument.objects.create(
            title="Chunk Test Document",
            version="1.0",
            file="knowledge_documents/chunk-test.pdf",
        )

        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            page_number=1,
            section_title="Test Section",
            content="Approved test content.",
        )

        document.delete()

        self.assertEqual(
            KnowledgeChunk.objects.count(),
            0,
        )


class KnowledgeAdminUploadTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.temporary_media = TemporaryDirectory()
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.temporary_media.name
        )
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        cls.temporary_media.cleanup()

        super().tearDownClass()

    def setUp(self):
        self.administrator = User.objects.create_superuser(
            username="knowledge-test-admin",
            password="StrongTestPassword123!",
        )
        self.client.force_login(self.administrator)
        self.add_url = reverse(
            "admin:knowledge_knowledgedocument_add"
        )

    def test_fake_pdf_content_is_rejected(self):
        fake_pdf = SimpleUploadedFile(
            "fake-document.pdf",
            b"This is not actually a PDF.",
            content_type="application/pdf",
        )

        response = self.client.post(
            self.add_url,
            {
                "title": "Fake PDF",
                "version": "1.0",
                "file": fake_pdf,
                "status": KnowledgeDocument.Status.ACTIVE,
                "owner": "Support Operations Manager",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "The uploaded file is not a valid PDF.",
        )
        self.assertEqual(
            KnowledgeDocument.objects.count(),
            0,
        )

    def test_valid_pdf_upload_generates_checksum(self):
        pdf_content = (
            b"%PDF-1.4\n"
            b"% Test knowledge document\n"
            b"%%EOF\n"
        )
        valid_pdf = SimpleUploadedFile(
            "valid-document.pdf",
            pdf_content,
            content_type="application/pdf",
        )

        response = self.client.post(
            self.add_url,
            {
                "title": "Valid Knowledge Document",
                "version": "1.0",
                "file": valid_pdf,
                "effective_date": "2026-07-01",
                "review_date": "2026-10-01",
                "status": KnowledgeDocument.Status.ACTIVE,
                "owner": "Support Operations Manager",
            },
        )

        self.assertEqual(response.status_code, 302)

        document = KnowledgeDocument.objects.get(
            title="Valid Knowledge Document"
        )

        self.assertEqual(
            document.checksum,
            hashlib.sha256(pdf_content).hexdigest(),
        )
        self.assertFalse(document.is_indexed)