from uuid import UUID

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from support_chat.models import ChatSession
from support_chat.orchestration import process_customer_message


CHAT_SESSION_KEY = "harbor_pine_chat_session_id"
CHAT_CONTINUE_ONCE_KEY = "harbor_pine_continue_chat_once"
MAX_MESSAGE_LENGTH = 2000


def create_new_chat_session(request):
    chat_session = ChatSession.objects.create()

    request.session[CHAT_SESSION_KEY] = str(
        chat_session.session_id
    )

    return chat_session


def get_or_create_chat_session(request):
    stored_session_id = request.session.get(
        CHAT_SESSION_KEY
    )

    if stored_session_id:
        try:
            UUID(stored_session_id)
        except (TypeError, ValueError):
            stored_session_id = None

    if stored_session_id:
        chat_session = ChatSession.objects.filter(
            session_id=stored_session_id
        ).first()

        if chat_session:
            return chat_session

    return create_new_chat_session(request)


@xframe_options_sameorigin
@require_http_methods(["GET", "POST"])
def chat_page(request):
    widget_mode = request.GET.get("widget") == "1"
    error = ""

    if request.method == "GET":
        continue_session_id = request.session.pop(
            CHAT_CONTINUE_ONCE_KEY,
            None,
        )

        current_session_id = request.session.get(
            CHAT_SESSION_KEY
        )

        should_continue_existing_chat = (
            continue_session_id
            and continue_session_id
            == current_session_id
        )

        if should_continue_existing_chat:
            chat_session = get_or_create_chat_session(
                request
            )
        else:
            chat_session = create_new_chat_session(
                request
            )

    else:
        chat_session = get_or_create_chat_session(
            request
        )

    if request.method == "POST":
        customer_text = request.POST.get(
            "message",
            "",
        ).strip()

        privacy_confirmed = (
            chat_session.privacy_acknowledged
            or request.POST.get(
                "privacy_acknowledged"
            )
            == "yes"
        )

        if not privacy_confirmed:
            error = (
                "Please acknowledge the privacy "
                "notice before sending a message."
            )

        elif not customer_text:
            error = (
                "Please enter a support question."
            )

        elif len(customer_text) > MAX_MESSAGE_LENGTH:
            error = (
                f"Your message must not exceed "
                f"{MAX_MESSAGE_LENGTH} characters."
            )

        else:
            if not chat_session.privacy_acknowledged:
                chat_session.privacy_acknowledged = True

                chat_session.save(
                    update_fields=[
                        "privacy_acknowledged",
                        "updated_at",
                    ]
                )

            process_customer_message(
                chat_session,
                customer_text,
            )

            request.session[
                CHAT_CONTINUE_ONCE_KEY
            ] = str(
                chat_session.session_id
            )

            chat_url = reverse(
                "support_chat:chat"
            )

            if widget_mode:
                return redirect(
                    f"{chat_url}?widget=1"
                )

            return redirect(chat_url)

    context = {
        "chat_session": chat_session,
        "chat_messages": (
            chat_session.messages.all()
        ),
        "error": error,
        "max_message_length": (
            MAX_MESSAGE_LENGTH
        ),
        "widget_mode": widget_mode,
    }

    return render(
        request,
        "support_chat/chat.html",
        context,
    )