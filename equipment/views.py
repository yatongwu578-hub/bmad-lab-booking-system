from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from accounts.models import Role

from .forms import EquipmentCreateForm
from .models import EquipmentStatus
from .services import (
    EquipmentCreationFailed,
    EquipmentCreationUnknown,
    EquipmentNumberConflict,
    create_equipment,
    get_equipment_detail,
    list_equipment,
)


@never_cache
@require_safe
@login_required
def equipment_catalog(request):
    try:
        equipment_items = list_equipment(request.user)
    except PermissionDenied:
        return HttpResponseForbidden("无权查看设备资料。")
    return render(
        request,
        "equipment/catalog.html",
        {"account": request.user, "equipment_items": equipment_items},
    )


@never_cache
@require_safe
@login_required
def equipment_detail(request, pk):
    try:
        equipment = get_equipment_detail(request.user, pk)
    except PermissionDenied:
        return HttpResponseForbidden("无权查看设备资料。")
    if equipment is None:
        return render(request, "equipment/not_found.html", {"account": request.user}, status=404)
    return render(
        request,
        "equipment/detail.html",
        {"account": request.user, "equipment": equipment},
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
