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