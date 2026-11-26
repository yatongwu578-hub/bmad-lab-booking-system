from django.conf import settings
from django.db import models


class ReservationStatus(models.TextChoices):
    PENDING = "pending", "待审核"
    APPROVED = "approved", "已批准"
    REJECTED = "rejected", "已拒绝"
    CANCELLED = "cancelled", "已取消"
    EXPIRED = "expired", "已失效"


class Reservation(models.Model):
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    equipment = models.ForeignKey("equipment.Equipment", on_delete=models.PROTECT)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=ReservationStatus.choices, default=ReservationStatus.PENDING)
    applied_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(status__in=ReservationStatus.values), name="reservation_status_valid"),
            models.CheckConstraint(condition=models.Q(end_at__gt=models.F("start_at")), name="reservation_start_before_end"),
        ]
