from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def validate_document_size(uploaded_file):
    if uploaded_file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(
            "The PDF must not be larger than 10 MB."
        )


class FAQ(models.Model):
    faq_id = models.CharField(
        max_length=20,
        unique=True,
    )
    category = models.CharField(
        max_length=100,
        db_index=True,
    )
    question = models.CharField(
        max_length=500,
    )
    approved_answer = models.TextField()
    keywords = models.TextField(
        blank=True,
        help_text="Separate search keywords using commas.",
    )
    is_enabled = models.BooleanField(
        default=True,
        db_index=True,
    )
    effective_date = models.DateField(
        blank=True,
        null=True,
    )
    review_date = models.DateField(
        blank=True,
        null=True,
    )
    owner = models.CharField(
        max_length=150,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["category", "faq_id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        indexes = [
            models.Index(
                fields=["is_enabled", "category"],
                name="faq_enabled_category_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.effective_date
            and self.review_date
            and self.review_date < self.effective_date
        ):
            raise ValidationError(
                {
                    "review_date": (
                        "The review date cannot be earlier "
                        "than the effective date."
                    )
                }
            )

    def __str__(self):
        return f"{self.faq_id} - {self.question}"


class KnowledgeDocument(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(
        max_length=255,
    )
    version = models.CharField(
        max_length=50,
    )
    file = models.FileField(
        upload_to="knowledge_documents/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf"]
            ),
            validate_document_size,
        ],
    )
    effective_date = models.DateField(
        blank=True,
        null=True,
    )
    review_date = models.DateField(
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    owner = models.CharField(
        max_length=150,
        blank=True,
    )
    checksum = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
    )
    is_indexed = models.BooleanField(
        default=False,
        editable=False,
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["title", "version"],
                name="unique_document_title_version",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.effective_date
            and self.review_date
            and self.review_date < self.effective_date
        ):
            raise ValidationError(
                {
                    "review_date": (
                        "The review date cannot be earlier "
                        "than the effective date."
                    )
                }
            )

        if self.file:
            suffix = Path(self.file.name).suffix.lower()

            if suffix != ".pdf":
                raise ValidationError(
                    {
                        "file": (
                            "Only PDF knowledge documents "
                            "are allowed."
                        )
                    }
                )

    def __str__(self):
        return f"{self.title} - version {self.version}"


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(
        blank=True,
        null=True,
    )
    section_title = models.CharField(
        max_length=255,
        blank=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk_index",
            ),
        ]

    def __str__(self):
        return (
            f"{self.document.title} - "
            f"chunk {self.chunk_index}"
        )