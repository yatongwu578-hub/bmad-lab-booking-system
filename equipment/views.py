from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from accounts.policies import can_reserve

from .forms import EquipmentCreateForm, EquipmentEditForm
from .models import EquipmentStatus
from .services import (
    EquipmentCreationFailed,
    EquipmentCreationUnknown,
    EquipmentEditFailed,
    EquipmentEditUnknown,
    EquipmentNumberConflict,
    create_equipment,
    edit_equipment,
    get_equipment_detail,
    is_equipment_admin,
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
        {
            "account": request.user, "equipment": equipment,
            "edit_pk": pk if is_equipment_admin(request.user) else None,
            "reserve_pk": pk if can_reserve(request.user) else None,
        },
    )


def require_equipment_admin(user):
    if not is_equipment_admin(user):
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


@never_cache
@require_http_methods(["GET", "POST"])
@login_required
def edit_equipment_view(request, pk):
    require_equipment_admin(request.user)
    context = {"account": request.user, "equipment_pk": pk}
    if request.method == "POST":
        form = EquipmentEditForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                saved = edit_equipment(request.user, pk, form.cleaned_data)
            except EquipmentEditUnknown:
                return render(request, "equipment/edit_result.html", {**context, "unknown": True}, status=503)
            except EquipmentEditFailed:
                return render(request, "equipment/edit_result.html", context, status=503)
            if saved:
                return redirect("equipment-detail", pk=pk)
            return render(request, "equipment/not_found.html", context, status=404)

    equipment = get_equipment_detail(request.user, pk)
    if equipment is None:
        return render(request, "equipment/not_found.html", context, status=404)
    if request.method == "GET":
        form = EquipmentEditForm(initial=equipment)
    return render(
        request,
        "equipment/edit_form.html",
        {**context, "form": form, "equipment": equipment},
        status=200 if request.method == "GET" else 400,
    )
