"""Preserve the rejected 16:37 POST and continue only safe GET coverage, never a second booking POST."""

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import gettempdir
from uuid import uuid4

import story23_teacher_followup as base


PREV = base.RUN
RUN = base.OLD / "teacher-recovery-20261127-163714-f93c0b3c"
RECEIPT = "source-review.json"
DENIAL = "dbe13b6193b9af1a6ed6f6e969823475beb332c7166dd7334b7f122c895c6d98"
HALTED = "ffa052a265c93b2b59c697963b3e9ebd7ff467413372a2867e1810a16dc68b31"
MARKER = "STORY23_READONLY_RESUME_EVIDENCE_RECORDED"
check, load, read, write, digest = base.check, base.load, base.read, base.write, base.digest


def events_at(folder):
    events = [json.loads(line) for line in read(folder / "browser-http.jsonl").splitlines() if line.strip()]
    logged = Counter((m[1], m[2].partition("?")[0], int(m[3])) for m in re.finditer(
        r'"([A-Z]+) (\S+) HTTP/[^ ]+" (\d{3}) \d+', read(folder / "server.stderr.txt")))
    check(events and logged == Counter((e["method"], e["path"], e["status"]) for e in events), "Django and guard HTTP logs differ")
    return events


def review():
    recovered, acl, reads = base.original()
    prior = load(PREV / "before.json")
    check(prior["source_hashes"] == base.inputs(), "Original follow-up inputs changed")
    preflight = prior["preflight"]
    check(re.fullmatch(r"preflight-[0-9a-f]{12}", preflight), "Original preflight directory unbound")
    prior_acl = PREV / preflight / "acl.json"
    check(prior["preflight_acl_sha256"] == digest(prior_acl) and load(prior_acl) == acl,
          "Original follow-up ACL unbound or changed")
    listener = load(PREV / "listener-planned.json")
    launch = load(PREV / "chrome-launch.json")
    check(launch["pid"] == listener["pid"] and launch["origin"] == listener["origin"] == base.ORIGIN
          and load(PREV / "chrome-launches-requested.json")["complete"] is True, "Original Chrome launch unbound")
    events = events_at(PREV)
    posts = [e for e in events if e["method"] == "POST" and e["path"].endswith("/reserve/")]
    teacher = prior["plan"]["teacher"]
    guard_source = read(base.HERE / "run-story-2-3-demo-server.py")
    for message, expected in (("预约时段与本次只读核验计划不符。", DENIAL), ("本次验证已中止，请保留证据，不要重放。", HALTED)):
        check(message in guard_source and sha256(message.encode("utf-8")).hexdigest() == expected,
              "Archived response fingerprint no longer matches the approved guard")
    check(teacher["mode"] == "submit_once" and len(posts) == 1 and posts[0]["path"] == teacher["path"]
          and posts[0]["role"] == "teacher" and posts[0]["account_id"] == prior["plan"]["role_ids"]["teacher"]
          and posts[0]["status"] == 403 and posts[0]["guard_rejected"] and not posts[0]["writes"]
          and posts[0]["body_sha256"] == DENIAL and not (PREV / "teacher-post-intent.txt").exists(),
          "Not a certified pre-write time rejection. Keep old run stopped and do not submit")
    check(any(e["at"] > posts[0]["at"] and e.get("body_sha256") == HALTED for e in events), "No recorded halt")
    check(any(e["role"] is None and e["path"] == base.LIST and e["method"] == "GET" and e["status"] == 302
              and e.get("location") == "/login/?next=/reservations/" and e.get("chrome") and not e["writes"]
              and not e["guard_rejected"] for e in events), "No retained anonymous redirect")
    files = [PREV / n for n in ("before.json", "browser-http.jsonl", "server.stdout.txt", "server.stderr.txt",
                                "listener-planned.json", "chrome-launch.json", "chrome-launches-requested.json")]
    files.extend([prior_acl, PREV / preflight / "app-acl.stdout.txt", Path(__file__).resolve()])
    state = {"original_run": PREV.name, "prior_listener": listener, "teacher_post": posts[0],
             "slot_beijing": [teacher["start"], teacher["end"]], "teacher_post_intent": False,
             "diagnosis": "teacher form slot differs from preflight; rejected before business view; later guard halted",
             "old_anonymous_redirect": True, "old_student_reads": len(reads), "evidence_sha256": {str(p.relative_to(base.ROOT.parents[1])): digest(p) for p in files}}
    return state, recovered, acl, reads, prior


def protect():
    check(not base.listeners(), "8003 is currently occupied; no process will be stopped by this tool")


def projection(data, now):
    import story23_formal_demo as demo
    return {"observed_beijing": now.astimezone(demo.BEIJING), "hashes": demo.snapshot(data),
            "reservations": [dict(id=r["id"], account_id=r["applicant_id"], device_id=r["equipment_id"], status=r["status"],
                                  start=r["start_at"].astimezone(demo.BEIJING), end=r["end_at"].astimezone(demo.BEIJING),
                                  effective=r["status"] == "approved" or (r["status"] == "pending" and r["start_at"] > now)) for r in data["reservations"]],
            "history_ids": [h["id"] for h in data["history"]]}


def serve(recovered, acl, reads, prior):
    protect()
    check(base.CHROME.is_file(), "Chrome not found")
    check(not any((RUN / n).exists() for n in ("before.json", "listener-planned.json")), "Recovery window has already started; use Chrome or Finish, not Serve")
    attempt = RUN / ("preflight-" + uuid4().hex[:12])
    attempt.mkdir()
    try:
        base.credentials()
        import story23_formal_demo as demo
        sample, now, data = base.database(attempt, "teacher-before", acl)
        db = projection(data, now)
        write(attempt / "current-db.json", db)
        role_ids = {k: v["account_id"] for k, v in sample["accounts"].items()}
        check(role_ids == prior["plan"]["role_ids"] and sample["missing_id"] == 2**62, "Approved account or missing-ID control changed")
        history = [h for h in data["history"] if h["reservation_id"] == 1]
        check(db["hashes"]["reservations"].get("1") == recovered["current_hashes"]["reservations"]["1"]
              and len(history) == 1 and demo.system_expiry(history[0]) and history[0]["id"] == recovered["history_ids"][0],
              "Previously certified student record changed")
        now = now.astimezone(demo.BEIJING)
        deadline = now + timedelta(minutes=20)
        horizon = deadline + timedelta(minutes=2)
        own = [r for r in data["reservations"] if r["applicant_id"] == role_ids["teacher"]]
        unsafe = [r["id"] for r in own if r["status"] == "pending" and r["start_at"] <= horizon]
        teacher = {"mode": "reuse", "reservation_id": min(r["id"] for r in own)} if own and not unsafe else {
            "mode": "read_only_unsafe" if own else "read_only_empty", "unsafe_ids": unsafe}
        plan = {"role_ids": role_ids, "expiry_mode": "already_expired", "deadline": deadline.isoformat(),
                "horizon": horizon.isoformat(), "observed": now.isoformat(), "teacher": teacher}
        protect()
        write(RUN / "before.json", {"plan": plan, "db": db, "preflight": attempt.name, "acl_sha256": digest(attempt / "acl.json"),
                                    "source_review_sha256": digest(RUN / RECEIPT)})
    except Exception as error:
        write(attempt / "failure.json", {"error": str(error) if type(error) in (ValueError, RuntimeError) else type(error).__name__})
        raise
    write(RUN / "listener-planned.json", {"pid": os.getpid(), "origin": base.ORIGIN, "deadline": deadline.isoformat()})
    base.RUN = RUN
    base.install_guard(plan, reads)
    globals()["FollowupGuard"] = base.FollowupGuard
    print(f"Preflight passed. Storage: {RUN}\nDeadline: {deadline.isoformat()}\nZero booking POST. Mode: {teacher['mode']}", flush=True)
    print(f"Live database receipt: {attempt / 'current-db.json'}", flush=True)
    if teacher["mode"] == "reuse":
        print(f"Teacher detail: {base.ORIGIN}/reservations/{teacher['reservation_id']}/result/", flush=True)
    with (RUN / "server.stdout.txt").open("x", encoding="utf-8", buffering=1) as stdout, \
         (RUN / "server.stderr.txt").open("x", encoding="utf-8", buffering=1) as stderr:
        from django.core.management import execute_from_command_line
        with redirect_stdout(stdout), redirect_stderr(stderr):
            handlers = [h for h in logging.getLogger("django.server").handlers if isinstance(h, logging.StreamHandler)]
            check(handlers, "Django server log handler missing")
            streams = [(h, h.setStream(stderr)) for h in handlers]
            try:
                execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8003", "--noreload"])
            finally:
                for h, stream in streams:
                    if stream is not None:
                        h.setStream(stream)


def chrome():
    planned = load(RUN / "listener-planned.json")
    check(base.listeners() == [("127.0.0.1:8003", planned["pid"])] and planned["origin"] == base.ORIGIN
          and datetime.now().astimezone() < datetime.fromisoformat(planned["deadline"]), "Recovery listener absent, mismatched or expired")
    stamp = RUN / "chrome-launch.json"
    if stamp.is_file():
        check(load(stamp)["pid"] == planned["pid"] and (RUN / "chrome-ready.json").is_file(), "Incomplete Chrome launch; preserve evidence")
        print("Use the two already opened login windows; no duplicate profiles.")
        return
    write(stamp, {"pid": planned["pid"], "roles": ["teacher", "admin"], "requested_at": datetime.now().astimezone()})
    for role in ("teacher", "admin"):
        path = Path(gettempdir()) / ("LabBooking-story23-readonly-" + role + "-" + uuid4().hex)
        subprocess.Popen([str(base.CHROME), f"--user-data-dir={path}", "--no-first-run", "--disable-sync", "--new-window", base.ORIGIN + "/login/"])
    write(RUN / "chrome-ready.json", {"complete": True})
    print("Opened separate teacher and admin login windows. No student or anonymous request needed.")


def finish(before, acl):
    protect()
    post = RUN / ("post-" + uuid4().hex[:12])
    post.mkdir()
    print(f"Postcheck evidence: {post}", flush=True)
    try:
        base.credentials()
        _, now, data = base.database(post, "teacher-after", acl)
        after = projection(data, now)
        write(post / "current-db.json", after)
        events = events_at(RUN)
        check(load(RUN / "chrome-ready.json")["complete"] is True and load(RUN / "chrome-launch.json")["pid"] == load(RUN / "listener-planned.json")["pid"], "Chrome receipt unbound")
        plan = before["plan"]
        teacher = plan["teacher"]

        def hits(role, route, code):
            return [e for e in events if e["role"] == role and e["path"] == route and e["status"] == code
                    and e["method"] == "GET" and e.get("chrome") and not e["guard_rejected"] and not e["writes"]]

        checks = {"all_business_rows_unchanged": after["hashes"] == before["db"]["hashes"],
                  "no_student_or_booking_post": all(e["role"] in {None, "teacher", "admin"}
                      and e["account_id"] == plan["role_ids"].get(e["role"]) and e["status"] < 500
                      and (e["method"] == "GET" or (e["method"] == "POST" and e["path"] in {"/login/", "/logout/"}))
                      and (not e["writes"] or set(e["writes"]) <= {"session", "last-login"} and e["path"] in {"/login/", "/logout/"})
                      for e in events),
                  "teacher_same_404": any(a.get("body_sha256") and a["body_sha256"] == b.get("body_sha256")
                                           for a in hits("teacher", base.FOREIGN, 404) for b in hits("teacher", base.MISSING, 404)),
                  "admin_no_entry_and_real_403": any(base.LIST not in e.get("links", [base.LIST])
                                                      for e in hits("admin", base.IDENTITY, 200)) and bool(hits("admin", base.LIST, 403)),
                  "anonymous_302_from_original_real_log": True}
        own_chain = None
        if teacher["mode"] == "reuse":
            route = f"/reservations/{teacher['reservation_id']}/result/"
            lists = hits("teacher", base.LIST, 200)
            own_chain = any(base.LIST in d.get("links", []) and any(l["at"] < d["at"] and route in l.get("links", []) for l in lists)
                            and any(l["at"] > d["at"] and route in l.get("links", []) for l in lists) for d in hits("teacher", route, 200))
            checks["teacher_existing_list_detail_return"] = own_chain
        result = {"checks": checks, "teacher_own_chain": own_chain, "teacher_mode": teacher["mode"],
                  "historical_post": "HTTP 403 pre-write; never replayed", "story_status": "review",
                  "formal_teacher_gap": None if own_chain else "Real teacher own list-detail-return not evidenced",
                  "request_log_sha256": digest(RUN / "browser-http.jsonl"), "before_sha256": digest(RUN / "before.json")}
        write(post / "result.json", result)
        with (post / "chrome-receipt.md").open("x", encoding="utf-8") as out:
            out.write("# Story 2.3 · 零预约 POST 恢复取证\n\n原学生及匿名证据沿用。教师原 403 不重放。Story 保持 review。\n\n")
            out.write(f"- 教师模式 `{teacher['mode']}`。教师本人链路 `{own_chain}`，未自动认定最终验收。\n")
            out.write("- [当前数据库](current-db.json) · [ACL](acl.json) · [断言结果](result.json)\n")
            out.writelines(f"- `{key}` — {'通过' if val else '缺证或不满足'}\n" for key, val in checks.items())
            out.write("\n| 北京时间 | 角色/ID | 请求 | HTTP | 写入 |\n| --- | --- | --- | --- | --- |\n")
            out.writelines(f"| {e['at']} | {e['role']}/{e['account_id']} | `{e['method']} {base.ORIGIN}{e['path']}` | {e['status']} | {e['writes']} |\n" for e in events)
        if not all(checks.values()):
            print("Missing: " + ", ".join(k for k, v in checks.items() if not v))
            return 1
        print(MARKER + ("; teacher own chain still unverified" if own_chain is None else ""))
        return 0
    except Exception as error:
        write(post / "failure.json", {"error": str(error) if type(error) in (ValueError, RuntimeError) else type(error).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["Inspect", "Serve", "Chrome", "Finish"])
    phase = parser.parse_args().phase
    state, recovered, acl, reads, prior = review()
    RUN.mkdir(exist_ok=True)
    source = RUN / RECEIPT
    if source.exists():
        check(load(source) == state, "Archived evidence or recovery utility differs")
    else:
        write(source, state)
    if phase == "Inspect":
        print(f"Archived rejected POST and old anonymous 302. 8003 listeners: {base.listeners()}. {source}")
        return 0
    check(sys.version_info[:3] == (3, 13, 17), "Use original .venv Python 3.13.17")
    if phase == "Serve":
        serve(recovered, acl, reads, prior)
        return 0
    before = load(RUN / "before.json")
    check(before["source_review_sha256"] == digest(source) and re.fullmatch(r"preflight-[0-9a-f]{12}", before["preflight"])
          and before["acl_sha256"] == digest(RUN / before["preflight"] / "acl.json"), "Recovery source or preflight changed")
    if phase == "Chrome":
        chrome()
        return 0
    return finish(before, acl)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        print(f"Story 2.3 read-only recovery stopped: {error}", file=sys.stderr)
        raise SystemExit(1) from None
