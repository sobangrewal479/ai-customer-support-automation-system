from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from dashboard.services import get_dashboard_summary


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