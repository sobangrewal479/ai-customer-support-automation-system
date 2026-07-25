from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from crm_lite.models import HandoffRequest, Lead


DUPLICATE_LOOKBACK_DAYS = 30

CATEGORY_PRIORITY = {
    HandoffRequest.Category.HUMAN_REQUEST: (
        HandoffRequest.Priority.NORMAL
    ),
    HandoffRequest.Category.UNSUPPORTED: (
        HandoffRequest.Priority.NORMAL
    ),
    HandoffRequest.Category.COMPLAINT: (
        HandoffRequest.Priority.HIGH
    ),
    HandoffRequest.Category.PAYMENT_REFUND: (
        HandoffRequest.Priority.HIGH
    ),
    HandoffRequest.Category.SAFETY_LEGAL: (
        HandoffRequest.Priority.URGENT
    ),
    HandoffRequest.Category.PRIVACY_REQUEST: (
        HandoffRequest.Priority.URGENT
    ),
    HandoffRequest.Category.HIGH_VALUE_SALES: (
        HandoffRequest.Priority.HIGH
    ),
    HandoffRequest.Category.OTHER: (
        HandoffRequest.Priority.NORMAL
    ),
}

PRIORITY_SLA_HOURS = {
    HandoffRequest.Priority.LOW: 48,
    HandoffRequest.Priority.NORMAL: 24,
    HandoffRequest.Priority.HIGH: 4,
    HandoffRequest.Priority.URGENT: 1,
}

PRIORITY_OWNER = {
    HandoffRequest.Priority.LOW: "Support Queue",
    HandoffRequest.Priority.NORMAL: "Support Queue",
    HandoffRequest.Priority.HIGH: (
        "Priority Support Queue"
    ),
    HandoffRequest.Priority.URGENT: (
        "Escalation Queue"
    ),
}


def determine_handoff_priority(category):
    return CATEGORY_PRIORITY.get(
        category,
        HandoffRequest.Priority.NORMAL,
    )


def calculate_sla_due_at(priority, *, current_time=None):
    start_time = current_time or timezone.now()

    hours = PRIORITY_SLA_HOURS.get(
        priority,
        PRIORITY_SLA_HOURS[
            HandoffRequest.Priority.NORMAL
        ],
    )

    return start_time + timedelta(hours=hours)


@transaction.atomic
def create_lead_from_form(form, *, session=None):
    if not form.is_valid():
        raise ValueError(
            "A valid lead form is required."
        )

    lead = form.save(commit=False)
    lead.source_session = session

    duplicate_cutoff = (
        timezone.now()
        - timedelta(days=DUPLICATE_LOOKBACK_DAYS)
    )

    lead.duplicate_review_required = (
        Lead.objects.filter(
            email__iexact=lead.email,
            inquiry_type=lead.inquiry_type,
            created_at__gte=duplicate_cutoff,
        )
        .exclude(
            status=Lead.Status.CLOSED,
        )
        .exists()
    )

    lead.full_clean()
    lead.save()

    return lead


@transaction.atomic
def create_handoff_from_form(form, *, session=None):
    if not form.is_valid():
        raise ValueError(
            "A valid handoff form is required."
        )

    handoff = form.save(commit=False)
    handoff.session = session

    handoff.priority = determine_handoff_priority(
        handoff.category
    )

    handoff.assigned_owner = PRIORITY_OWNER[
        handoff.priority
    ]

    handoff.sla_due_at = calculate_sla_due_at(
        handoff.priority
    )

    handoff.full_clean()
    handoff.save()

    return handoff