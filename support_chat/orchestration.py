import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from django.db import transaction
from django.urls import reverse

from catalog.retrieval import (
    get_availability_message,
    resolve_product,
)
from knowledge.models import FAQ
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


ORDER_LOOKUP_ACTION_CUES = {
    "check",
    "find",
    "lookup",
    "track",
    "tracking",
}


ORDER_LOOKUP_STATE_CUES = {
    "status",
    "tracking",
}


ORDER_LOOKUP_EXCLUSION_CUES = {
    "add",
    "cancel",
    "cancellation",
    "edit",
    "refund",
    "remove",
    "return",
    "returns",
    "substitute",
    "swap",
}


SHIPPING_TIME_DURATION_CUES = (
    "how long",
    "how many days",
    "how much time",
    "how soon",
    "shipping time",
    "delivery time",
    "transit time",
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
    "shipping_time": (
        "How long does standard shipping take?"
    ),
    "return_eligibility": (
        "What is the return window?"
    ),
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


RELEVANCE_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "long",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "the",
    "to",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "would",
    "you",
    "your",
}


MIN_CUSTOMER_FAQ_SCORE = 8
MIN_CUSTOMER_DOCUMENT_SCORE = 3
MIN_FAQ_SCORE_MARGIN = 2
MIN_DOCUMENT_SCORE_MARGIN = 1


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


def _matches(query, patterns):
    normalized_query = normalize_topic(query)

    return any(
        pattern.search(normalized_query)
        for pattern in patterns
    )


def _matches_close_token(
    token,
    candidates,
    minimum_ratio=0.80,
):
    if token in candidates:
        return True

    return any(
        SequenceMatcher(
            None,
            token,
            candidate,
        ).ratio()
        >= minimum_ratio
        for candidate in candidates
    )


def is_greeting(query):
    return normalize_topic(query) in GREETING_WORDS


def is_support_capabilities_request(query):
    return _matches(
        query,
        SUPPORT_CAPABILITIES_PATTERNS,
    )


def is_unsupported_load_question(query):
    return _matches(
        query,
        UNSUPPORTED_LOAD_PATTERNS,
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

    has_timing_cue = any(
        cue in normalized_query
        for cue in RESTOCK_TIMING_CUES
    )

    return (
        has_restock_term
        and has_timing_cue
    )


def is_order_lookup_request(query):
    normalized_query = normalize_topic(
        query
    )

    normalized_query = (
        normalized_query.replace(
            "look up",
            "lookup",
        )
    )

    tokens = normalized_query.split()

    has_order_context = any(
        token in {
            "order",
            "orders",
        }
        for token in tokens
    )

    if not has_order_context:
        return False

    if any(
        token in ORDER_LOOKUP_EXCLUSION_CUES
        for token in tokens
    ):
        return False

    if (
        "where" in tokens
        and "my" in tokens
    ):
        return True

    has_state_cue = any(
        _matches_close_token(
            token,
            ORDER_LOOKUP_STATE_CUES,
        )
        for token in tokens
    )

    if has_state_cue:
        return True

    has_lookup_action = any(
        _matches_close_token(
            token,
            ORDER_LOOKUP_ACTION_CUES,
        )
        for token in tokens
    )

    return has_lookup_action


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

    has_duration = any(
        cue in normalized_query
        for cue in SHIPPING_TIME_DURATION_CUES
    )

    has_delivery = any(
        cue in normalized_query
        for cue in SHIPPING_TIME_DELIVERY_CUES
    )

    return (
        has_duration
        and has_delivery
    )


def is_return_eligibility_condition_question(query):
    normalized_query = normalize_topic(query)

    has_return_action = any(
        cue in normalized_query
        for cue in RETURN_ELIGIBILITY_ACTION_CUES
    )

    has_condition = any(
        cue in normalized_query
        for cue in RETURN_ELIGIBILITY_CONDITION_CUES
    )

    has_return_timing = any(
        cue in normalized_query
        for cue in (
            "how long",
            "how many days",
            "how much time",
            "return window",
            "after receiving",
            "after delivery",
            "after delivered",
            "after i receive",
            "after i get",
            "days after",
        )
    )

    return (
        has_return_action
        and (
            has_condition
            or has_return_timing
        )
    )


def is_product_overview_request(query):
    return _matches(
        query,
        PRODUCT_OVERVIEW_PATTERNS,
    )


def is_generic_product_help_request(query):
    normalized_query = normalize_topic(query)

    if (
        "specific product" in normalized_query
        and "sku" in normalized_query
        and any(
            phrase in normalized_query
            for phrase in (
                "don t know",
                "do not know",
                "dont know",
            )
        )
    ):
        return True

    if (
        "product" in normalized_query
        and any(
            phrase in normalized_query
            for phrase in (
                "don t know the sku",
                "do not know the sku",
                "dont know the sku",
            )
        )
    ):
        return True

    return _matches(
        query,
        GENERIC_PRODUCT_HELP_PATTERNS,
    )


def detect_product_category(query):
    normalized_query = normalize_topic(query)

    if "home organization" in normalized_query:
        return "Home Organization"

    for term, display_name in (
        PRODUCT_CATEGORY_TERMS.items()
    ):
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

    words = set(
        normalized_query.split()
    )

    if words.intersection(
        CATEGORY_BROWSE_BLOCKERS
    ):
        return False

    if normalized_query == normalize_topic(
        category
    ):
        return True

    return bool(
        words.intersection(
            CATEGORY_BROWSE_CUES
        )
    )


def is_support_hours_question(query):
    normalized_query = normalize_topic(query)

    if "business hours" in normalized_query:
        return True

    has_support_context = any(
        phrase in normalized_query
        for phrase in (
            "support",
            "customer support",
            "human support",
            "agent",
            "representative",
        )
    )

    has_hours_context = any(
        phrase in normalized_query
        for phrase in (
            "hours",
            "open",
            "close",
            "available",
        )
    )

    return (
        has_support_context
        and has_hours_context
    )


def is_explicit_human_request(query):
    normalized_query = normalize_topic(query)

    if normalized_query in {
        "human support",
        "human help",
        "talk to a human",
        "speak to a human",
        "talk to a person",
        "speak to a person",
        "talk to an agent",
        "speak to an agent",
    }:
        return True

    patterns = (
        (
            r"\b(?:speak|talk|chat)\s+"
            r"(?:to|with)\s+(?:a\s+)?"
            r"(?:human|person|agent|representative)\b"
        ),
        (
            r"\b(?:connect|transfer|route|send|direct|point)"
            r"\s+me\s+(?:to|toward|towards)\s+"
            r"(?:a\s+)?"
            r"(?:human|person|agent|representative|human support)\b"
        ),
        (
            r"\b(?:can|could|would)\s+you\s+"
            r"(?:connect|transfer|route|send|direct|point)"
            r"\s+me\b.*\b"
            r"(?:human|person|agent|representative|support)\b"
        ),
        (
            r"\b(?:i\s+)?(?:want|need|would like)\s+"
            r"(?:to\s+)?"
            r"(?:speak|talk|chat|connect)\b.*\b"
            r"(?:human|person|agent|representative)\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def get_requested_quantity(query):
    quantities = []

    normalized_query = normalize_topic(query)

    for match in re.finditer(
        (
            r"\b(\d{1,5})\s*"
            r"(?:units?|pieces?|items?|products?|shelves?)?\b"
        ),
        normalized_query,
    ):
        quantities.append(
            int(match.group(1))
        )

    return max(
        quantities,
        default=0,
    )


def is_bulk_quote_request(query):
    normalized_query = normalize_topic(query)

    quantity = get_requested_quantity(
        query
    )

    has_quote = any(
        phrase in normalized_query
        for phrase in (
            "quote",
            "quotation",
            "written quote",
            "pricing quote",
        )
    )

    has_bulk_context = any(
        phrase in normalized_query
        for phrase in (
            "bulk",
            "wholesale",
            "large order",
            "large quantity",
        )
    )

    has_action = any(
        phrase in normalized_query
        for phrase in (
            "i need",
            "i want",
            "i would like",
            "we need",
            "we want",
            "request",
            "get a",
            "receive a",
            "place an order",
            "buy",
            "purchase",
            "order",
        )
    )

    if (
        has_quote
        and (
            has_bulk_context
            or quantity >= 2
        )
    ):
        return True

    informational_starts = (
        "do you offer",
        "do u offer",
        "what is",
        "what are",
        "how does",
        "is there",
    )

    if (
        has_bulk_context
        and has_action
        and not normalized_query.startswith(
            informational_starts
        )
    ):
        return True

    return (
        quantity >= 50
        and has_action
    )


def is_trade_application_request(query):
    normalized_query = normalize_topic(query)

    return bool(
        re.search(
            (
                r"\b(?:apply|sign up|enroll)\b"
                r".*\btrade\s+program\b"
            ),
            normalized_query,
        )
        or re.search(
            (
                r"\b(?:i|we)\s+"
                r"(?:want|would like|need)\s+to\s+join\b"
                r".*\btrade\s+program\b"
            ),
            normalized_query,
        )
    )


def is_privacy_action_request(query):
    normalized_query = normalize_topic(query)

    patterns = (
        (
            r"\b(?:please|can you|could you|"
            r"i want you to|i need you to)\s+"
            r"(?:delete|erase|remove|correct|change|access)\b"
            r".*\b(?:my\s+)?(?:personal\s+)?data\b"
        ),
        (
            r"^(?:delete|erase|remove|correct)\s+"
            r"(?:my\s+)?(?:personal\s+)?data\b"
        ),
        (
            r"\b(?:delete|erase|remove|correct)\s+"
            r"(?:my\s+)?personal\s+information\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_order_cancellation_action(query):
    normalized_query = normalize_topic(query)

    patterns = (
        (
            r"\b(?:please\s+)?cancel\s+"
            r"(?:my|the)\s+order\b"
        ),
        (
            r"\b(?:can|could|would)\s+you\s+cancel\b"
            r".*\border\b"
        ),
        (
            r"\b(?:i|we)\s+"
            r"(?:want|need|would like)\s+"
            r"(?:to\s+)?cancel\b"
            r".*\border\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_address_change_action(query):
    normalized_query = normalize_topic(query)

    patterns = (
        (
            r"\b(?:can|could|would)\s+you\s+change\b"
            r".*\b(?:delivery|shipping)?\s*address\b"
        ),
        (
            r"\bplease\s+change\s+"
            r"(?:my\s+)?"
            r"(?:delivery|shipping)\s+address\b"
        ),
        (
            r"\b(?:i|we)\s+"
            r"(?:need|want|would like)\s+"
            r"(?:you\s+)?to\s+change\b"
            r".*\b(?:delivery|shipping)?\s*address\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_order_edit_action(query):
    normalized_query = normalize_topic(query)

    patterns = (
        (
            r"\b(?:can|could|would)\s+you\s+"
            r"(?:add|remove|change|substitute|swap)\b"
            r".*\b(?:item|product)\b"
            r".*\border\b"
        ),
        (
            r"\bplease\s+"
            r"(?:add|remove|change|substitute|swap)\b"
            r".*\b(?:item|product)\b"
            r".*\border\b"
        ),
        (
            r"\b(?:i|we)\s+"
            r"(?:need|want|would like)\s+"
            r"(?:you\s+)?to\s+"
            r"(?:add|remove|change|substitute|swap)\b"
            r".*\border\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_damage_event_request(query):
    normalized_query = normalize_topic(query)

    patterns = (
        (
            r"\bmy\b.*\b"
            r"(?:arrived|came|was delivered)\b"
            r".*\b(?:damaged|broken|incorrect|wrong)\b"
        ),
        (
            r"\b(?:i|we)\s+"
            r"(?:received|got)\b"
            r".*\b(?:damaged|broken|incorrect|wrong)\b"
        ),
        (
            r"\b(?:wrong|incorrect)\s+"
            r"(?:item|product)\b"
            r".*\b(?:arrived|received|delivered|got)\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_safety_event_request(query):
    normalized_query = normalize_topic(query)

    patterns = (
        (
            r"\b(?:started smoking|caught fire|"
            r"is smoking|is overheating|overheated)\b"
        ),
        (
            r"\b(?:injured me|hurt me|"
            r"burned me|burnt me)\b"
        ),
        (
            r"\b(?:i|we)\s+"
            r"(?:was|were|got)\s+"
            r"(?:injured|hurt|burned|burnt)\b"
        ),
        (
            r"\bcaused\s+"
            r"(?:an\s+)?(?:injury|burn)\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_payment_dispute_request(query):
    normalized_query = normalize_topic(query)

    patterns = (
        r"\b(?:payment|refund|charge)\s+dispute\b",
        r"\bchargeback\b",
        r"\b(?:fraud|fraudulent)\b",
        (
            r"\b(?:charged|billed)\s+"
            r"(?:twice|incorrectly|wrong)\b"
        ),
        (
            r"\bmy\s+refund\b.*\b"
            r"(?:missing|late|not received|"
            r"hasn t arrived|has not arrived)\b"
        ),
    )

    return any(
        re.search(
            pattern,
            normalized_query,
        )
        for pattern in patterns
    )


def is_complaint_request(query):
    normalized_query = normalize_topic(query)

    return bool(
        re.search(
            (
                r"\b(?:file|make|submit)\s+"
                r"(?:a\s+)?complaint\b"
            ),
            normalized_query,
        )
        or re.search(
            (
                r"\bi\s+"
                r"(?:want|need|would like)\s+"
                r"to\s+complain\b"
            ),
            normalized_query,
        )
        or re.search(
            r"\bspeak\s+to\s+(?:a\s+)?manager\b",
            normalized_query,
        )
    )


def is_legal_escalation_request(query):
    normalized_query = normalize_topic(query)

    return bool(
        re.search(
            (
                r"\b(?:legal action|lawyer|attorney|"
                r"regulator|consumer protection|"
                r"media inquiry)\b"
            ),
            normalized_query,
        )
    )


def is_policy_exception_request(query):
    normalized_query = normalize_topic(query)

    return bool(
        re.search(
            (
                r"\b(?:make|approve|give|allow)\b"
                r".*\bexception\b"
            ),
            normalized_query,
        )
        or re.search(
            (
                r"\boverride\b.*"
                r"\b(?:policy|return|refund|final sale)\b"
            ),
            normalized_query,
        )
    )


def limit_words(
    value,
    maximum_words=120,
):
    words = value.split()

    if len(words) <= maximum_words:
        return value

    return (
        " ".join(
            words[:maximum_words]
        )
        + "..."
    )


def normalize_customer_knowledge_voice(value):
    normalized = value or ""

    for (
        source_text,
        customer_text,
    ) in CUSTOMER_VOICE_REPLACEMENTS:
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

    for pattern in (
        INTERNAL_KNOWLEDGE_PATTERNS
    ):
        cleaned = pattern.sub(
            " ",
            cleaned,
        )

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

    return (
        normalize_customer_knowledge_voice(
            cleaned
        )
    )


def contains_internal_knowledge_marker(value):
    normalized_value = (
        value or ""
    ).lower()

    return any(
        marker in normalized_value
        for marker in (
            INTERNAL_KNOWLEDGE_MARKERS
        )
    )


def normalize_relevance_token(token):
    if (
        token.endswith("ies")
        and len(token) > 4
    ):
        return f"{token[:-3]}y"

    if (
        token.endswith("s")
        and len(token) > 3
        and not token.endswith("ss")
    ):
        return token[:-1]

    return token


def get_relevance_tokens(value):
    return {
        normalize_relevance_token(
            token
        )
        for token in re.findall(
            r"[a-z0-9]+",
            (value or "").lower(),
        )
        if token not in (
            RELEVANCE_STOP_WORDS
        )
    }


def get_customer_safe_knowledge_result(
    results,
    query="",
):
    query_tokens = get_relevance_tokens(
        query
    )

    safe_candidates = []

    for result in results:
        safe_content = (
            sanitize_customer_knowledge_text(
                result.content
            )
        )

        if not safe_content:
            continue

        if contains_internal_knowledge_marker(
            safe_content
        ):
            continue

        candidate_tokens = (
            get_relevance_tokens(
                " ".join(
                    [
                        result.title or "",
                        result.section_title or "",
                        safe_content,
                    ]
                )
            )
        )

        overlap_count = len(
            query_tokens.intersection(
                candidate_tokens
            )
        )

        if result.source_type == "faq":
            if (
                result.score
                < MIN_CUSTOMER_FAQ_SCORE
            ):
                continue

            if (
                overlap_count < 2
                and not (
                    len(query_tokens) == 1
                    and overlap_count == 1
                    and result.score >= 12
                )
            ):
                continue

        else:
            if (
                result.score
                < MIN_CUSTOMER_DOCUMENT_SCORE
            ):
                continue

            if (
                overlap_count < 2
                and not (
                    len(query_tokens) == 1
                    and overlap_count == 1
                    and result.score >= 6
                )
            ):
                continue

        safe_candidates.append(
            (
                result,
                limit_words(
                    safe_content
                ),
            )
        )

    if not safe_candidates:
        return None, ""

    (
        best_result,
        best_content,
    ) = safe_candidates[0]

    same_type_results = [
        candidate[0]
        for candidate in (
            safe_candidates[1:]
        )
        if candidate[0].source_type
        == best_result.source_type
    ]

    if same_type_results:
        second_result = (
            same_type_results[0]
        )

        margin = (
            best_result.score
            - second_result.score
        )

        if (
            best_result.source_type
            == "faq"
            and margin
            < MIN_FAQ_SCORE_MARGIN
            and best_result.score < 16
        ):
            return None, ""

        if (
            best_result.source_type
            == "document"
            and margin
            < MIN_DOCUMENT_SCORE_MARGIN
            and best_result.score < 6
        ):
            return None, ""

    return (
        best_result,
        best_content,
    )


def build_knowledge_source(result):
    if result.source_type == "document":
        return {
            "source_type": (
                result.source_type
            ),
            "source_id": (
                result.source_id
            ),
            "source_label": (
                "Approved Harbor & Pine "
                "support guide"
            ),
            "title": (
                result.section_title
                or (
                    "Harbor & Pine "
                    "support information"
                )
            ),
            "score": result.score,
            "page_number": (
                result.page_number
            ),
            "section_title": (
                result.section_title
            ),
        }

    return {
        "source_type": (
            result.source_type
        ),
        "source_id": (
            result.source_id
        ),
        "source_label": (
            result.source_label
        ),
        "title": (
            result.title
        ),
        "score": (
            result.score
        ),
        "page_number": (
            result.page_number
        ),
        "section_title": (
            result.section_title
        ),
    }


def build_product_source(product):
    return {
        "source_type": "product",
        "source_id": product.sku,
        "source_label": (
            f"{product.product_name} "
            f"({product.sku})"
        ),
        "title": product.product_name,
    }


def compose_product_answer(product):
    answer_parts = [
        (
            f"{product.product_name} "
            f"({product.sku}) is in the "
            f"{product.category} collection."
        ),
        (
            "The approved price is "
            f"${product.price_usd:.2f}."
        ),
        product.short_description,
        get_availability_message(
            product
        ),
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
            (
                "Dimensions: "
                f"{product.dimensions}."
            )
        )

    if product.care_instructions:
        answer_parts.append(
            (
                "Care: "
                f"{product.care_instructions}"
            )
        )

    return " ".join(
        answer_parts
    )


def build_product_ambiguous_response(
    product_resolution,
):
    candidate_lines = [
        (
            f"{result.product.product_name} "
            f"({result.product.sku})"
        )
        for result in (
            product_resolution.matches[:3]
        )
    ]

    return ChatResponse(
        text=(
            "I found more than one possible "
            "product. Please provide the SKU "
            "or choose one of these: "
            + "; ".join(candidate_lines)
            + "."
        ),
        intent=(
            ChatMessage.Intent.PRODUCT
        ),
        resolution_path=(
            ChatSession.ResolutionPath.PRODUCT
        ),
        source_references=tuple(
            build_product_source(
                result.product
            )
            for result in (
                product_resolution.matches[:3]
            )
        ),
        decision_metadata={
            "route": "product_ambiguous",
            "match_count": len(
                product_resolution.matches
            ),
        },
        outcome=(
            ChatSession.Outcome.IN_PROGRESS
        ),
    )


def build_category_browse_response(
    category,
    product_resolution,
):
    if (
        product_resolution.status
        == "ambiguous"
    ):
        return (
            build_product_ambiguous_response(
                product_resolution
            )
        )

    return ChatResponse(
        text=(
            f"I can help you browse "
            f"{category} products. "
            "Tell me what type of item you "
            "are looking for, or share a "
            "product name or SKU if you "
            "have one."
        ),
        intent=(
            ChatMessage.Intent.PRODUCT
        ),
        resolution_path=(
            ChatSession.ResolutionPath.PRODUCT
        ),
        source_references=(
            PRODUCT_CATALOG_SOURCE,
        ),
        decision_metadata={
            "route": (
                "product_category_browse"
            ),
            "category": category,
        },
        outcome=(
            ChatSession.Outcome.IN_PROGRESS
        ),
    )


def build_targeted_faq_response(
    route_key,
):
    canonical_query = (
        TARGETED_FAQ_QUERIES[
            route_key
        ]
    )

    knowledge_results = (
        retrieve_knowledge(
            canonical_query,
            faq_limit=3,
            document_limit=3,
        )
    )

    for result in knowledge_results:
        if (
            result.source_type
            != "faq"
        ):
            continue

        safe_content = (
            sanitize_customer_knowledge_text(
                result.content
            )
        )

        if not safe_content:
            continue

        if (
            contains_internal_knowledge_marker(
                safe_content
            )
        ):
            continue

        return ChatResponse(
            text=limit_words(
                safe_content
            ),
            intent=(
                ChatMessage.Intent.FAQ
            ),
            resolution_path=(
                ChatSession.ResolutionPath.FAQ
            ),
            source_references=(
                build_knowledge_source(
                    result
                ),
            ),
            decision_metadata={
                "route": (
                    f"targeted_"
                    f"{route_key}_faq"
                ),
                "score": result.score,
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    return None


def build_exact_enabled_faq_response(
    query,
):
    normalized_query = normalize_topic(
        query
    )

    if not normalized_query:
        return None

    faqs = FAQ.objects.filter(
        is_enabled=True
    ).only(
        "faq_id",
        "question",
        "approved_answer",
    )

    for faq in faqs:
        if (
            normalize_topic(
                faq.question
            )
            != normalized_query
        ):
            continue

        safe_content = (
            sanitize_customer_knowledge_text(
                faq.approved_answer
            )
        )

        if not safe_content:
            return None

        return ChatResponse(
            text=limit_words(
                safe_content
            ),
            intent=(
                ChatMessage.Intent.FAQ
            ),
            resolution_path=(
                ChatSession.ResolutionPath.FAQ
            ),
            source_references=(
                {
                    "source_type": "faq",
                    "source_id": (
                        faq.faq_id
                    ),
                    "source_label": (
                        f"FAQ {faq.faq_id}"
                    ),
                    "title": (
                        faq.question
                    ),
                    "score": 100.0,
                    "page_number": None,
                    "section_title": "",
                },
            ),
            decision_metadata={
                "route": (
                    "exact_enabled_faq"
                ),
                "score": 100.0,
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    return None


def extract_support_hours(value):
    normalized = re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()

    patterns = (
        re.compile(
            (
                r"\bMon(?:day)?\s*[-–—]\s*"
                r"Fri(?:day)?\s*,?\s*"
                r"\d{1,2}(?::\d{2})?\s*"
                r"(?:AM|PM)\s*[-–—]\s*"
                r"\d{1,2}(?::\d{2})?\s*"
                r"(?:AM|PM)\s*CT\s*;\s*"
                r"Sat(?:urday)?\s*,?\s*"
                r"\d{1,2}(?::\d{2})?\s*"
                r"(?:AM|PM)\s*[-–—]\s*"
                r"\d{1,2}(?::\d{2})?\s*"
                r"(?:AM|PM)\s*CT\b"
            ),
            re.IGNORECASE,
        ),
        re.compile(
            (
                r"\bMon(?:day)?\s*[-–—]\s*"
                r"Fri(?:day)?\s*,?\s*"
                r"\d{1,2}(?::\d{2})?\s*"
                r"(?:AM|PM)\s*[-–—]\s*"
                r"\d{1,2}(?::\d{2})?\s*"
                r"(?:AM|PM)\s*CT\b"
            ),
            re.IGNORECASE,
        ),
    )

    for pattern in patterns:
        match = pattern.search(
            normalized
        )

        if match:
            return match.group(0)

    return ""


def build_support_hours_response():
    knowledge_results = (
        retrieve_knowledge(
            (
                "business hours "
                "customer support hours"
            ),
            faq_limit=1,
            document_limit=5,
        )
    )

    for result in knowledge_results:
        if (
            result.source_type
            != "document"
        ):
            continue

        safe_content = (
            sanitize_customer_knowledge_text(
                result.content
            )
        )

        if not safe_content:
            continue

        if (
            contains_internal_knowledge_marker(
                safe_content
            )
        ):
            continue

        hours = extract_support_hours(
            safe_content
        )

        if not hours:
            continue

        return ChatResponse(
            text=(
                "Harbor & Pine human "
                "support hours are "
                f"{hours}."
            ),
            intent=(
                ChatMessage.Intent.DOCUMENT
            ),
            resolution_path=(
                ChatSession.ResolutionPath.DOCUMENT
            ),
            source_references=(
                build_knowledge_source(
                    result
                ),
            ),
            decision_metadata={
                "route": (
                    "support_hours"
                ),
                "score": result.score,
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    return None


def build_handoff_route_response(
    *,
    route,
    category,
    message,
):
    handoff_url = reverse(
        "crm_lite:human_handoff"
    )

    return ChatResponse(
        text=(
            f"{message} "
            "Please use the human-support "
            "request form: "
            f"{handoff_url}"
        ),
        intent=(
            ChatMessage.Intent.HANDOFF
        ),
        resolution_path=(
            ChatSession.ResolutionPath.HANDOFF
        ),
        source_references=(),
        decision_metadata={
            "route": route,
            "handoff_category": (
                category
            ),
            "next_url": handoff_url,
        },
        outcome=(
            ChatSession.Outcome.IN_PROGRESS
        ),
    )


def build_lead_route_response(
    *,
    route,
    inquiry_type,
    message,
):
    lead_url = reverse(
        "crm_lite:lead_capture"
    )

    return ChatResponse(
        text=(
            f"{message} "
            "Please use the inquiry form "
            "so the team can collect the "
            "required contact details and "
            "consent: "
            f"{lead_url}"
        ),
        intent=(
            ChatMessage.Intent.LEAD
        ),
        resolution_path=(
            ChatSession.ResolutionPath.LEAD
        ),
        source_references=(),
        decision_metadata={
            "route": route,
            "inquiry_type": (
                inquiry_type
            ),
            "next_url": lead_url,
        },
        outcome=(
            ChatSession.Outcome.IN_PROGRESS
        ),
    )


def build_operational_response(query):
    if is_safety_event_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "urgent_safety_handoff"
                ),
                category=(
                    "safety_legal"
                ),
                message=(
                    "Please stop using the "
                    "product and request urgent "
                    "human support. I can't "
                    "diagnose the issue, assign "
                    "fault, or promise a "
                    "resolution."
                ),
            )
        )

    if is_legal_escalation_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "legal_escalation_handoff"
                ),
                category=(
                    "safety_legal"
                ),
                message=(
                    "This needs review by the "
                    "appropriate Harbor & Pine "
                    "team rather than a chatbot "
                    "response."
                ),
            )
        )

    if is_privacy_action_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "privacy_request_handoff"
                ),
                category=(
                    "privacy_request"
                ),
                message=(
                    "I can't complete or verify "
                    "a personal-data request in "
                    "chat. It needs authorized "
                    "human review."
                ),
            )
        )

    if is_payment_dispute_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "payment_refund_handoff"
                ),
                category=(
                    "payment_refund"
                ),
                message=(
                    "A payment or refund dispute "
                    "needs human review. Please "
                    "don't send payment-card "
                    "credentials or other "
                    "sensitive information in "
                    "chat."
                ),
            )
        )

    if is_order_cancellation_action(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "order_cancellation_handoff"
                ),
                category=(
                    "human_request"
                ),
                message=(
                    "I can't cancel an order "
                    "directly. A time-sensitive "
                    "support request is the "
                    "correct next step, and "
                    "cancellation is not complete "
                    "until an authorized person "
                    "or system confirms it."
                ),
            )
        )

    if is_address_change_action(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "address_change_handoff"
                ),
                category=(
                    "human_request"
                ),
                message=(
                    "I can't change a delivery "
                    "address directly. A support "
                    "specialist can review the "
                    "request if fulfillment has "
                    "not started, but a change "
                    "is not guaranteed."
                ),
            )
        )

    if is_order_edit_action(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "order_edit_handoff"
                ),
                category=(
                    "human_request"
                ),
                message=(
                    "I can't add, remove, "
                    "substitute, or change order "
                    "items directly. A support "
                    "specialist can review the "
                    "request, but fulfillment "
                    "status may prevent changes."
                ),
            )
        )

    if is_damage_event_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "damage_handoff"
                ),
                category=(
                    "complaint"
                ),
                message=(
                    "A damaged or incorrect item "
                    "needs human review. Keep the "
                    "order ID and affected-item "
                    "details available; the team "
                    "may also request photos."
                ),
            )
        )

    if is_complaint_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "complaint_handoff"
                ),
                category="complaint",
                message=(
                    "I can route this for "
                    "human review."
                ),
            )
        )

    if is_policy_exception_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "policy_exception_handoff"
                ),
                category=(
                    "human_request"
                ),
                message=(
                    "I can't approve or promise "
                    "a policy exception. A "
                    "support specialist can "
                    "review the request."
                ),
            )
        )

    if is_explicit_human_request(
        query
    ):
        return (
            build_handoff_route_response(
                route=(
                    "explicit_human_handoff"
                ),
                category=(
                    "human_request"
                ),
                message=(
                    "Yes. I can point you to "
                    "the human-support request "
                    "workflow."
                ),
            )
        )

    if is_bulk_quote_request(
        query
    ):
        return (
            build_lead_route_response(
                route=(
                    "bulk_quote_lead"
                ),
                inquiry_type=(
                    "bulk_order"
                ),
                message=(
                    "A bulk or written-quote "
                    "request should go through "
                    "the sales inquiry workflow."
                ),
            )
        )

    if is_trade_application_request(
        query
    ):
        return (
            build_lead_route_response(
                route=(
                    "trade_program_lead"
                ),
                inquiry_type=(
                    "trade_program"
                ),
                message=(
                    "Trade-program interest is "
                    "reviewed case by case. I "
                    "can point you to the inquiry "
                    "workflow; approval, terms, "
                    "and discounts aren't "
                    "promised in chat."
                ),
            )
        )

    return None


def build_response(query):
    if is_greeting(query):
        return ChatResponse(
            text=GREETING_RESPONSE,
            intent=(
                ChatMessage.Intent.GREETING
            ),
            resolution_path=(
                ChatSession.ResolutionPath.NONE
            ),
            source_references=(),
            decision_metadata={
                "route": "greeting",
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    if is_support_capabilities_request(
        query
    ):
        return ChatResponse(
            text=(
                SUPPORT_CAPABILITIES_RESPONSE
            ),
            intent=(
                ChatMessage.Intent.GREETING
            ),
            resolution_path=(
                ChatSession.ResolutionPath.NONE
            ),
            source_references=(),
            decision_metadata={
                "route": (
                    "support_capabilities"
                ),
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    exact_faq_response = (
        build_exact_enabled_faq_response(
            query
        )
    )

    if exact_faq_response:
        return exact_faq_response

    operational_response = (
        build_operational_response(
            query
        )
    )

    if operational_response:
        return operational_response

    if is_support_hours_question(
        query
    ):
        response = (
            build_support_hours_response()
        )

        if response:
            return response

    if is_shipping_time_question(
        query
    ):
        response = (
            build_targeted_faq_response(
                "shipping_time"
            )
        )

        if response:
            return response

    if (
        is_return_eligibility_condition_question(
            query
        )
    ):
        response = (
            build_targeted_faq_response(
                "return_eligibility"
            )
        )

        if response:
            return response

    if is_unsupported_load_question(
        query
    ):
        return ChatResponse(
            text=SAFE_FALLBACK,
            intent=(
                ChatMessage.Intent.UNSUPPORTED
            ),
            resolution_path=(
                ChatSession.ResolutionPath.FALLBACK
            ),
            source_references=(),
            decision_metadata={
                "route": (
                    "unsupported_load_rating"
                ),
            },
            outcome=(
                ChatSession.Outcome.FALLBACK
            ),
        )

    if (
        is_unsupported_product_spec_question(
            query
        )
    ):
        return ChatResponse(
            text=SAFE_FALLBACK,
            intent=(
                ChatMessage.Intent.UNSUPPORTED
            ),
            resolution_path=(
                ChatSession.ResolutionPath.FALLBACK
            ),
            source_references=(),
            decision_metadata={
                "route": (
                    "unsupported_product_"
                    "specification"
                ),
            },
            outcome=(
                ChatSession.Outcome.FALLBACK
            ),
        )

    if is_order_lookup_request(
        query
    ):
        return ChatResponse(
            text=(
                ORDER_VERIFICATION_PROMPT
            ),
            intent=(
                ChatMessage.Intent.ORDER
            ),
            resolution_path=(
                ChatSession.ResolutionPath.ORDER
            ),
            source_references=(),
            decision_metadata={
                "route": (
                    "order_verification_required"
                ),
            },
            outcome=(
                ChatSession.Outcome.IN_PROGRESS
            ),
        )

    if is_product_overview_request(
        query
    ):
        return ChatResponse(
            text=(
                PRODUCT_OVERVIEW_RESPONSE
            ),
            intent=(
                ChatMessage.Intent.PRODUCT
            ),
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=(
                PRODUCT_CATALOG_SOURCE,
            ),
            decision_metadata={
                "route": (
                    "product_overview"
                ),
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    if is_generic_product_help_request(
        query
    ):
        return ChatResponse(
            text=(
                GENERIC_PRODUCT_HELP_RESPONSE
            ),
            intent=(
                ChatMessage.Intent.PRODUCT
            ),
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=(
                PRODUCT_CATALOG_SOURCE,
            ),
            decision_metadata={
                "route": (
                    "generic_product_help"
                ),
            },
            outcome=(
                ChatSession.Outcome.IN_PROGRESS
            ),
        )

    product_resolution = (
        resolve_product(
            query,
            limit=5,
        )
    )

    exact_product_match = (
        product_resolution.status
        == "found"
        and (
            product_resolution
            .best_match
            .score
            >= 20
        )
    )

    if exact_product_match:
        best_match = (
            product_resolution.best_match
        )

        product = (
            best_match.product
        )

        return ChatResponse(
            text=compose_product_answer(
                product
            ),
            intent=(
                ChatMessage.Intent.PRODUCT
            ),
            resolution_path=(
                ChatSession.ResolutionPath.PRODUCT
            ),
            source_references=(
                build_product_source(
                    product
                ),
            ),
            decision_metadata={
                "route": "product",
                "score": (
                    best_match.score
                ),
                "matched_fields": list(
                    best_match.matched_fields
                ),
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    if is_category_browse_request(
        query
    ):
        return (
            build_category_browse_response(
                detect_product_category(
                    query
                ),
                product_resolution,
            )
        )

    knowledge_results = (
        retrieve_knowledge(
            query,
            faq_limit=3,
            document_limit=3,
        )
    )

    (
        best_result,
        safe_knowledge_content,
    ) = (
        get_customer_safe_knowledge_result(
            knowledge_results,
            query=query,
        )
    )

    if best_result:
        intent = (
            ChatMessage.Intent.FAQ
            if (
                best_result.source_type
                == "faq"
            )
            else (
                ChatMessage.Intent.DOCUMENT
            )
        )

        resolution_path = (
            ChatSession.ResolutionPath.FAQ
            if (
                best_result.source_type
                == "faq"
            )
            else (
                ChatSession
                .ResolutionPath
                .DOCUMENT
            )
        )

        return ChatResponse(
            text=(
                safe_knowledge_content
            ),
            intent=intent,
            resolution_path=(
                resolution_path
            ),
            source_references=(
                build_knowledge_source(
                    best_result
                ),
            ),
            decision_metadata={
                "route": (
                    best_result.source_type
                ),
                "score": (
                    best_result.score
                ),
            },
            outcome=(
                ChatSession.Outcome.RESOLVED
            ),
        )

    if (
        product_resolution.status
        == "ambiguous"
    ):
        return (
            build_product_ambiguous_response(
                product_resolution
            )
        )

    return ChatResponse(
        text=SAFE_FALLBACK,
        intent=(
            ChatMessage.Intent.UNSUPPORTED
        ),
        resolution_path=(
            ChatSession.ResolutionPath.FALLBACK
        ),
        source_references=(),
        decision_metadata={
            "route": "fallback",
        },
        outcome=(
            ChatSession.Outcome.FALLBACK
        ),
    )


def record_unanswered_question(
    session,
    question,
):
    normalized_topic = normalize_topic(
        question
    )

    unanswered = (
        UnansweredQuestion.objects.filter(
            normalized_topic=(
                normalized_topic
            ),
            status__in=[
                UnansweredQuestion.Status.OPEN,
                (
                    UnansweredQuestion
                    .Status
                    .REVIEWING
                ),
            ],
        )
        .first()
    )

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

    return (
        UnansweredQuestion.objects.create(
            question=question,
            normalized_topic=(
                normalized_topic
            ),
            session=session,
        )
    )


@transaction.atomic
def process_customer_message(
    session,
    customer_text,
):
    customer_message = (
        ChatMessage.objects.create(
            session=session,
            sender_type=(
                ChatMessage
                .SenderType
                .CUSTOMER
            ),
            message=customer_text,
        )
    )

    response = build_response(
        customer_text
    )

    assistant_message = (
        ChatMessage.objects.create(
            session=session,
            sender_type=(
                ChatMessage
                .SenderType
                .ASSISTANT
            ),
            message=response.text,
            detected_intent=(
                response.intent
            ),
            resolution_path=(
                response.resolution_path
            ),
            source_references=list(
                response.source_references
            ),
            decision_metadata=(
                response.decision_metadata
            ),
        )
    )

    session.outcome = (
        response.outcome
    )

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

    if (
        response.resolution_path
        == (
            ChatSession
            .ResolutionPath
            .FALLBACK
        )
    ):
        record_unanswered_question(
            session,
            customer_text,
        )

    return (
        customer_message,
        assistant_message,
    )