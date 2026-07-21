from django.contrib import admin

from support_chat.models import (
    ChatMessage,
    ChatSession,
    UnansweredQuestion,
)


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    can_delete = False
    readonly_fields = (
        "sender_type",
        "message",
        "detected_intent",
        "resolution_path",
        "source_references",
        "decision_metadata",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "session_id",
        "channel",
        "outcome",
        "resolution_path",
        "privacy_acknowledged",
        "started_at",
    )
    list_filter = (
        "channel",
        "outcome",
        "resolution_path",
        "privacy_acknowledged",
        "started_at",
    )
    search_fields = (
        "session_id",
        "messages__message",
    )
    readonly_fields = (
        "session_id",
        "started_at",
        "updated_at",
    )
    ordering = ("-started_at",)
    inlines = (ChatMessageInline,)
    list_per_page = 50


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "sender_type",
        "detected_intent",
        "resolution_path",
        "created_at",
    )
    list_filter = (
        "sender_type",
        "detected_intent",
        "resolution_path",
        "created_at",
    )
    search_fields = (
        "session__session_id",
        "message",
    )
    readonly_fields = (
        "session",
        "sender_type",
        "message",
        "detected_intent",
        "resolution_path",
        "source_references",
        "decision_metadata",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "normalized_topic",
        "occurrence_count",
        "status",
        "session",
        "first_seen_at",
        "last_seen_at",
    )
    list_filter = (
        "status",
        "first_seen_at",
        "last_seen_at",
    )
    search_fields = (
        "question",
        "normalized_topic",
    )
    readonly_fields = (
        "question",
        "normalized_topic",
        "session",
        "occurrence_count",
        "first_seen_at",
        "last_seen_at",
    )
    ordering = (
        "-occurrence_count",
        "-last_seen_at",
    )