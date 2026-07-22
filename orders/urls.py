from django.urls import path

from orders import views


app_name = "orders"

urlpatterns = [
    path("", views.order_lookup, name="lookup"),
]