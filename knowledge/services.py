from django.db import transaction
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .models import KnowledgeChunk, KnowledgeDocument


DEFAULT_CHUNK_WORDS = 180
DEFAULT_OVERLAP_WORDS = 30
MAX_PAGE_STREAM_BYTES = 5 * 1024 * 1024


class DocumentIndexingError(Exception):
    """Raised when a knowledge document cannot be indexed."""


def normalize_extracted_text(text):
    cleaned_lines = []

    for line in text.splitlines():
        cleaned_line = " ".join(line.split())

        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def split_text_into_chunks(
    text,
    max_words=DEFAULT_CHUNK_WORDS,
    overlap_words=DEFAULT_OVERLAP_WORDS,
):
    if max_words <= overlap_words:
        raise ValueError(
            "max_words must be greater than overlap_words."
        )

    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))

        if end >= len(words):
            break

        start = end - overlap_words

    return chunks


def find_section_title(page_text, page_number):
    lines = [
        line.strip()
        for line in page_text.splitlines()
        if line.strip()
    ]

    for index, line in enumerate(lines):
        if line.upper().startswith("SECTION "):
            if index + 1 < len(lines):
                return lines[index + 1][:255]

            return line[:255]

    return f"Document page {page_number}"


def extract_page_text(page):
    page_contents = page.get_contents()

    if page_contents is not None:
        content_size = len(page_contents.get_data())

        if content_size > MAX_PAGE_STREAM_BYTES:
            raise DocumentIndexingError(
                "A PDF page is too complex to process safely."
            )

    extracted_text = page.extract_text() or ""

    return normalize_extracted_text(extracted_text)


def index_document(document):
    if document.status != KnowledgeDocument.Status.ACTIVE:
        raise DocumentIndexingError(
            "Only active knowledge documents can be indexed."
        )

    try:
        with document.file.open("rb") as document_file:
            reader = PdfReader(
                document_file,
                strict=False,
            )

            if reader.is_encrypted:
                raise DocumentIndexingError(
                    "Encrypted PDFs cannot be indexed."
                )

            pending_chunks = []
            chunk_index = 0

            for page_number, page in enumerate(
                reader.pages,
                start=1,
            ):
                page_text = extract_page_text(page)

                if not page_text:
                    continue

                section_title = find_section_title(
                    page_text,
                    page_number,
                )

                page_chunks = split_text_into_chunks(
                    page_text
                )

                for chunk_content in page_chunks:
                    pending_chunks.append(
                        KnowledgeChunk(
                            document=document,
                            chunk_index=chunk_index,
                            page_number=page_number,
                            section_title=section_title,
                            content=chunk_content,
                        )
                    )
                    chunk_index += 1

    except DocumentIndexingError:
        raise
    except (
        FileNotFoundError,
        OSError,
        PdfReadError,
        ValueError,
    ) as error:
        raise DocumentIndexingError(
            "The PDF could not be read or indexed."
        ) from error

    if not pending_chunks:
        raise DocumentIndexingError(
            "No searchable text was found in the PDF."
        )

    with transaction.atomic():
        document.chunks.all().delete()

        KnowledgeChunk.objects.bulk_create(
            pending_chunks
        )

        document.is_indexed = True
        document.save(
            update_fields=[
                "is_indexed",
                "updated_at",
            ]
        )

    return len(pending_chunks)