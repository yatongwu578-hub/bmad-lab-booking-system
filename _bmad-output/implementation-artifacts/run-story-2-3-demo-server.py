"""Local smoke-only gate for Story 2.3. Delegates all admitted requests to normal Django views."""
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from threading import Event, Lock

import psycopg
from django.db import DatabaseError, connection
from django.http import HttpResponse

from story23_formal_demo import BEIJING, SYSTEM_REASON, at

RUN = PLAN = None
LOG_LOCK = Lock()
HALTED = Event()
STUDENT_READS = []
DETAIL = re.compile(r"/reservations/([0-9]+)/result/")
RESERVATION = '"reservations_reservation"'
HISTORY = '"audit_operationhistory"'
TEACHER_INSERT = (
    'INSERT INTO "reservations_reservation" ("applicant_id", "equipment_id", "start_at", "end_at", '
    '"status", "applied_at") VALUES (%s, %s, %s, %s, %s, %s) RETURNING "reservations_reservation"."id"'
)


def query(sql, params=()):
    with connection.cursor() as c:
        c.execute(sql, params)
        return c.fetchall()


def record(data):
    with LOG_LOCK, (RUN / "browser-http.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, sort_keys=True, ensure_ascii=True, default=str) + "\n")
        f.flush()


def independent_student_snapshot():
    with psycopg.connect(host="127.0.0.1", hostaddr="127.0.0.1", port=5433, dbname="lab_booking",
                         user="lab_booking_app", passfile=os.environ["PGPASSFILE"], connect_timeout=5) as c:
        c.execute("SET TRANSACTION READ ONLY")
        c.execute("SET LOCAL statement_timeout='5s'")
        actual = c.execute("""SELECT pg_catalog.current_database(), session_user, current_user,
                     pg_catalog.host(pg_catalog.inet_server_addr()), pg_catalog.inet_server_port(),
                     pg_catalog.current_setting('server_version_num')""").fetchone()
        if actual != ("lab_booking", "lab_booking_app", "lab_booking_app", "127.0.0.1", 5433, "170012"):
            raise RuntimeError("Wrong independent observer target")
        row = c.execute("""SELECT r.status FROM public.reservations_reservation AS r
                            WHERE r.id=1 AND r.applicant_id=%s""", (PLAN["role_ids"]["student"],)).fetchone()
        ids = c.execute("""SELECT h.id FROM public.audit_operationhistory AS h
                            WHERE h.reservation_id=1 AND h.action='expire' AND h.actor_type='system'
                              AND h.reason=%s ORDER BY h.id""", (SYSTEM_REASON,)).fetchall()
        return {"status": row[0] if row else None, "history_ids": [h[0] for h in ids]}


def sql_write_label(kind, sql, params, plan):
    """Match the admitted ORM statements, not just the URL or a name supplied by the browser."""
    p = params or ()
    if kind == "student-list" and plan["expiry_mode"] == "expire_once":
        if (sql.startswith(f'UPDATE {RESERVATION} SET "status" = %s WHERE (')
            and sql.endswith(f' AND {RESERVATION}."id" = %s)')
            and len(p) >= 6 and p[0] == "expired" and p[1] == plan["role_ids"]["student"] and p[-1] == 1):
            return "expire-1"
        if (sql.startswith(f'INSERT INTO {HISTORY} ("object_type", "reservation_id", "equipment_id", "action", ')
            and len(p) == 10 and tuple(p[:9]) ==
              ("reservation", 1, None, "expire", "pending", "expired", "system", None, SYSTEM_REASON)):
            return "expire-history-1"
    if kind == "teacher-post" and plan["teacher"]["mode"] == "submit_once":
        t = plan["teacher"]
        if (sql == TEACHER_INSERT and len(p) == 6 and p[0] == plan["role_ids"]["teacher"]
            and p[1] == t["device_id"] and p[2] == at(t["start"]) and p[3] == at(t["end"]) and p[4] == "pending"):
            return "teacher-create"
    if kind == "authentication":
        if re.match(r'^(?:INSERT INTO|UPDATE|DELETE FROM) "django_session"(?:\s|$)', sql):
            return "session"
        if sql.startswith('UPDATE "accounts_user" SET "last_login" = %s WHERE ') and len(p) == 2 and p[-1] in plan["role_ids"].values():
            return "last-login"
    return None


class AuthorizedGuard:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        writes = []

        def execution(execute, sql, params, many, context):
            text = sql.strip()
            verb = text.partition(" ")[0].splitlines()[0].upper()
            if verb not in {"SELECT", "SET", "SAVEPOINT", "RELEASE", "ROLLBACK"}:
                kind = getattr(request, "_s23_kind", "")
                label = sql_write_label(kind, text, params, PLAN) if not many else None
                if not label or (label not in {"session", "last-login"} and label in writes):
                    raise DatabaseError("Out-of-scope verification write was stopped before execution")
                if label not in {"session", "last-login"} and datetime.now(BEIJING) >= at(PLAN["horizon"]):
                    raise DatabaseError("Approved write window has elapsed")
                writes.append(label)
            return execute(sql, params, many, context)

        try:
            with connection.execute_wrapper(execution):
                response = self.get_response(request)
        except Exception:
            response = HttpResponse("验证入口故障，停止并保留证据。", status=503)
        user = request.user
        role = user.role if user.is_authenticated else None
        event = dict(at=datetime.now(BEIJING).isoformat(), role=role,
                     account_id=user.pk if user.is_authenticated else None, method=request.method,
                     path=request.path, status=response.status_code, writes=writes)
        if getattr(request, "_s23_kind", None) == "student-list" and response.status_code == 200:
            try:
                state = independent_student_snapshot()
                if state["status"] != "expired" or len(state["history_ids"]) != 1:
                    raise RuntimeError("Missing exact student transition")
                event["student_snapshot"] = state
                with LOG_LOCK:
                    STUDENT_READS.append((state, list(writes)))
            except Exception:
                event["verification_error"] = "student readback not certified"
                response = HttpResponse("学生回读未核验，勿重放。", status=503)
                event["status"] = response.status_code
        if response.status_code >= 500 or (request.method == "POST" and request.path.endswith("/reserve/")
                                          and response.status_code != 201):
            HALTED.set()
        record(event)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        path, method = request.path, request.method
        if HALTED.is_set():
            return HttpResponse("本次验证已中止，请保留证据，不要重放。", status=403)
        if datetime.now(BEIJING) >= at(PLAN["deadline"]):
            return HttpResponse("本次验证窗口已结束。", status=403)
        if method not in {"GET", "POST"}:
            return HttpResponse("本次验证范围不包含此请求。", status=403)
        user = request.user
        role = user.role if user.is_authenticated else None
        if role and PLAN["role_ids"].get(role) != user.pk:
            return HttpResponse("请使用当前获准账号的独立窗口。", status=403)
        if path in {"/login/", "/logout/"}:
            if path == "/login/" and method == "POST":
                from accounts.forms import AccountAuthenticationForm
                try:
                    entered = AccountAuthenticationForm.base_fields["username"].clean(request.POST.get("username"))
                except Exception:
                    return HttpResponse("登录账号未在本次验证授权内。", status=403)
                approved = query("SELECT a.id,a.role,a.is_active FROM public.accounts_user AS a WHERE a.username=%s", (entered,))
                if (len(approved) != 1 or not approved[0][2] or
                        PLAN["role_ids"].get(approved[0][1]) != approved[0][0]):
                    return HttpResponse("登录账号未在本次验证授权内。", status=403)
            request._s23_kind = "authentication"
            return None
        if path == "/identity/" and method == "GET":
            return None
        detail = DETAIL.fullmatch(path)
        if method == "GET" and (path == "/reservations/" or detail):
            if role not in ("student", "teacher"):
                return None  # Preserve the real app's login redirect and administrator 403.
            args = [user.pk, at(PLAN["horizon"])]
            where = ""
            if detail:
                rid = int(detail[1])
                if rid >= 2**63:
                    return None
                where = " AND r.id=%s"
                args.append(rid)
            due = [r[0] for r in query("""SELECT r.id FROM public.reservations_reservation AS r
                         WHERE r.applicant_id=%s AND r.status='pending' AND r.start_at<=%s""" + where, args)]
            allowed = ({1} if role == "student" and not detail and PLAN["expiry_mode"] == "expire_once" else set())
            if not set(due) <= allowed:
                return HttpResponse("当前待审核候选超出本次授权范围。", status=403)
            if role == "student" and not detail:
                request._s23_kind = "student-list"
            return None
        teacher = PLAN["teacher"]
        if teacher["mode"] == "submit_once" and path == teacher["path"] and role == "teacher":
            if method == "GET":
                return None
            from reservations.services import _parse_local
            start_fields = request.POST.getlist("start_at")
            end_fields = request.POST.getlist("end_at")
            try:
                exact_slot = (len(start_fields) == len(end_fields) == 1
                              and _parse_local(start_fields[0]) == at(teacher["start"])
                              and _parse_local(end_fields[0]) == at(teacher["end"]))
            except (ValueError, OverflowError):
                exact_slot = False
            if not exact_slot:
                return HttpResponse("预约时段与本次只读核验计划不符。", status=403)
            with LOG_LOCK:
                s = STUDENT_READS[:]
            if (len(s) < 2 or s[0][0] != s[1][0] or s[1][1] or
                    (PLAN["expiry_mode"] == "expire_once" and s[0][1] != ["expire-1", "expire-history-1"])):
                return HttpResponse("请先完成学生列表的首次和重复读回。", status=403)
            check = query("""SELECT e.status,
                EXISTS (SELECT 1 FROM public.reservations_reservation AS r WHERE r.equipment_id=e.id
                        AND r.status='pending' AND r.start_at<=%s),
                EXISTS (SELECT 1 FROM public.reservations_reservation AS r WHERE r.equipment_id=e.id
                        AND r.start_at<%s AND r.end_at>%s AND r.status IN ('pending','approved')),
                EXISTS (SELECT 1 FROM public.reservations_reservation AS r WHERE r.applicant_id=%s)
                FROM public.equipment_equipment AS e WHERE e.id=%s""",
                (at(PLAN["horizon"]), at(teacher["end"]), at(teacher["start"]), user.pk, teacher["device_id"]))
            if check != [("available", False, False, False)]:
                return HttpResponse("设备、时段或教师已有预约已变化，停止提交。", status=403)
            try:
                with (RUN / "teacher-post-intent.txt").open("x", encoding="ascii") as f:
                    f.write(datetime.now(BEIJING).isoformat()+"\n")
            except FileExistsError:
                return HttpResponse("本批已放行一次提交，不得重放。", status=403)
            request._s23_kind = "teacher-post"
            return None
        return HttpResponse("本次验证范围不包含此操作。", status=403)


def main():
    global RUN, PLAN
    if sys.argv[1:] != ["127.0.0.1:8003", "--noreload"] or sys.version_info[:3] != (3,13,17):
        raise RuntimeError("Original .venv and fixed loopback listener are required")
    RUN = Path(os.environ["STORY23_DEMO_RECEIPT"]).resolve(strict=True)
    source = (RUN / "sample-before.json").read_bytes()
    if sha256(source).hexdigest().upper() != (RUN / "sample-before.sha256").read_text(encoding="utf-8").strip():
        raise RuntimeError("Approved sample fingerprint differs")
    PLAN = json.loads(source)["sample"]["demo"]
    if (not PLAN["ready"] or datetime.now(BEIJING) >= at(PLAN["deadline"]) or
         os.environ.get("LAB_BOOKING_DB_MODE") != "runtime"):
        raise RuntimeError("Approved window or runtime mode invalid")
    with (RUN / "guard-start.txt").open("x", encoding="ascii") as receipt:
        receipt.write("STORY23_VERIFICATION_GUARD_CONFIGURED\n")
    project = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project))
    from django.conf import settings
    from django.core.management import execute_from_command_line
    settings.MIDDLEWARE = [*settings.MIDDLEWARE, "__main__.AuthorizedGuard"]
    execute_from_command_line(["manage.py", "runserver", *sys.argv[1:]])


if __name__ == "__main__":
    main()
