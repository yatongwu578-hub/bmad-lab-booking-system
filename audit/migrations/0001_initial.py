import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("equipment", "0001_initial"),
        ("reservations", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="OperationHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_type", models.CharField(choices=[("reservation", "预约"), ("equipment", "设备")], max_length=16)),
                ("action", models.CharField(max_length=32)),
                ("before_status", models.CharField(max_length=16)),
                ("after_status", models.CharField(max_length=16)),
                ("actor_type", models.CharField(max_length=16)),
                ("reason", models.TextField()),
                ("decision_at", models.DateTimeField()),
                ("recorded_at", models.DateTimeField()),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("reservation", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="reservations.reservation")),
                ("equipment", models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to="equipment.equipment")),
            ],
            options={"constraints": [
                models.CheckConstraint(
                    condition=(models.Q(object_type="reservation", reservation__isnull=False, equipment__isnull=True)
                               | models.Q(object_type="equipment", reservation__isnull=True, equipment__isnull=False)),
                    name="history_exactly_one_matching_object",
                ),
            ]},
        ),
    ]
