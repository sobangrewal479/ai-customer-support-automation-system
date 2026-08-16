import re
from dataclasses import dataclass

from .models import FAQ, KnowledgeChunk, KnowledgeDocument


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "long",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "the",
    "to",
    "we",
    "what",
    "with",
    "you",
    "your",
}

MIN_FAQ_SCORE = 4
MIN_DOCUMENT_SCORE = 2


@dataclass(frozen=True)
class RetrievalResult:
    source_type: str
    source_id: str
    title: str
    content: str
    score: float
    category: str = ""
    page_number: int | None = None
    section_title: str = ""

    @property
    def source_label(self):
        if self.source_type == "faq":
            return f"FAQ {self.source_id}"

        page_label = ""

        if self.page_number:
            page_label = f", page {self.page_number}"

        return (
            f"{self.title}{page_label}"
            f" - {self.section_title}"
        )


def normalize_token(token):
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"

    if (
        token.endswith("s")
        and len(token) > 3
        and not token.endswith("ss")
    ):
        return token[:-1]

    return token


def tokenize(text):
    raw_tokens = re.findall(
        r"[a-z0-9]+",
        text.lower(),
    )

    return [
        normalize_token(token)
        for token in raw_tokens
        if token not in STOP_WORDS
    ]


def calculate_overlap(query_tokens, candidate_text):
    candidate_tokens = set(tokenize(candidate_text))

    return len(query_tokens & candidate_tokens)


def search_faqs(
    query,
    limit=3,
    min_score=MIN_FAQ_SCORE,
):
    query_token_list = tokenize(query)
    query_tokens = set(query_token_list)

    if not query_tokens:
        return []

    query_phrase = " ".join(query_token_list)
    results = []

    faqs = FAQ.objects.filter(
        is_enabled=True
    ).only(
        "faq_id",
        "category",
        "question",
        "approved_answer",
        "keywords",
    )

    for faq in faqs:
        question_score = calculate_overlap(
            query_tokens,
            faq.question,
        )
        keyword_score = calculate_overlap(
            query_tokens,
            faq.keywords,
        )
        answer_score = calculate_overlap(
            query_tokens,
            faq.approved_answer,
        )

        score = (
            question_score * 4
            + keyword_score * 3
            + answer_score
        )

        normalized_question = " ".join(
            tokenize(faq.question)
        )

        if (
            query_phrase
            and query_phrase in normalized_question
        ):
            score += 6

        if score < min_score:
            continue

        results.append(
            RetrievalResult(
                source_type="faq",
                source_id=faq.faq_id,
                title=faq.question,
                content=faq.approved_answer,
                score=float(score),
                category=faq.category,
            )
        )

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            result.source_id,
        ),
    )[:limit]


def search_document_chunks(
    query,
    limit=3,
    min_score=MIN_DOCUMENT_SCORE,
):
    query_tokens = set(tokenize(query))

    if not query_tokens:
        return []

    results = []

    chunks = KnowledgeChunk.objects.filter(
        document__status=(
            KnowledgeDocument.Status.ACTIVE
        ),
        document__is_indexed=True,
    ).select_related(
        "document"
    )

    for chunk in chunks:
        section_score = calculate_overlap(
            query_tokens,
            chunk.section_title,
        )
        content_score = calculate_overlap(
            query_tokens,
            chunk.content,
        )

        score = (
            section_score * 3
            + content_score
        )

        if score < min_score:
            continue

        results.append(
            RetrievalResult(
                source_type="document",
                source_id=str(chunk.pk),
                title=chunk.document.title,
                content=chunk.content,
                score=float(score),
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
        )

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            result.source_id,
        ),
    )[:limit]


def retrieve_knowledge(
    query,
    faq_limit=3,
    document_limit=3,
):
    results = [
        *search_faqs(
            query,
            limit=faq_limit,
        ),
        *search_document_chunks(
            query,
            limit=document_limit,
        ),
    ]

    return sorted(
        results,
        key=lambda result: (
            -result.score,
            result.source_type,
            result.source_id,
        ),
    )