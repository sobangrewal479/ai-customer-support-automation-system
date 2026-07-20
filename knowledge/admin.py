import hashlib

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import FAQ, KnowledgeChunk, KnowledgeDocument
from .services import (
    DocumentIndexingError,
    index_document,
)


class KnowledgeDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = KnowledgeDocument
        fields = "__all__"

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            return uploaded_file

        original_position = uploaded_file.tell()
        header = uploaded_file.read(5)
        uploaded_file.seek(original_position)

        if header != b"%PDF-":
            raise ValidationError(
                "The uploaded file is not a valid PDF."
            )

        return uploaded_file


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        "faq_id",
        "category",
        "short_question",
        "is_enabled",
        "review_date",
        "updated_at",
    )
    list_filter = (
        "is_enabled",
        "category",
        "review_date",
    )
    search_fields = (
        "faq_id",
        "question",
        "approved_answer",
        "keywords",
    )
    list_editable = (
        "is_enabled",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "category",
        "faq_id",
    )

    @admin.display(description="Question")
    def short_question(self, obj):
        if len(obj.question) <= 70:
            return obj.question

        return f"{obj.question[:67]}..."


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    form = KnowledgeDocumentAdminForm
    actions = (
        "index_selected_documents",
    )

    list_display = (
        "title",
        "version",
        "status",
        "is_indexed",
        "effective_date",
        "review_date",
        "uploaded_at",
    )
    list_filter = (
        "status",
        "is_indexed",
        "effective_date",
        "review_date",
    )
    search_fields = (
        "title",
        "version",
        "owner",
        "checksum",
    )
    readonly_fields = (
        "checksum",
        "is_indexed",
        "uploaded_at",
        "updated_at",
    )
    ordering = (
        "-uploaded_at",
    )

    @admin.action(
        description="Index or re-index selected active PDFs"
    )
    def index_selected_documents(
        self,
        request,
        queryset,
    ):
        success_count = 0
        failed_documents = []

        for document in queryset:
            try:
                index_document(document)
                success_count += 1
            except DocumentIndexingError as error:
                failed_documents.append(
                    f"{document.title}: {error}"
                )

        if success_count:
            self.message_user(
                request,
                (
                    f"{success_count} knowledge document(s) "
                    "indexed successfully."
                ),
                level=messages.SUCCESS,
            )

        if failed_documents:
            self.message_user(
                request,
                " ".join(failed_documents),
                level=messages.ERROR,
            )

    def save_model(self, request, obj, form, change):
        super().save_model(
            request,
            obj,
            form,
            change,
        )

        if "file" in form.changed_data or not obj.checksum:
            digest = hashlib.sha256()

            with obj.file.open("rb") as document_file:
                for file_chunk in iter(
                    lambda: document_file.read(8192),
                    b"",
                ):
                    digest.update(file_chunk)

            obj.checksum = digest.hexdigest()
            obj.is_indexed = False
            obj.save(
                update_fields=[
                    "checksum",
                    "is_indexed",
                    "updated_at",
                ]
            )


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "chunk_index",
        "page_number",
        "section_title",
    )
    list_filter = (
        "document",
        "page_number",
    )
    search_fields = (
        "section_title",
        "content",
    )
    readonly_fields = (
        "document",
        "chunk_index",
        "page_number",
        "section_title",
        "content",
        "created_at",
    )

    def has_add_permission(self, request):
        return False