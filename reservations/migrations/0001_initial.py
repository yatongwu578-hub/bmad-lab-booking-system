import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("equipment", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="Reservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("pending", "待审核"), ("approved", "已批准"), ("rejected", "已拒绝"), ("cancelled", "已取消"), ("expired", "已失效")], default="pending", max_length=16)),
                ("applied_at", models.DateTimeField()),
                ("applicant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("equipment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="equipment.equipment")),
            ],
            options={"constraints": [
                models.CheckConstraint(condition=models.Q(status__in=["pending", "approved", "rejected", "cancelled", "expired"]), name="reservation_status_valid"),
                models.CheckConstraint(condition=models.Q(end_at__gt=models.F("start_at")), name="reservation_start_before_end"),
            ]},
        ),
    ]
