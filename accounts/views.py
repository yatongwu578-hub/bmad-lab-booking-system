from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .models import Role


@never_cache
@require_safe
@login_required
def identity(request):
    user = request.user
    if not user.is_active or user.role not in Role.values:
        raise PermissionDenied
    return render(request, "accounts/identity.html", {"account": user})
