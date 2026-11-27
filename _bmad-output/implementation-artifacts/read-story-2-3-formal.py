"""Story 2.3 formal evidence reads only. Run with the existing project .venv."""
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import runpy
import sys
from zoneinfo import ZoneInfo

import django

HERE = Path(__file__).resolve().parent
LEGACY = HERE / "story-2-1-targeted-independent-recheck" / "release-story-2-1.py"
LEGACY_HASH = "4aacbdf0ad62531f8852e00ea9703ffc3d6038e8188903c463810078576eda31"
OLD = HERE / "story-2-2-runtime-20261127-000918-77eb9198" / "runtime-readonly-before.json"
HISTORY = "audit_operationhistory"
ADD = {(HISTORY, c, "SELECT") for c in ("reservation_id", "action", "actor_type", "reason")}
ROLES = ("student", "teacher", "admin")
BEIJING = ZoneInfo("Asia/Shanghai")


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def pack(value):
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


def fingerprint(value):
    return sha256(pack(value).encode("utf-8")).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, data):
    with path.open("x", encoding="utf-8") as output:
        output.write(pack(data) + "\n")


def certify(l, connection, phase):
    one, rows = l["one"], l["rows"]
    owner = l["APP"]
    need(one(connection, "SELECT pg_catalog.current_setting('transaction_read_only') AS mode")["mode"] == "on",
         "Read-only transaction not active")
    identity = l["identity"](connection, owner)
    # Match the JSON receipt container while preserving every migration and table value.
    migrations = list(l["readiness"](connection))
    need(l["state_ready"](migrations), "Existing reservation/audit migration records differ")
    old_acl = fingerprint(l["old_privileges"](connection))
    need(old_acl == load(OLD)["snapshot"]["previous_acl_sha256"], "Account/device/session ACL changed vs D-042")
    l["default_grants"](connection)
    l["schema"](connection, phase)
    matrix = rows(connection, l["MATRIX"])
    raw = rows(connection, l["RAW_ACL"])
    roles = one(connection, "SELECT 'lab_booking_app'::pg_catalog.regrole::oid AS app, "
                            "'lab_booking_migrator'::pg_catalog.regrole::oid AS owner")
    expected = {(r["relation_name"], r["column_name"], r["operation"]) for r in matrix if r["expected_after"]}
    actual = {(r["relation_name"], r["column_name"], r["operation"]) for r in matrix if r["effective"]}
    explicit = {(r["object"], r["column_name"], r["privilege_type"]) for r in raw}
    l["record"]("story23-acl-probe", dict(stage=phase, identity=identity, migrations=migrations,
         effective_matrix=matrix, explicit_acl=sorted(raw, key=pack)))
    need(len(matrix) == 76 and len(expected) == 26 and not (expected & ADD) and
         all(r["object_owner"] == l["MIGRATOR"] and not r["can_delegate"] for r in matrix) and
         next(iter(one(connection, l["ACL_GUARD"]).values())) is True and
         len(raw) == len(explicit) and explicit == actual and
         all(r["grantee"] == roles["app"] and r["grantor"] == roles["owner"]
             and not r["is_grantable"] and r["column_name"] for r in raw),
         "Unexpected effective or direct ACL, ownership, table privilege, or grant option")
    state = ("EXACT" if actual == expected | ADD else "NEEDS_FOUR" if actual == expected else "DRIFT")
    need(state != "DRIFT", "Partial, extra, or missing effective permission")
    evidence = dict(identity=identity, migrations=migrations, state=state, prior_acl_sha256=old_acl,
                    effective_matrix=matrix, explicit_acl=sorted(raw, key=pack))
    return state, evidence


def account_inputs():
    path = os.environ.get("STORY23_ACCOUNTS_MANIFEST")
    if not path:
        return {role: os.environ.get("STORY23_ACCOUNT_" + role.upper()) for role in ROLES}

    manifest = Path(path)
    root = HERE.parents[1]
    need(manifest.is_absolute() and not manifest.resolve().is_relative_to(root),
         "Use the existing protected account manifest outside the repository")
    django.setup()
    from accounts.management.commands.seed_accounts import read_manifest
    try:
        entries = read_manifest(manifest)
    except Exception:
        raise RuntimeError("Protected account manifest unreadable or invalid; details suppressed") from None
    result = {}
    for role in ROLES:
        names = [username for username, fields in entries.items() if fields[0] == role]
        need(len(names) == 1, f"Automatic selection requires exactly one manifest entry for {role}; use an approved exact login selection")
        result[role] = names[0]
    return result


def candidate(l, c, before=None):
    rows, one = l["rows"], l["one"]
    now = one(c, "SELECT pg_catalog.clock_timestamp() AS at")["at"].astimezone(BEIJING)
    selected = {}
    inputs = account_inputs() if before is None else {}
    for role in ROLES:
        if before is None:
            username = inputs[role]
            need(bool(username), "All three authorized preset usernames are required")
            data = rows(c, "SELECT a.id,a.role,a.is_active FROM public.accounts_user AS a "
                           "WHERE a.username=%s", (username,))
        else:
            data = rows(c, "SELECT a.id,a.role,a.is_active FROM public.accounts_user AS a WHERE a.id=%s",
                        (before["accounts"][role]["account_id"],))
        need(len(data) == 1 and data[0]["role"] == role and data[0]["is_active"],
             f"Authorized {role} account is absent, inactive or has a different role")
        selected[role] = data[0]["id"]
    need(len(set(selected.values())) == 3, "Selected accounts are not distinct")
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    deadline = min(now + timedelta(minutes=20), next_hour - timedelta(minutes=1))
    if before is not None:
        deadline = datetime.fromisoformat(before["deadline_beijing"])

    accounts = {}
    for role, pk in selected.items():
        data = rows(c, """SELECT r.id,r.applicant_id,r.equipment_id,r.start_at,r.end_at,r.applied_at,
                                 r.status AS reservation_status,e.number AS device_number,e.name AS device_name,
                                 e.category,e.location,e.description,e.status AS device_status
                          FROM public.reservations_reservation AS r
                          JOIN public.equipment_equipment AS e ON e.id=r.equipment_id
                          WHERE r.applicant_id=%s ORDER BY r.id""", (pk,))
        ids = [r["id"] for r in data]
        history = rows(c, """SELECT h.id,h.reservation_id,h.action,h.actor_type,h.reason
                             FROM public.audit_operationhistory AS h
                             WHERE h.reservation_id=ANY(%s::bigint[]) ORDER BY h.id""", (ids,)) if ids else []
        unsafe = [r["id"] for r in data if r["reservation_status"] == "pending" and r["start_at"] <= deadline]
        account = {
            "account_id": pk, "snapshot_sha256": fingerprint(data),
            "history_count": len(history), "history_sha256": fingerprint(history),
            "qualifying_reason_ids": sorted({
                h["reservation_id"] for h in history if h["actor_type"] == "admin" and h["reason"].strip()
                and any(r["id"] == h["reservation_id"] and
                        (r["reservation_status"], h["action"]) in (("rejected", "reject"), ("cancelled", "cancel"))
                        for r in data)
            }),
            "unsafe_pending_ids": unsafe,
            "reservations": [dict(id=r["id"], device_id=r["equipment_id"], device_number=r["device_number"],
                                  device_status=r["device_status"], reservation_status=r["reservation_status"],
                                  start_beijing=r["start_at"].astimezone(BEIJING),
                                  end_beijing=r["end_at"].astimezone(BEIJING),
                                  effective=(r["reservation_status"] == "approved" or
                                             (r["reservation_status"] == "pending" and r["start_at"] > now)))
                             for r in data],
        }
        accounts[role] = account
    missing = 2**62
    need(not rows(c, "SELECT r.id FROM public.reservations_reservation AS r WHERE r.id=%s", (missing,)),
         "Missing-detail control unexpectedly exists")
    receipt = dict(observed_beijing=now, deadline_beijing=deadline, accounts=accounts, missing_id=missing)
    if before is None:
        remaining = deadline - now
        affected_roles = [r for r in ("student", "teacher") if accounts[r]["unsafe_pending_ids"]]
        missing_details = [r for r in ("student", "teacher") if not accounts[r]["reservations"]]
        receipt["browser_business_safe"] = remaining >= timedelta(minutes=3) and not affected_roles
        receipt["browser_full_ready"] = receipt["browser_business_safe"] and not missing_details
        receipt["window_sufficient"] = remaining >= timedelta(minutes=3)
        receipt["blocked_roles_fr018"] = affected_roles
        receipt["roles_without_details"] = missing_details
    else:
        receipt["unchanged"] = all(
            pack(accounts[r]) == pack(before["accounts"][r]) for r in ROLES)
        receipt["within_window"] = now <= deadline
    return receipt


def main():
    phase, directory = sys.argv[1:3]
    need(bool(re.fullmatch(r"acl-before|acl-after|recover-[0-9]+|sample-inspect|sample-before|sample-after|demo-before|demo-after", phase)),
         "Unexpected read-only phase")
    need(sys.version_info[:3] == (3, 13, 17) and django.get_version() == "5.2.19", "Original runtime version mismatch")
    need(os.environ.get("LAB_BOOKING_DB_MODE") == "runtime", "Expected runtime")
    receipt = Path(directory).resolve(strict=True)
    need(receipt.is_dir(), "Missing receipt directory")
    sys.path.insert(0, str(HERE.parents[1]))
    from lab_booking.database_config import reject_connection_overrides
    reject_connection_overrides()
    need(sha256(LEGACY.read_bytes()).hexdigest() == LEGACY_HASH, "Reviewed D-042 reader changed")
    need(Path(os.environ["PGPASSFILE"]).is_absolute(), "Absolute protected passfile required")
    # Import certified read helpers only. Never dispatch the legacy release command.
    legacy = runpy.run_path(str(LEGACY), run_name="story23_readers_only")
    need(legacy["APP"] == "lab_booking_app" and legacy["DB"] == "lab_booking", "Reviewed reader identity differs")
    with legacy["connect"]("lab_booking_app") as conn, conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '12s'")
        state, evidence = certify(legacy, conn, phase)
        if phase == "acl-after" or phase.startswith(("sample-", "demo-")):
            earlier = load(receipt / "acl-before.json")
            need(state == "EXACT" and evidence["prior_acl_sha256"] == earlier["prior_acl_sha256"],
                 "Exact post-authorization matrix not verified")
            need(evidence["migrations"] == earlier["migrations"], "Migration records changed")
        if phase in {"sample-inspect", "sample-before", "demo-before"}:
            evidence["sample"] = candidate(legacy, conn)
        if phase == "sample-after":
            before = load(receipt / "sample-before.json")["sample"]
            evidence["sample"] = candidate(legacy, conn, before)
    if phase in {"demo-before", "demo-after"}:
        from story23_formal_demo import plan, tables, verify
        with legacy["connect"](legacy["MIGRATOR"]) as witness, witness.transaction():
            witness.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY")
            witness.execute("SET LOCAL statement_timeout = '12s'")
            need(legacy["one"](witness, "SELECT pg_catalog.current_setting('transaction_read_only') AS mode")["mode"] == "on",
                 "Independent owner readback is not read-only")
            evidence["independent_identity"] = legacy["identity"](witness, legacy["MIGRATOR"])
            data = tables(legacy, witness)
            if phase == "demo-before":
                now = legacy["one"](witness, "SELECT pg_catalog.clock_timestamp() AS at")["at"]
                evidence["sample"]["demo"] = plan(evidence["sample"], data, now)
                evidence["sample"]["deadline_beijing"] = evidence["sample"]["demo"]["deadline"]
            else:
                before = load(receipt / "sample-before.json")["sample"]["demo"]
                events = [json.loads(line) for line in (receipt / "browser-http.jsonl").read_text(encoding="utf-8").splitlines()]
                try:
                    evidence["outcome"] = verify(before, data, events)
                except RuntimeError as error:
                    evidence["not_verified"] = str(error)
                    from story23_formal_demo import snapshot
                    evidence["after_hashes"] = snapshot(data)
                    write(receipt / "sample-after-unverified.json", evidence)
                    raise
    filename = {"demo-before": "sample-before", "demo-after": "sample-after"}.get(phase, phase)
    write(receipt / f"{filename}.json", evidence)
    if phase == "sample-before":
        sample = evidence["sample"]
        if sample["blocked_roles_fr018"]:
            ids = "; ".join(
                role + "=" + ",".join(map(str, sample["accounts"][role]["unsafe_pending_ids"]))
                for role in sample["blocked_roles_fr018"])
            raise RuntimeError("FR-018 blocks the read-only smoke; unsafe pending IDs: " + ids)
        need(sample["window_sufficient"], "Fewer than three minutes before the safe Beijing deadline; do not start the smoke")
    if phase == "sample-after":
        need(evidence["sample"]["unchanged"], "Business snapshot changed. Preserve evidence and do not replay.")
    print(f"STORY23_READ_{state}_OK", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        detail = str(error) if type(error) is RuntimeError else "Check protected settings, schema or SQLSTATE; no replay."
        print(f"Story 2.3 read-only stopped: {type(error).__name__} "
              f"[{getattr(error, 'sqlstate', None) or 'n/a'}] {detail}", file=sys.stderr)
        sys.exit(1)
