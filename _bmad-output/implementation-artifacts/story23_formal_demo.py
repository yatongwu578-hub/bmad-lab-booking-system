"""Read-only planning and differential verification for the approved Story 2.3 demo."""
from datetime import datetime, timedelta
from hashlib import sha256
import json
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")
DEMO_DEVICE = "EQ-DEMO-S12-20261125"
SYSTEM_REASON = "开始时间已到仍待审核"


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def canonical(data):
    return json.dumps(data, ensure_ascii=True, default=str, sort_keys=True, separators=(",", ":"))


def digest(data):
    return sha256(canonical(data).encode()).hexdigest()


def at(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def tables(legacy, conn):
    """Only the already-provisioned owner, in a read-only transaction. Never read passwords or sessions."""
    rows = legacy["rows"]
    return {
        "reservations": rows(conn, """SELECT r.id,r.applicant_id,r.equipment_id,r.start_at,r.end_at,
                        r.applied_at,r.status FROM public.reservations_reservation AS r ORDER BY r.id"""),
        "history": rows(conn, """SELECT h.id,h.object_type,h.reservation_id,h.equipment_id,h.action,
                   h.before_status,h.after_status,h.actor_type,h.actor_id,h.reason,h.decision_at,h.recorded_at
                   FROM public.audit_operationhistory AS h ORDER BY h.id"""),
        "equipment": rows(conn, """SELECT e.id,e.number,e.name,e.category,e.location,e.description,e.status
                     FROM public.equipment_equipment AS e ORDER BY e.id"""),
        "accounts": rows(conn, """SELECT a.id,a.username,a.role,a.is_active,a.is_staff,a.is_superuser,
                    a.first_name,a.last_name,a.email,a.date_joined FROM public.accounts_user AS a ORDER BY a.id"""),
    }


def index(items):
    return {str(row["id"]): digest(row) for row in items}


def snapshot(data):
    return {name: index(rows) for name, rows in data.items()}


def system_expiry(row):
    return (
        row["object_type"] == "reservation" and row["reservation_id"] == 1 and row["equipment_id"] is None
        and row["action"] == "expire" and row["before_status"] == "pending" and row["after_status"] == "expired"
        and row["actor_type"] == "system" and row["actor_id"] is None and row["reason"] == SYSTEM_REASON
        and at(row["recorded_at"]) >= at(row["decision_at"])
    )


def conflict(rows, device, start, end, now):
    return any(r["equipment_id"] == device and at(r["start_at"]) < end and start < at(r["end_at"])
               and (r["status"] == "approved" or (r["status"] == "pending" and at(r["start_at"]) > now))
               for r in rows)


def valid_slot(start, end, horizon):
    return (start.tzinfo is not None and end.tzinfo is not None and start > horizon
            and start.astimezone(BEIJING).date() == end.astimezone(BEIJING).date()
            and all(not (t.minute or t.second or t.microsecond) for t in (start, end))
            and end - start == timedelta(hours=1) and end.astimezone(BEIJING).hour <= 23)


def plan(sample, data, now):
    now = now.astimezone(BEIJING)
    deadline = now + timedelta(minutes=25)
    # Extra time covers pending-boundary races while a submitted request obtains its device lock.
    horizon = deadline + timedelta(minutes=2)
    roles = {role: entry["account_id"] for role, entry in sample["accounts"].items()}
    rows, history = data["reservations"], data["history"]
    target, = [r for r in rows if r["id"] == 1]
    need(target["applicant_id"] == roles["student"] and at(target["start_at"]) <= now,
         "Approved #1 does not belong to the selected student or has not reached its start")
    previous = [h for h in history if h["reservation_id"] == 1]
    if target["status"] == "pending":
        need(not previous, "Expected no prior history for pending #1; stop")
        expiry = "expire_once"
    elif target["status"] == "expired":
        need(len(previous) == 1 and system_expiry(previous[0]) and
             at(previous[0]["decision_at"]) >= at(target["start_at"]),
             "Already-expired #1 has no uniquely matching system audit; stop")
        expiry = "already_expired"
    else:
        raise RuntimeError("Approved #1 no longer has an eligible status")
    due = [r for r in rows if r["status"] == "pending" and at(r["start_at"]) <= horizon]
    extra = [r["id"] for r in due if r["applicant_id"] in (roles["student"], roles["teacher"]) and r["id"] != 1]
    need(not extra, "Other student/teacher pending rows within safety horizon: " + ",".join(map(str, extra)))

    own = sorted(r["id"] for r in rows if r["applicant_id"] == roles["teacher"])
    if own:
        teacher = {"mode": "reuse", "reservation_id": own[0]}
    else:
        devices = [e for e in data["equipment"] if e["number"] == DEMO_DEVICE and e["status"] == "available"]
        need(len(devices) == 1, "Previously designated demo equipment is not available")
        d = devices[0]["id"]
        risks = [r["id"] for r in due if r["equipment_id"] == d and r["id"] != 1]
        need(not risks, "Teacher submission might expire other device rows: " + ",".join(map(str, risks)))
        first = max(now + timedelta(minutes=60), horizon + timedelta(minutes=15))
        start = first.replace(minute=0, second=0, microsecond=0)
        if start < first:
            start += timedelta(hours=1)
        for offset in range(24 * 7):
            begin = start + timedelta(hours=offset)
            end = begin + timedelta(hours=1)
            if valid_slot(begin, end, horizon) and not conflict(rows, d, begin, end, now):
                teacher = {
                    "mode": "submit_once", "device_id": d, "device_number": DEMO_DEVICE,
                    "path": f"/equipment/{d}/reserve/", "start": begin.isoformat(), "end": end.isoformat(),
                    "form_start": begin.strftime("%Y-%m-%dT%H:%M"), "form_end": end.strftime("%Y-%m-%dT%H:%M"),
                }
                break
        else:
            raise RuntimeError("No valid conflict-free demo window in the next seven days")
    return {
        "ready": True, "role_ids": roles, "observed": now.isoformat(), "deadline": deadline.isoformat(),
        "horizon": horizon.isoformat(), "expiry_mode": expiry, "student_reservation": target,
        "history1": [x["id"] for x in previous], "hashes": snapshot(data), "teacher": teacher,
        "student_effective_before": at(target["start_at"]) > now and target["status"] == "pending",
    }


def verify(plan, after, events):
    before = plan["hashes"]
    end_state = snapshot(after)
    first_start = at(plan["student_reservation"]["start_at"])
    now = at(events[-1]["at"]) if events else None
    need(now is not None, "No real browser request receipts")
    need(not any(e.get("status", 500) >= 500 for e in events), "Formal browser run contains an unresolved server failure")
    need(end_state["equipment"] == before["equipment"] and end_state["accounts"] == before["accounts"],
         "Equipment or non-session account fields changed")
    after_res = end_state["reservations"]
    before_res = before["reservations"]
    need(set(before_res) <= set(after_res), "Existing reservation removed")
    same = {rid: after_res[rid] for rid in before_res if rid != "1"}
    need(same == {rid: h for rid, h in before_res.items() if rid != "1"}, "Unapproved existing reservation changed")

    target, = [r for r in after["reservations"] if r["id"] == 1]
    expected1 = {**plan["student_reservation"], "status": "expired"}
    need(digest(target) == digest(expected1), "Student #1 did not expire cleanly")
    existing_hist = before["history"]
    after_hist = end_state["history"]
    need(set(existing_hist) <= set(after_hist) and {hid: after_hist[hid] for hid in existing_hist} == existing_hist,
         "Existing history changed or was removed")
    new_history = [h for h in after["history"] if str(h["id"]) not in existing_hist]
    expiring = plan["expiry_mode"] == "expire_once"
    need(len(new_history) == int(expiring), "Unexpected additional history count")
    history1 = [h for h in after["history"] if h["reservation_id"] == 1]
    need(len(history1) == 1 and system_expiry(history1[0]) and at(history1[0]["decision_at"]) >= first_start,
         "Student #1 lacks exactly one valid system expiry history")
    if expiring:
        need(at(plan["observed"]) <= at(history1[0]["decision_at"]) <= at(plan["horizon"]),
             "Student #1 expiry decision outside the approved verification window")
    else:
        need(plan["history1"] == [history1[0]["id"]], "An already expired #1 was not reused unchanged")

    teacher = plan["teacher"]
    added = [r for r in after["reservations"] if str(r["id"]) not in before_res]
    new_expected = teacher["mode"] == "submit_once"
    need(len(added) == int(new_expected), "Teacher demo count or unapproved write differs")
    if new_expected:
        row = added[0]
        need(row["applicant_id"] == plan["role_ids"]["teacher"] and row["equipment_id"] == teacher["device_id"]
             and row["status"] == "pending" and at(row["start_at"]) == at(teacher["start"])
             and at(row["end_at"]) == at(teacher["end"])
             and at(plan["observed"]) <= at(row["applied_at"]) < at(row["start_at"])
             and at(row["applied_at"]) <= at(plan["horizon"]), "Unexpected teacher reservation content")
        teacher_id = row["id"]
    else:
        teacher_id = teacher["reservation_id"]

    def hits(role, method, path, status):
        return [e for e in events if e.get("role") == role and e.get("method") == method
                and e.get("path") == path and e.get("status") == status]

    lists = hits("student", "GET", "/reservations/", 200)
    first = [e for e in lists if e.get("student_snapshot", {}).get("status") == "expired"]
    need(len(first) >= 2 and all(e["student_snapshot"]["history_ids"] == [history1[0]["id"]] for e in first),
         "Two actual student list reads with unchanged history are not certified")
    if expiring:
        need(first[0].get("writes") == ["expire-1", "expire-history-1"] and
             all(not e.get("writes") for e in first[1:]), "Expiry was not attributed to the first student list or repeat wrote")
    else:
        need(all(not e.get("writes") for e in first), "Already-expired #1 attempted another write")
    need(len(hits("teacher", "GET", "/reservations/", 200)) >= 2 and
         hits("teacher", "GET", f"/reservations/{teacher_id}/result/", 200), "Teacher list, detail or return missing")
    need(hits("student", "GET", "/reservations/1/result/", 200), "Student expired detail missing")
    for role in ("student", "teacher", "admin"):
        need(hits(role, "GET", "/identity/", 200), f"{role} identity not evidenced")
    need(hits("admin", "GET", "/reservations/", 403), "Administrator denial not evidenced")
    need(hits("teacher", "GET", "/reservations/1/result/", 404) and
         hits("teacher", "GET", "/reservations/4611686018427387904/result/", 404), "Foreign/missing detail controls missing")
    posts = [e for e in events if e.get("method") == "POST" and e.get("path", "").endswith("/reserve/")]
    if new_expected:
        need(len(posts) == 1 and posts[0] in hits("teacher", "POST", teacher["path"], 201)
             and posts[0].get("writes") == ["teacher-create"], "Exactly one actual teacher 201 not certified")
    else:
        need(not posts, "Teacher existing record must be reused without submitting")
    return {
        "student_id": 1, "student_status": "expired", "student_effective_before": plan["student_effective_before"],
        "student_effective_after": False, "student_history": history1[0],
        "student_repeated_reads": len(first), "teacher_reservation_id": teacher_id,
        "teacher_mode": teacher["mode"], "teacher_new_row": added[0] if added else None,
        "outside_approved_delta_unchanged": True,
    }
