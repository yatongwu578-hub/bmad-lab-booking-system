"""Story 2.2 formal runtime read-back only. Run with the original project .venv."""

from datetime import datetime, time, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os
import runpy
import sys

import django

HERE = Path(__file__).resolve().parent
D041 = HERE / "story-2-1-targeted-independent-recheck" / "release-story-2-1.py"
D041_SHA = "4aacbdf0ad62531f8852e00ea9703ffc3d6038e8188903c463810078576eda31"
HOST = "127.0.0.1"
DEVICE = "EQ-DEMO-S12-20261125"
BEIJING = ZoneInfo("Asia/Shanghai")


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def fingerprint(rows):
    payload = json.dumps(rows, default=str, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def dates(bookings, now):
    today = now.astimezone(BEIJING).date()

    def overlapping(day):
        start = datetime.combine(day, time.min, BEIJING)
        end = start + timedelta(days=1)
        return [r for r in bookings if r["start_at"] < end and start < r["end_at"]]

    def no_pending(items):
        return not any(r["status"] == "pending" for r in items)

    choices = {}
    for offset in range(1, 15):
        day = today + timedelta(days=offset)
        if not any(r["status"] in {"approved", "pending"} for r in overlapping(day)):
            choices["empty"] = day.isoformat()
            break
    eligible = {r["start_at"].astimezone(BEIJING).date() for r in bookings if r["status"] == "approved"}
    for day in sorted(eligible):
        items = overlapping(day)
        if not no_pending(items):
            continue
        if any(r["status"] == "approved" and r["end_at"] > now for r in items):
            choices.setdefault("approved", day.isoformat())
        if any(r["status"] == "approved" and r["end_at"] <= now for r in items):
            choices.setdefault("historical", day.isoformat())
    return choices


def main():
    phase, directory = sys.argv[1:]
    require(phase in {"before", "after"}, "Invalid read-back phase")
    receipt = Path(directory).resolve(strict=True)
    require(sys.version_info[:3] == (3, 13, 17) and django.get_version() == "5.2.19", "Runtime version mismatch")
    require(os.environ.get("LAB_BOOKING_DB_MODE") == "runtime", "Wrong runtime mode")
    require(Path(os.environ["PGPASSFILE"]).is_absolute(), "Expected protected absolute passfile")
    sys.path.insert(0, str(HERE.parents[1]))
    from lab_booking.database_config import reject_connection_overrides

    reject_connection_overrides()
    require(sha256(D041.read_bytes()).hexdigest() == D041_SHA, "D-042 certified ACL reader changed")
    # Import reviewed query helpers only. Its release dispatch runs only as __main__.
    legacy = runpy.run_path(str(D041), run_name="story22_certified_d041_readers")
    require(legacy["APP"] == "lab_booking_app" and legacy["DB"] == "lab_booking", "Unexpected certified reader target")
    check = legacy["one"]
    with legacy["connect"]("lab_booking_app") as connection, connection.transaction():
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute("SET LOCAL statement_timeout = '12s'")
        require(check(connection, "SELECT current_setting('transaction_read_only') AS mode")["mode"] == "on",
                "Read-only transaction not active")
        identity = legacy["identity"](connection, "lab_booking_app")
        require(identity["host"] == HOST, "Unexpected target host")
        require(legacy["state_ready"](legacy["readiness"](connection)), "Existing reservation/audit migrations not certified")
        prior_acl = legacy["old_privileges"](connection)
        legacy["default_grants"](connection)
        legacy["schema"](connection, phase)
        require(legacy["acl"](connection, phase) == "ready", "D-042 permission matrix not in ready state")
        require(check(connection, """SELECT
            pg_catalog.has_table_privilege(current_user,'public.django_session','SELECT')
            AND pg_catalog.has_table_privilege(current_user,'public.django_session','INSERT')
            AND pg_catalog.has_table_privilege(current_user,'public.django_session','UPDATE')
            AND pg_catalog.has_table_privilege(current_user,'public.django_session','DELETE')
            AND pg_catalog.has_column_privilege(current_user,'public.accounts_user','last_login','UPDATE')
            AND pg_catalog.has_column_privilege(current_user,'public.accounts_user','password','UPDATE')
            AND pg_catalog.has_table_privilege(current_user,'public.django_migrations','SELECT') AS ok""")["ok"],
                "Required login, session or migration read privilege missing")

        device = check(connection, """SELECT e.id,e.number,e.name,e.category,e.location,e.description,e.status
            FROM public.equipment_equipment AS e WHERE e.number=%s""", (DEVICE,))
        bookings = legacy["rows"](connection, """SELECT r.id,r.applicant_id,r.equipment_id,r.start_at,
            r.end_at,r.status,r.applied_at FROM public.reservations_reservation AS r
            WHERE r.equipment_id=%s ORDER BY r.id""", (device["id"],))
        history_ids = legacy["rows"](connection, "SELECT h.id FROM public.audit_operationhistory AS h ORDER BY h.id")
        now = check(connection, "SELECT pg_catalog.clock_timestamp() AS observed_at")["observed_at"]
        snapshot = {
            "device_id": device["id"], "device_sha256": fingerprint(device),
            "reservations": len(bookings), "reservations_sha256": fingerprint(bookings),
            "history_ids": len(history_ids), "history_ids_sha256": fingerprint(history_ids),
            "previous_acl_sha256": fingerprint(prior_acl),
        }
        smoke_dates = dates(bookings, now)

    summary = {"identity": identity, "snapshot": snapshot, "device_number": DEVICE,
               "observed_at": now.isoformat(), "smoke_dates_without_pending": smoke_dates, "phase": phase}
    out = receipt / ("runtime-readonly-" + phase + ".json")
    with out.open("x", encoding="utf-8") as file:
        file.write(json.dumps(summary, sort_keys=True, ensure_ascii=True) + "\n")
    if phase == "after":
        before = json.loads((receipt / "runtime-readonly-before.json").read_text(encoding="utf-8"))
        require(before["identity"] == identity and before["snapshot"] == snapshot,
                "Detected data or inherited ACL drift. Stop and investigate without replay.")
    print("STORY22_RUNTIME_READONLY_" + phase.upper() + "_OK", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        state = getattr(error, "sqlstate", None) or "n/a"
        info = str(error) if type(error) is RuntimeError else "See error type and SQLSTATE; do not print credentials."
        print(f"Story 2.2 stopped: {type(error).__name__} [{state}] {info}", file=sys.stderr)
        sys.exit(1)
