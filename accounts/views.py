from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .models import Role


class AccountLogoutView(LogoutView):
    def get_success_url(self):
        return reverse("login")


@never_cache
@require_safe
@login_required
def identity(request):
    user = request.user
    if not user.is_active or user.role not in Role.values:
        raise PermissionDenied
    return render(request, "accounts/identity.html", {"account": user})
