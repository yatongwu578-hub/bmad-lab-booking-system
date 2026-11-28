"""Story 2.4 scope adapter for the existing W01 no-business-write smoke guard."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
from wsgiref.simple_server import WSGIRequestHandler, make_server

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
W01 = runpy.run_path(str(HERE / "story-2-5-review-support/serve-story-2-5-w01-smoke.py"))
need, now, sql_kind, ready = (W01[key] for key in ("need", "utcnow", "sql_kind", "w01_ready"))
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--accounts", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--stop", type=Path)
    args = parser.parse_args()
    need(os.getenv("LAB_BOOKING_DB_MODE") == "runtime", "Formal runtime mode is required.")
    inspection = read(args.inspection)
    identity = inspection["identity"]
    need((identity["database"], identity["login"], identity["role"], identity["host"],
          identity["port"], identity["version"], identity["read_only"]) ==
         ("lab_booking", "lab_booking_app", "lab_booking_app", "127.0.0.1", 5433, "170012", "on")
         and inspection["acl_result"] == "EXACT_COLUMNS_PRESENT" and not inspection["missing"]
         and inspection["business_snapshot"] and not inspection["port_in_use_at_inspection"],
         "No exact read-only ACL/snapshot qualification.")
    deadline = datetime.fromisoformat(inspection["samples"]["safe_until"])
    need(now() < deadline, "Formal safe window has expired.")
    from django.db import DatabaseError, connection, transaction
    from lab_booking.wsgi import application
    from accounts.models import User
    from reservations.models import Reservation, ReservationStatus as Status

    if args.accounts:
        need(args.baseline is not None and not args.events, "Account preflight requires certified migration baseline.")
        W01["check_accounts"](args.accounts)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL statement_timeout = '5s'")
                cursor.execute("SELECT clock_timestamp(), current_setting('transaction_isolation')")
                clock, isolation = cursor.fetchone()
                need(clock < deadline and isolation == "read committed", "Formal plan is late or isolation differs.")
                cursor.execute('SELECT app,name FROM public.django_migrations ORDER BY app COLLATE "C",name COLLATE "C"')
                migrations = [list(row) for row in cursor.fetchall()]
                need(migrations == read(args.baseline)["schema"][1], "Migration ledger differs; no migration authorized.")
            actors = {row["role"]: User.objects.filter(username=User.normalize_username(row["username"].strip()),
                      role=row["role"], is_active=True).values_list("pk", flat=True).get() for row in read(args.accounts)}
            applicants = {role: actors[role] for role in ("student", "teacher")}
            candidates, risks = [], {}
            for role, actor in applicants.items():
                owned = Reservation.objects.filter(applicant_id=actor)
                due = owned.filter(status=Status.PENDING, start_at__lte=deadline).count()
                risks[role] = due
                selected = owned.filter(status__in=(Status.PENDING, Status.APPROVED), start_at__gt=deadline
                                        ).order_by("start_at", "pk").values_list("pk", flat=True).first()
                if selected:
                    candidates.append((due != 0, role, selected))
            if candidates:
                unsafe_list, owner, target = min(candidates)
                outsider = next(role for role in applicants if role != owner)
            else:
                owner, unsafe_list = None, True
                existing = Reservation.objects.order_by("pk").values_list("pk", "applicant_id").first()
                target = existing[0] if existing else None
                outsider = next(role for role, actor in applicants.items() if not existing or actor != existing[1])
            latest = Reservation.objects.order_by("-pk").values_list("pk", flat=True).first() or 0
            plan = {"inspection_sha256": SHA(args.inspection), "port": inspection["desired_port"],
                    "deadline": deadline.isoformat(), "as_of": clock.isoformat(), "isolation": isolation,
                    "migrations": migrations, "existing_target": target, "absent": latest + 1,
                    "owner_role": owner, "deny_role": outsider, "list_safe": not unsafe_list,
                    "list_risk_to_deadline": risks}
        with args.plan.open("x", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False)
        print("STORY24_FORMAL_PLAN_OK")
        return

    plan = read(args.plan)
    need(args.events and args.stop and not args.stop.exists() and plan["inspection_sha256"] == SHA(args.inspection)
         and plan["port"] == inspection["desired_port"] and plan["deadline"] == deadline.isoformat(),
         "The guarded routes are not bound to this inspection.")
    pk = plan["existing_target"]
    reads = {"/identity/", f'/reservations/{plan["absent"]}/cancel/'}
    if pk:
        reads.add(f"/reservations/{pk}/cancel/")
    if plan["owner_role"]:
        reads.add(f"/reservations/{pk}/result/")
        if plan["list_safe"]:
            reads.add("/reservations/")
    account = {"/login/", "/logout/"}

    class Quiet(WSGIRequestHandler):
        def log_message(self, *_):
            pass

    with args.events.open("x", encoding="utf-8") as out:
        def event(**data):
            out.write(json.dumps({"at": now().isoformat(), **data}) + "\n")
            out.flush()

        def guard(environ, start_response):
            if now() < deadline:
                response = ready(environ, start_response)
                if response is not None:
                    return response
            method, path, query = (environ.get(key, "") for key in ("REQUEST_METHOD", "PATH_INFO", "QUERY_STRING"))
            status, blocked, technical, business = "500", [], [], []
            try:
                if not (now() < deadline and ((method == "GET" and path in reads and not query)
                        or (path in account and method in {"GET", "POST"} and (not query or
                            (method == "GET" and path == "/login/" and len(query) <= 256 and query.startswith("next=")))))):
                    blocked.append("path-or-window")
                    status = "409"
                    start_response("409 Conflict", [("Content-Type", "text/plain; charset=utf-8")])
                    return [b"Outside the inspected no-write smoke scope."]

                def execute(invoke, sql, params, many, context):
                    kind = sql_kind(method, path, sql, many)
                    if kind == "blocked":
                        blocked.append("sql-write-or-unclassified")
                        raise DatabaseError("Formal smoke rejected non-technical DML or unknown SQL.")
                    if kind in {"session", "last_login"}:
                        technical.append(kind)
                    if kind in {"business-read", "business-lock"}:
                        business.append(kind)
                    return invoke(sql, params, many, context)

                def respond(line, headers, exc_info=None):
                    nonlocal status
                    status = line.split(" ", 1)[0]
                    return start_response(line, headers, exc_info)

                with connection.execute_wrapper(execute):
                    result = application(environ, respond)
                    try:
                        return list(result)
                    finally:
                        if hasattr(result, "close"):
                            result.close()
            finally:
                if path in reads or path in account or path.endswith("/cancel/"):
                    event(event="document", method=method, path=path, status=int(status),
                          query_sha256=hashlib.sha256(("?" + query).encode()).hexdigest() if query else None,
                          guard_blocked=blocked, technical=technical, business=business)

        with make_server("127.0.0.1", plan["port"], guard, handler_class=Quiet) as server:
            server.timeout = 0.5
            event(event="ready", pid=os.getpid(), port=plan["port"], plan_sha256=SHA(args.plan))
            print("STORY24_FORMAL_SERVER_READY", flush=True)
            try:
                while now() < deadline and not args.stop.exists():
                    server.handle_request()
            finally:
                event(event="stop")


if __name__ == "__main__":
    main()
