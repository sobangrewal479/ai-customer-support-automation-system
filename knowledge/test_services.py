from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import KnowledgeChunk, KnowledgeDocument
from .services import (
    DocumentIndexingError,
    index_document,
    split_text_into_chunks,
)


class FakePageContents:
    def get_data(self):
        return b"small mock page content"


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_contents(self):
        return FakePageContents()

    def extract_text(self):
        return self.text


class KnowledgeIndexingServiceTests(TestCase):
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

    def create_document(
        self,
        status=KnowledgeDocument.Status.ACTIVE,
    ):
        uploaded_file = SimpleUploadedFile(
            "service-test.pdf",
            b"%PDF-1.4\n%%EOF\n",
            content_type="application/pdf",
        )

        return KnowledgeDocument.objects.create(
            title="Service Test Document",
            version="1.0",
            file=uploaded_file,
            status=status,
        )

    def test_text_is_split_with_overlap(self):
        text = " ".join(
            f"word-{number}"
            for number in range(20)
        )

        chunks = split_text_into_chunks(
            text,
            max_words=10,
            overlap_words=2,
        )

        self.assertEqual(len(chunks), 3)
        self.assertIn("word-8", chunks[1])

    @patch("knowledge.services.PdfReader")
    def test_active_document_is_indexed(self, mock_reader):
        document = self.create_document()

        mock_reader.return_value = SimpleNamespace(
            is_encrypted=False,
            pages=[
                FakePage(
                    "SECTION 01\nShipping\n"
                    "Approved shipping information."
                ),
                FakePage(
                    "SECTION 02\nReturns\n"
                    "Approved return information."
                ),
            ],
        )

        created_count = index_document(document)
        document.refresh_from_db()

        self.assertEqual(created_count, 2)
        self.assertEqual(document.chunks.count(), 2)
        self.assertTrue(document.is_indexed)

        first_chunk = document.chunks.first()

        self.assertEqual(first_chunk.page_number, 1)
        self.assertEqual(
            first_chunk.section_title,
            "Shipping",
        )

    def test_draft_document_is_rejected(self):
        document = self.create_document(
            status=KnowledgeDocument.Status.DRAFT
        )

        with self.assertRaises(DocumentIndexingError):
            index_document(document)

    @patch("knowledge.services.PdfReader")
    def test_encrypted_document_is_rejected(
        self,
        mock_reader,
    ):
        document = self.create_document()

        mock_reader.return_value = SimpleNamespace(
            is_encrypted=True,
            pages=[],
        )

        with self.assertRaises(DocumentIndexingError):
            index_document(document)

    @patch("knowledge.services.PdfReader")
    def test_document_without_text_is_rejected(
        self,
        mock_reader,
    ):
        document = self.create_document()

        mock_reader.return_value = SimpleNamespace(
            is_encrypted=False,
            pages=[
                FakePage(""),
            ],
        )

        with self.assertRaises(DocumentIndexingError):
            index_document(document)

        document.refresh_from_db()

        self.assertFalse(document.is_indexed)
        self.assertEqual(
            KnowledgeChunk.objects.count(),
            0,
        )