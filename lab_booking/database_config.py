import os

from django.core.exceptions import ImproperlyConfigured


DATABASE_TARGETS = {
    "runtime": ("lab_booking", "lab_booking_app"),
    "migration": ("lab_booking", "lab_booking_migrator"),
    "test": ("test_lab_booking", "lab_booking_test"),
}
HOST = "127.0.0.1"
PORT = "5433"
SERVER_VERSION_NUM = 170012

CONFLICTING_ENVIRONMENT = (
    "PGHOST", "PGHOSTADDR", "PGPORT", "PGDATABASE", "PGUSER",
    "PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS",
)


def reject_connection_overrides():
    conflicts = [name for name in CONFLICTING_ENVIRONMENT if name in os.environ]
    if conflicts:
        names = "、".join(conflicts)
        raise ImproperlyConfigured(f"请移除冲突的 PostgreSQL 环境变量：{names}。")
