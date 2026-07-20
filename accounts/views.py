from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render


@login_required(login_url="accounts:login")
def portal(request):
    if request.user.is_superuser:
        role_name = "Administrator"
    elif request.user.groups.filter(name="Support Agent").exists():
        role_name = "Support Agent"
    else:
        raise PermissionDenied(
            "Your account does not have staff portal access."
        )

    context = {
        "role_name": role_name,
    }

    return render(request, "accounts/portal.html", context)