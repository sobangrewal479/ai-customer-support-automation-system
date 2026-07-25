from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from crm_lite.forms import (
    HandoffRequestForm,
    LeadCaptureForm,
)
from crm_lite.services import (
    create_handoff_from_form,
    create_lead_from_form,
)
from support_chat.views import get_or_create_chat_session


@require_http_methods(["GET", "POST"])
def lead_capture(request):
    chat_session = get_or_create_chat_session(request)

    if request.method == "POST":
        form = LeadCaptureForm(request.POST)

        if form.is_valid():
            lead = create_lead_from_form(
                form,
                session=chat_session,
            )

            messages.success(
                request,
                (
                    f"Thank you, {lead.name}. Your inquiry "
                    "has been saved and sent to the Harbor "
                    "& Pine team."
                ),
            )

            return redirect(
                "crm_lite:lead_capture"
            )
    else:
        form = LeadCaptureForm()

    return render(
        request,
        "crm_lite/lead_capture.html",
        {
            "form": form,
        },
    )


@require_http_methods(["GET", "POST"])
def human_handoff(request):
    chat_session = get_or_create_chat_session(request)

    if request.method == "POST":
        form = HandoffRequestForm(request.POST)

        if form.is_valid():
            handoff = create_handoff_from_form(
                form,
                session=chat_session,
            )

            messages.success(
                request,
                (
                    "Your human-support request has been "
                    "created. It was assigned to the "
                    f"{handoff.assigned_owner}."
                ),
            )

            return redirect(
                "crm_lite:human_handoff"
            )
    else:
        form = HandoffRequestForm()

    return render(
        request,
        "crm_lite/human_handoff.html",
        {
            "form": form,
        },
    )