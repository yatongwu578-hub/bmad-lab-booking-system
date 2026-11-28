import re
from urllib.parse import unquote_to_bytes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, RequestDataTooBig
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden
from django.http.request import RawPostDataException, UnreadablePostError
from django.middleware.csrf import CSRF_SECRET_LENGTH, CSRF_TOKEN_LENGTH
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from equipment.models import EquipmentStatus
from equipment.services import get_equipment_detail

from .forms import (
    AdminReservationCancelForm, AdminReservationFilterForm, AdminReservationRejectForm,
    OccupancyDateForm, ReservationForm,
)
from .models import ReservationStatus
from .services import (
    BEIJING,
    CANCELLATION_STATUSES,
    ReservationFailed,
    ReservationUnknown,
    approve_reservation,
    can_admin_cancel,
    cancel_admin_reservation,
    cancel_own_reservation,
    get_admin_cancellation_candidate,
    get_admin_reservation,
    get_admin_reservations,
    get_cancellation_candidate,
    get_daily_occupancy,
    get_own_reservations,
    get_reservation_result,
    reject_reservation,
    require_applicant,
    require_occupancy_reader,
    require_reservation_admin,
    submit_reservation,
)


CONFLICT_MESSAGE = "所选时段与有效预约冲突，请选择其他时段。"
UNAVAILABLE_MESSAGE = "设备当前不可用，不能申请预约。"
INVALID_TIME_MESSAGE = "预约须为北京时间同一天的整点时段，开始必须晚于判定时间，至少一小时，且最晚 23:00 结束。"
READ_FAILED = "本次结果读取未成功，数据库事务已回滚。"
READ_UNKNOWN = "结果待核查，暂勿重复查询。"
READ_FORBIDDEN = "无权查询本人预约。"
RESULT_NOT_FOUND = "预约记录不存在或不可访问。"
ADMIN_FORBIDDEN = "无权查询管理员预约记录。"
APPROVAL_RESULTS = {
    "approved": (200, "预约已批准，原预约时段和占用已保留。"),
    "terminal": (409, "预约当前状态不允许批准。"),
    "expired": (409, "预约开始时间已到，不能批准。该待审核预约已失效。"),
    "unavailable": (409, "设备当前不可用，不能批准预约。"),
    "missing": (404, "预约记录不存在。"),
}
APPROVAL_FAILED = "本次批准操作未成功，数据库事务已回滚。"
APPROVAL_UNKNOWN = "批准结果待核查，请勿重复提交。可主动返回预约详情核查。"
ADMIN_CANCELLATION_RESULTS = {
    "cancelled": (200, "预约已取消，原记录已保留，占用已释放。"),
    "missing": (404, RESULT_NOT_FOUND),
    "terminal": (409, "预约当前状态不允许取消，未执行取消。"),
    "ended": (409, "已批准预约的结束时间已到，未执行取消。"),
    "expired": (409, "预约开始时间已到，该待审核预约已失效，未执行取消。"),
    "expired_reason_required": (400, "请输入取消原因。预约开始时间已到，该待审核预约已失效，未执行取消。"),
}
CANCELLATION_MESSAGES = {
    "cancelled": "预约已取消，原记录已保留。",
    "terminal": "预约当前状态不允许取消。",
    "started": "预约开始时间已到，不能取消。",
    "expired": "预约开始时间已到，不能取消。该待审核预约已失效。",
}
CANCELLATION_TOKEN_FIELD = b"csrfmiddlewaretoken"
# Each field-name/token byte may be percent-encoded, plus the literal '=' separator.
MAX_CANCELLATION_FORM_LENGTH = 3 * (len(CANCELLATION_TOKEN_FIELD) + CSRF_TOKEN_LENGTH) + 1
HISTORY_ACTION_LABELS = {"approve": "批准", "reject": "拒绝", "cancel": "取消", "expire": "失效"}
HISTORY_ACTOR_LABELS = {"system": "系统", "admin": "业务管理员", "student": "学生", "teacher": "教师",
                        "applicant": "申请人"}


def _beijing_text(value):
    local = value.astimezone(BEIJING)
    timespec = "microseconds" if local.microsecond else ("seconds" if local.second else "minutes")
    return local.replace(tzinfo=None).isoformat(sep=" ", timespec=timespec)


def _display_record(record):
    return dict(
        record,
        cancellation_candidate=record["status"] in CANCELLATION_STATUSES,
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
    displayed = [_display_record(row) for row in records]
    return render(request, "reservations/list.html", {
        "records": displayed,
        "cancellation_candidates": [row for row in displayed if row["cancellation_candidate"]],
    })


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


def _valid_cancellation_form(request):
    if request.content_type != "application/x-www-form-urlencoded":
        return False
    declared_length = request.META.get("CONTENT_LENGTH") or ""
    if not re.fullmatch(r"[0-9]{1,3}", declared_length):
        return False
    length = int(declared_length)
    if not 0 < length <= MAX_CANCELLATION_FORM_LENGTH:
        return False
    try:
        body = request.body
    except (RawPostDataException, UnreadablePostError, RequestDataTooBig):
        return False
    if len(body) != length or re.search(rb"%(?![0-9A-Fa-f]{2})", body):
        return False
    name, separator, value = body.partition(b"=")
    if not separator or unquote_to_bytes(name) != CANCELLATION_TOKEN_FIELD:
        return False
    token = unquote_to_bytes(value)
    # The view checks form shape. Django CSRF still authenticates the token.
    return len(token) in (CSRF_SECRET_LENGTH, CSRF_TOKEN_LENGTH) and re.fullmatch(rb"[A-Za-z0-9]+", token) is not None


@never_cache
@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def reservation_cancel(request, pk):
    template = "reservations/cancel.html"
    if request.GET or (request.method == "POST" and not _valid_cancellation_form(request)):
        return HttpResponseBadRequest("取消预约请求格式无效。")
    try:
        if request.method == "GET":
            record = get_cancellation_candidate(request.user, pk)
            if record is not None:
                return render(request, template, {"record": _display_record(record), "confirmation": True})
        else:
            outcome = cancel_own_reservation(request.user, pk)
            if outcome.record is not None:
                success = outcome.outcome == "cancelled"
                return render(request, template, {
                    "record": _display_record(outcome.record),
                    "message": CANCELLATION_MESSAGES[outcome.outcome],
                    "cancelled": success,
                }, status=200 if success else 409)
    except PermissionDenied:
        return HttpResponseForbidden("无权取消本人预约。")
    except ReservationFailed:
        message = ("无法读取取消确认信息，预约未更改。" if request.method == "GET"
                   else "本次取消未成功，数据库事务已回滚。")
        return render(request, template, {"error": message}, status=503)
    except ReservationUnknown:
        return render(request, template, {"error": "取消结果待核查，请勿重复提交。"}, status=503)
    return render(request, template, {"error": RESULT_NOT_FOUND}, status=404)


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


def _filter_query(number):
    return "?" + urlencode({"equipment": number}) if number is not None else ""


def _admin_cancel_link(row, filter_query, at):
    if can_admin_cancel(row, at):
        return reverse("admin-reservation-cancel", args=[row["id"]]) + filter_query
    return None


def _display_history(entries):
    status_labels = dict(ReservationStatus.choices)
    return [dict(
        entry,
        action_label=HISTORY_ACTION_LABELS.get(entry["action"], entry["action"]),
        actor_label=HISTORY_ACTOR_LABELS.get(entry["actor_type"], entry["actor_type"]),
        before_label=status_labels.get(entry["before_status"], entry["before_status"]),
        after_label=status_labels.get(entry["after_status"], entry["after_status"]),
        decision_text=_beijing_text(entry["decision_at"]),
        recorded_text=_beijing_text(entry["recorded_at"]),
    ) for entry in entries]


@never_cache
@require_GET
@login_required
def admin_reservation_list(request):
    template = "reservations/admin_list.html"
    form = AdminReservationFilterForm(request.GET)
    context = {"form": form}
    try:
        require_reservation_admin(request.user)
        if not form.is_valid():
            return render(request, template, context, status=400)
        number = form.cleaned_data["equipment"]
        records = get_admin_reservations(request.user, number)
    except PermissionDenied:
        return HttpResponseForbidden(ADMIN_FORBIDDEN)
    except ReservationFailed:
        return render(request, template, {**context, "error": READ_FAILED}, status=503)
    except ReservationUnknown:
        return render(request, template, {**context, "error": READ_UNKNOWN}, status=503)
    # UI hints use server time and never affect the existing read transaction or a later POST.
    at, filter_query = timezone.now(), _filter_query(number)
    return render(request, template, {
        **context, "equipment_number": number, "filter_query": filter_query,
        "records": [dict(_display_record(row), cancel_url=_admin_cancel_link(row, filter_query, at)) for row in records],
    })


@never_cache
@require_GET
@login_required
def admin_reservation_detail(request, pk):
    template = "reservations/admin_detail.html"
    form = AdminReservationFilterForm(request.GET)
    try:
        require_reservation_admin(request.user)
        back_url = reverse("admin-reservation-list")
        if not form.is_valid():
            return render(request, template, {"back_url": back_url, "error": "设备编号参数无效。"}, status=400)
        filter_query = _filter_query(form.cleaned_data["equipment"])
        back_url += filter_query
        record = get_admin_reservation(request.user, pk)
    except PermissionDenied:
        return HttpResponseForbidden(ADMIN_FORBIDDEN)
    except ReservationFailed:
        return render(request, template, {"back_url": back_url, "error": READ_FAILED}, status=503)
    except ReservationUnknown:
        return render(request, template, {"back_url": back_url, "error": READ_UNKNOWN}, status=503)
    if record is None:
        return render(request, template, {"back_url": back_url, "error": RESULT_NOT_FOUND}, status=404)
    context = {
        "back_url": back_url, "record": _display_record(record), "history": _display_history(record["history"]),
        "cancel_url": _admin_cancel_link(record, filter_query, timezone.now()),
        "approval_candidate": (record["status"] == ReservationStatus.PENDING
                               and record["equipment__status"] == EquipmentStatus.AVAILABLE),
    }
    if record["status"] == ReservationStatus.PENDING:
        context.update(
            reject_form=AdminReservationRejectForm(),
            reject_url=reverse("admin-reservation-reject", args=[pk]) + filter_query,
        )
    return render(request, template, context)


@never_cache
@require_POST
@login_required
@csrf_protect
def admin_reservation_approve(request, pk):
    detail_url = reverse("admin-reservation-detail", args=[pk])
    try:
        outcome = approve_reservation(request.user, pk)
    except PermissionDenied:
        return HttpResponseForbidden("无权批准预约。")
    except ReservationFailed:
        status, message = 503, APPROVAL_FAILED
    except ReservationUnknown:
        status, message = 503, APPROVAL_UNKNOWN
    else:
        status, message = APPROVAL_RESULTS[outcome]
        if outcome == "missing":
            detail_url = None
    return render(request, "reservations/admin_approval_result.html", {
        "detail_url": detail_url, "message": message, "approved": status == 200,
    }, status=status)


@never_cache
@require_POST
@login_required
@csrf_protect
def admin_reservation_reject(request, pk):
    template = "reservations/admin_reject.html"
    context = {"back_url": reverse("admin-reservation-detail", args=[pk])}
    try:
        require_reservation_admin(request.user)
        filter_form = AdminReservationFilterForm(request.GET)
        if not filter_form.is_valid():
            return render(request, template, {**context, "error": "设备编号参数无效。"}, status=400)
        filter_query = _filter_query(filter_form.cleaned_data["equipment"])
        context["back_url"] += filter_query
        if request.content_type not in {"application/x-www-form-urlencoded", "multipart/form-data"}:
            return render(request, template, {**context, "error": "拒绝预约请求格式无效。"}, status=400)
        form = AdminReservationRejectForm(request.POST, request.FILES)
        outcome = "invalid_form"
        if form.is_valid():
            outcome = reject_reservation(request.user, pk, form.cleaned_data["reason"])
    except PermissionDenied:
        return HttpResponseForbidden("无权拒绝预约。")
    except ReservationFailed:
        return render(request, template, {**context, "error": "本次拒绝未成功，数据库事务已回滚。"}, status=503)
    except ReservationUnknown:
        return render(request, template, {**context, "error": "拒绝结果待核查，请勿重复提交。"}, status=503)
    if outcome in ("invalid_form", "reason_required"):
        if outcome == "reason_required":
            form.add_error("reason", form.fields["reason"].error_messages["required"])
        return render(request, template, {
            **context, "reject_form": form,
            "reject_url": reverse("admin-reservation-reject", args=[pk]) + filter_query,
        }, status=400)
    if outcome == "rejected":
        return redirect(context["back_url"])
    status, error = {
        "missing": (404, RESULT_NOT_FOUND),
        "terminal": (409, "只有待审核的预约可以拒绝。"),
        "expired": (409, "预约开始时间已到，该待审核预约已失效，未执行拒绝。"),
    }[outcome]
    return render(request, template, {**context, "error": error}, status=status)


def _valid_admin_cancel_query(request):
    # WSGI represents the original query bytes as ISO-8859-1 text. Validate those
    # bytes before QueryDict can preserve bad escapes or replace invalid UTF-8.
    try:
        raw = request.META.get("QUERY_STRING", "").encode("iso-8859-1")
        if re.search(rb"%(?![0-9A-Fa-f]{2})", raw):
            return False
        unquote_to_bytes(raw).decode("utf-8")
    except UnicodeError:
        return False
    return True


def _admin_cancel_form(request):
    # The confirmation page uses the native URL-encoded form. Do not let a parser's
    # recovery from invalid syntax turn a malformed request into a blank reason.
    if request.content_type != "application/x-www-form-urlencoded":
        return None
    try:
        body = request.body
        if re.search(rb"%(?![0-9A-Fa-f]{2})", body):
            return None
        for field in body.split(b"&") if body else ():
            name, separator, value = field.partition(b"=")
            if not name or not separator:
                return None
            unquote_to_bytes(name).decode("utf-8")
            unquote_to_bytes(value).decode("utf-8")
        return AdminReservationCancelForm(request.POST)
    except (RawPostDataException, UnreadablePostError, RequestDataTooBig, UnicodeError):
        return None


@never_cache
@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def admin_reservation_cancel(request, pk):
    template = "reservations/admin_cancel.html"
    context = {"back_url": reverse("admin-reservation-list")}
    try:
        require_reservation_admin(request.user)
        if not _valid_admin_cancel_query(request):
            return render(request, template, {**context, "error": "设备编号参数无效。"}, status=400)
        filter_form = AdminReservationFilterForm(request.GET)
        if not filter_form.is_valid():
            return render(request, template, {**context, "error": "设备编号参数无效。"}, status=400)
        filter_query = _filter_query(filter_form.cleaned_data["equipment"])
        context["back_url"] += filter_query
        detail_url = reverse("admin-reservation-detail", args=[pk]) + filter_query
        cancel_url = reverse("admin-reservation-cancel", args=[pk]) + filter_query
        if request.method == "GET":
            record = get_admin_cancellation_candidate(request.user, pk)
            if record is None:
                return render(request, template, {**context, "error": RESULT_NOT_FOUND}, status=404)
            context.update(record=_display_record(record), detail_url=detail_url)
            if can_admin_cancel(record, timezone.now()):
                context.update(form=AdminReservationCancelForm(), cancel_url=cancel_url)
                return render(request, template, context)
            return render(request, template, {
                **context, "error": "预约当前状态或时间不允许取消。",
            }, status=409)

        form = _admin_cancel_form(request)
        if form is None or not form.is_valid():
            # Malformed submissions are rejected without a target lookup or any FR-018 write.
            return render(request, template, {**context, "error": "取消预约请求格式无效。"}, status=400)
        reason = form.cleaned_data["reason"]
        result = cancel_admin_reservation(request.user, pk, reason)
    except PermissionDenied:
        return HttpResponseForbidden("无权取消管理员预约记录。")
    except ReservationFailed:
        error = ("无法读取取消确认信息，预约未更改。" if request.method == "GET"
                 else "本次取消未成功，数据库事务已回滚。")
        return render(request, template, {**context, "error": error}, status=503)
    except ReservationUnknown:
        return render(request, template, {
            **context, "error": "取消结果待核查，请勿重复提交。",
        }, status=503)

    if result.record is not None:
        context.update(record=_display_record(result.record), detail_url=detail_url)
    if result.outcome == "reason_required":
        form.add_error("reason", form.fields["reason"].error_messages["required"])
        return render(request, template, {**context, "form": form, "cancel_url": cancel_url}, status=400)
    status, message = ADMIN_CANCELLATION_RESULTS[result.outcome]
    if not reason and result.outcome in {"terminal", "ended"}:
        message = form.fields["reason"].error_messages["required"] + message
    return render(request, template, {
        **context, "message" if status == 200 else "error": message,
    }, status=status)
