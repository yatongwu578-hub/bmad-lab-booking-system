"""Read current production DB evidence after the archived Story 2.3 Finish failure.

No HTTP, new reservations, GRANT, migration, test dispatch, or passfile contents.
The original Finish result is never overwritten or promoted.
"""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import runpy
import sys
from uuid import uuid4


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BEIJING = timezone(timedelta(hours=8))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Provide the original failed Finish directory")
    failed = Path(sys.argv[1]).resolve(strict=True)
    scope = failed.parent
    summary = runpy.run_path(str(HERE / "fill-story-2-3-chrome-receipt.py"))
    summary["render"](scope)  # verifies the approved files, listener and dual HTTP logs
    archived = summary["archived_failure"](scope, failed)
    passfile = Path(os.environ.get("PGPASSFILE") or
                    (Path(os.environ["LOCALAPPDATA"]) / "LabBooking/PostgreSQL17/pgpass.conf"))
    if not passfile.is_absolute() or passfile.resolve().is_relative_to(ROOT) or not passfile.is_file():
        raise RuntimeError("Existing protected passfile is unavailable")
    os.environ["PGPASSFILE"] = str(passfile)
    run = scope / f"recovery-readonly-{datetime.now(BEIJING):%Y%m%d-%H%M%S-%f}-{uuid4().hex[:8]}"
    run.mkdir()
    print(f"Read-only evidence directory: {run}", flush=True)
    try:
        sys.path.insert(0, str(ROOT))
        from lab_booking.database_config import reject_connection_overrides
        from story23_formal_demo import snapshot, system_expiry, tables
        reject_connection_overrides()
        reader = runpy.run_path(str(HERE / "read-story-2-3-formal.py"))
        legacy_path = reader["LEGACY"]
        if summary["digest"](legacy_path).lower() != reader["LEGACY_HASH"]:
            raise RuntimeError("Reviewed shared reader changed")
        sys.argv = [str(legacy_path), "story23-recovery-readonly", str(run)]
        legacy = runpy.run_path(str(legacy_path), run_name="story23_readers_only")

        def configure(connection):
            connection.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY")
            connection.execute("SET LOCAL statement_timeout = '12s'")
            if legacy["one"](connection, "SELECT current_setting('transaction_read_only') AS mode")["mode"] != "on":
                raise RuntimeError("Read-only transaction not active")

        with legacy["connect"](legacy["APP"]) as app, app.transaction():
            configure(app)
            state, acl = reader["certify"](legacy, app, "story23-recovery-readonly")
        reader["write"](run / "current-acl.json", acl)
        with legacy["connect"](legacy["MIGRATOR"]) as owner, owner.transaction():
            configure(owner)
            identity = legacy["identity"](owner, legacy["MIGRATOR"])
            now = legacy["one"](owner, "SELECT pg_catalog.clock_timestamp() AS at")["at"]
            data = tables(legacy, owner)
        hashes = snapshot(data)
        original = reader["load"](scope / "sample-before.json")["sample"]["demo"]
        earlier = archived["after_hashes"]
        reservations = [dict(reservation_id=r["id"], account_id=r["applicant_id"], device_id=r["equipment_id"],
                             status=r["status"], start_beijing=r["start_at"].astimezone(BEIJING),
                             end_beijing=r["end_at"].astimezone(BEIJING),
                             effective=r["status"] == "approved" or (r["status"] == "pending" and r["start_at"] > now))
                        for r in data["reservations"]]
        changes = {table: {"added": sorted(set(rows) - set(earlier[table])),
                           "removed": sorted(set(earlier[table]) - set(rows)),
                           "changed": sorted(key for key in rows.keys() & earlier[table].keys() if rows[key] != earlier[table][key])}
                   for table, rows in hashes.items()}
        history1 = [h for h in data["history"] if h["reservation_id"] == 1]
        reader["write"](run / "current-db.json", dict(
            failed_finish=failed.name, failed_snapshot_sha256=summary["digest"](failed / "sample-after-unverified.json"),
            observed_beijing=now.astimezone(BEIJING), owner_identity=identity, acl_state=state, read_only=True,
            reservations=reservations, history_ids=[h["id"] for h in data["history"]],
            student_history=[{k: h[k] for k in ("id", "reservation_id", "action", "actor_type", "before_status", "after_status", "decision_at", "recorded_at")} for h in history1],
            student_history_exact=len(history1) == 1 and system_expiry(history1[0]) and history1[0]["id"] == archived["history_id"],
            teacher_reservation_ids=[r["reservation_id"] for r in reservations if r["account_id"] == original["role_ids"]["teacher"]],
            current_hashes=hashes, changes_since_failed_finish=changes))
    except Exception as error:
        detail = str(error) if type(error) is RuntimeError else type(error).__name__
        (run / "failure.txt").write_text(f"{detail}\n", encoding="utf-8")
        print(f"Read-only recovery did not complete. See {run / 'failure.txt'}", file=sys.stderr)
        return 1
    print("STORY23_RECOVERY_READ_ONLY_RECORDED (not a formal acceptance marker)")
    print(json.dumps({"acl_state": state, "changes_since_failed_finish": changes}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        print(f"Read-only recovery stopped: {error}", file=sys.stderr)
        raise SystemExit(1) from None
