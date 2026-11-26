from django.conf import settings
from django.db import models


class HistoryObject(models.TextChoices):
    RESERVATION = "reservation", "预约"
    EQUIPMENT = "equipment", "设备"


class OperationHistory(models.Model):
    object_type = models.CharField(max_length=16, choices=HistoryObject.choices)
    reservation = models.ForeignKey("reservations.Reservation", on_delete=models.PROTECT, null=True)
    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=32)
    before_status = models.CharField(max_length=16)
    after_status = models.CharField(max_length=16)
    actor_type = models.CharField(max_length=16)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    reason = models.TextField()
    decision_at = models.DateTimeField()
    recorded_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(object_type=HistoryObject.RESERVATION, reservation__isnull=False, equipment__isnull=True)
                    | models.Q(object_type=HistoryObject.EQUIPMENT, reservation__isnull=True, equipment__isnull=False)
                ),
                name="history_exactly_one_matching_object",
            ),
        ]
