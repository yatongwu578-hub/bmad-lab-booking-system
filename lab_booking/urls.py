from django.contrib.auth.views import LoginView
from django.urls import path

from accounts.views import identity


urlpatterns = [
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("identity/", identity, name="identity"),
]
