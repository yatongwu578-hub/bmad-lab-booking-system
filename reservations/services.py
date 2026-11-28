import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied
from django.db import Error, transaction
from django.db.models import Q

from accounts.models import Role, User
from accounts.policies import RESERVATION_ROLES, can_reserve, is_business_admin
from audit.services import (
    append_reservation_cancellation,
    append_reservation_expiry,
    read_admin_reservation_reasons,
    read_reservation_history,
    read_reservation_reasons,
)
from equipment.models import Equipment, EquipmentStatus
from equipment.services import get_equipment_detail, lock_equipment
from lab_booking.transactions import transaction_rejected

from .models import Reservation, ReservationStatus


BEIJING = ZoneInfo("Asia/Shanghai")
LOCAL_INPUT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?")
# Unlike a lost connection or SQLSTATE 40003, these server responses confirm rejection.
COMMIT_CANCELLATION_STATES = {"55P03", "57014"}
RESULT_FIELDS = (
    "id", "equipment_id", "equipment__number", "equipment__name", "equipment__status",
    "start_at", "end_at", "status",
)
CANCELLATION_STATUSES = frozenset({ReservationStatus.PENDING, ReservationStatus.APPROVED})


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
class Cancellation:
    outcome: str
    record: dict | None = None


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


def _read_own_reservations(user, pk=None):
    require_applicant(user)
    owned = Reservation.objects.filter(applicant_id=user.pk)
    if pk is not None:
        owned = owned.filter(pk=pk)

    def read(connection):
        # Freeze authorized IDs and their pending-device scope before taking any locks.
        candidates = list(owned.values_list("pk", "equipment_id", "status"))
        pending = {row_id: equipment_id for row_id, equipment_id, status in candidates
                   if status == ReservationStatus.PENDING}
        locked = {equipment_id for equipment_id in sorted(set(pending.values()))
                  if lock_equipment(equipment_id) is not None}

        _recheck_applicant(user.pk)
        fixed = owned.filter(pk__in=[row_id for row_id, _, _ in candidates])
        rows = list(fixed.order_by("-start_at", "-pk").values(*RESULT_FIELDS))
        if pending:
            decision_at = _decision_time(connection)
            # Do not expire a row whose device was not locked or which fell out of scope.
            eligible = [row["id"] for row in rows
                        if row["status"] == ReservationStatus.PENDING
                        and row["equipment_id"] in locked
                        and pending.get(row["id"]) == row["equipment_id"]]
            if eligible:
                expired = set(_expire(fixed.filter(pk__in=eligible), decision_at))
                for row in rows:
                    if row["id"] in expired:
                        row["status"] = ReservationStatus.EXPIRED

        reasons = read_reservation_reasons(
            connection,
            [row["id"] for row in rows if row["status"] == ReservationStatus.REJECTED],
            [row["id"] for row in rows if row["status"] == ReservationStatus.CANCELLED],
        )
        for row in rows:
            row["reason"] = reasons.get(row["id"])
        return rows

    return _durable_operation(read)


def get_own_reservations(user):
    return _read_own_reservations(user)


def get_reservation_result(user, pk):
    if pk is None:
        require_applicant(user)
        return None
    rows = _read_own_reservations(user, pk)
    return rows[0] if rows else None


def get_cancellation_candidate(user, pk):
    """Read an owned confirmation projection without taking locks or expiring rows."""
    require_applicant(user)
    try:
        _recheck_applicant(user.pk)
        return Reservation.objects.filter(pk=pk, applicant_id=user.pk).values(*RESULT_FIELDS).first()
    except Error:
        raise ReservationFailed from None


def cancel_own_reservation(user, pk):
    require_applicant(user)
    owned = Reservation.objects.filter(pk=pk, applicant_id=user.pk)
    try:
        _recheck_applicant(user.pk)
        equipment_id = owned.values_list("equipment_id", flat=True).first()
    except Error:
        raise ReservationFailed from None
    if equipment_id is None:
        return Cancellation("missing")

    def cancel(connection):
        if lock_equipment(equipment_id) is None:
            return Cancellation("missing")
        _recheck_applicant(user.pk)
        target = owned.filter(equipment_id=equipment_id)
        row = target.values(*RESULT_FIELDS).first()
        if row is None:
            return Cancellation("missing")
        decision_at = _decision_time(connection)
        before_status = row["status"]
        if before_status not in CANCELLATION_STATUSES:
            return Cancellation("terminal", row)
        if decision_at >= row["start_at"]:
            if before_status == ReservationStatus.PENDING:
                if _expire(target, decision_at) != [row["id"]]:
                    raise ReservationFailed
                row["status"] = ReservationStatus.EXPIRED
                # Business rejection is returned normally so expiry and its audit can commit.
                return Cancellation("expired", row)
            return Cancellation("started", row)
        if target.filter(status=before_status).update(status=ReservationStatus.CANCELLED) != 1:
            raise ReservationFailed
        append_reservation_cancellation(row["id"], user.pk, before_status, decision_at)
        row["status"] = ReservationStatus.CANCELLED
        return Cancellation("cancelled", row)

    return _durable_operation(cancel)


def require_reservation_admin(user):
    if not is_business_admin(user):
        raise PermissionDenied


def _recheck_reservation_admin(pk):
    account = User.objects.filter(pk=pk).values_list("is_active", "role").first()
    if account != (True, Role.ADMIN):
        raise PermissionDenied


def _read_admin_reservations(user, *, equipment_number=None, pk=None):
    require_reservation_admin(user)

    def read(connection):
        _recheck_reservation_admin(user.pk)
        scoped = Reservation.objects.all()
        if equipment_number is not None:
            equipment_id = Equipment.objects.filter(number=equipment_number).values_list("pk", flat=True).first()
            if equipment_id is None:
                return []
            scoped = scoped.filter(equipment_id=equipment_id)
        if pk is not None:
            scoped = scoped.filter(pk=pk)

        # Freeze only the authorized candidates, including pending rows that have ended.
        candidates = list(scoped.values_list("pk", "equipment_id", "status"))
        pending = {row_id: device for row_id, device, status in candidates if status == ReservationStatus.PENDING}
        locked = {device for device in sorted(set(pending.values())) if lock_equipment(device) is not None}

        _recheck_reservation_admin(user.pk)
        fixed = scoped.filter(pk__in=[row_id for row_id, _, _ in candidates])
        rows = list(fixed.order_by("-start_at", "-pk").values(*RESULT_FIELDS, "applicant__username"))
        if pending or equipment_number is not None:
            decision_at = _decision_time(connection)
            eligible = [row["id"] for row in rows
                        if row["status"] == ReservationStatus.PENDING and row["equipment_id"] in locked
                        and pending.get(row["id"]) == row["equipment_id"]]
            if eligible:
                expired = set(_expire(fixed.filter(pk__in=eligible), decision_at))
                for row in rows:
                    if row["id"] in expired:
                        row["status"] = ReservationStatus.EXPIRED
            if equipment_number is not None:
                rows = [row for row in rows if row["end_at"] > decision_at and (
                    row["status"] == ReservationStatus.APPROVED
                    or (row["status"] == ReservationStatus.PENDING and row["start_at"] > decision_at)
                )]

        reasons = read_admin_reservation_reasons(connection, [row["id"] for row in rows])
        for row in rows:
            row["reason"] = reasons.get(row["id"])
        if pk is not None and rows:
            rows[0]["history"] = read_reservation_history(connection, pk)
        return rows

    return _durable_operation(read)


def get_admin_reservations(user, equipment_number=None):
    return _read_admin_reservations(user, equipment_number=equipment_number)


def get_admin_reservation(user, pk):
    if pk is None:
        require_reservation_admin(user)
        return None
    rows = _read_admin_reservations(user, pk=pk)
    return rows[0] if rows else None


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
