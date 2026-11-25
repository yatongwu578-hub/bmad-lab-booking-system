from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from accounts.models import Role

from .forms import EquipmentCreateForm
from .models import EquipmentStatus
from .services import (
    EquipmentCreationFailed,
    EquipmentCreationUnknown,
    EquipmentNumberConflict,
    create_equipment,
)


def require_equipment_admin(user):
    if not user.is_active or user.role != Role.ADMIN:
        raise PermissionDenied


@never_cache
@require_http_methods(["GET", "POST"])
@login_required
def create_equipment_view(request):
    require_equipment_admin(request.user)
    form = EquipmentCreateForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            equipment = create_equipment(request.user, form.cleaned_data)
        except EquipmentNumberConflict:
            form.add_error("number", "该设备编号已存在。")
        except EquipmentCreationUnknown:
            return render(request, "equipment/create_result.html", {"unknown": True}, status=503)
        except EquipmentCreationFailed:
            return render(request, "equipment/create_result.html", {"failed": True}, status=503)
        else:
            return render(request, "equipment/create_result.html", {"equipment": equipment}, status=201)
    return render(
        request,
        "equipment/create_form.html",
        {"form": form, "initial_status": EquipmentStatus.AVAILABLE.label},
    )
