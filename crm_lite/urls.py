from django.urls import path

from crm_lite import views


app_name = "crm_lite"

urlpatterns = [
    path(
        "lead/",
        views.lead_capture,
        name="lead_capture",
    ),
    path(
        "human-support/",
        views.human_handoff,
        name="human_handoff",
    ),
]