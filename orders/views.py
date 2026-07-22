from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from orders.forms import OrderLookupForm
from orders.services import lookup_order
from support_chat.views import get_or_create_chat_session


@require_http_methods(["GET", "POST"])
def order_lookup(request):
    chat_session = get_or_create_chat_session(request)
    lookup_result = None

    if request.method == "POST":
        form = OrderLookupForm(request.POST)

        if form.is_valid():
            lookup_result = lookup_order(
                order_id=form.cleaned_data["order_id"],
                billing_zip=form.cleaned_data["billing_zip"],
                session=chat_session,
            )
    else:
        form = OrderLookupForm()

    context = {
        "form": form,
        "lookup_result": lookup_result,
    }

    return render(
        request,
        "orders/order_lookup.html",
        context,
    )