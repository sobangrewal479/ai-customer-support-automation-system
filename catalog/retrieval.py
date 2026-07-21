import re
from dataclasses import dataclass

from catalog.models import Product


MINIMUM_PRODUCT_SCORE = 4
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ProductSearchResult:
    product: Product
    score: int
    matched_fields: tuple[str, ...]


@dataclass(frozen=True)
class ProductResolution:
    status: str
    matches: tuple[ProductSearchResult, ...]

    @property
    def best_match(self):
        if self.status == "found" and self.matches:
            return self.matches[0]

        return None


def normalize_text(value):
    return " ".join(TOKEN_PATTERN.findall((value or "").lower()))


def tokenize(value):
    return set(TOKEN_PATTERN.findall((value or "").lower()))


def score_product(product, normalized_query, query_tokens):
    score = 0
    matched_fields = []

    normalized_sku = normalize_text(product.sku)
    normalized_name = normalize_text(product.product_name)

    if normalized_query == normalized_sku:
        return 100, ("sku",)

    if (
        normalized_sku
        and normalized_sku in normalized_query
    ):
        return 90, ("sku",)

    if normalized_query == normalized_name:
        return 80, ("product_name",)

    if normalized_query and normalized_query in normalized_name:
        score += 20
        matched_fields.append("product_name")

    fields_and_weights = (
        ("product_name", product.product_name, 8),
        ("sku", product.sku, 6),
        ("category", product.category, 4),
        ("material", product.material, 3),
        ("color", product.color, 3),
        ("short_description", product.short_description, 1),
    )

    for field_name, field_value, weight in fields_and_weights:
        matching_tokens = query_tokens.intersection(
            tokenize(field_value)
        )

        if matching_tokens:
            score += len(matching_tokens) * weight

            if field_name not in matched_fields:
                matched_fields.append(field_name)

    return score, tuple(matched_fields)


def search_products(query, limit=5):
    normalized_query = normalize_text(query)

    if not normalized_query:
        return []

    query_tokens = tokenize(query)
    results = []

    for product in Product.objects.all():
        score, matched_fields = score_product(
            product,
            normalized_query,
            query_tokens,
        )

        if score >= MINIMUM_PRODUCT_SCORE:
            results.append(
                ProductSearchResult(
                    product=product,
                    score=score,
                    matched_fields=matched_fields,
                )
            )

    results.sort(
        key=lambda result: (
            -result.score,
            result.product.sku,
        )
    )

    return results[:limit]


def resolve_product(query, limit=5):
    results = search_products(query, limit=limit)

    if not results:
        return ProductResolution(
            status="not_found",
            matches=(),
        )

    if (
        len(results) > 1
        and results[0].score == results[1].score
    ):
        return ProductResolution(
            status="ambiguous",
            matches=tuple(results),
        )

    return ProductResolution(
        status="found",
        matches=tuple(results),
    )


def get_availability_message(product):
    messages = {
        Product.Status.ACTIVE: (
            "This product is active in the approved catalog."
        ),
        Product.Status.LOW_STOCK: (
            "This product is marked as low stock. Availability "
            "cannot be guaranteed or reserved in chat."
        ),
        Product.Status.OUT_OF_STOCK: (
            "This product is currently out of stock. The approved "
            "record does not provide a restock date."
        ),
        Product.Status.DISCONTINUED: (
            "This product is discontinued. Human support can help "
            "with general alternatives, but no replacement is promised."
        ),
    }

    return messages[product.status]