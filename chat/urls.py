from django.urls import path
from .views import register_view, login_view

urlpatterns = [
    path("api/register/", register_view, name="register"),
    path("api/login/", login_view, name="login"),
]
