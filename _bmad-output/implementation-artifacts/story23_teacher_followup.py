"""One guarded Story 2.3 continuation. The original student evidence is read, never replayed."""
import argparse
from contextvars import ContextVar
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
from uuid import uuid4


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT.parents[1] / "outputs/story-2-3-formal-20261127-120858-648-0dcaa5b4/smoke-20261127-153153-150-bcfae1cb"
FAILED = OLD / "finish-20261127-160523-638-de559216"
RECOVERY = OLD / "recovery-readonly-20261127-161757-129445-f93c0b3c"
RUN = OLD / "teacher-followup-20261127-161757-f93c0b3c"
ORIGIN = "http://127.0.0.1:8003"
LIST = "/reservations/"
IDENTITY = "/identity/"
FOREIGN = "/reservations/1/result/"
MISSING = "/reservations/4611686018427387904/result/"
CHROME = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe"
SUMMARY = runpy.run_path(str(HERE / "fill-story-2-3-chrome-receipt.py"))
read, digest, check = (SUMMARY[k] for k in ("read", "digest", "require"))
FILES = [OLD / "browser-http.jsonl", FAILED / "sample-after-unverified.json", RECOVERY / "current-acl.json",
         RECOVERY / "current-db.json", Path(__file__).resolve(), HERE / "read-story-2-3-audit-acl.ps1"]


def load(path):
    return json.loads(read(path))


def write(path, value):
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=True, sort_keys=True, default=str)
        out.write("\n")


def original():
    SUMMARY["render"](OLD)
    archive = SUMMARY["archived_failure"](OLD, FAILED)
    recovered = load(RECOVERY / "current-db.json")
    old_acl = load(FAILED / "sample-after-unverified.json")
    acl = load(RECOVERY / "current-acl.json")
    check(recovered["failed_finish"] == FAILED.name and recovered["failed_snapshot_sha256"] == digest(FILES[1])
          and recovered["read_only"] is True and recovered["current_hashes"] == archive["after_hashes"]
          and recovered["student_history_exact"] is True and recovered["history_ids"] == [archive["history_id"]]
          and recovered["acl_state"] == acl["state"] == "EXACT"
          and all(acl[key] == old_acl[key] for key in ("identity", "migrations", "effective_matrix", "explicit_acl", "prior_acl_sha256")),
          "Recovered evidence does not match archived student/delta/ACL")
    prior = [json.loads(line) for line in read(FILES[0]).splitlines()]
    reads = [(e["student_snapshot"], e["writes"]) for e in prior if "student_snapshot" in e]
    return recovered, acl, reads


def listeners():
    out = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], encoding="ascii", errors="replace")
    return [(m[1], int(m[2])) for m in re.finditer(r"(?m)^\s*TCP\s+(\S+:8003)\s+\S+\s+LISTENING\s+(\d+)\s*$", out)]


def inputs():
    return {p.name: digest(p) for p in FILES}


def credentials():
    sys.path.insert(0, str(ROOT))
    from lab_booking.database_config import reject_connection_overrides
    reject_connection_overrides()
    check(not any(x in os.environ for x in ("PYTHONHOME", "PYTHONPATH")), "Conflicting Python environment")
    local = Path(os.environ["LOCALAPPDATA"]) / "LabBooking"
    pf = Path(os.environ.get("PGPASSFILE") or local / "PostgreSQL17/pgpass.conf")
    check(pf.is_absolute() and pf.is_file() and not pf.resolve().is_relative_to(ROOT), "Protected passfile unavailable")
    os.environ.update(PGPASSFILE=str(pf), LAB_BOOKING_DB_MODE="runtime", DJANGO_SETTINGS_MODULE="lab_booking.settings",
                      LAB_BOOKING_SECRET_KEY=uuid4().hex + uuid4().hex,
                      STORY23_ACCOUNTS_MANIFEST=str(local / "Protected/accounts.json"))


def database(out, phase, previous):
    import story23_formal_demo as demo
    reader = runpy.run_path(str(HERE / "read-story-2-3-formal.py"))
    path = reader["LEGACY"]
    check(digest(path).lower() == reader["LEGACY_HASH"], "Reviewed reader changed")
    argv = sys.argv[:]
    try:
        sys.argv = [str(path), phase, str(out)]
        legacy = runpy.run_path(str(path), run_name="story23_readers_only")
    finally:
        sys.argv = argv

    def protect(c):
        c.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY")
        c.execute("SET LOCAL statement_timeout = '12s'")
        check(legacy["one"](c, "SELECT current_setting('transaction_read_only') AS mode")["mode"] == "on", "Not read only")

    with legacy["connect"](legacy["APP"]) as app, app.transaction():
        protect(app)
        state, acl = reader["certify"](legacy, app, phase)
        write(out / "acl.json", acl)
        check(state == "EXACT" and acl == previous, "ACL or schema differs from actual recovery")
        opening = phase == "teacher-before"
        sample = reader["candidate"](legacy, app) if opening else None
    with legacy["connect"](legacy["MIGRATOR"]) as owner, owner.transaction():
        protect(owner)
        legacy["identity"](owner, legacy["MIGRATOR"])
        now = legacy["one"](owner, "SELECT clock_timestamp() AS at")["at"]
        data = demo.tables(legacy, owner)
    with (out / "app-acl.stdout.txt").open("xb") as stdout, (out / "app-acl.stderr.txt").open("xb") as stderr:
        process = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
                                  str(HERE / "read-story-2-3-audit-acl.ps1")],
                                 stdout=stdout, stderr=stderr, timeout=18, creationflags=subprocess.CREATE_NO_WINDOW)
    lines = read(out / "app-acl.stdout.txt").splitlines()
    check(process.returncode == 0 and lines.count("ACL_RESULT=EXACT_COLUMNS_PRESENT") == 1
          and lines.count("STORY23_ACL_READONLY_OK") == 1, "Independent app ACL read did not pass")
    return sample, now, data


class Links(HTMLParser):
    def __init__(self, response):
        super().__init__()
        self.paths = set()
        self.feed(response.content.decode(response.charset, errors="replace"))

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href")
        if tag == "a" and href and (href == LIST or re.fullmatch(r"/reservations/[0-9]+/result/", href)):
            self.paths.add(href)


def install_guard(plan, reads):
    from django.conf import settings
    from django.http import HttpResponseForbidden
    spec = importlib.util.spec_from_file_location("original_story23_guard", HERE / "run-story-2-3-demo-server.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.RUN, guard.PLAN = RUN, plan
    guard.STUDENT_READS[:] = reads  # copied machine observations, no student requests in this run
    collect = ContextVar("story23_collect")
    save = guard.record
    guard.record = lambda event: collect.get().append(event)

    class FollowupGuard(guard.AuthorizedGuard):
        def __call__(self, request):
            rows = []
            token = collect.set(rows)
            try:
                response = super().__call__(request)
                for row in rows:
                    row["chrome"] = bool(re.search(r"\bChrome/\d+", request.META.get("HTTP_USER_AGENT", "")))
                    row["guard_rejected"] = getattr(request, "_s23_rejected", False)
                    if response.status_code in {403, 404} and not response.streaming:
                        row["body_sha256"] = sha256(response.content).hexdigest()
                    if response.status_code in {200, 201} and not response.streaming and (
                            request.path in {IDENTITY, LIST} or guard.DETAIL.fullmatch(request.path) or response.status_code == 201):
                        row["links"] = sorted(Links(response).paths)
                    if response.status_code == 302:
                        location = response.get("Location", "")
                        if location in {IDENTITY, "/login/", "/login/?next=/reservations/"}:
                            row["location"] = location
                    save(row)
                return response
            finally:
                collect.reset(token)

        def process_view(self, request, view, args, kwargs):
            def deny():
                request._s23_rejected = True
                return HttpResponseForbidden("本次教师补证不包含此操作。")

            if request.get_host() != "127.0.0.1:8003" or getattr(request.user, "role", None) == "student":
                return deny()
            if request.method == "POST" and request.path == "/login/":
                from accounts.forms import AccountAuthenticationForm
                try:
                    name = AccountAuthenticationForm.base_fields["username"].clean(request.POST.get("username"))
                except Exception:
                    return deny()
                result = guard.query("SELECT id, role, is_active FROM public.accounts_user WHERE username=%s", (name,))
                if len(result) != 1 or not result[0][2] or result[0][1] not in {"teacher", "admin"} or plan["role_ids"].get(result[0][1]) != result[0][0]:
                    return deny()
            response = super().process_view(request, view, args, kwargs)
            request._s23_rejected = response is not None
            return response

    globals()["FollowupGuard"] = FollowupGuard
    settings.MIDDLEWARE = [*settings.MIDDLEWARE, "__main__.FollowupGuard"]


def serve(recovered, acl, reads):
    check(not listeners() and CHROME.is_file(), "8003 is occupied or Chrome is unavailable")
    RUN.mkdir(exist_ok=True)
    check(not any((RUN / p).exists() for p in ("before.json", "teacher-post-intent.txt", "listener-planned.json")),
          "A guarded window already exists. No second Serve or reservation submission.")
    pre = RUN / ("preflight-" + uuid4().hex[:12])
    pre.mkdir()
    try:
        credentials()
        import story23_formal_demo as demo
        sample, now, data = database(pre, "teacher-before", acl)
        original_plan = load(OLD / "sample-before.json")["sample"]["demo"]
        plan = demo.plan(sample, data, now)
        check(plan["role_ids"] == original_plan["role_ids"] and plan["expiry_mode"] == "already_expired"
              and plan["history1"] == recovered["history_ids"] and sample["missing_id"] == 2**62,
              "Approved accounts, negative control or student lineage differs")
        baseline = recovered["current_hashes"]
        check(all(plan["hashes"][k] == baseline[k] for k in ("accounts", "equipment", "history"))
              and all(str(row["id"]) in baseline["reservations"] or row["applicant_id"] == plan["role_ids"]["teacher"] for row in data["reservations"])
              and all(plan["hashes"]["reservations"].get(rid) == value for rid, value in baseline["reservations"].items()),
              "Unexplained database drift since the read-only recovery")
        check(not listeners(), "8003 became occupied during preflight")
        write(RUN / "before.json", {"source_hashes": inputs(), "plan": plan, "missing_id": sample["missing_id"],
                                    "preflight": pre.name, "preflight_acl_sha256": digest(pre / "acl.json"),
                                    "teacher_reservations": sample["accounts"]["teacher"]["reservations"]})
    except Exception as error:
        write(pre / "failure.json", {"error": str(error) if type(error) in (ValueError, RuntimeError) else type(error).__name__})
        raise
    write(RUN / "listener-planned.json", {"pid": os.getpid(), "origin": ORIGIN, "deadline": plan["deadline"]})
    print(f"Evidence: {RUN}\nBeijing deadline: {plan['deadline']}", flush=True)
    teacher = plan["teacher"]
    print((f"REUSE #{teacher['reservation_id']} — no POST\nDetail: {ORIGIN}/reservations/{teacher['reservation_id']}/result/" if teacher["mode"] == "reuse" else
           f"ONE POST: {ORIGIN}{teacher['path']}\nDevice: {teacher['device_number']}\nBeijing: {teacher['form_start']} -> {teacher['form_end']}"), flush=True)
    print(f"Login: {ORIGIN}/login/\nList and return: {ORIGIN}{LIST}\nForeign: {ORIGIN}{FOREIGN}\nMissing: {ORIGIN}{MISSING}", flush=True)
    check(not listeners(), "8003 became occupied during preflight")
    install_guard(plan, reads)
    # Preserve Django access output independently of the guarded structured log.
    with (RUN / "server.stdout.txt").open("x", encoding="utf-8", buffering=1) as stdout, \
         (RUN / "server.stderr.txt").open("x", encoding="utf-8", buffering=1) as stderr:
        from contextlib import redirect_stderr, redirect_stdout
        from django.core.management import execute_from_command_line
        print("Preflight passed. Use the separate Chrome command. Ctrl+C here when done.", flush=True)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # django.setup() during account preflight created its handler before stderr was redirected.
            handlers = [h for h in logging.getLogger("django.server").handlers if isinstance(h, logging.StreamHandler)]
            check(bool(handlers), "Django access handler unavailable")
            streams = [(h, h.setStream(stderr)) for h in handlers]
            try:
                execute_from_command_line(["manage.py", "runserver", "127.0.0.1:8003", "--noreload"])
            finally:
                for h, stream in streams:
                    if stream is not None:
                        h.setStream(stream)


def chrome():
    planned = load(RUN / "listener-planned.json")
    check(listeners() == [("127.0.0.1:8003", planned["pid"])], "Exact new 8003 listener not ready")
    check(datetime.now().astimezone() < datetime.fromisoformat(planned["deadline"]), "Fresh verification window expired")
    check(planned["origin"] == ORIGIN and CHROME.is_file(), "Unexpected listener or browser")
    command = "(Get-Item -LiteralPath '" + str(CHROME).replace("'", "''") + "').VersionInfo.ProductVersion"
    version = subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                      encoding="ascii", creationflags=subprocess.CREATE_NO_WINDOW, timeout=8).strip()
    check(re.fullmatch(r"\d+(?:\.\d+){3}", version), "Unexpected Chrome product version")
    profile = RUN / "chrome-launch.json"
    write(profile, {"origin": ORIGIN, "pid": planned["pid"], "roles": ["teacher", "admin", "anonymous"],
                    "chrome_version": version,
                    "requested_at": datetime.now().astimezone().isoformat()})
    import tempfile
    for role, route in (("teacher", "/login/"), ("admin", "/login/"), ("anonymous", LIST)):
        path = Path(tempfile.gettempdir()) / f"LabBooking-story23-followup-{role}-{uuid4().hex}"
        subprocess.Popen([str(CHROME), f"--user-data-dir={path}", "--no-first-run", "--disable-sync",
                          "--new-window", ORIGIN + route])
    write(RUN / "chrome-launches-requested.json", {"complete": True})
    print("Windows requested in order: teacher login, admin login, anonymous redirect. Keep the same origin.")


def assess(plan, now, data, events):
    import story23_formal_demo as demo
    known, actual = plan["hashes"], demo.snapshot(data)
    flags = {}

    def hits(role, path, status, method="GET"):
        return [e for e in events if (e["role"], e["path"], e["status"], e["method"]) == (role, path, status, method)
                and e.get("chrome") and not e.get("guard_rejected")]

    added = set(actual["reservations"]) - set(known["reservations"])
    keep = {k: v for k, v in actual["reservations"].items() if k not in added}
    flags["student_and_all_existing_rows_unchanged"] = (keep == known["reservations"] and all(actual[k] == known[k] for k in ("accounts", "equipment", "history")))
    t = plan["teacher"]
    once = t["mode"] == "submit_once"
    rows = [r for r in data["reservations"] if str(r["id"]) in added]
    row = rows[0] if len(rows) == 1 else None
    tid = row["id"] if once and row else t.get("reservation_id")
    route = f"/reservations/{tid}/result/" if tid else None
    teacher_rows = [r for r in data["reservations"] if r["applicant_id"] == plan["role_ids"]["teacher"]]
    flags["teacher_delta"] = ((row is not None and row["applicant_id"] == plan["role_ids"]["teacher"]
                              and row["equipment_id"] == t["device_id"] and row["status"] == "pending"
                              and row["start_at"] == demo.at(t["start"]) and row["end_at"] == demo.at(t["end"])
                              and demo.at(plan["observed"]) <= row["applied_at"] < row["start_at"]
                              and row["applied_at"] <= demo.at(plan["horizon"])) if once else
                              not added and any(r["id"] == tid for r in teacher_rows))
    history = [h for h in data["history"] if h["reservation_id"] == 1]
    flags["student_history_unchanged"] = len(history) == 1 and demo.system_expiry(history[0]) and [h["id"] for h in history] == plan["history1"]
    posts = [e for e in events if e["method"] == "POST" and e["path"].endswith("/reserve/")]
    flags["teacher_form_and_single_201_or_zero_post_reuse"] = (
        len(posts) == 1 and posts[0] in hits("teacher", t.get("path"), 201, "POST")
        and posts[0]["writes"] == ["teacher-create"] and any(g["at"] < posts[0]["at"] for g in hits("teacher", t["path"], 200))
        and {LIST, route} <= set(posts[0].get("links", [])) and (RUN / "teacher-post-intent.txt").is_file()
    ) if once else not posts and not (RUN / "teacher-post-intent.txt").exists()
    teacher_identity = hits("teacher", IDENTITY, 200)
    flags["teacher_identity_and_login"] = any(LIST in e.get("links", []) for e in teacher_identity) and any(
        e.get("location") == IDENTITY for e in hits("teacher", "/login/", 302, "POST"))
    lists = hits("teacher", LIST, 200)
    details = hits("teacher", route, 200)
    flags["teacher_list_detail_return"] = any(
        LIST in d.get("links", []) and any(l["at"] < d["at"] and route in l.get("links", []) for l in lists)
        and any(l["at"] > d["at"] and route in l.get("links", []) for l in lists) for d in details)
    flags["teacher_same_404"] = any(a.get("body_sha256") and a.get("body_sha256") == b.get("body_sha256") and not a["writes"] and not b["writes"]
                                    for a in hits("teacher", FOREIGN, 404) for b in hits("teacher", MISSING, 404))
    flags["admin_no_entry_and_real_403"] = any(LIST not in e.get("links", [LIST]) for e in hits("admin", IDENTITY, 200)) and any(
        not e["writes"] for e in hits("admin", LIST, 403))
    flags["anonymous_booking_redirect"] = any(e.get("location") == "/login/?next=/reservations/" and not e["writes"]
                                               for e in hits(None, LIST, 302))
    flags["no_student_replay_no_other_writes_or_server_failure"] = bool(events) and all(
        e["role"] in {None, "teacher", "admin"} and e["account_id"] == plan["role_ids"].get(e["role"])
        and demo.at(plan["observed"]) <= demo.at(e["at"]) <= now and e["status"] < 500 and
        set(e["writes"]) <= ({"teacher-create"} if e in posts else {"session", "last-login"} if e["path"] in {"/login/", "/logout/"} else set())
        for e in events)
    return flags, dict(teacher_mode=t["mode"], teacher_id=tid, teacher_new_row=row if once else None,
                       teacher_own_statuses=[{"id": r["id"], "status": r["status"], "effective": r["status"] == "approved"
                                              or (r["status"] == "pending" and r["start_at"] > now)} for r in teacher_rows],
                       student_occupancy=False if flags["student_and_all_existing_rows_unchanged"] and flags["student_history_unchanged"] else None,
                       history_ids=[h["id"] for h in history], changes_added=sorted(added), hashes=actual)


def finish(before, acl):
    check(not listeners(), "Stop the supplementary 8003 server first")
    out = RUN / ("post-" + datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex[:8])
    out.mkdir()
    try:
        credentials()
        launch = load(RUN / "chrome-launch.json")
        check(launch["pid"] == load(RUN / "listener-planned.json")["pid"]
              and load(RUN / "chrome-launches-requested.json")["complete"] is True, "Chrome launch evidence unbound")
        _, now, data = database(out, "teacher-after", acl)
        path = RUN / "browser-http.jsonl"
        events = [json.loads(line) for line in read(path).splitlines()]
        flags, result = assess(before["plan"], now, data, events)
        from collections import Counter
        django = Counter((m[1], m[2].partition("?")[0], int(m[3])) for m in re.finditer(
            r'"(GET|POST) (\S+) HTTP/[^ ]+" (\d{3}) \d+', read(RUN / "server.stderr.txt")))
        flags["django_log_matches_guard_log"] = django == Counter((e["method"], e["path"], e["status"]) for e in events)
        write(out / "result.json", {"checks": flags, "result": result, "observed_beijing": now.astimezone(SUMMARY["BEIJING"]),
                                    "raw_http_sha256": digest(path), "before_sha256": digest(RUN / "before.json"),
                                    "acl_sha256": digest(out / "acl.json"), "independent_app_acl_sha256": digest(out / "app-acl.stdout.txt")})
        with (out / "chrome-receipt.md").open("x", encoding="utf-8") as f:
            f.write("# Story 2.3 教师与权限补证\n\n原学生 #1 独立证据沿用，未再发学生请求。\n\n")
            f.write("- 数据库和 ACL 结果见 [result.json](result.json) 和 [acl.json](acl.json)。\n")
            f.write(f"- 教师模式 `{result['teacher_mode']}`，预约 ID `{result['teacher_id']}`，新增 ID `{result['changes_added']}`。\n")
            f.write("- 正式人工结论未代填。仅确认教师页面显示、导航体验及团队验收结论。\n\n")
            f.writelines(f"- `{key}` — {'通过' if value else '缺证或不满足'}\n" for key, value in flags.items())
            f.write("\n| 北京时间 | 角色/ID | 方法 URL | HTTP | 重定向/写入 |\n| --- | --- | --- | --- | --- |\n")
            for e in events:
                f.write(f"| {e['at']} | {e['role']}/{e['account_id']} | `{e['method']} {ORIGIN}{e['path']}` | {e['status']} | {e.get('location', '')} {e['writes']} |\n")
        if not all(flags.values()):
            print("Missing or rejected: " + ", ".join(k for k, value in flags.items() if not value))
            return 1
        write(out / "verified.json", {"marker": "STORY23_TEACHER_FOLLOWUP_MACHINE_OK"})
        print("STORY23_TEACHER_FOLLOWUP_MACHINE_OK — human outcome not implied")
        return 0
    except Exception as error:
        write(out / "failure.json", {"error": str(error) if type(error) in (ValueError, RuntimeError) else type(error).__name__})
        raise
    finally:
        print(f"Postcheck evidence: {out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["InspectArchive", "Serve", "Chrome", "Finish"])
    phase = parser.parse_args().phase
    recovered, acl, reads = original()
    if phase == "InspectArchive":
        print(f"Bound archive and recovery, {len(reads)} student reads, {recovered['observed_beijing']}; ACL EXACT; no browser or DB calls")
        return 0
    check(sys.version_info[:3] == (3, 13, 17), "Use the original project .venv Python 3.13.17")
    if phase == "Serve":
        serve(recovered, acl, reads)
        return 0
    before = load(RUN / "before.json")
    check(before["source_hashes"] == inputs(), "Follow-up or archived evidence changed after preflight")
    check(re.fullmatch(r"preflight-[0-9a-f]{12}", before["preflight"])
          and before["preflight_acl_sha256"] == digest(RUN / before["preflight"] / "acl.json"), "Preflight ACL evidence changed")
    if phase == "Chrome":
        chrome()
        return 0
    return finish(before, acl)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"Story 2.3 continuation stopped: {error}", file=sys.stderr)
        raise SystemExit(1) from None
