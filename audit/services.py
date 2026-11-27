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
