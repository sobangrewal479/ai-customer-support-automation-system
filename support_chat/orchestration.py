import re
from dataclasses import dataclass

from django.db import transaction

from catalog.retrieval import (
    get_availability_message,
    resolve_product,
)
from knowledge.retrieval import retrieve_knowledge
from support_chat.models import (
    ChatMessage,
    ChatSession,
    UnansweredQuestion,
)


SAFE_FALLBACK = (
    "I could not confirm that from the approved Harbor & Pine "
    "information, so I do not want to guess. I can help you "
    "request human support."
)

GREETING_RESPONSE = (
    "Hello! I can help with Harbor & Pine FAQs, products, "
    "policies, and approved support information."
)

ORDER_VERIFICATION_PROMPT = (
    "I can help check an order. For privacy, please use the "
    "secure order lookup form and provide the exact order ID "
    "and matching billing ZIP. Do not include payment-card "
    "details or other sensitive information."
)

GREETING_WORDS = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}

UNSUPPORTED_LOAD_PATTERNS = (
    re.compile(
        r"\b(?:hold|support|carry)\b"
        r".*\b(?:pound|pounds|lb|lbs|kilogram|kilograms|kg)\b"
    ),
    re.compile(
        r"\b(?:weight|load)\s+"
        r"(?:capacity|limit|rating)\b"
    ),
)

ORDER_LOOKUP_PATTERNS = (
    re.compile(
        r"\bwhere\s+is\s+my\s+order\b"
    ),
    re.compile(
        r"\b(?:where is|track|tracking|check|find)\b"
        r".*\border\b"
    ),
    re.compile(
        r"\border\b.*\b"
        r"(?:status|track|tracking|delivery|arrive|arrival)\b"
    ),
)


@dataclass(frozen=True)
class ChatResponse:
    text: str
    intent: str
    resolution_path: str
    source_references: tuple[dict, ...]
    decision_metadata: dict
    outcome: str


def normalize_topic(value):
    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            (value or "").lower(),
        )
    )[:200]


def is_greeting(query):
    normalized_query = normalize_topic(query)

    return normalized_query in GREETING_WORDS


def is_unsupported_load_question(query):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in UNSUPPORTED_LOAD_PATTERNS
    )


def is_order_lookup_request(query):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in ORDER_LOOKUP_PATTERNS
    )


def limit_words(value, maximum_words=120):
    words = value.split()

    if len(words) <= maximum_words:
        return value

    return " ".join(words[:maximum_words]) + "..."


def build_knowledge_source(result):
    return {
        "source_type": result.source_type,
        "source_id": result.source_id,
        "source_label": result.source_label,
        "title": result.title,
        "score": result.score,
        "page_number": result.page_number,
        "section_title": result.section_title,
    }


def build_product_source(product):
    return {
        "source_type": "product",
        "source_id": product.sku,
        "source_label": (
            f"{product.product_name} ({product.sku})"
        ),
        "title": product.product_name,
    }


def compose_product_answer(product):
    answer_parts = [
        (
            f"{product.product_name} ({product.sku}) is in the "
            f"{product.category} collection."
        ),
        f"The approved price is ${product.price_usd:.2f}.",
        product.short_description,
        get_availability_message(product),
    ]

    if product.material:
        answer_parts.append(
            f"Material: {product.material}."
        )

    if product.color:
        answer_parts.append(
            f"Color: {product.color}."
        )

    if product.dimensions:
        answer_parts.append(
            f"Dimensions: {product.dimensions}."
        )

    if product.care_instructions:
        answer_parts.append(
            f"Care: {product.care_instructions}"
        )

    return " ".join(answer_parts)


def build_response(query):
    if is_greeting(query):
        return ChatResponse(
            text=GREETING_RESPONSE,
            intent=ChatMessage.Intent.GREETING,
            resolution_path=(
                ChatSession.ResolutionPath.NONE
            ),
            source_references=(),
            decision_metadata={
                "route": "greeting",
            },
            outcome=ChatSession.Outcome.RESOLVED,
        )

    if is_unsupported_load_question(query):
        return ChatResponse(
            text=SAFE_FALLBACK,
            intent=ChatMessage.Intent.UNSUPPORTED,
            resolution_path=(
                ChatSession.ResolutionPath.FALLBACK
            ),
            source_references=(),
            decision_metadata={
                "route": "unsupported_load_rating",
            },
            outcome=ChatSession.Outcome.FALLBACK,
        )

    if is_order_lookup_request(query):
        return ChatResponse(
            text=ORDER_VERIFICATION_PROMPT,
            intent=ChatMessage.Intent.ORDER,
            resolution_path=(
                ChatSession.ResolutionPath.ORDER
            ),
            source_references=(),
            decision_metadata={
                "route": "order_verification_required",
            },
            outcome=ChatSession.Outcome.IN_PROGRESS,
        )

    knowledge_results = retrieve_knowledge(
        query,
        faq_limit=3,
        document_limit=3,
    )

    product_resolution = resolve_product(
        query,
        limit=5,
    )

    exact_product_match = (
        product_resolution.status == "found"
        and product_resolution.best_match.score >= 20
    )

    if exact_product_match:
        best_match = product_resolution.best_match
        product = best_match.product

        return ChatResponse(
            text=compose_product_answer(product),
            intent=ChatMessage.Intent.PRODUCT,
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=(
                build_product_source(product),
            ),
            decision_metadata={
                "route": "product",
                "score": best_match.score,
                "matched_fields": list(
                    best_match.matched_fields
                ),
            },
            outcome=ChatSession.Outcome.RESOLVED,
        )

    if knowledge_results:
        best_result = knowledge_results[0]

        intent = (
            ChatMessage.Intent.FAQ
            if best_result.source_type == "faq"
            else ChatMessage.Intent.DOCUMENT
        )

        resolution_path = (
            ChatSession.ResolutionPath.FAQ
            if best_result.source_type == "faq"
            else ChatSession.ResolutionPath.DOCUMENT
        )

        return ChatResponse(
            text=limit_words(best_result.content),
            intent=intent,
            resolution_path=resolution_path,
            source_references=(
                build_knowledge_source(best_result),
            ),
            decision_metadata={
                "route": best_result.source_type,
                "score": best_result.score,
            },
            outcome=ChatSession.Outcome.RESOLVED,
        )

    if product_resolution.status == "ambiguous":
        candidate_lines = [
            (
                f"{result.product.product_name} "
                f"({result.product.sku})"
            )
            for result in product_resolution.matches[:3]
        ]

        return ChatResponse(
            text=(
                "I found more than one possible product. "
                "Please provide the SKU or choose one of these: "
                + "; ".join(candidate_lines)
                + "."
            ),
            intent=ChatMessage.Intent.PRODUCT,
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=tuple(
                build_product_source(result.product)
                for result in product_resolution.matches[:3]
            ),
            decision_metadata={
                "route": "product_ambiguous",
                "match_count": len(
                    product_resolution.matches
                ),
            },
            outcome=ChatSession.Outcome.IN_PROGRESS,
        )

    return ChatResponse(
        text=SAFE_FALLBACK,
        intent=ChatMessage.Intent.UNSUPPORTED,
        resolution_path=(
            ChatSession.ResolutionPath.FALLBACK
        ),
        source_references=(),
        decision_metadata={
            "route": "fallback",
        },
        outcome=ChatSession.Outcome.FALLBACK,
    )


def record_unanswered_question(
    session,
    question,
):
    normalized_topic = normalize_topic(question)

    unanswered = UnansweredQuestion.objects.filter(
        normalized_topic=normalized_topic,
        status__in=[
            UnansweredQuestion.Status.OPEN,
            UnansweredQuestion.Status.REVIEWING,
        ],
    ).first()

    if unanswered:
        unanswered.occurrence_count += 1
        unanswered.session = session
        unanswered.question = question
        unanswered.save(
            update_fields=[
                "occurrence_count",
                "session",
                "question",
                "last_seen_at",
            ]
        )

        return unanswered

    return UnansweredQuestion.objects.create(
        question=question,
        normalized_topic=normalized_topic,
        session=session,
    )


@transaction.atomic
def process_customer_message(
    session,
    customer_text,
):
    customer_message = ChatMessage.objects.create(
        session=session,
        sender_type=(
            ChatMessage.SenderType.CUSTOMER
        ),
        message=customer_text,
    )

    response = build_response(customer_text)

    assistant_message = ChatMessage.objects.create(
        session=session,
        sender_type=(
            ChatMessage.SenderType.ASSISTANT
        ),
        message=response.text,
        detected_intent=response.intent,
        resolution_path=response.resolution_path,
        source_references=list(
            response.source_references
        ),
        decision_metadata=(
            response.decision_metadata
        ),
    )

    session.outcome = response.outcome
    session.resolution_path = (
        response.resolution_path
    )
    session.save(
        update_fields=[
            "outcome",
            "resolution_path",
            "updated_at",
        ]
    )

    if response.resolution_path == (
        ChatSession.ResolutionPath.FALLBACK
    ):
        record_unanswered_question(
            session,
            customer_text,
        )

    return customer_message, assistant_message