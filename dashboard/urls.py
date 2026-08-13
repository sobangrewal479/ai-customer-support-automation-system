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
    path(
        "unanswered-questions/",
        views.unanswered_question_list,
        name="unanswered_question_list",
    ),
    path(
        "leads/",
        views.lead_list,
        name="lead_list",
    ),
    path(
        "human-support-requests/",
        views.handoff_request_list,
        name="handoff_request_list",
    ),
    path(
        "order-activity/",
        views.order_activity_list,
        name="order_activity_list",
    ),
    path(
        "products/",
        views.product_list,
        name="product_list",
    ),
]