import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied
from django.db import Error, transaction
from django.db.models import Q

from accounts.models import Role, User
from accounts.policies import RESERVATION_ROLES, can_reserve
from audit.services import append_reservation_expiry
from equipment.models import Equipment, EquipmentStatus
from equipment.services import get_equipment_detail, lock_equipment
from lab_booking.transactions import transaction_rejected

from .models import Reservation, ReservationStatus


BEIJING = ZoneInfo("Asia/Shanghai")
LOCAL_INPUT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?")
# Unlike a lost connection or SQLSTATE 40003, these server responses confirm rejection.
COMMIT_CANCELLATION_STATES = {"55P03", "57014"}
RESULT_FIELDS = ("id", "equipment_id", "equipment__number", "equipment__name", "start_at", "end_at", "status")


class ReservationFailed(Exception):
    pass


class ReservationUnknown(Exception):
    pass


@dataclass(frozen=True)
class Submission:
    outcome: str
    record: dict | None = None
    equipment: dict | None = None


@dataclass(frozen=True)
class OccupancyInterval:
    start_at: datetime
    end_at: datetime
    category: str


@dataclass(frozen=True)
class DailyOccupancy:
    equipment: dict
    decision_at: datetime
    occupied: tuple[OccupancyInterval, ...]
    historical: tuple[OccupancyInterval, ...]
    unoccupied: tuple[OccupancyInterval, ...]


def require_occupancy_reader(user):
    if not user.is_authenticated or not user.is_active or user.role not in Role.values:
        raise PermissionDenied


def _recheck_occupancy_reader(pk):
    row = User.objects.filter(pk=pk).values_list("is_active", "role").first()
    if row is None or not row[0] or row[1] not in Role.values:
        raise PermissionDenied


def require_applicant(user):
    if not can_reserve(user):
        raise PermissionDenied


def _recheck_applicant(pk):
    row = User.objects.filter(pk=pk).values_list("is_active", "role").first()
    if row is None or not row[0] or row[1] not in RESERVATION_ROLES:
        raise PermissionDenied


def _decision_time(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT clock_timestamp() AS decision_at")
        return cursor.fetchone()[0]


def _parse_local(value):
    if not isinstance(value, str) or not LOCAL_INPUT.fullmatch(value):
        raise ValueError
    return datetime.fromisoformat(value).replace(tzinfo=BEIJING)


def valid_window(raw_start, raw_end, decision_at):
    try:
        start, end = _parse_local(raw_start), _parse_local(raw_end)
        if (start.date() == end.date() and start > decision_at
                and not any((start.minute, start.second, start.microsecond, end.minute, end.second, end.microsecond))
                and end - start >= timedelta(hours=1) and end.time() <= time(23)):
            return start, end
    except (ValueError, OverflowError):
        pass
    return None


def _expire(queryset, decision_at):
    due = queryset.filter(status=ReservationStatus.PENDING, start_at__lte=decision_at)
    expired = list(due.order_by("pk").values_list("pk", flat=True))
    for pk in expired:
        if due.filter(pk=pk).update(status=ReservationStatus.EXPIRED) != 1:
            raise ReservationFailed
        append_reservation_expiry(pk, decision_at)
    return expired


def _durable_operation(operation):
    connection = transaction.get_connection()
    ready_to_commit = False
    try:
        if not connection.in_atomic_block and not connection.get_autocommit():
            raise RuntimeError("预约操作要求由服务管理最外层事务。")
        with transaction.atomic(durable=True):
            result = operation(connection)
            if connection.closed_in_transaction or transaction.get_rollback():
                raise ReservationFailed
            ready_to_commit = True
    except Error as error:
        if ready_to_commit and not transaction_rejected(error, additional_sqlstates=COMMIT_CANCELLATION_STATES):
            raise ReservationUnknown from None
        raise ReservationFailed from None
    return result


def submit_reservation(user, equipment_pk, raw_start, raw_end):
    require_applicant(user)

    def submit(connection):
        if lock_equipment(equipment_pk) is None:
            return Submission("missing")
        equipment = Equipment.objects.values("number", "name", "status").get(pk=equipment_pk)
        _recheck_applicant(user.pk)
        decision_at = _decision_time(connection)
        reservations = Reservation.objects.filter(equipment_id=equipment_pk)
        _expire(reservations, decision_at)
        if equipment["status"] != EquipmentStatus.AVAILABLE:
            return Submission("unavailable", equipment=equipment)
        window = valid_window(raw_start, raw_end, decision_at)
        if window is None:
            return Submission("invalid_time", equipment=equipment)
        start, end = window
        effective = Q(status=ReservationStatus.APPROVED) | Q(status=ReservationStatus.PENDING, start_at__gt=decision_at)
        if reservations.filter(effective, start_at__lt=end, end_at__gt=start).exists():
            return Submission("conflict", equipment=equipment)
        created = reservations.create(applicant_id=user.pk, equipment_id=equipment_pk,
                                      start_at=start, end_at=end, applied_at=decision_at)
        return Submission("created", {
            "id": created.pk, "equipment_id": equipment_pk, "equipment__number": equipment["number"],
            "equipment__name": equipment["name"], "start_at": start, "end_at": end, "status": created.status,
        })

    return _durable_operation(submit)


def get_reservation_result(user, pk):
    require_applicant(user)
    owned = Reservation.objects.filter(pk=pk, applicant_id=user.pk)

    def read(connection):
        candidate = owned.values(*RESULT_FIELDS).first()
        if candidate is None or candidate["status"] != ReservationStatus.PENDING:
            return candidate
        equipment_id = candidate["equipment_id"]
        if lock_equipment(equipment_id) is None:
            return None
        _recheck_applicant(user.pk)
        fixed = owned.filter(equipment_id=equipment_id)
        current = fixed.values(*RESULT_FIELDS).first()
        if current is None or current["status"] != ReservationStatus.PENDING:
            return current
        decision_at = _decision_time(connection)
        if _expire(fixed, decision_at):
            current["status"] = ReservationStatus.EXPIRED
        return current

    return _durable_operation(read)


def _project_daily_occupancy(equipment, day_start, day_end, decision_at, rows):
    occupied, historical = [], []
    for start_at, end_at, status in rows:
        if status == ReservationStatus.APPROVED:
            category = ("historical" if end_at <= decision_at else
                        "in_progress" if start_at <= decision_at else "approved_future")
        elif status == ReservationStatus.PENDING and start_at > decision_at:
            category = "pending"
        else:
            continue
        interval = OccupancyInterval(max(start_at, day_start), min(end_at, day_end), category)
        (historical if category == "historical" else occupied).append(interval)

    unoccupied = []
    covered_until = day_start
    # Take the complement of today's occupied and historical intervals, including overlaps.
    for interval in sorted((*occupied, *historical), key=lambda item: item.start_at):
        if covered_until < interval.start_at:
            unoccupied.append(OccupancyInterval(covered_until, interval.start_at, "unoccupied"))
        covered_until = max(covered_until, interval.end_at)
    if covered_until < day_end:
        unoccupied.append(OccupancyInterval(covered_until, day_end, "unoccupied"))
    return DailyOccupancy(
        {key: equipment[key] for key in ("number", "name", "status_label")},
        decision_at, tuple(occupied), tuple(historical), tuple(unoccupied),
    )


def get_daily_occupancy(user, equipment_pk, day):
    require_occupancy_reader(user)
    day_start = datetime.combine(day, time.min, BEIJING).astimezone(UTC)
    day_end = datetime.combine(day + timedelta(days=1), time.min, BEIJING).astimezone(UTC)

    def read(connection):
        if not Equipment.objects.filter(pk=equipment_pk).exists():
            return None
        scoped = Reservation.objects.filter(equipment_id=equipment_pk, start_at__lt=day_end, end_at__gt=day_start)
        # Freeze scope before locking, including any pending row that has already ended.
        candidates = list(scoped.values_list("pk", "status"))
        has_pending = any(status == ReservationStatus.PENDING for _, status in candidates)
        if has_pending and lock_equipment(equipment_pk) is None:
            return None

        # Recheck the account and read current rows independently of the lock statement.
        _recheck_occupancy_reader(user.pk)
        equipment = get_equipment_detail(user, equipment_pk)
        if equipment is None:
            return None
        fixed = scoped.filter(pk__in=[pk for pk, _ in candidates])
        rows = list(fixed.order_by("start_at", "end_at", "pk").values_list("start_at", "end_at", "status"))
        decision_at = _decision_time(connection)
        if has_pending:
            _expire(fixed, decision_at)
        return _project_daily_occupancy(equipment, day_start, day_end, decision_at, rows)

    return _durable_operation(read)
