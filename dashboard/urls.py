from django.urls import path

from dashboard import views


app_name = "dashboard"

urlpatterns = [
    path(
        "",
        views.dashboard_home,
        name="home",
    ),
    path(
        "conversations/",
        views.conversation_list,
        name="conversation_list",
    ),
    path(
        "conversations/<uuid:session_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
]