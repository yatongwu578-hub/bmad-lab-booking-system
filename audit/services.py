from django.db.models.functions import Now

from reservations.models import ReservationStatus

from .models import HistoryObject, OperationHistory


EXPIRY_REASON = "开始时间已到仍待审核"


def read_reservation_reasons(connection, rejected_ids, cancelled_ids):
    """Project only the latest matching admin reason for each authorized candidate."""
    if not rejected_ids and not cancelled_ids:
        return {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (h.reservation_id) h.reservation_id, h.reason
            FROM public.audit_operationhistory AS h
            WHERE h.actor_type = %s AND (
                (h.action = %s AND h.reservation_id = ANY(%s::bigint[]))
                OR (h.action = %s AND h.reservation_id = ANY(%s::bigint[]))
            )
            ORDER BY h.reservation_id, h.id DESC
            """,
            ["admin", "reject", rejected_ids, "cancel", cancelled_ids],
        )
        return {pk: reason for pk, reason in cursor.fetchall() if reason.strip()}


def append_reservation_expiry(reservation_id, decision_at):
    """Append within the reservation service's device-locked transaction."""
    OperationHistory.objects.create(
        object_type=HistoryObject.RESERVATION,
        reservation_id=reservation_id,
        action="expire",
        before_status=ReservationStatus.PENDING,
        after_status=ReservationStatus.EXPIRED,
        actor_type="system",
        actor_id=None,
        reason=EXPIRY_REASON,
        decision_at=decision_at,
        recorded_at=Now(),
    )


def append_reservation_cancellation(reservation_id, applicant_id, before_status, decision_at):
    """Append a self-cancellation within the device-locked transaction."""
    OperationHistory.objects.create(
        object_type=HistoryObject.RESERVATION,
        reservation_id=reservation_id,
        action="cancel",
        before_status=before_status,
        after_status=ReservationStatus.CANCELLED,
        actor_type="applicant",
        actor_id=applicant_id,
        reason="",
        decision_at=decision_at,
        recorded_at=Now(),
    )


def read_admin_reservation_reasons(connection, reservation_ids):
    """Read the latest nonblank reason from a stored transition for each scoped ID."""
    if not reservation_ids:
        return {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (h.reservation_id) h.reservation_id, h.reason
            FROM public.audit_operationhistory AS h
            WHERE h.reservation_id = ANY(%s::bigint[])
              AND h.action IN (%s, %s, %s, %s)
              AND h.reason ~ '[^[:space:]]'
            ORDER BY h.reservation_id, h.id DESC
            """,
            [reservation_ids, "approve", "reject", "cancel", "expire"],
        )
        return dict(cursor.fetchall())


def read_reservation_history(connection, reservation_id):
    """Project exactly the columns needed for one already-authorized reservation."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT h.id, h.reservation_id, h.action, h.before_status, h.after_status,
                   h.actor_type, h.actor_id, a.username AS actor_username, h.reason,
                   h.decision_at, h.recorded_at
            FROM public.audit_operationhistory AS h
            LEFT JOIN public.accounts_user AS a ON a.id = h.actor_id
            WHERE h.reservation_id = %s
            ORDER BY h.recorded_at, h.id
            """,
            [reservation_id],
        )
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
