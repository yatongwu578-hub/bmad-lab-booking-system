from django.contrib.auth.views import LoginView
from django.urls import path

from accounts.forms import AccountAuthenticationForm
from accounts.views import AccountLogoutView, identity
from equipment.urls import urlpatterns as equipment_urlpatterns
from reservations.urls import urlpatterns as reservation_urlpatterns


urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=AccountAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", AccountLogoutView.as_view(), name="logout"),
    path("identity/", identity, name="identity"),
] + equipment_urlpatterns + reservation_urlpatterns
