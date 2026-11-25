from django.db import models


class EquipmentStatus(models.TextChoices):
    AVAILABLE = "available", "可用"
    MAINTENANCE = "maintenance", "维修"
    DISABLED = "disabled", "停用"


class Equipment(models.Model):
    number = models.CharField(max_length=32)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80)
    location = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.AVAILABLE,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["number"], name="equipment_number_unique"),
            models.CheckConstraint(
                condition=models.Q(status__in=EquipmentStatus.values),
                name="equipment_status_valid",
            ),
        ]
