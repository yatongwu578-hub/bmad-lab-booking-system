from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from equipment.services import get_equipment_detail

from .forms import ReservationForm
from .models import ReservationStatus
from .services import BEIJING, ReservationFailed, ReservationUnknown, get_reservation_result, require_applicant, submit_reservation


CONFLICT_MESSAGE = "所选时段与有效预约冲突，请选择其他时段。"
UNAVAILABLE_MESSAGE = "设备当前不可用，不能申请预约。"
INVALID_TIME_MESSAGE = "预约须为北京时间同一天的整点时段，开始必须晚于判定时间，至少一小时，且最晚 23:00 结束。"


def _render_result(request, record=None, *, created=False, error=None):
    if record is not None:
        record = dict(record, status_label=ReservationStatus(record["status"]).label,
                      start_text=record["start_at"].astimezone(BEIJING).strftime("%Y-%m-%d %H:%M"),
                      end_text=record["end_at"].astimezone(BEIJING).strftime("%Y-%m-%d %H:%M"))
    return render(request, "reservations/result.html", {"record": record, "created": created, "error": error},
                  status=503 if error else (201 if created else 200))


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
def reservation_result(request, pk):
    try:
        record = get_reservation_result(request.user, pk)
    except ReservationFailed:
        return _render_result(request, error="本次结果读取未成功，数据库事务已回滚。")
    except ReservationUnknown:
        return _render_result(request, error="结果待核查，请勿重复提交。")
    if record is None:
        raise Http404
    return _render_result(request, record)
