import hashlib
import json
import platform
import re
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from datetime import datetime, timedelta
from http.cookiejar import CookieJar
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Barrier, Event, Thread
from time import monotonic_ns, sleep, time_ns
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.handlers.wsgi import WSGIHandler
from django.core.management.base import BaseCommand, CommandError
from django.db import Error, OperationalError, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from django.utils.crypto import get_random_string

from accounts.models import Role, User
from audit.models import OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus
from lab_booking.database_config import DATABASE_TARGETS, HOST, PORT, SERVER_VERSION_NUM
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status
from reservations.views import CONFLICT_MESSAGE, INVALID_TIME_MESSAGE, UNAVAILABLE_MESSAGE

from ._chrome_probe import chrome, fill

GROUPS = ("pre-migrate", "baseline", "browser-correction", "permissions", "interleavings", "faults", "nfr001-standard",
          "time-boundaries")
STORY_MIGRATIONS = {("reservations", "0001_initial"): "reservations_reservation",
                    ("audit", "0001_initial"): "audit_operationhistory"}
PROBE = ContextVar("story21_request_probe", default=None)
CSRF = re.compile(r'(name="csrfmiddlewaretoken" value=")([^"]+)(")')
REAL_DECISION = services._decision_time


def require(condition, message):
    if not condition:
        raise CommandError(message)


def query(connection, sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() if cursor.description else None


def target(connection):
    database, role = DATABASE_TARGETS["test"]
    identity = query(connection, """
        SELECT current_database() AS db_name, session_user AS login_role, current_user AS effective_role,
               host(inet_server_addr()) AS server_host, inet_server_port() AS server_port,
               current_setting('server_version_num') AS version_num, current_setting('transaction_isolation') AS isolation,
               rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls AS role_excess,
               has_database_privilege(current_user, %s, 'CONNECT') AS business_connect, pg_backend_pid() AS backend_pid
        FROM pg_roles WHERE rolname = current_user
    """, [DATABASE_TARGETS["runtime"][0]])
    require(identity is not None and identity[:-1] == (database, role, role, HOST, int(PORT), str(SERVER_VERSION_NUM),
                                                       "read committed", False, False), "Incorrect isolated database target")
    query(connection, "SET statement_timeout = '45s'")
    query(connection, "SET lock_timeout = '35s'")
    return identity


def wait_for(callback, label, timeout_seconds=10):
    deadline = monotonic_ns() + timeout_seconds * 10**9
    while monotonic_ns() < deadline:
        result = callback()
        if result:
            return result
        sleep(.02)
    raise CommandError(f"Timeout: {label}")


def sqlstate(error):
    return getattr(error.__cause__, "sqlstate", None)


def observe_decision(connection):
    instant = REAL_DECISION(connection)
    trace = PROBE.get()
    if trace is not None:
        trace["decisions"].append(instant)
    return instant


def is_account_recheck(sql):
    # values_list() in Django 5.2 can alias each projected column with AS.
    projection, source, predicate = sql.partition(' FROM "accounts_user" WHERE ')
    if not source or not projection.startswith("SELECT ") or '"accounts_user"."id" = %s' not in predicate:
        return False
    columns = [item.partition(" AS ")[0] for item in projection.removeprefix("SELECT ").split(", ")]
    return len(columns) == 2 and set(columns) == {'"accounts_user"."is_active"', '"accounts_user"."role"'}


RESERVATION = '"reservations_reservation"'
EQUIPMENT = '"equipment_equipment"'
I7_OWNER = f'{RESERVATION}."applicant_id" = %s AND {RESERVATION}."id" = %s'
I7_FIXED = f'{I7_OWNER} AND {RESERVATION}."equipment_id" = %s'
I7_DUE = f'{I7_FIXED} AND {RESERVATION}."start_at" <= %s AND {RESERVATION}."status" = %s'
I7_RESULT = (
    f'SELECT {RESERVATION}."id" AS "id", {RESERVATION}."equipment_id" AS "equipment_id", '
    f'{EQUIPMENT}."number" AS "equipment__number", {EQUIPMENT}."name" AS "equipment__name", '
    f'{RESERVATION}."start_at" AS "start_at", {RESERVATION}."end_at" AS "end_at", {RESERVATION}."status" AS "status" '
    f'FROM {RESERVATION} INNER JOIN {EQUIPMENT} ON ({RESERVATION}."equipment_id" = {EQUIPMENT}."id")'
)
I7_ORDER = f'ORDER BY {RESERVATION}."id" ASC LIMIT 1'
I7_SQL = {
    f'{I7_RESULT} WHERE ({I7_OWNER}) {I7_ORDER}': "candidate",
    f'SELECT {EQUIPMENT}."id" AS "pk" FROM {EQUIPMENT} WHERE {EQUIPMENT}."id" = %s LIMIT 21 FOR UPDATE': "lock",
    ('SELECT "accounts_user"."is_active" AS "is_active", "accounts_user"."role" AS "role" '
     'FROM "accounts_user" WHERE "accounts_user"."id" = %s ORDER BY "accounts_user"."id" ASC LIMIT 1'): "account",
    f'{I7_RESULT} WHERE ({I7_FIXED}) {I7_ORDER}': "fixed",
    "SELECT clock_timestamp() AS decision_at": "decision",
    f'SELECT {RESERVATION}."id" AS "pk" FROM {RESERVATION} WHERE ({I7_DUE}) ORDER BY 1 ASC': "due",
    f'UPDATE {RESERVATION} SET "status" = %s WHERE ({I7_DUE} AND {RESERVATION}."id" = %s)': "update",
}


def i7_binding(sql, params, many, sql_index):
    """Allow only the I7 target query shapes and their typed fixture parameters."""
    kind = I7_SQL.get(sql)
    if kind is None or many:
        return None
    integer = lambda value: type(value) is int and value > 0
    instant = lambda value: isinstance(value, datetime) and value.utcoffset() is not None
    pending = lambda value: isinstance(value, str) and value == Status.PENDING
    expired = lambda value: isinstance(value, str) and value == Status.EXPIRED
    validators = {
        "candidate": (integer, integer),
        "lock": (integer,),
        "account": (integer,),
        "fixed": (integer, integer, integer),
        "decision": (),
        "due": (integer, integer, integer, instant, pending),
        "update": (expired, integer, integer, integer, instant, pending, integer),
    }[kind]
    values = () if params is None else params
    if isinstance(values, (tuple, list)) and len(values) == len(validators) and all(
        check(value) for check, value in zip(validators, values, strict=True)
    ):
        return dict(sql_index=sql_index, kind=kind, params=list(values))


class ProbeWSGI(WSGIHandler):
    def __init__(self, cases):
        super().__init__()
        self.cases = cases

    def _get_response(self, request):
        # BaseHandler calls this inside the middleware chain. Resolve the very request's lazy user,
        # not the account or role label supplied by the fixture that started the request.
        trace = PROBE.get()
        if trace is not None and "principal" in trace:
            user = request.user
            authenticated = bool(user.is_authenticated)
            trace["principal"] = dict(user_id=user.pk if authenticated else None,
                                      role=str(user.role) if authenticated else None,
                                      is_active=bool(user.is_active), is_authenticated=authenticated,
                                      method=request.method, path=request.path)
        return super()._get_response(request)

    def get_response(self, request):
        app = connections["default"]
        case = self.cases.get(request.headers.get("X-Story21-Probe"))
        identity = target(app)
        if case is None:
            return super().get_response(request)
        trace, control = case
        trace.update(identity=identity, pid=identity[-1], server_start_ns=monotonic_ns(),
                     decisions=[], sql=[], commit_attempts=0, history_attempts=0, reservation_attempts=0)
        if control.get("capture_principal"):
            trace["principal"] = None
        if control.get("capture_i7"):
            trace["i7_bindings"] = []
        token = PROBE.set(trace)
        real_commit = app._commit

        def trace_sql(execute, sql, params, many, context):
            # Never save auth/session SQL parameters. Lock intervals use the server process clock.
            record = any(table in sql for table in ('"reservations_reservation"', '"audit_operationhistory"', '"equipment_equipment"'))
            record = record or "clock_timestamp() AS decision_at" in sql or is_account_recheck(sql)
            if record:
                if "i7_bindings" in trace:
                    binding = i7_binding(sql, params, many, len(trace["sql"]))
                    if binding is not None:
                        trace["i7_bindings"].append(binding)
                trace["sql"].append(sql)
            if "FOR UPDATE" in sql:
                trace["lock_attempt_ns"] = monotonic_ns()
            try:
                if sql.startswith('INSERT INTO "audit_operationhistory"'):
                    trace["history_attempts"] += 1
                    if control.get("fault") == "F1-history":
                        params = ("invalid", *params[1:])
                elif sql.startswith('INSERT INTO "reservations_reservation"'):
                    trace["reservation_attempts"] += 1
                    if control.get("fault") == "F1-reservation":
                        # Model INSERT order: applicant, equipment, start, end, status, applied.
                        params = (*params[:4], "invalid_status", *params[5:])
                result = execute(sql, params, many, context)
                if "FOR UPDATE" in sql:
                    trace["lock_acquired_ns"] = monotonic_ns()
                return result
            except Error as error:
                trace["sqlstate"] = sqlstate(error)
                raise

        def commit():
            trace["commit_attempts"] += 1
            trace["commit_enter_ns"] = monotonic_ns()
            if control.get("before_commit"):
                control["before_commit"]()
            fault = control.get("fault")
            if fault == "F2":
                query(app, "CREATE TEMP TABLE story21_commit_probe (n int UNIQUE DEFERRABLE INITIALLY DEFERRED) ON COMMIT DROP")
                query(app, "INSERT INTO pg_temp.story21_commit_probe VALUES (1), (1)")
            if fault == "F3":
                control["terminate"](identity[-1])
            try:
                real_commit()
                if fault == "F4":
                    # Commit on PostgreSQL, then discard successful confirmation at the driver boundary.
                    app.connection.close()
                    raise OperationalError("Story 2.1 simulated missing COMMIT confirmation")
                trace["commit_return_ns"] = monotonic_ns()
            except Error as error:
                trace["sqlstate"] = sqlstate(error)
                raise

        try:
            with app.execute_wrapper(trace_sql), patch.object(app, "_commit", side_effect=commit):
                return super().get_response(request)
        finally:
            trace["server_end_ns"] = monotonic_ns()
            PROBE.reset(token)


class ThreadedServer(ThreadingMixIn, WSGIServer):
    request_queue_size = 64


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def url(name, pk):
    return reverse(name, args=[pk])


def window(start, end):
    return {key: value.astimezone(services.BEIJING).strftime("%Y-%m-%dT%H:%M")
            for key, value in (("start_at", start), ("end_at", end))}


def scrub(body):
    return CSRF.sub(r"\1[redacted]\3", body)


class Experiment:
    def __init__(self, observer, server, cases, prefix, report):
        self.observer, self.server, self.cases, self.prefix, self.report = observer, server, cases, prefix, report
        self.session_keys = set()
        self.password = get_random_string(28)
        self.users = {}
        self.counter = 0
        self.base = f"http://{HOST}:{server.server_port}"

    def now(self):
        return query(self.observer, "SELECT clock_timestamp() AS observer_now")[0]

    def fixture(self, status=EquipmentStatus.AVAILABLE):
        self.counter += 1
        return Equipment.objects.create(number=f"{self.prefix}{self.counter}", name=f"Story21 fixture {self.counter}",
                                        category="probe", location="loopback", status=status)

    def future(self):
        start = (self.now().astimezone(services.BEIJING) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        return start, start + timedelta(hours=1)

    def make(self, dev, start, end, role=Role.STUDENT, status=Status.PENDING):
        return Reservation.objects.create(applicant=self.users[role], equipment=dev, start_at=start, end_at=end,
                                          status=status, applied_at=start - timedelta(days=1))

    def snapshot(self, dev, start=None, end=None):
        with self.observer.cursor() as cursor:
            def fetch(sql, params):
                cursor.execute(sql, params)
                fields = [column.name for column in cursor.description]
                return [dict(zip(fields, row, strict=True)) for row in cursor.fetchall()]

            device, = fetch("SELECT * FROM equipment_equipment WHERE id = %s", [dev.pk])
            rows = fetch("SELECT * FROM reservations_reservation WHERE equipment_id = %s ORDER BY id", [dev.pk])
            history = fetch("SELECT h.* FROM audit_operationhistory h LEFT JOIN reservations_reservation r "
                            "ON h.reservation_id = r.id WHERE r.equipment_id = %s OR h.equipment_id = %s ORDER BY h.id", [dev.pk, dev.pk])
        now = self.now()
        active = [row for row in rows if (row["status"] == Status.APPROVED or (
            row["status"] == Status.PENDING and row["start_at"] > now)) and (start is None or (
                row["start_at"] < end and start < row["end_at"]))]
        return dict(observed_at=now, device=device, rows=rows, effective=active, history=history)

    def http(self, opener, path, values=None, *, token=None, csrf=None):
        fields = None if values is None else dict(values)
        if csrf is not None:
            fields["csrfmiddlewaretoken"] = csrf
        headers = {"X-Story21-Probe": token} if token else {}
        request = Request(self.base + path, data=None if fields is None else urlencode(fields).encode(), headers=headers)
        start = monotonic_ns()
        start_wall = time_ns()
        try:
            response = opener.open(request, timeout=65)
        except HTTPError as error:
            response = error
        except (OSError, TimeoutError) as error:
            return dict(status=None, error=type(error).__name__, client_start_ns=start,
                        client_start_wall_ns=start_wall, client_end_ns=monotonic_ns())
        try:
            with response:
                return dict(status=response.code, body=response.read().decode("utf-8"), location=response.headers.get("Location"),
                            client_start_ns=start, client_start_wall_ns=start_wall, client_end_ns=monotonic_ns())
        except (OSError, TimeoutError) as error:
            return dict(status=None, error=type(error).__name__, client_start_ns=start, client_start_wall_ns=start_wall,
                        client_end_ns=monotonic_ns())

    def pair(self, role, form_path=None):
        cookies = CookieJar()
        opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(cookies), NoRedirect())
        login = self.http(opener, reverse("login"))
        require(login["status"] == 200, "Real login form unavailable")
        login_csrf = CSRF.search(login["body"])[2]
        if role is not None:
            login = self.http(opener, reverse("login"), {"username": self.users[role].username, "password": self.password}, csrf=login_csrf)
            require(login["status"] == 302, "Fixture session login failed")
            ids = [cookie.value for cookie in cookies if cookie.name == settings.SESSION_COOKIE_NAME]
            require(len(ids) == 1, "Fixture login did not create one session")
            self.session_keys.add(ids[0])
        else:
            return opener, login_csrf
        form = self.http(opener, form_path or reverse("login"))
        require(form["status"] == 200 and CSRF.search(form["body"]) is not None, "CSRF form unavailable")
        return opener, CSRF.search(form["body"])[2]

    def prepare(self, pair, path, values=None, *, control=None, use_csrf=True, role=None):
        token = uuid4().hex
        trace = {}
        self.cases[token] = (trace, control or {})
        opener, csrf = pair

        def execute():
            try:
                outcome = self.http(opener, path, values, token=token, csrf=csrf if values is not None and use_csrf else None)
                if "body" in outcome:
                    outcome["body"] = scrub(outcome["body"])
                return dict(role=role, input=values, path=path, response=outcome, server=trace)
            finally:
                self.cases.pop(token)

        return execute, trace

    @staticmethod
    def expect(outcome, status, message=None):
        response = outcome["response"]
        require(response["status"] == status and (message is None or message in response["body"]),
                f"Expected HTTP {status}, received {response['status']} ({message or 'status-only'})")

    def wait_blocker(self, trace, blocker):
        pid = wait_for(lambda: trace.get("pid"), "HTTP actor backend PID")

        def blocked():
            blockers = query(self.observer, "SELECT pg_blocking_pids(%s) AS blockers", [pid])[0]
            return blockers if blocker in blockers else None

        return wait_for(blocked, "actual PostgreSQL lock wait")

    @staticmethod
    def expiry(snapshot, reservation_id, decision=None):
        row, = (row for row in snapshot["rows"] if row["id"] == reservation_id)
        record, = (row for row in snapshot["history"] if row["reservation_id"] == reservation_id)
        require(row["status"] == Status.EXPIRED and record["object_type"] == "reservation"
                and record["equipment_id"] is None and record["actor_id"] is None and record["actor_type"] == "system"
                and record["action"] == "expire" and record["before_status"] == Status.PENDING
                and record["after_status"] == Status.EXPIRED and record["reason"] == EXPIRY_REASON
                and row["start_at"] <= record["decision_at"] <= record["recorded_at"] <= snapshot["observed_at"]
                and (decision is None or record["decision_at"] == decision), "Incomplete or inconsistent expiry/history")

    @staticmethod
    def unchanged(before, after):
        return all(before[key] == after[key] for key in ("device", "rows", "effective", "history"))

    @staticmethod
    def fingerprint(snapshot):
        stable = {key: snapshot[key] for key in ("device", "rows", "effective", "history")}
        payload = json.dumps(stable, sort_keys=True, default=str, ensure_ascii=False).encode()
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def check_order(outcome):
        trace = outcome["server"]
        statements = trace["sql"]
        locks = [i for i, sql in enumerate(statements) if "FOR UPDATE" in sql]
        clocks = [i for i, sql in enumerate(statements) if "clock_timestamp() AS decision_at" in sql]
        require(len(locks) == len(clocks) == len(trace["decisions"]) == trace["commit_attempts"] == 1,
                "Expected one device lock, clock and COMMIT")
        lock, clock = locks[0], clocks[0]
        require('"equipment_equipment"."id"' in statements[lock] and "SKIP LOCKED" not in statements[lock],
                "Lock is not the required primary-key lock")
        between = statements[lock + 1:clock]
        require(any(is_account_recheck(sql) for sql in between)
                and any(('"equipment_equipment"."status"' in sql or '"reservations_reservation"."status"' in sql)
                        for sql in between), "No separate reread of target and account after locking")

    def hold_device(self, dev):
        Equipment.objects.select_for_update().values_list("pk", flat=True).get(pk=dev.pk)

    def standard(self):
        for round_number in range(1, 11):
            dev = self.fixture()
            start, end = self.future()
            values, path = window(start, end), url("reservation-submit", dev.pk)
            before = self.snapshot(dev, start, end)
            require(not before["rows"] and not before["effective"] and before["device"]["status"] == EquipmentStatus.AVAILABLE,
                    "Standard round is not isolated and initially available")
            actors = []
            for index in range(20):
                role = (Role.STUDENT, Role.TEACHER)[index // 10]
                execute, _ = self.prepare(self.pair(role, path), path, values, role=role)
                actors.append(execute)
            release = {}

            def released():
                release.update(monotonic_ns=monotonic_ns(), wall_ns=time_ns())

            barrier = Barrier(20, action=released, timeout=30)

            def worker(execute):
                barrier.wait()
                return execute()

            with ThreadPoolExecutor(max_workers=20) as pool:
                results = list(pool.map(worker, actors))
            after = self.snapshot(dev, start, end)
            traces = [outcome["server"] for outcome in results]
            overlaps = [
                [a["pid"], b["pid"]] for a in traces for b in traces
                if a is not b and a.get("lock_acquired_ns", float("inf")) <= b.get("lock_attempt_ns", -1)
                and b.get("lock_attempt_ns", float("inf")) < a.get("commit_enter_ns", -1)
            ]
            counts = dict(success=sum(x["response"]["status"] == 201 for x in results),
                          conflict=sum(x["response"]["status"] == 409 and CONFLICT_MESSAGE in x["response"].get("body", "")
                                       for x in results),
                          no_response=sum(x["response"]["status"] is None for x in results))
            counts["other"] = 20 - sum(counts.values())
            client_starts = [row["response"]["client_start_ns"] for row in results]
            self.report(round=round_number, before=before, after=after, release=release, counts=counts,
                        start_distribution_ns=[x - release["monotonic_ns"] for x in client_starts],
                        observed_overlaps=overlaps, accounts={str(role): user.pk for role, user in self.users.items()
                                                             if role in (Role.STUDENT, Role.TEACHER)}, responses=results)
            require(counts == dict(success=1, conflict=19, no_response=0, other=0), "Standard HTTP outcome counts mismatch")
            require(len({t["pid"] for t in traces}) == 20 and overlaps, "No proof of 20 distinct backends and actual contention")
            for result in results:
                self.check_order(result)
            winner, = (row for row in results if row["response"]["status"] == 201)
            require(len(after["rows"]) == len(after["effective"]) == 1 and not after["history"]
                    and after["rows"] == after["effective"]
                    and after["rows"][0]["status"] == Status.PENDING
                    and (after["rows"][0]["start_at"], after["rows"][0]["end_at"]) == (start, end)
                    and after["rows"][0]["applicant_id"] == self.users[winner["role"]].pk
                    and after["rows"][0]["applied_at"] == winner["server"]["decisions"][0],
                    "Standard final reservation differs from the HTTP winner")

    def simultaneous(self, first, second, first_trace, second_trace, entered, release):
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(first)
            try:
                require(entered.wait(10), "First actor did not reach held COMMIT")
                b = pool.submit(second)
                blockers = self.wait_blocker(second_trace, first_trace["pid"])
            finally:
                release.set()
            return a.result(), b.result(), blockers

    @staticmethod
    def commit_latch():
        entered, release = Event(), Event()

        def before_commit():
            entered.set()
            require(release.wait(28), "Test-only COMMIT latch timed out")

        return entered, release, {"before_commit": before_commit}

    def i1(self):
        dev = self.fixture()
        start, end = self.future()
        path, values = url("reservation-submit", dev.pk), window(start, end)
        before = self.snapshot(dev)
        entered, release, control = self.commit_latch()
        first, a_trace = self.prepare(self.pair(Role.STUDENT, path), path, values, control=control, role=Role.STUDENT)
        second, b_trace = self.prepare(self.pair(Role.TEACHER, path), path, values, role=Role.TEACHER)
        a, b, blockers = self.simultaneous(first, second, a_trace, b_trace, entered, release)
        after = self.snapshot(dev, start, end)
        adjacent_path = url("reservation-submit", self.fixture().pk)
        adjacent = self.prepare(self.pair(Role.TEACHER, path), path, window(end, end + timedelta(hours=1)))[0]()
        different = self.prepare(self.pair(Role.STUDENT, adjacent_path), adjacent_path, values)[0]()
        self.report(case="I1", before=before, after=after, blockers=blockers, responses=[a, b, adjacent, different])
        self.expect(a, 201)
        self.expect(b, 409, CONFLICT_MESSAGE)
        self.expect(adjacent, 201)
        self.expect(different, 201)
        self.check_order(a)
        self.check_order(b)
        require(len({self.observer_identity[-1], a_trace["pid"], b_trace["pid"]}) == 3 and
                len(after["rows"]) == len(after["effective"]) == 1 and not after["history"], "I1 data mismatch")

    def i2_i3(self, status, *, request_first):
        dev = self.fixture()
        start, end = self.future()
        path = url("reservation-submit", dev.pk)
        old = self.make(dev, self.now() - timedelta(minutes=1), end) if not request_first else None
        before = self.snapshot(dev)
        pair = self.pair(Role.STUDENT, path)
        entered, release, control = self.commit_latch()
        execute, trace = self.prepare(pair, path, window(start, end), control=control if request_first else None)
        writer_trace = {}

        def writer():
            app = connections["default"]
            try:
                writer_trace["pid"] = target(app)[-1]
                with transaction.atomic():
                    self.hold_device(dev)
                    Equipment.objects.filter(pk=dev.pk).update(status=status)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            if request_first:
                a = pool.submit(execute)
                try:
                    require(entered.wait(10), "Applicant did not reach held COMMIT")
                    b = pool.submit(writer)
                    blockers = self.wait_blocker(writer_trace, trace["pid"])
                    require(self.unchanged(before, self.snapshot(dev)), "I3 uncommitted request leaked")
                finally:
                    release.set()
                response = a.result()
                b.result()
            else:
                app = connections["default"]
                with transaction.atomic():
                    self.hold_device(dev)
                    Equipment.objects.filter(pk=dev.pk).update(status=status)
                    a = pool.submit(execute)
                    blockers = self.wait_blocker(trace, target(app)[-1])
                    require(self.unchanged(before, self.snapshot(dev)), "I2 uncommitted status leaked")
                response = a.result()
        after = self.snapshot(dev, start, end)
        self.report(case="I3" if request_first else "I2", status=status, before=before, after=after,
                    blockers=blockers, response=response, writer=writer_trace)
        self.check_order(response)
        require(after["device"]["status"] == status and len(after["rows"]) == 1, "I2/I3 durable data mismatch")
        if request_first:
            self.expect(response, 201)
            require(len(after["effective"]) == 1 and not after["history"], "I3 changed initial pending occupancy")
        else:
            self.expect(response, 409, UNAVAILABLE_MESSAGE)
            self.expiry(after, old.pk, trace["decisions"][0])
            require(len(after["history"]) == 1 and not after["effective"], "I2 expiry data mismatch")

    def i4(self, *, read_first):
        dev, other = self.fixture(), self.fixture()
        start, end = self.future()
        old = self.make(dev, self.now() - timedelta(minutes=1), end)
        approved = self.make(dev, end, end + timedelta(hours=1), status=Status.APPROVED)
        unrelated = self.make(other, self.now() - timedelta(minutes=1), end)
        submit, result = url("reservation-submit", dev.pk), url("reservation-result", old.pk)
        before, other_before = self.snapshot(dev), self.snapshot(other)
        entered, release, control = self.commit_latch()
        owner = self.pair(Role.STUDENT, submit)
        applicant = self.pair(Role.TEACHER, submit)
        reader, read_trace = self.prepare(owner, result, control=control if read_first else None)
        writer, write_trace = self.prepare(applicant, submit, window(start, end), control=None if read_first else control)
        if read_first:
            read, write, blockers = self.simultaneous(reader, writer, read_trace, write_trace, entered, release)
        else:
            write, read, blockers = self.simultaneous(writer, reader, write_trace, read_trace, entered, release)
        repeat = self.prepare(owner, result)[0]()
        after, other_after = self.snapshot(dev, start, end), self.snapshot(other)
        self.report(case="I4", reader_first=read_first, before=before, after=after, blockers=blockers,
                    other_before=other_before, other_after=other_after, responses=[read, write, repeat])
        self.expect(read, 200, "已失效")
        self.expect(repeat, 200, "已失效")
        self.expect(write, 201)
        self.expiry(after, old.pk, (read_trace if read_first else write_trace)["decisions"][0])
        require(self.unchanged(other_before, other_after) and len(after["rows"]) == 3
                and len(after["history"]) == len(after["effective"]) == 1
                and any(row["id"] == approved.pk and row["status"] == Status.APPROVED for row in after["rows"]),
                "I4 affected unrelated/approved state, or failed to release old occupancy")

    def i5(self, kind):
        dev = self.fixture(EquipmentStatus.DISABLED if kind == "unavailable" else EquipmentStatus.AVAILABLE)
        start, end = self.future()
        old = self.make(dev, self.now() - timedelta(minutes=1), end)
        conflict = self.make(dev, start, end, status=Status.APPROVED) if kind == "conflict" else None
        path = url("reservation-submit", dev.pk)
        values = window(start, end) if kind != "invalid" else {"start_at": "bad"}
        before = self.snapshot(dev)
        response = self.prepare(self.pair(Role.STUDENT, path), path, values)[0]()
        after = self.snapshot(dev)
        self.report(case="I5", kind=kind, before=before, after=after, response=response)
        code, text = {"unavailable": (409, UNAVAILABLE_MESSAGE), "invalid": (400, INVALID_TIME_MESSAGE),
                      "conflict": (409, CONFLICT_MESSAGE)}[kind]
        self.expect(response, code, text)
        self.check_order(response)
        self.expiry(after, old.pk, response["server"]["decisions"][0])
        require(len(after["rows"]) == len(before["rows"]) and len(after["history"]) == 1
                and before["effective"] == after["effective"]
                and (conflict is None or after["effective"][0]["id"] == conflict.pk), "I5 durable data mismatch")

    def i6(self, *, read, deactivate):
        dev = self.fixture()
        start, end = self.future()
        now = self.now()
        old = self.make(dev, now - timedelta(hours=2), now - timedelta(hours=1))
        form = url("reservation-submit", dev.pk)
        app = connections["default"]
        applicant = self.users[Role.STUDENT]
        before = self.snapshot(dev)
        execute, trace = self.prepare(self.pair(Role.STUDENT, form), url("reservation-result", old.pk) if read else form,
                                      None if read else window(start, end), role=Role.STUDENT)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                with transaction.atomic():
                    self.hold_device(dev)
                    actor = pool.submit(execute)
                    blockers = self.wait_blocker(trace, target(app)[-1])
                    change = ("is_active", False) if deactivate else ("role", Role.ADMIN)
                    require(query(self.observer, f"UPDATE accounts_user SET {change[0]} = %s WHERE id = %s RETURNING id",
                                  [change[1], applicant.pk]) == (applicant.pk,), "Test-only revoke failed")
                response = actor.result()
        finally:
            User.objects.filter(pk=applicant.pk).update(is_active=True, role=Role.STUDENT)
        after = self.snapshot(dev)
        self.report(case="I6", read=read, requested_revocation=change, blockers=blockers,
                    before=before, after=after, response=response)
        self.expect(response, 403)
        require(not trace["decisions"] and not trace["commit_attempts"] and self.unchanged(before, after)
                and dev.name not in response["response"]["body"], "Post-lock revoke leaked or wrote business state")

    def i7(self):
        dev = self.fixture()
        now = self.now()
        terminal = self.make(dev, now - timedelta(hours=3), now - timedelta(hours=2), status=Status.EXPIRED)
        old = self.make(dev, now - timedelta(hours=2), now - timedelta(hours=1))
        form = url("reservation-submit", dev.pk)
        pair = self.pair(Role.STUDENT, form)
        terminal_read, _ = self.prepare(pair, url("reservation-result", terminal.pk))
        pending_read, trace = self.prepare(pair, url("reservation-result", old.pk), control={"capture_i7": True})
        repeat, _ = self.prepare(pair, url("reservation-result", old.pk))
        before = self.snapshot(dev)
        app = connections["default"]
        blocker_pid = target(app)[-1]
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                self.hold_device(dev)
                terminal_response = pool.submit(terminal_read).result(timeout=5)
                actor = pool.submit(pending_read)
                blockers = self.wait_blocker(trace, blocker_pid)
                blocked_ns = monotonic_ns()
                same_owner = self.make(dev, now - timedelta(hours=5), now - timedelta(hours=4))
                same_inserted_ns = monotonic_ns()
                other_owner = self.make(dev, now - timedelta(hours=3), now - timedelta(hours=2), role=Role.TEACHER)
                other_inserted_ns = monotonic_ns()
                during = self.snapshot(dev)
                commit_enter_ns = monotonic_ns()
            commit_return_ns = monotonic_ns()
            pending_response = actor.result()
        after = self.snapshot(dev)
        repeated = repeat()
        repeated_after = self.snapshot(dev)
        self.report(case="I7", before=before, during=during, after=after, repeated_after=repeated_after,
                    candidates={name: {"id": row.pk, "applicant_id": row.applicant_id, "equipment_id": row.equipment_id,
                                       "start_at": row.start_at, "end_at": row.end_at, "initial_status": row.status}
                                for name, row in (("target", old), ("terminal", terminal),
                                                  ("same_owner_added", same_owner), ("other_owner_added", other_owner))},
                    observer_pid=self.observer_identity[-1], blocked_pid=trace["pid"], blocker_pid=blocker_pid,
                    blockers=blockers, timing=dict(blocked_ns=blocked_ns, same_inserted_ns=same_inserted_ns,
                                                   other_inserted_ns=other_inserted_ns,
                                                   commit_enter_ns=commit_enter_ns, commit_return_ns=commit_return_ns),
                    responses=[terminal_response, pending_response, repeated])
        for response, expected in ((terminal_response, terminal), (pending_response, old), (repeated, old)):
            self.expect(response, 200, "已失效")
            require(f"<dd>{expected.pk}</dd>" in response["response"]["body"], "I7 returned the wrong reservation")
        self.check_order(pending_response)
        decision, = trace["decisions"]
        owner_target = [old.applicant_id, old.pk]
        fixed_scope = [*owner_target, dev.pk]
        due_scope = [*fixed_scope, decision, Status.PENDING]
        expected_bindings = [dict(sql_index=index, kind=kind, params=params) for index, (kind, params) in enumerate((
            ("candidate", owner_target), ("lock", [dev.pk]), ("account", [old.applicant_id]),
            ("fixed", fixed_scope), ("decision", []), ("due", due_scope),
            ("update", [Status.EXPIRED, *due_scope, old.pk]),
        ))]
        require(trace["i7_bindings"] == expected_bindings and len(trace["sql"]) == 8
                and trace["sql"][7].startswith('INSERT INTO "audit_operationhistory"')
                and trace["history_attempts"] == 1 and trace["reservation_attempts"] == 0,
                "I7 did not lock, reread, decide, and expire exactly the fixed fixture target in order")
        self.expiry(after, old.pk, decision)
        rows = {row["id"]: row for row in after["rows"]}
        expected_statuses = {terminal.pk: Status.EXPIRED, old.pk: Status.EXPIRED,
                             same_owner.pk: Status.PENDING, other_owner.pk: Status.PENDING}
        require({pk: row["status"] for pk, row in rows.items()} == expected_statuses
                and rows[same_owner.pk]["applicant_id"] == old.applicant_id != rows[other_owner.pk]["applicant_id"]
                and not after["effective"] and len(after["history"]) == 1
                and self.unchanged(before, during) and self.unchanged(after, repeated_after)
                and all("lock_attempt_ns" not in result["server"] and not result["server"]["decisions"]
                        for result in (terminal_response, repeated))
                and len({trace["pid"], blocker_pid, self.observer_identity[-1]}) == 3
                and trace["lock_attempt_ns"] <= blocked_ns < same_inserted_ns <= other_inserted_ns
                <= commit_enter_ns <= trace["lock_acquired_ns"],
                "I7 timing, fixed-candidate scope or repeat/terminal control failed")

    def interleavings(self):
        self.i1()
        for status in (EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED):
            self.i2_i3(status, request_first=False)
            self.i2_i3(status, request_first=True)
        for read_first in (True, False):
            self.i4(read_first=read_first)
        for kind in ("unavailable", "invalid", "conflict"):
            self.i5(kind)
        for read in (True, False):
            for deactivate in (True, False):
                self.i6(read=read, deactivate=deactivate)
        self.i7()

    def browser_correction(self):
        dev = self.fixture()
        start, end = self.future()
        invalid = window(start + timedelta(minutes=30), end + timedelta(minutes=30))
        valid = window(start, end)
        detail = url("equipment-detail", dev.pk)
        form = url("reservation-submit", dev.pk)
        opener, _ = self.pair(Role.STUDENT)
        cookie_jar, = (handler.cookiejar for handler in opener.handlers if isinstance(handler, HTTPCookieProcessor))
        session, = (cookie for cookie in cookie_jar if cookie.name == settings.SESSION_COOKIE_NAME)
        before = self.snapshot(dev)
        evidence = dict(before=before, invalid=invalid, corrected=valid, student_id=self.users[Role.STUDENT].pk)
        with chrome() as browser:
            try:
                version = browser.call("Browser.getVersion")
                evidence["chrome"] = version["product"]
                cookie = browser.call("Network.setCookie", name=session.name, value=session.value, url=self.base,
                                      httpOnly=True, path="/")
                require(cookie.get("success"), "Chrome could not establish the real isolated fixture session")
                browser.call("Page.navigate", url=self.base + detail)
                link = f'a[href="{form}"]'
                browser.document(self.base + detail, 200, f"!!document.querySelector({json.dumps(link)})")
                browser.click(link)
                button = 'form[aria-describedby="time-rules"] button[type=submit]'
                browser.document(self.base + form, 200, f"!!document.querySelector({json.dumps(button)})")
                evidence["initial_validity"] = fill(browser, invalid, bypass=True)
                require(evidence["initial_validity"]["buttonNoValidate"], "Chrome did not prepare the initial illegal request")
                browser.click(button)
                evidence["rejected"] = browser.document(self.base + form, 400, """(() => {
                    const alert = document.querySelector('[role="alert"]');
                    if (!alert) return null;
                    const inputs = [...document.querySelectorAll('input[type="datetime-local"]')];
                    return {alert: alert.textContent, timeRules: document.querySelector('#time-rules').textContent,
                            bound: Object.fromEntries(inputs.map(input => [input.name, input.getAttribute('value')]))};
                })()""")
                evidence["after_reject"] = self.snapshot(dev)
                require(evidence["rejected"]["alert"] == INVALID_TIME_MESSAGE
                        and evidence["rejected"]["bound"] == invalid and self.unchanged(before, evidence["after_reject"]),
                        "Initial Chrome POST did not preserve the rejected values or wrote state")
                # This is still the actual bound 400 document. Do not bypass any validation on this submit.
                corrected = evidence["corrected_validity"] = fill(browser, valid)
                require(not corrected["formNoValidate"] and not corrected["buttonNoValidate"],
                        "Native validation was disabled on the correction")
                browser.click(button)
                require(corrected["valid"] and [item["value"] for item in corrected["inputs"]] == list(valid.values())
                        and all(item["valid"] and not item["stepMismatch"] for item in corrected["inputs"]),
                        "Chrome native validation blocked legal hours on the same rejected form")
                evidence["confirmation"] = browser.document(self.base + form, 201, """(() => {
                    const link = document.querySelector('main a');
                    if (!link) return null;
                    return {title: document.querySelector('h1').textContent, path: link.getAttribute('href'),
                            fields: [...document.querySelectorAll('dd')].map(element => element.textContent)};
                })()""")
                evidence["after_create"] = self.snapshot(dev)
                row, = evidence["after_create"]["rows"]
                result_path = url("reservation-result", row["id"])
                expected_fields = [str(row["id"]), f"{dev.number} · {dev.name}",
                                   f'{valid["start_at"].replace("T", " ")} 至 {valid["end_at"].replace("T", " ")}', "待审核"]
                require((row["applicant_id"], row["equipment_id"], row["start_at"], row["end_at"], row["status"])
                        == (self.users[Role.STUDENT].pk, dev.pk, start, end, Status.PENDING)
                        and evidence["after_create"]["effective"] == [row] and not evidence["after_create"]["history"]
                        and evidence["confirmation"] == dict(title="预约申请提交成功", path=result_path, fields=expected_fields),
                        "Chrome confirmation disagrees with the independently committed reservation")
                browser.click(f'a[href="{result_path}"]')
                evidence["readback"] = browser.document(self.base + result_path, 200, """(() => {
                    const fields = [...document.querySelectorAll('dd')].map(element => element.textContent);
                    return fields.length ? {title: document.querySelector('h1').textContent, fields} : null;
                })()""")
                evidence["after_read"] = self.snapshot(dev)
                require(evidence["readback"] == dict(title="我的预约结果", fields=expected_fields)
                        and self.unchanged(evidence["after_create"], evidence["after_read"]),
                        "Chrome owner readback disagrees with the independent final state")
                require([(doc["url"], doc["status"]) for doc in browser.documents] ==
                        [(self.base + path, status) for path, status in ((detail, 200), (form, 200), (form, 400),
                                                                        (form, 201), (result_path, 200))],
                        "Unexpected browser navigation or HTTP response sequence")
            finally:
                self.report(case="P01-chrome-correction", documents=browser.documents, **evidence)

    def permissions(self):
        dev = self.fixture()
        other = self.fixture()
        start, end = self.future()
        now = self.now()
        old = self.make(dev, now - timedelta(hours=2), now - timedelta(hours=1))
        form, result = url("reservation-submit", dev.pk), url("reservation-result", old.pk)
        values = window(start, end)
        student = self.pair(Role.STUDENT, form)
        teacher = self.pair(Role.TEACHER, form)
        active_peer = User.objects.create_user(username=f"{self.prefix}student-peer", password=self.password, role=Role.STUDENT)
        main_student = self.users[Role.STUDENT]
        self.users[Role.STUDENT] = active_peer
        try:
            peer = self.pair(Role.STUDENT, form)
        finally:
            self.users[Role.STUDENT] = main_student
        admin = self.pair(Role.ADMIN)
        anon = self.pair(None)
        # Use a separate account for the stale session while leaving student positive controls authorized.
        denied = User.objects.create_user(username=f"{self.prefix}inactive", password=self.password, role=Role.STUDENT)
        self.users[Role.STUDENT] = denied
        try:
            inactive = self.pair(Role.STUDENT, form)
        finally:
            self.users[Role.STUDENT] = main_student
        User.objects.filter(pk=denied.pk).update(is_active=False)
        detail = url("equipment-detail", dev.pk)
        for role, pair in [(Role.STUDENT, student), (Role.TEACHER, teacher), (Role.ADMIN, admin)]:
            response = self.prepare(pair, detail, role=role)[0]()
            self.report(case="detail-link", response=response)
            self.expect(response, 200)
            require((f'href="{form}"' in response["response"]["body"]) == (role != Role.ADMIN), "Wrong detail link permission")
        cases = [
            ("admin-get", admin, form, None, True, 403),
            ("anon-get", anon, form, None, True, 302),
            ("inactive-get", inactive, form, None, True, 302),
            ("admin-post", admin, form, values, True, 403),
            ("anon-post", anon, form, values, True, 302),
            ("inactive-post", inactive, form, values, True, 302),
            ("missing-csrf", student, form, values, False, 403),
            ("wrong-csrf", (student[0], teacher[1]), form, values, True, 403),
            ("foreign-result", teacher, result, None, True, 404),
            ("admin-result", admin, result, None, True, 403),
            ("anon-result", anon, result, None, True, 302),
            ("inactive-result", inactive, result, None, True, 302),
            ("missing-result", teacher, url("reservation-result", 2**62), None, True, 404),
            ("result-post", student, result, {}, True, 405),
        ]
        responses = {}
        for name, pair, path, data, csrf, code in cases:
            before = self.snapshot(dev)
            response = self.prepare(pair, path, data, use_csrf=csrf)[0]()
            after = self.snapshot(dev)
            self.report(case=name, before=before, after=after, response=response)
            self.expect(response, code)
            responses[name] = response["response"]
            require(dev.name not in response["response"]["body"] and dev.number not in response["response"]["body"]
                    and "lock_attempt_ns" not in response["server"] and not response["server"]["decisions"]
                    and self.unchanged(before, after), "Denied request leaked or acquired a business lock/wrote state")
        require(responses["foreign-result"]["body"] == responses["missing-result"]["body"], "Foreign GET differs from missing GET")

        observe_principal = {"capture_principal": True}
        missing = url("reservation-result", 2**62)
        peer_before = self.snapshot(dev)
        peer_foreign = self.prepare(peer, result, role=Role.STUDENT, control=observe_principal)[0]()
        peer_after = self.snapshot(dev)
        peer_missing = self.prepare(peer, missing, role=Role.STUDENT, control=observe_principal)[0]()
        missing_after = self.snapshot(dev)
        denied_fingerprints = [self.fingerprint(snapshot) for snapshot in (peer_before, peer_after, missing_after)]
        self.report(case="foreign-result-same-role", owner_id=main_student.pk, requester_id=active_peer.pk,
                    role=Role.STUDENT, observer_pid=self.observer_identity[-1],
                    before=peer_before, after=peer_after, missing_after=missing_after,
                    fingerprints=denied_fingerprints, responses=[peer_foreign, peer_missing])
        self.expect(peer_foreign, 404)
        self.expect(peer_missing, 404)
        protected = (dev.name, dev.number, main_student.username, "待审核", "已失效", f"<dd>{old.pk}</dd>",
                     *(moment.astimezone(services.BEIJING).strftime("%Y-%m-%d %H:%M")
                       for moment in (old.start_at, old.end_at)))
        foreign_body = peer_foreign["response"]["body"]
        require(main_student.pk != active_peer.pk and main_student.is_active and active_peer.is_active
                and len(set(denied_fingerprints)) == 1 and peer_after["rows"][0]["status"] == Status.PENDING
                and not peer_after["effective"] and not peer_after["history"]
                and foreign_body == peer_missing["response"]["body"]
                and all(value not in foreign_body for value in protected)
                and all(case["response"]["location"] is None
                        and "lock_attempt_ns" not in case["server"] and not case["server"]["decisions"]
                        and not case["server"]["history_attempts"] and not case["server"]["reservation_attempts"]
                        and all(sql.startswith("SELECT ") for sql in case["server"]["sql"])
                        and case["server"]["pid"] != self.observer_identity[-1] for case in (peer_foreign, peer_missing)),
                "Same-role foreign result exposed state, redirected, attempted a write, or differed from an absent record")
        before = self.snapshot(dev)
        owned = self.prepare(student, result, control=observe_principal)[0]()
        repeated = self.prepare(student, result, control=observe_principal)[0]()
        after = self.snapshot(dev)
        self.report(case="own-ended-repeat", owner_id=main_student.pk, target_id=old.pk,
                    before=before, after=after, responses=[owned, repeated])
        self.expect(owned, 200, "已失效")
        self.expect(repeated, 200, "已失效")
        for case, user_id, path in ((peer_foreign, active_peer.pk, result), (peer_missing, active_peer.pk, missing),
                                    (owned, main_student.pk, result), (repeated, main_student.pk, result)):
            require(case["server"]["principal"] == dict(user_id=user_id, role=Role.STUDENT, is_active=True,
                                                        is_authenticated=True, method="GET", path=path),
                    "Result request did not resolve the expected active student in the real auth middleware")
        self.expiry(after, old.pk, owned["server"]["decisions"][0])
        for index, (role, pair) in enumerate(((Role.STUDENT, student), (Role.TEACHER, teacher))):
            before = self.snapshot(dev)
            data = window(start + timedelta(hours=index), end + timedelta(hours=index))
            if index == 1:
                data.update(applicant=self.users[Role.ADMIN].pk, applicant_id=main_student.pk,
                            equipment=other.pk, equipment_id=other.pk, timezone="UTC")
            response = self.prepare(pair, form, data, role=role)[0]()
            after = self.snapshot(dev)
            row, = (r for r in after["rows"] if r not in before["rows"])
            read = self.prepare(pair, url("reservation-result", row["id"]), role=role)[0]()
            self.report(case="authorized" if index == 0 else "tampered-authorized", before=before, after=after,
                        other=self.snapshot(other), responses=[response, read])
            self.expect(response, 201)
            self.expect(read, 200, "待审核")
            require((row["applicant_id"], row["equipment_id"], row["start_at"], row["end_at"], row["applied_at"])
                    == (self.users[role].pk, dev.pk, start + timedelta(hours=index), end + timedelta(hours=index),
                        response["server"]["decisions"][0]) and not self.snapshot(other)["rows"], "Trusted data source mismatch")
        denied_count = sum(response["status"] in (302, 403, 404) for name, response in responses.items()
                           if name != "missing-result") + int(peer_foreign["response"]["status"] == 404)
        self.report(denied=denied_count, missing_control=2, unsupported_method_control=1,
                    positive_submission_controls=2, tampered_subset=1)

    def faults(self):
        def terminate(pid):
            app = connections["default"]
            killer = app.copy(alias="story21-killer")
            try:
                require(target(killer)[-1] != pid, "Termination must use a separate isolated backend")
                require(query(killer, "SELECT pg_terminate_backend(%s, 3000) AS terminated", [pid]) == (True,),
                        "Could not terminate the isolated request backend")
            finally:
                killer.close()

        for fault in ("F1-history", "F1-reservation", "F2", "F3", "F4"):
            dev = self.fixture()
            start, end = self.future()
            old = self.make(dev, self.now() - timedelta(minutes=1), end)
            path = url("reservation-submit", dev.pk)
            before = self.snapshot(dev)
            response = self.prepare(self.pair(Role.STUDENT, path), path, window(start, end),
                                    control={"fault": fault, "terminate": terminate})[0]()
            after = self.snapshot(dev)
            trace = response["server"]
            self.report(case=fault, before=before, after=after, response=response,
                        confirmation_simulated=fault == "F4")
            unknown = fault in ("F3", "F4")
            self.expect(response, 503, "结果待核查，请勿重复提交。" if unknown else "数据库事务已回滚")
            require("记录编号" not in response["response"]["body"] and CONFLICT_MESSAGE not in response["response"]["body"]
                    and (not unknown or "已回滚" not in response["response"]["body"])
                    and len(trace["decisions"]) == trace["history_attempts"] == 1
                    and trace["reservation_attempts"] == int(fault != "F1-history")
                    and trace["commit_attempts"] == int(not fault.startswith("F1")), "Fault evidence indicates retry or misleading response")
            code = trace.get("sqlstate")
            if unknown:
                require(code is None or code.startswith("08") or code in {"57P01", "57P02", "57P03"},
                        "Disconnect did not manifest as a connection error")
            else:
                require(code == ("23514" if fault.startswith("F1") else "23505"), "Wrong injected PostgreSQL SQLSTATE")
            if fault == "F4":
                self.expiry(after, old.pk, trace["decisions"][0])
                require(len(after["rows"]) == 2 and len(after["effective"]) == len(after["history"]) == 1,
                        "F4 real commit did not persist the combined result")
            else:
                require(self.unchanged(before, after), "Fault left partial durable rows")

    def time_boundaries(self):
        now = self.now().astimezone(services.BEIJING)
        start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        # 23:00 cannot be a valid start (23:00 is the latest legal end).
        while start.hour == 23 or start - now < timedelta(seconds=30):
            start += timedelta(hours=1)
        end = start + timedelta(hours=1)
        self.report(case="schedule", actual_server_now=now, boundary=start, legal_window=window(start, end))
        self.announce(f"B3/B4 real server boundary (Asia/Shanghai): {start.isoformat()}; waiting without a device lock")
        b3, b4 = self.fixture(), self.fixture()
        b3_old = self.make(b3, now - timedelta(hours=2), now - timedelta(hours=1))
        form3, form4 = url("reservation-submit", b3.pk), url("reservation-submit", b4.pk)
        pair3, pair4 = self.pair(Role.STUDENT, form3), self.pair(Role.TEACHER, form4)
        entered, release, control = self.commit_latch()
        exec3, trace3 = self.prepare(pair3, form3, window(start, end), role=Role.STUDENT)
        exec4, trace4 = self.prepare(pair4, form4, window(start, end), control=control, role=Role.TEACHER)
        while self.now() < start - timedelta(seconds=12):
            sleep(min(2, max(0.02, (start - self.now()).total_seconds() - 12)))
        require(self.now() < start - timedelta(seconds=8), "Missed scheduled real boundary before obtaining locks")
        app = connections["default"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                with transaction.atomic():
                    self.hold_device(b3)
                    actor3 = pool.submit(exec3)
                    actor4 = pool.submit(exec4)
                    blockers = self.wait_blocker(trace3, target(app)[-1])
                    blocked_at = self.now()
                    require(blocked_at < start and entered.wait(7) and trace4["decisions"][0] < start,
                            "Not ready before actual Beijing hour")
                    before3, before4 = self.snapshot(b3), self.snapshot(b4)
                    require(len(before3["rows"]) == 1 and not before3["history"]
                            and not before4["rows"] and not before4["history"], "Observer saw uncommitted boundary writes")
                    wait_for(lambda: self.now() >= start, "real Beijing start", timeout_seconds=20)
                    releasing_at = self.now()
            finally:
                release.set()
            response3, response4 = actor3.result(), actor4.result()
        after3, after4 = self.snapshot(b3), self.snapshot(b4)
        self.report(case="B3", real_blocked_at=blocked_at, release_at=releasing_at, start=start,
                    before=before3, after=after3, blockers=blockers, response=response3)
        self.report(case="B4", real_blocked_at=blocked_at, release_at=releasing_at, start=start,
                    before=before4, after=after4, response=response4)
        self.check_order(response3)
        self.check_order(response4)
        self.expect(response3, 400, INVALID_TIME_MESSAGE)
        self.expect(response4, 201)
        require(blocked_at < start <= releasing_at <= trace3["decisions"][0]
                and trace4["decisions"][0] < start and len(after3["rows"]) == len(after3["history"]) == 1,
                "Lock crossing and sample timestamps not demonstrated")
        self.expiry(after3, b3_old.pk, trace3["decisions"][0])
        row, = after4["rows"]
        require(row["applied_at"] == trace4["decisions"][0] and row["status"] == Status.PENDING
                and not after4["effective"] and not after4["history"], "B4 late COMMIT persistence mismatch")
        result = self.prepare(pair4, url("reservation-result", row["id"]), role=Role.TEACHER)[0]()
        finalized = self.snapshot(b4)
        self.report(case="B4-readback", before=after4, after=finalized, response=result)
        self.expect(result, 200, "已失效")
        self.expiry(finalized, row["id"], result["server"]["decisions"][0])


def baseline(connection, existing_tables=None):
    # Store full-row digests, never account passwords, session payloads or key material.
    tables = ("accounts_user", "django_session", "equipment_equipment", "reservations_reservation", "audit_operationhistory")
    summary = {}
    with connection.cursor() as cursor:
        for name in tables:
            if existing_tables is not None and name not in existing_tables:
                continue
            cursor.execute(f'SELECT row_to_json(t)::text AS payload FROM public.{name} AS t ORDER BY 1')
            payloads = [row[0] for row in cursor.fetchall()]
            summary[name] = {"count": len(payloads), "sha256": hashlib.sha256(json.dumps(payloads).encode()).hexdigest()}
    return summary


def pre_migration_state(connection):
    executor = MigrationExecutor(connection)
    executor.loader.check_consistent_history(connection)
    state = IsolatedPostgresRunner.database_state(connection)
    require(state[2:] == (0, 0), "Isolated database must have zero accounts and sessions before migration")
    tables, applied = {row[0] for row in state[0]}, set(state[1])
    require(not any(app in {"reservations", "audit"} and (app, name) not in STORY_MIGRATIONS for app, name in applied),
            "Unexpected reservation/audit migration already recorded; no rollback or migration authorized")
    require(all((key in applied) == (table in tables) for key, table in STORY_MIGRATIONS.items()),
            "Story migration tracking and actual table presence disagree")
    plan = [(migration.app_label, migration.name, backwards)
            for migration, backwards in executor.migration_plan(executor.loader.graph.leaf_nodes())]
    require(all(not backwards and (app, name) in STORY_MIGRATIONS for app, name, backwards in plan),
            "Only forward Story 2.1 initial migrations are authorized")
    require({(app, name) for app, name, _ in plan} == STORY_MIGRATIONS.keys() - applied,
            "Migration plan does not match the missing Story 2.1 initial migrations")
    return {"schema": state, "rows": baseline(connection, tables), "forward_plan": plan}


class Command(BaseCommand):
    help = "Run real loopback reservation probes only against the pre-created PostgreSQL test database."

    def add_arguments(self, parser):
        parser.add_argument("--group", choices=GROUPS, required=True)
        parser.add_argument("--evidence", type=Path, required=True)

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Reservation probes require the sole guarded test database")
        app = connections["default"]
        require(app.get_autocommit() and not app.in_atomic_block, "Probe fixtures must be genuinely committed")
        observer = app.copy(alias="story21-observer")
        group = options["group"]
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        try:
            observer_identity = target(observer)
            app_identity = target(app)
            require(observer_identity[-1] != app_identity[-1], "Observer connection is not independent")
            if group == "pre-migrate":
                state = pre_migration_state(app)
                with options["evidence"].open("x", encoding="utf-8") as raw:
                    json.dump({"database": app_identity, **state}, raw, sort_keys=True)
                self.stdout.write("STORY21_PROBE_OK pre-migrate")
                return
            before_schema = runner.setup_databases(aliases={"default": True})
            before = baseline(observer)
            if group == "baseline":
                with options["evidence"].open("x", encoding="utf-8") as raw:
                    json.dump({"schema": before_schema, "rows": before}, raw, sort_keys=True)
                self.stdout.write("STORY21_PROBE_OK baseline")
                return
            cases = {}
            prefix = f"S21-{uuid4().hex[:18]}-"
            with options["evidence"].open("x", encoding="utf-8") as raw:
                def report(**record):
                    raw.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                    raw.flush()

                report(group=group, hostname=platform.node(), python=platform.python_version(), machine=platform.platform(),
                       database=observer_identity, fixture_prefix=prefix, before=before, schema_before=before_schema)
                with make_server(HOST, 0, ProbeWSGI(cases), server_class=ThreadedServer, handler_class=QuietHandler) as server:
                    experiment = Experiment(observer, server, cases, prefix, report)
                    experiment.observer_identity = observer_identity
                    experiment.announce = lambda line: self.stdout.write(line, ending="\n")
                    thread = Thread(target=server.serve_forever, name="story21-loopback")
                    thread.start()
                    try:
                        for role in (Role.STUDENT, Role.TEACHER, Role.ADMIN):
                            experiment.users[role] = User.objects.create_user(
                                username=prefix + role, role=role, password=experiment.password)
                        with patch.object(services, "_decision_time", observe_decision):
                            {
                                "browser-correction": experiment.browser_correction,
                                "permissions": experiment.permissions,
                                "interleavings": experiment.interleavings,
                                "faults": experiment.faults,
                                "nfr001-standard": experiment.standard,
                                "time-boundaries": experiment.time_boundaries,
                            }[group]()
                    finally:
                        server.shutdown()
                        thread.join()
                        server.server_close()  # Wait for request threads before deleting owned fixtures.
                        equipment_ids = list(Equipment.objects.filter(number__startswith=prefix).values_list("pk", flat=True))
                        owned = Reservation.objects.filter(equipment_id__in=equipment_ids)
                        with transaction.atomic():
                            Session.objects.filter(session_key__in=experiment.session_keys).delete()
                            OperationHistory.objects.filter(reservation__in=owned).delete()
                            owned.delete()
                            Equipment.objects.filter(pk__in=equipment_ids).delete()
                            User.objects.filter(username__startswith=prefix).delete()
                        after = baseline(observer)
                        after_schema = runner.database_state(observer)
                        report(cleanup=True, after=after, schema_after=after_schema)
                        require(after == before and after_schema == before_schema, "Full-row or schema baseline changed")
            self.stdout.write(f"STORY21_PROBE_OK {group}")
        finally:
            observer.close()
            app.close()
