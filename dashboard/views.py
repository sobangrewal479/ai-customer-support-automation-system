from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from dashboard.services import (
    get_conversation_contact_records,
    get_conversation_records,
    get_dashboard_summary,
    get_handoff_request_records,
    get_lead_records,
    get_unanswered_question_records,
)
from support_chat.models import ChatSession


@login_required
def dashboard_home(request):
    summary = get_dashboard_summary()

    return render(
        request,
        "dashboard/home.html",
        {
            "summary": summary,
        },
    )


@login_required
def conversation_list(request):
    conversations = get_conversation_records()

    return render(
        request,
        "dashboard/conversation_list.html",
        {
            "conversations": conversations,
        },
    )


@login_required
def conversation_detail(request, session_id):
    conversation = get_object_or_404(
        ChatSession.objects.prefetch_related(
            "messages"
        ),
        pk=session_id,
    )

    contact_records = get_conversation_contact_records(
        conversation
    )

    return render(
        request,
        "dashboard/conversation_detail.html",
        {
            "conversation": conversation,
            "linked_leads": contact_records[
                "linked_leads"
            ],
            "linked_handoff_requests": contact_records[
                "linked_handoff_requests"
            ],
            "has_linked_contact": contact_records[
                "has_linked_contact"
            ],
        },
    )


@login_required
def unanswered_question_list(request):
    unanswered_questions = (
        get_unanswered_question_records()
    )

    return render(
        request,
        "dashboard/unanswered_question_list.html",
        {
            "unanswered_questions": unanswered_questions,
        },
    )


@login_required
def lead_list(request):
    leads = get_lead_records()

    return render(
        request,
        "dashboard/lead_list.html",
        {
            "leads": leads,
        },
    )


@login_required
def handoff_request_list(request):
    handoff_requests = (
        get_handoff_request_records()
    )

    return render(
        request,
        "dashboard/handoff_request_list.html",
        {
            "handoff_requests": handoff_requests,
        },
    )