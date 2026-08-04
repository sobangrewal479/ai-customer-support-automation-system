from catalog.models import Product
from crm_lite.models import HandoffRequest, Lead
from orders.models import OrderLookupAttempt
from support_chat.models import (
    ChatSession,
    UnansweredQuestion,
)


def get_dashboard_summary():
    return {
        "chat_sessions": ChatSession.objects.count(),
        "unanswered_questions": (
            UnansweredQuestion.objects.count()
        ),
        "leads": Lead.objects.count(),
        "handoff_requests": (
            HandoffRequest.objects.count()
        ),
        "order_lookup_attempts": (
            OrderLookupAttempt.objects.count()
        ),
        "products": Product.objects.count(),
    }


def get_conversation_records():
    return (
        ChatSession.objects
        .prefetch_related("messages")
        .all()
    )


def get_conversation_contact_records(conversation):
    linked_leads = Lead.objects.filter(
        source_session=conversation,
    )

    linked_handoff_requests = HandoffRequest.objects.filter(
        session=conversation,
    )

    return {
        "linked_leads": linked_leads,
        "linked_handoff_requests": linked_handoff_requests,
        "has_linked_contact": (
            linked_leads.exists()
            or linked_handoff_requests.exists()
        ),
    }


def get_unanswered_question_records():
    return (
        UnansweredQuestion.objects
        .select_related(
            "session",
            "converted_faq",
        )
        .all()
    )


def get_lead_records():
    return (
        Lead.objects
        .select_related("source_session")
        .all()
    )