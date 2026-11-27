from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from equipment.models import EquipmentStatus
from equipment.services import get_equipment_detail

from .forms import OccupancyDateForm, ReservationForm
from .models import ReservationStatus
from .services import (
    BEIJING,
    ReservationFailed,
    ReservationUnknown,
    get_daily_occupancy,
    get_own_reservations,
    get_reservation_result,
    require_applicant,
    require_occupancy_reader,
    submit_reservation,
)


CONFLICT_MESSAGE = "所选时段与有效预约冲突，请选择其他时段。"
UNAVAILABLE_MESSAGE = "设备当前不可用，不能申请预约。"
INVALID_TIME_MESSAGE = "预约须为北京时间同一天的整点时段，开始必须晚于判定时间，至少一小时，且最晚 23:00 结束。"
READ_FAILED = "本次结果读取未成功，数据库事务已回滚。"
READ_UNKNOWN = "结果待核查，暂勿重复查询。"
READ_FORBIDDEN = "无权查询本人预约。"
RESULT_NOT_FOUND = "预约记录不存在或不可访问。"


def _beijing_text(value):
    local = value.astimezone(BEIJING)
    timespec = "microseconds" if local.microsecond else ("seconds" if local.second else "minutes")
    return local.replace(tzinfo=None).isoformat(sep=" ", timespec=timespec)


def _display_record(record):
    return dict(
        record,
        status_label=ReservationStatus(record["status"]).label,
        equipment_status_label=(EquipmentStatus(record["equipment__status"]).label
                                if "equipment__status" in record else None),
        date_text=record["start_at"].astimezone(BEIJING).date().isoformat(),
        start_text=_beijing_text(record["start_at"]),
        end_text=_beijing_text(record["end_at"]),
    )


def _render_result(request, record=None, *, created=False, error=None, status=None):
    return render(
        request, "reservations/result.html",
        {"record": _display_record(record) if record is not None else None, "created": created, "error": error},
        status=status if status is not None else (503 if error else (201 if created else 200)),
    )


@never_cache
@require_http_methods(["GET", "POST"])
@login_required
def reserve_equipment(request, pk):
    require_applicant(request.user)
    form = ReservationForm(request.POST if request.method == "POST" else None)
    status = 200
    message = None
    if request.method == "POST":
        try:
            # Do not short-circuit an authorized invalid POST before device-scoped expiry.
            outcome = submit_reservation(request.user, pk, request.POST.get("start_at"), request.POST.get("end_at"))
        except ReservationFailed:
            return _render_result(request, error="本次申请未成功，数据库事务已回滚。")
        except ReservationUnknown:
            return _render_result(request, error="结果待核查，请勿重复提交。")
        if outcome.outcome == "created":
            return _render_result(request, outcome.record, created=True)
        if outcome.outcome == "missing":
            raise Http404
        status, message = {
            "invalid_time": (400, INVALID_TIME_MESSAGE),
            "unavailable": (409, UNAVAILABLE_MESSAGE),
            "conflict": (409, CONFLICT_MESSAGE),
        }[outcome.outcome]
        equipment = outcome.equipment
    else:
        equipment = get_equipment_detail(request.user, pk)
        if equipment is None:
            raise Http404
    return render(request, "reservations/form.html", {"form": form, "equipment": equipment, "message": message}, status=status)


@never_cache
@require_GET
@login_required
def reservation_list(request):
    try:
        records = get_own_reservations(request.user)
    except PermissionDenied:
        return HttpResponseForbidden(READ_FORBIDDEN)
    except ReservationFailed:
        return render(request, "reservations/list.html", {"error": READ_FAILED}, status=503)
    except ReservationUnknown:
        return render(request, "reservations/list.html", {"error": READ_UNKNOWN}, status=503)
    return render(request, "reservations/list.html", {"records": [_display_record(row) for row in records]})


@never_cache
@require_GET
@login_required
def reservation_result(request, pk):
    try:
        record = get_reservation_result(request.user, pk)
    except PermissionDenied:
        return HttpResponseForbidden(READ_FORBIDDEN)
    except ReservationFailed:
        return _render_result(request, error=READ_FAILED)
    except ReservationUnknown:
        return _render_result(request, error=READ_UNKNOWN)
    if record is None:
        return _render_result(request, error=RESULT_NOT_FOUND, status=404)
    return _render_result(request, record)


@never_cache
@require_GET
@login_required
def equipment_occupancy(request, pk):
    try:
        require_occupancy_reader(request.user)
        form = OccupancyDateForm(request.GET)
        context = {"form": form, "equipment_pk": pk}
        if not form.is_valid():
            return render(request, "reservations/occupancy.html", context, status=400)
        day = form.cleaned_data["date"]
        result = get_daily_occupancy(request.user, pk, day)
    except PermissionDenied:
        return HttpResponseForbidden("无权查询设备占用。")
    except ReservationFailed:
        return render(request, "reservations/occupancy.html",
                      {"error": "本次占用查询未成功，数据库事务已回滚。"}, status=503)
    except ReservationUnknown:
        return render(request, "reservations/occupancy.html",
                      {"error": "本次占用查询结果待核查，暂勿重复查询。"}, status=503)
    if result is None:
        return render(request, "reservations/occupancy.html", {"error": "设备不存在。"}, status=404)
    return render(request, "reservations/occupancy.html", {**context, "day": day, "result": result})
