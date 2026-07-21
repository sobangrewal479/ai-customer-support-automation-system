from django.urls import path

from support_chat import views


app_name = "support_chat"

urlpatterns = [
    path("", views.chat_page, name="chat"),
]