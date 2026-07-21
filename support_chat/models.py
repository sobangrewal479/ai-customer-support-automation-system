import uuid

from django.db import models


class ChatSession(models.Model):
    class Outcome(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        HANDOFF = "handoff", "Human handoff"
        FALLBACK = "fallback", "Fallback"
        ABANDONED = "abandoned", "Abandoned"

    class ResolutionPath(models.TextChoices):
        NONE = "none", "Not resolved"
        FAQ = "faq", "FAQ"
        PRODUCT = "product", "Product"
        DOCUMENT = "document", "Document"
        ORDER = "order", "Order"
        LEAD = "lead", "Lead"
        HANDOFF = "handoff", "Human handoff"
        FALLBACK = "fallback", "Fallback"

    session_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    channel = models.CharField(
        max_length=30,
        default="website",
    )
    privacy_acknowledged = models.BooleanField(
        default=False,
    )
    outcome = models.CharField(
        max_length=20,
        choices=Outcome.choices,
        default=Outcome.IN_PROGRESS,
        db_index=True,
    )
    resolution_path = models.CharField(
        max_length=20,
        choices=ResolutionPath.choices,
        default=ResolutionPath.NONE,
        db_index=True,
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Chat {self.session_id}"


class ChatMessage(models.Model):
    class SenderType(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    class Intent(models.TextChoices):
        GREETING = "greeting", "Greeting"
        FAQ = "faq", "FAQ"
        PRODUCT = "product", "Product"
        DOCUMENT = "document", "Document"
        ORDER = "order", "Order"
        LEAD = "lead", "Lead"
        HANDOFF = "handoff", "Human handoff"
        UNSUPPORTED = "unsupported", "Unsupported"

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender_type = models.CharField(
        max_length=20,
        choices=SenderType.choices,
        db_index=True,
    )
    message = models.TextField()
    detected_intent = models.CharField(
        max_length=20,
        choices=Intent.choices,
        blank=True,
        db_index=True,
    )
    resolution_path = models.CharField(
        max_length=20,
        choices=ChatSession.ResolutionPath.choices,
        default=ChatSession.ResolutionPath.NONE,
    )
    source_references = models.JSONField(
        default=list,
        blank=True,
    )
    decision_metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return (
            f"{self.get_sender_type_display()} message "
            f"in {self.session_id}"
        )


class UnansweredQuestion(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWING = "reviewing", "Reviewing"
        CONVERTED = "converted", "Converted to FAQ"
        CLOSED = "closed", "Closed"

    question = models.TextField()
    normalized_topic = models.CharField(
        max_length=200,
        db_index=True,
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        related_name="unanswered_questions",
        null=True,
        blank=True,
    )
    occurrence_count = models.PositiveIntegerField(
        default=1,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    review_notes = models.TextField(
        blank=True,
    )
    converted_faq = models.ForeignKey(
        "knowledge.FAQ",
        on_delete=models.SET_NULL,
        related_name="converted_unanswered_questions",
        null=True,
        blank=True,
    )
    first_seen_at = models.DateTimeField(
        auto_now_add=True,
    )
    last_seen_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-occurrence_count", "-last_seen_at"]

    def __str__(self):
        return self.normalized_topic