from dataclasses import dataclass

from django.db import transaction

from orders.models import (
    BILLING_ZIP_PATTERN,
    ORDER_ID_PATTERN,
    MockOrder,
    OrderLookupAttempt,
)


MAX_FAILED_ATTEMPTS = 3

GENERIC_VERIFICATION_FAILURE = (
    "I could not verify that order with the information "
    "provided. Please check the order ID and billing ZIP. "
    "For your privacy, I cannot search or display other records."
)

REPEATED_FAILURE_RESPONSE = (
    "I could not continue order verification after repeated "
    "failed attempts. I can help you request human support."
)

FAILED_OUTCOMES = {
    OrderLookupAttempt.Outcome.NOT_FOUND,
    OrderLookupAttempt.Outcome.ZIP_MISMATCH,
    OrderLookupAttempt.Outcome.MISSING_DATA,
    OrderLookupAttempt.Outcome.BLOCKED,
}


@dataclass(frozen=True)
class OrderLookupResult:
    outcome: str
    verified: bool
    message: str
    approved_data: dict
    requires_security_handoff: bool = False


def normalize_order_id(value):
    return (value or "").strip().upper()


def normalize_billing_zip(value):
    return (value or "").strip()


def get_consecutive_failure_count(session):
    if session is None:
        return 0

    failure_count = 0

    outcomes = OrderLookupAttempt.objects.filter(
        session=session
    ).values_list(
        "outcome",
        flat=True,
    )

    for outcome in outcomes:
        if outcome == OrderLookupAttempt.Outcome.VERIFIED:
            break

        if outcome in FAILED_OUTCOMES:
            failure_count += 1

    return failure_count


def record_attempt(
    session,
    provided_order_id,
    outcome,
    matched_order=None,
):
    return OrderLookupAttempt.objects.create(
        session=session,
        provided_order_id=provided_order_id[:30],
        matched_order=matched_order,
        outcome=outcome,
    )


def get_order_next_step(order):
    next_steps = {
        MockOrder.Status.PROCESSING: (
            "Please check again later for updated fulfillment "
            "information."
        ),
        MockOrder.Status.PACKED: (
            "Please check again later for updated carrier "
            "information."
        ),
        MockOrder.Status.SHIPPED: (
            "Use the carrier tracking reference for the latest "
            "movement updates."
        ),
        MockOrder.Status.OUT_FOR_DELIVERY: (
            "Use the carrier tracking reference for the latest "
            "delivery updates."
        ),
        MockOrder.Status.DELIVERED: (
            "If the package is marked delivered but was not "
            "received, request high-priority human support."
        ),
        MockOrder.Status.CANCELLED: (
            "A support specialist can review questions about "
            "this cancellation, but the assistant cannot "
            "reverse or change it."
        ),
    }

    return next_steps[order.status]


def build_approved_order_data(order):
    approved_data = {
        "order_id": order.order_id,
        "status": order.get_status_display(),
        "eta_window": order.eta_window,
        "next_step": get_order_next_step(order),
    }

    if order.carrier:
        approved_data["carrier"] = order.carrier

    if order.tracking_reference:
        approved_data[
            "tracking_reference"
        ] = order.tracking_reference

    return approved_data


def build_verified_message(order):
    message_parts = [
        (
            f"Order {order.order_id} is currently "
            f"{order.get_status_display().lower()}."
        )
    ]

    if order.carrier:
        message_parts.append(
            f"Carrier: {order.carrier}."
        )

    if order.tracking_reference:
        message_parts.append(
            "Tracking reference: "
            f"{order.tracking_reference}."
        )

    if order.eta_window:
        message_parts.append(
            "Estimated arrival window: "
            f"{order.eta_window}. This is an estimate, "
            "not a guaranteed delivery date."
        )

    message_parts.append(
        get_order_next_step(order)
    )

    return " ".join(message_parts)


def blocked_result():
    return OrderLookupResult(
        outcome=OrderLookupAttempt.Outcome.BLOCKED,
        verified=False,
        message=REPEATED_FAILURE_RESPONSE,
        approved_data={},
        requires_security_handoff=True,
    )


@transaction.atomic
def lookup_order(
    order_id,
    billing_zip,
    session=None,
):
    normalized_order_id = normalize_order_id(
        order_id
    )
    normalized_zip = normalize_billing_zip(
        billing_zip
    )

    if (
        session is not None
        and OrderLookupAttempt.objects.filter(
            session=session,
            outcome=OrderLookupAttempt.Outcome.BLOCKED,
        ).exists()
    ):
        record_attempt(
            session=session,
            provided_order_id=normalized_order_id,
            outcome=OrderLookupAttempt.Outcome.BLOCKED,
        )

        return blocked_result()

    if (
        not ORDER_ID_PATTERN.fullmatch(
            normalized_order_id
        )
        or not BILLING_ZIP_PATTERN.fullmatch(
            normalized_zip
        )
    ):
        failure_outcome = (
            OrderLookupAttempt.Outcome.MISSING_DATA
        )
        matched_order = None
    else:
        order = MockOrder.objects.filter(
            order_id=normalized_order_id
        ).first()

        if order is None:
            failure_outcome = (
                OrderLookupAttempt.Outcome.NOT_FOUND
            )
            matched_order = None
        elif order.billing_zip != normalized_zip:
            failure_outcome = (
                OrderLookupAttempt.Outcome.ZIP_MISMATCH
            )
            matched_order = None
        else:
            record_attempt(
                session=session,
                provided_order_id=normalized_order_id,
                matched_order=order,
                outcome=(
                    OrderLookupAttempt.Outcome.VERIFIED
                ),
            )

            return OrderLookupResult(
                outcome=(
                    OrderLookupAttempt.Outcome.VERIFIED
                ),
                verified=True,
                message=build_verified_message(order),
                approved_data=build_approved_order_data(
                    order
                ),
            )

    previous_failures = (
        get_consecutive_failure_count(session)
    )

    if (
        session is not None
        and previous_failures + 1
        >= MAX_FAILED_ATTEMPTS
    ):
        record_attempt(
            session=session,
            provided_order_id=normalized_order_id,
            outcome=OrderLookupAttempt.Outcome.BLOCKED,
        )

        return blocked_result()

    record_attempt(
        session=session,
        provided_order_id=normalized_order_id,
        outcome=failure_outcome,
        matched_order=matched_order,
    )

    return OrderLookupResult(
        outcome=failure_outcome,
        verified=False,
        message=GENERIC_VERIFICATION_FAILURE,
        approved_data={},
    )