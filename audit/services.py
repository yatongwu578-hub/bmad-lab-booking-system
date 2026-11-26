from django.db.models.functions import Now

from reservations.models import ReservationStatus

from .models import HistoryObject, OperationHistory


EXPIRY_REASON = "开始时间已到仍待审核"


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
