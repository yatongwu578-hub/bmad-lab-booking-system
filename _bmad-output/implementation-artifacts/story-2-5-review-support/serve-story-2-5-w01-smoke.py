"""Loopback-only, no-business-write W01 formal smoke server. Not run by inspection."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server


def need(condition, message):
    if not condition:
        raise SystemExit(message)


def utcnow():
    return datetime.now(timezone.utc)


def w01_ready(environ, start_response):
    """Tool-only liveness probe. No Django, SQL, account or business data."""
    if (environ.get("REQUEST_METHOD") == "HEAD" and environ.get("PATH_INFO") == "/__w01_ready"
            and not environ.get("QUERY_STRING")):
        start_response("204 No Content", [("X-W01-Ready", str(os.getpid())), ("Cache-Control", "no-store")])
        return []
    return None


def hashed(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SESSION_WRITE = re.compile(r'^(?:INSERT INTO|UPDATE|DELETE FROM) "django_session"(?:\s|\().*$', re.IGNORECASE)
LAST_LOGIN = re.compile(r'^UPDATE "accounts_user" SET "last_login" = %s '
                        r'WHERE "accounts_user"\."id" = %s$', re.IGNORECASE)
BUSINESS_SQL = re.compile(r'\b(?:equipment_equipment|reservations_reservation|audit_operationhistory)\b', re.IGNORECASE)


def sql_kind(method, path, sql, many=False):
    normalized = " ".join(sql.strip().split())
    if many or ";" in normalized:
        return "blocked"
    if normalized.startswith("SELECT ") and not re.search(
            r'\b(?:setval|nextval|set_config|lo_[a-z_]+|dblink[a-z_]*)\s*\(', normalized, re.IGNORECASE):
        if re.search(r'\bFOR (?:NO KEY )?UPDATE\b', normalized, re.IGNORECASE):
            return "business-lock" if BUSINESS_SQL.search(normalized) else "blocked"
        return "business-read" if BUSINESS_SQL.search(normalized) else "read"
    if method == "POST" and path in {"/login/", "/logout/"}:
        if SESSION_WRITE.fullmatch(normalized):
            return "session"
        if path == "/login/" and LAST_LOGIN.fullmatch(normalized):
            return "last_login"
    return "blocked"


def check_accounts(path):
    try:
        from django.contrib.auth.hashers import check_password, get_hasher, identify_hasher
        from django.db import connection, transaction
        from accounts.models import User

        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        preferred = get_hasher()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            for role in ("student", "teacher", "admin"):
                item, = (row for row in rows if row["role"] == role)
                name = User.normalize_username(item["username"].strip())
                active = User.objects.get(username=name, role=role, is_active=True)
                hasher = identify_hasher(active.password)
                if (active.is_staff or active.is_superuser or hasher.algorithm != preferred.algorithm
                        or preferred.must_update(active.password) or not check_password(item["password"], active.password)):
                    raise ValueError("Account preflight mismatch")
    except Exception:
        raise SystemExit("Formal account preflight failed: check the existing protected manifest and runtime account status.") from None
    print("STORY25_W01_ACCOUNTS_READONLY_OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", type=Path)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--stop-file", type=Path)
    parser.add_argument("--check-accounts", type=Path)
    args = parser.parse_args()
    need(os.environ.get("LAB_BOOKING_DB_MODE") == "runtime"
         and os.environ.get("DJANGO_SETTINGS_MODULE", "lab_booking.settings") == "lab_booking.settings",
         "Only the existing runtime connection and settings are allowed.")
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    if args.check_accounts:
        from lab_booking.wsgi import application
        check_accounts(args.check_accounts)
        return
    need(args.inspection and args.events and not (args.stop_file and args.stop_file.exists()),
         "Missing formal inspection/events or stop flag already exists.")
    plan = json.loads(args.inspection.read_text(encoding="utf-8-sig"))
    identity = plan["identity"]
    need(identity["database"] == "lab_booking" and identity["role"] == identity["login"] == "lab_booking_app"
         and identity["host"] == "127.0.0.1" and identity["port"] == 5433
         and identity["version"] == "170012" and identity["read_only"] == "on"
         and plan["acl_result"] == "EXACT_COLUMNS_PRESENT" and plan["missing"] == []
         and plan["business_snapshot"], "Requires exact W01 inspection with a read-only pre-smoke snapshot.")
    sample = plan["samples"]
    need(all(sample["active_roles"].get(role, 0) > 0 for role in ("student","teacher","admin")),
         "The reviewed formal database does not have one active account per business role.")
    deadline = datetime.fromisoformat(sample["safe_until"])
    need(utcnow() < deadline, "Preflight window expired; collect a new read-only snapshot.")
    port = plan["desired_port"]
    need(1024 <= port <= 65535 and not plan["port_in_use_at_inspection"], "Preflight port was occupied.")
    from django.db import DatabaseError, connection
    from lab_booking.wsgi import application

    manageable = "/reservations/manage/"
    entry = sample.get("filter")
    detail_ids = set()
    detail = sample.get("detail")
    if detail:
        detail_ids.add(int(detail["id"]))
    if entry and entry["detail_id"] is not None:
        detail_ids.add(int(entry["detail_id"]))
    detail_paths = {f"{manageable}{pk}/" for pk in detail_ids}
    account_paths = {"/login/", "/logout/", "/identity/"}
    with args.events.open("x", encoding="utf-8") as stream:
        def event(payload):
            stream.write(json.dumps({"at": utcnow().isoformat(), **payload}, ensure_ascii=False) + "\n")
            stream.flush()

        def scoped(path, raw):
            if path in account_paths:
                return True
            params = parse_qs(raw, keep_blank_values=True, max_num_fields=8)
            if path == manageable and not params:
                return sample["full_unsafe_pending"] == 0
            permitted_filter = entry and params == {"equipment": [entry["number"]]}
            if path == manageable:
                return bool(permitted_filter)
            return path in detail_paths and (not params or bool(permitted_filter))

        def guard(environ, start_response):
            if utcnow() < deadline:
                ready = w01_ready(environ, start_response)
                if ready is not None:
                    return ready
            path = environ.get("PATH_INFO", "")
            query = environ.get("QUERY_STRING", "")
            method = environ.get("REQUEST_METHOD", "")
            allowed = utcnow() < deadline and method in {"GET", "HEAD", "POST"}
            try:
                allowed = allowed and len(query) <= 512 and scoped(path, query)
            except ValueError:
                allowed = False
            technical = []
            blocked = []
            business = []
            status = "500"
            try:
                if not allowed or (method == "POST" and path not in {"/login/", "/logout/"}):
                    blocked.append("path-or-window")
                    status = "409"
                    start_response("409 Conflict", [("Content-Type", "text/plain; charset=utf-8")])
                    return [b"Outside inspected W01 browser route or safe window."]

                def execute(next_execute, sql, params, many, context):
                    kind = sql_kind(method, path, sql, many)
                    if kind == "blocked":
                        blocked.append("sql-write-or-unclassified")
                        raise DatabaseError("W01 smoke blocked a non-technical write or an unrecognized statement.")
                    if kind in {"session", "last_login"}:
                        technical.append(kind)
                    if kind in {"business-read", "business-lock"}:
                        business.append(kind)
                    return next_execute(sql, params, many, context)

                def response(status_line, headers, exc_info=None):
                    nonlocal status
                    status = status_line.split(" ",1)[0]
                    return start_response(status_line,headers,exc_info)

                with connection.execute_wrapper(execute):
                    result = application(environ, response)
                    try:
                        # All smoke pages are small, scoped HTML. Capture any lazy execution inside the guard.
                        return list(result)
                    finally:
                        if hasattr(result, "close"):
                            result.close()
            finally:
                if path in account_paths or re.fullmatch(r"/reservations/manage/(?:\d+/)?", path):
                    event({"event": "document", "method": method, "path": path,
                           "query_sha256": hashed("?" + query) if query else None,
                           "status": int(status), "allowed_tech_writes": technical, "guard_blocked": blocked,
                           "business_sql_categories": business})

        class Quiet(WSGIRequestHandler):
            def log_message(self, *_):
                pass

        with make_server("127.0.0.1", port, guard, handler_class=Quiet) as server:
            server.timeout = 0.5
            event({"event":"ready", "port":port,"pid":os.getpid(),"deadline":deadline.isoformat(),
                   "python":str(Path(sys.executable).absolute()),
                   "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "inspection_sha256":hashlib.sha256(args.inspection.read_bytes()).hexdigest()})
            print("STORY25_W01_SMOKE_READY", flush=True)
            try:
                while utcnow() < deadline and not (args.stop_file and args.stop_file.exists()):
                    server.handle_request()
            except KeyboardInterrupt:
                pass
            finally:
                event({"event":"stop"})


if __name__ == "__main__":
    main()
