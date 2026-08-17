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

SUPPORT_CAPABILITIES_RESPONSE = (
    "I can help with Harbor & Pine product discovery, product "
    "details, shipping and returns, approved policies, order "
    "lookup, and general support questions. If something needs "
    "a person, I can also point you toward human support."
)

ORDER_VERIFICATION_PROMPT = (
    "I can help check an order. For privacy, please use the "
    "secure order lookup form and provide the exact order ID "
    "and matching billing ZIP. Do not include payment-card "
    "details or other sensitive information."
)

PRODUCT_OVERVIEW_RESPONSE = (
    "Harbor & Pine offers products across five main categories: "
    "Home Organization, Kitchen, Bath, Office, and Outdoor. "
    "Tell me which category you are interested in, or share a "
    "product name or SKU, and I can help with the approved "
    "product details."
)

GENERIC_PRODUCT_HELP_RESPONSE = (
    "Absolutely. Tell me the product name if you know it, or "
    "describe what you are looking for. You can also choose "
    "Home Organization, Kitchen, Bath, Office, or Outdoor. "
    "If you have a SKU, you can share that too."
)

PRODUCT_CATALOG_SOURCE = {
    "source_type": "product",
    "source_id": "catalog-overview",
    "source_label": "Approved product catalog",
    "title": "Harbor & Pine product categories",
}


GREETING_WORDS = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}


SUPPORT_CAPABILITIES_PATTERNS = (
    re.compile(
        r"\bwhat\s+can\s+(?:you|u)\s+"
        r"help\s+me\s+with\b"
    ),
    re.compile(
        r"\bhow\s+can\s+(?:you|u)\s+help\b"
    ),
    re.compile(
        r"\bwhat\s+can\s+(?:you|u)\s+do\b"
    ),
    re.compile(
        r"\bwhat\s+do\s+(?:you|u)\s+"
        r"help\s+with\b"
    ),
    re.compile(
        r"\bwhat\s+can\s+this\s+"
        r"(?:chatbot|bot|support)\s+do\b"
    ),
)


UNSUPPORTED_LOAD_PATTERNS = (
    re.compile(
        r"\b(?:hold|support|carry)\b"
        r".*\b(?:pound|pounds|lb|lbs|kilogram|kilograms|kg)\b"
    ),
    re.compile(
        r"\b(?:weight|load)\s+"
        r"(?:capacity|limit|rating)\b"
    ),
    re.compile(
        r"\b(?:safe|safely|rated)\b"
        r".*\b\d+(?:\.\d+)?\s*"
        r"(?:pound|pounds|lb|lbs|kilogram|kilograms|kg)\b"
    ),
    re.compile(
        r"\b\d+(?:\.\d+)?\s*"
        r"(?:pound|pounds|lb|lbs|kilogram|kilograms|kg)\b"
        r".*\b(?:safe|safely|rated)\b"
    ),
)

UNSUPPORTED_WARRANTY_CUES = (
    "warranty",
    "warranties",
)

RESTOCK_TERMS = (
    "restock",
    "restocked",
    "restocking",
    "back in stock",
)

RESTOCK_TIMING_CUES = (
    "when",
    "how long",
    "what date",
    "date",
    "expected",
    "expect",
    "estimate",
    "estimated",
    "soon",
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


SHIPPING_TIME_DURATION_CUES = (
    "how long",
    "how many days",
    "how much time",
    "how soon",
)

SHIPPING_TIME_DELIVERY_CUES = (
    "shipping",
    "delivery",
    "delivered",
    "arrive",
    "arrival",
    "reach",
    "get to me",
    "get here",
)

RETURN_ELIGIBILITY_ACTION_CUES = (
    "return",
    "send back",
)

RETURN_ELIGIBILITY_CONDITION_CUES = (
    "used",
    "using",
    "use it",
    "worn",
    "wear",
    "wore",
    "washed",
    "opened",
    "open it",
)

TARGETED_FAQ_QUERIES = {
    "shipping_time": "How long does standard shipping take?",
    "return_eligibility": "What is the return window?",
}


PRODUCT_OVERVIEW_PATTERNS = (
    re.compile(
        r"\bwhat\s+do\s+"
        r"(?:you\s+guys|you|u)\s+"
        r"(?:sell|offer|carry|have)\b"
    ),
    re.compile(
        r"\bwhat\s+"
        r"(?:kind|kinds|type|types|categories)\s+"
        r"of\s+products\b"
    ),
    re.compile(
        r"\bwhat\s+products\b"
        r".*\b(?:offer|sell|carry|have)\b"
    ),
    re.compile(
        r"\bwhat\s+does\s+harbor\s+and\s+pine\b"
        r".*\b(?:offer|sell|carry|have)\b"
    ),
    re.compile(
        r"\b(?:show|list)\s+me\s+"
        r"(?:your|the)\s+products\b"
    ),
    re.compile(
        r"\bproduct\s+categories\b"
    ),
)


GENERIC_PRODUCT_HELP_PATTERNS = (
    re.compile(
        r"\b(?:help|guide|assist)\s+me\s+"
        r"(?:about|with)\s+"
        r"(?:(?:a|one)\s+)?"
        r"(?:certain|specific)?\s*product\b"
    ),
    re.compile(
        r"\b(?:can|could|would)\s+(?:you|u)\b"
        r".*\b(?:help|guide|assist)\b"
        r".*\b(?:certain|specific)?\s*product\b"
    ),
    re.compile(
        r"\bi\s+need\s+help\s+"
        r"(?:choosing|finding)\s+"
        r"(?:a\s+)?product\b"
    ),
    re.compile(
        r"\b(?:help|guide|assist)\s+me\s+"
        r"(?:with|about)\s+one\s+of\s+"
        r"(?:your|the)\s+products\b"
    ),
)


PRODUCT_CATEGORY_TERMS = {
    "home organization": "Home Organization",
    "kitchen": "Kitchen",
    "bath": "Bath",
    "office": "Office",
    "outdoor": "Outdoor",
}


CATEGORY_BROWSE_CUES = {
    "anything",
    "browse",
    "find",
    "have",
    "help",
    "interested",
    "looking",
    "need",
    "offer",
    "product",
    "products",
    "recommend",
    "sell",
    "show",
    "something",
    "want",
}


CATEGORY_BROWSE_BLOCKERS = {
    "cancel",
    "cancellation",
    "care",
    "clean",
    "cleaning",
    "delivery",
    "refund",
    "return",
    "returns",
    "shipping",
    "warranty",
}


INTERNAL_KNOWLEDGE_PATTERNS = (
    re.compile(
        r"H&P\s+Harbor\s*&\s*Pine\s+Living\s+"
        r"Mock\s+Knowledge\s+Base\s+v[\d.]+",
        re.IGNORECASE,
    ),
    re.compile(
        r"Fictional\s+practice\s+document\s*-\s*"
        r"not\s+a\s+real\s+company\s+policy",
        re.IGNORECASE,
    ),
    re.compile(
        r"CONFIDENTIAL\s*-\s*MOCK\s+CLIENT\s+DATA",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bPage\s+\d+\b",
        re.IGNORECASE,
    ),
)


INTERNAL_KNOWLEDGE_MARKERS = (
    "mock knowledge base",
    "fictional practice",
    "not a real company policy",
    "mock client data",
    "synthetic sku",
    "synthetic skus",
    "synthetic order",
    "synthetic orders",
    "practice build",
    "portfolio project",
)

CUSTOMER_VOICE_REPLACEMENTS = (
    (
        "The assistant cannot change an address.",
        "I can't change your delivery address directly.",
    ),
    (
        (
            "The assistant should not declare a package lost; "
            "it can create a support request if the delay "
            "continues or the customer is concerned."
        ),
        (
            "A delayed tracking update does not necessarily "
            "mean your package is lost. If the delay continues "
            "or you're concerned, I can help you request support."
        ),
    ),
    (
        (
            "Customers normally pay return shipping for "
            "preference-based returns."
        ),
        (
            "You would normally pay return shipping for a "
            "preference-based return."
        ),
    ),
    (
        "The financial institution may need additional time.",
        "Your financial institution may need additional time.",
    ),
    (
        (
            "No. The assistant can create a high-priority "
            "cancellation request, but cancellation is not "
            "complete until an authorized system or person "
            "confirms it."
        ),
        (
            "No. I can create a high-priority cancellation "
            "request, but the cancellation is not complete "
            "until an authorized system or person confirms it."
        ),
    ),
    (
        (
            "The assistant cannot edit an order. It can create "
            "a handoff for review, but fulfillment status may "
            "prevent changes."
        ),
        (
            "I can't edit your order directly. I can create "
            "a support request for review, but fulfillment "
            "status may prevent changes."
        ),
    ),
    (
        (
            "The assistant must not diagnose, assign fault, "
            "or promise a resolution."
        ),
        (
            "I can't diagnose the issue, assign fault, or "
            "promise a resolution."
        ),
    ),
    (
        (
            "No. It can explain an approved active code but "
            "cannot create a code, override restrictions, or "
            "promise a manual discount."
        ),
        (
            "No. I can explain an approved active code, but "
            "I can't create a code, override restrictions, or "
            "promise a manual discount."
        ),
    ),
    (
        (
            "Yes, but the assistant cannot complete or verify "
            "the request. It must create a privacy handoff to "
            "the authorized human owner."
        ),
        (
            "Yes, but I can't complete or verify the request "
            "myself. The request needs to be routed to the "
            "authorized privacy owner."
        ),
    ),
    (
        (
            "The assistant can capture quantity, desired date, "
            "ZIP code, and contact information for a written "
            "quote."
        ),
        (
            "I can collect your quantity, desired date, ZIP "
            "code, and contact information for a written quote."
        ),
    ),
    (
        (
            "The assistant can capture interest but cannot "
            "promise approval, terms, or discounts."
        ),
        (
            "I can record your interest, but I can't promise "
            "approval, terms, or discounts."
        ),
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


def is_support_capabilities_request(query):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in SUPPORT_CAPABILITIES_PATTERNS
    )


def is_unsupported_load_question(query):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in UNSUPPORTED_LOAD_PATTERNS
    )


def is_unsupported_product_spec_question(query):
    normalized_query = normalize_topic(query)

    if any(
        cue in normalized_query
        for cue in UNSUPPORTED_WARRANTY_CUES
    ):
        return True

    has_restock_term = any(
        term in normalized_query
        for term in RESTOCK_TERMS
    )

    has_restock_timing_cue = any(
        cue in normalized_query
        for cue in RESTOCK_TIMING_CUES
    )

    return (
        has_restock_term
        and has_restock_timing_cue
    )


def is_order_lookup_request(query):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in ORDER_LOOKUP_PATTERNS
    )


def is_shipping_time_question(query):
    normalized_query = normalize_topic(query)

    if any(
        blocker in normalized_query
        for blocker in (
            "return",
            "refund",
            "cancel",
            "cancellation",
            "change address",
        )
    ):
        return False

    has_duration_cue = any(
        cue in normalized_query
        for cue in SHIPPING_TIME_DURATION_CUES
    )

    has_delivery_cue = any(
        cue in normalized_query
        for cue in SHIPPING_TIME_DELIVERY_CUES
    )

    return has_duration_cue and has_delivery_cue


def is_return_eligibility_condition_question(query):
    normalized_query = normalize_topic(query)

    has_return_action = any(
        cue in normalized_query
        for cue in RETURN_ELIGIBILITY_ACTION_CUES
    )

    has_condition_cue = any(
        cue in normalized_query
        for cue in RETURN_ELIGIBILITY_CONDITION_CUES
    )

    return has_return_action and has_condition_cue


def is_product_overview_request(query):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in PRODUCT_OVERVIEW_PATTERNS
    )


def is_generic_product_help_request(query):
    normalized_query = normalize_topic(query)

    if (
        "specific product" in normalized_query
        and "sku" in normalized_query
        and (
            "don t know" in normalized_query
            or "do not know" in normalized_query
            or "dont know" in normalized_query
        )
    ):
        return True

    if (
        "product" in normalized_query
        and (
            "don t know the sku" in normalized_query
            or "do not know the sku" in normalized_query
            or "dont know the sku" in normalized_query
        )
    ):
        return True

    return any(
        pattern.search(normalized_query)
        for pattern in GENERIC_PRODUCT_HELP_PATTERNS
    )


def detect_product_category(query):
    normalized_query = normalize_topic(query)

    if "home organization" in normalized_query:
        return "Home Organization"

    for term, display_name in PRODUCT_CATEGORY_TERMS.items():
        if term == "home organization":
            continue

        if re.search(
            rf"\b{re.escape(term)}\b",
            normalized_query,
        ):
            return display_name

    return None


def is_category_browse_request(query):
    normalized_query = normalize_topic(query)

    category = detect_product_category(query)

    if not category:
        return False

    words = set(normalized_query.split())

    if words.intersection(CATEGORY_BROWSE_BLOCKERS):
        return False

    normalized_category = normalize_topic(category)

    if normalized_query == normalized_category:
        return True

    return bool(
        words.intersection(CATEGORY_BROWSE_CUES)
    )


def limit_words(value, maximum_words=120):
    words = value.split()

    if len(words) <= maximum_words:
        return value

    return " ".join(words[:maximum_words]) + "..."


def normalize_customer_knowledge_voice(value):
    normalized = value or ""

    for source_text, customer_text in (
        CUSTOMER_VOICE_REPLACEMENTS
    ):
        normalized = re.sub(
            re.escape(source_text),
            customer_text,
            normalized,
            flags=re.IGNORECASE,
        )

    return normalized


def sanitize_customer_knowledge_text(value):
    cleaned = value or ""

    cleaned = re.sub(
        r"\bmock\s+trade\s+program\b",
        "trade program",
        cleaned,
        flags=re.IGNORECASE,
    )

    for pattern in INTERNAL_KNOWLEDGE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)

    cleaned = re.sub(
        r"\bSECTION\s+\d+\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip(" -|")

    cleaned = normalize_customer_knowledge_voice(
        cleaned
    )

    return cleaned


def contains_internal_knowledge_marker(value):
    normalized_value = (value or "").lower()

    return any(
        marker in normalized_value
        for marker in INTERNAL_KNOWLEDGE_MARKERS
    )


def get_customer_safe_knowledge_result(results):
    for result in results:
        safe_content = sanitize_customer_knowledge_text(
            result.content
        )

        if not safe_content:
            continue

        if contains_internal_knowledge_marker(
            safe_content
        ):
            continue

        return result, limit_words(safe_content)

    return None, ""


def build_knowledge_source(result):
    if result.source_type == "document":
        return {
            "source_type": result.source_type,
            "source_id": result.source_id,
            "source_label": (
                "Approved Harbor & Pine support guide"
            ),
            "title": (
                result.section_title
                or "Harbor & Pine support information"
            ),
            "score": result.score,
            "page_number": result.page_number,
            "section_title": result.section_title,
        }

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


def build_product_ambiguous_response(
    product_resolution,
):
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


def build_category_browse_response(
    category,
    product_resolution,
):
    if product_resolution.status == "ambiguous":
        return build_product_ambiguous_response(
            product_resolution
        )

    return ChatResponse(
        text=(
            f"I can help you browse {category} products. "
            "Tell me what type of item you are looking for, "
            "or share a product name or SKU if you have one."
        ),
        intent=ChatMessage.Intent.PRODUCT,
        resolution_path=(
            ChatSession.ResolutionPath.PRODUCT
        ),
        source_references=(
            PRODUCT_CATALOG_SOURCE,
        ),
        decision_metadata={
            "route": "product_category_browse",
            "category": category,
        },
        outcome=ChatSession.Outcome.IN_PROGRESS,
    )


def build_targeted_faq_response(route_key):
    canonical_query = TARGETED_FAQ_QUERIES[route_key]

    knowledge_results = retrieve_knowledge(
        canonical_query,
        faq_limit=3,
        document_limit=3,
    )

    for result in knowledge_results:
        if result.source_type != "faq":
            continue

        safe_content = sanitize_customer_knowledge_text(
            result.content
        )

        if not safe_content:
            continue

        if contains_internal_knowledge_marker(
            safe_content
        ):
            continue

        return ChatResponse(
            text=limit_words(safe_content),
            intent=ChatMessage.Intent.FAQ,
            resolution_path=(
                ChatSession.ResolutionPath.FAQ
            ),
            source_references=(
                build_knowledge_source(result),
            ),
            decision_metadata={
                "route": f"targeted_{route_key}_faq",
                "score": result.score,
            },
            outcome=ChatSession.Outcome.RESOLVED,
        )

    return None


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

    if is_support_capabilities_request(query):
        return ChatResponse(
            text=SUPPORT_CAPABILITIES_RESPONSE,
            intent=ChatMessage.Intent.GREETING,
            resolution_path=(
                ChatSession.ResolutionPath.NONE
            ),
            source_references=(),
            decision_metadata={
                "route": "support_capabilities",
            },
            outcome=ChatSession.Outcome.RESOLVED,
        )

    if is_shipping_time_question(query):
        response = build_targeted_faq_response(
            "shipping_time"
        )

        if response:
            return response

    if is_return_eligibility_condition_question(query):
        response = build_targeted_faq_response(
            "return_eligibility"
        )

        if response:
            return response

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


    if is_unsupported_product_spec_question(query):
        return ChatResponse(
            text=SAFE_FALLBACK,
            intent=ChatMessage.Intent.UNSUPPORTED,
            resolution_path=(
                ChatSession.ResolutionPath.FALLBACK
            ),
            source_references=(),
            decision_metadata={
                "route": "unsupported_product_specification",
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

    if is_product_overview_request(query):
        return ChatResponse(
            text=PRODUCT_OVERVIEW_RESPONSE,
            intent=ChatMessage.Intent.PRODUCT,
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=(
                PRODUCT_CATALOG_SOURCE,
            ),
            decision_metadata={
                "route": "product_overview",
            },
            outcome=ChatSession.Outcome.RESOLVED,
        )

    if is_generic_product_help_request(query):
        return ChatResponse(
            text=GENERIC_PRODUCT_HELP_RESPONSE,
            intent=ChatMessage.Intent.PRODUCT,
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=(
                PRODUCT_CATALOG_SOURCE,
            ),
            decision_metadata={
                "route": "generic_product_help",
            },
            outcome=ChatSession.Outcome.IN_PROGRESS,
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

    if is_category_browse_request(query):
        category = detect_product_category(query)

        return build_category_browse_response(
            category,
            product_resolution,
        )

    knowledge_results = retrieve_knowledge(
        query,
        faq_limit=3,
        document_limit=3,
    )

    (
        best_result,
        safe_knowledge_content,
    ) = get_customer_safe_knowledge_result(
        knowledge_results
    )

    if best_result:
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
            text=safe_knowledge_content,
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
        return build_product_ambiguous_response(
            product_resolution
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