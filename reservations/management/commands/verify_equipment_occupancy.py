import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from threading import Event, Thread
from time import monotonic_ns
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4
from wsgiref.simple_server import make_server

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.handlers.wsgi import WSGIHandler
from django.core.management.base import BaseCommand
from django.db import Error, OperationalError, connections, transaction

from accounts.models import Role, User
from audit.models import OperationHistory
from equipment.models import Equipment
from lab_booking.database_config import HOST
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status
from reservations.views import CONFLICT_MESSAGE

from .verify_reservation_transactions import (
    PROBE,
    Experiment,
    ProbeWSGI,
    QuietHandler,
    ThreadedServer,
    baseline,
    is_account_recheck,
    observe_decision,
    query,
    require,
    sqlstate,
    target,
    url,
    wait_for,
    window,
)


RESERVATIONS = '"reservations_reservation"'
EQUIPMENT = '"equipment_equipment"'
HISTORY = '"audit_operationhistory"'
CLOCK = "SELECT clock_timestamp() AS decision_at"
EXPECTED_CASES = (
    "role-student", "role-teacher", "role-admin", "anonymous", "inactive-session", "invalid-date",
    "missing-equipment", "no-pending", "empty", "revoked-while-waiting", "frozen-legal",
    "frozen-due", "real-start-boundary", "real-post-decision-boundary", "submit-first", "query-first", "stale-result-conflict",
    "history-second", "commit-rejected", "commit-disconnected", "confirmation-lost",
)


class OccupancyWSGI(ProbeWSGI):
    """Trace only the existing isolated HTTP harness's opted-in requests."""

    def get_response(self, request):
        app = connections["default"]
        identity = target(app)
        case = self.cases.get(request.headers.get("X-Story21-Probe"))
        if case is None:
            return WSGIHandler.get_response(self, request)
        trace, control = case
        trace.update(identity=identity, pid=identity[-1], principal=None, statements=[], decisions=[],
                     commits=0, history_inserts=0)
        token = PROBE.set(trace)
        actual_commit = app._commit

        def intercept(execute, sql, params, many, context):
            if any(table in sql for table in (RESERVATIONS, EQUIPMENT, HISTORY)) or sql == CLOCK or is_account_recheck(sql):
                trace["statements"].append({"sql": sql, "bind": list(params or ()), "at_ns": monotonic_ns()})
            if sql.startswith(f'INSERT INTO {HISTORY}'):
                trace["history_inserts"] += 1
                if control.get("fault") == "history-second" and trace["history_inserts"] == 2:
                    # Send an invalid object_type on the second real PostgreSQL INSERT.
                    params = ("invalid", *params[1:])
            try:
                result = execute(sql, params, many, context)
                if "FOR UPDATE" in sql:
                    trace["lock_return_ns"] = monotonic_ns()
                return result
            except Error as error:
                trace["sqlstate"] = sqlstate(error)
                raise

        def commit():
            trace["commits"] += 1
            trace["commit_enter_ns"] = monotonic_ns()
            fault = control.get("fault")
            if "before_commit" in control:
                control["before_commit"]()
            if fault == "commit-rejected":
                query(app, "CREATE TEMP TABLE story22_fault(n int UNIQUE DEFERRABLE INITIALLY DEFERRED) ON COMMIT DROP")
                query(app, "INSERT INTO pg_temp.story22_fault VALUES (1), (1)")
            if fault == "commit-disconnected":
                killer = app.copy(alias="story22-killer")
                try:
                    require(target(killer)[-1] != trace["pid"], "COMMIT fault requires another isolated backend")
                    require(query(killer, "SELECT pg_terminate_backend(%s, 3000)", [trace["pid"]]) == (True,),
                            "Could not disconnect the isolated request backend")
                finally:
                    killer.close()
            try:
                actual_commit()
                trace["server_commit_return_ns"] = monotonic_ns()
                if fault == "confirmation-lost":
                    # A real successful PostgreSQL commit, with a simulated lost driver confirmation.
                    app.connection.close()
                    raise OperationalError("Story 2.2 simulated missing COMMIT confirmation")
            except Error as error:
                trace["sqlstate"] = sqlstate(error)
                raise

        try:
            with app.execute_wrapper(intercept), patch.object(app, "_commit", side_effect=commit):
                return WSGIHandler.get_response(self, request)
        finally:
            PROBE.reset(token)


class OccupancyExperiment(Experiment):
    def occupancy(self, dev, day, role=Role.ADMIN, *, pair=None, control=None):
        path = url("equipment-occupancy", dev)
        if day is not None:
            path += "?" + urlencode({"date": day})
        return self.prepare(pair or self.pair(role), path, control=control, role=role)

    def one(self, dev, day, role=Role.ADMIN, **kwargs):
        execute, _ = self.occupancy(dev, day, role, **kwargs)
        return execute()

    def hang_commit(self):
        entered, release = Event(), Event()

        def pause():
            entered.set()
            require(release.wait(25), "Timed out holding an in-flight isolated transaction")

        return entered, release, {"before_commit": pause}

    def hold_pid(self, dev):
        self.hold_device(dev)
        return query(connections["default"], "SELECT pg_backend_pid()")[0]

    @staticmethod
    def interval(start, end):
        return " ～ ".join(value.astimezone(services.BEIJING).strftime("%Y-%m-%d %H:%M:%S") for value in (start, end))

    @staticmethod
    def no_write(result):
        require(not any(re.match(r"^(INSERT|UPDATE|DELETE) ", stmt["sql"]) for stmt in result["server"]["statements"]),
                "Unexpected business DML")

    @staticmethod
    def scope(result, device, day, ids, *, locked):
        trace = result["server"]
        statements = trace["statements"]
        clocks = [i for i, stmt in enumerate(statements) if stmt["sql"] == CLOCK]
        locks = [(i, stmt) for i, stmt in enumerate(statements) if "FOR UPDATE" in stmt["sql"]]
        candidates = [(i, stmt) for i, stmt in enumerate(statements)
                      if stmt["sql"].startswith("SELECT ") and f'FROM {RESERVATIONS}' in stmt["sql"]]
        require(len(clocks) == len(trace["decisions"]) == trace["commits"] == 1, "Expected one clock and COMMIT")
        require(len(locks) == int(locked), "Wrong lock count")
        idx, candidate = candidates[0]
        utc_start = datetime.combine(day, time.min, services.BEIJING).astimezone(UTC)
        utc_end = datetime.combine(day + timedelta(days=1), time.min, services.BEIJING).astimezone(UTC)

        def scoped(statement):
            sql, bind = statement["sql"], statement["bind"]
            predicates = list(re.finditer(r'"reservations_reservation"\."(end_at|equipment_id|start_at)" (>|=|<) %s', sql))
            require(len(predicates) == 3 and {match.groups(): bind[sql[:match.start()].count("%s")] for match in predicates} ==
                    {("end_at", ">"): utc_start, ("start_at", "<"): utc_end, ("equipment_id", "="): device},
                    "Incorrect device/day binding")

        scoped(candidate)
        projection = candidate["sql"].partition(" FROM ")[0]
        require(re.findall(r'"reservations_reservation"\."([a-z_]+)"', projection) == ["id", "status"] and
                len(candidate["bind"]) == 3, "Candidate projection or stable predicates changed")
        lower = idx
        if locked:
            lower, lock = locks[0]
            require(idx < lower < clocks[0] and f'FROM {EQUIPMENT}' in lock["sql"]
                    and f'{EQUIPMENT}."id" = %s' in lock["sql"] and lock["bind"] == [device],
                    "Lock did not bind solely to target equipment after freeze")
        between = [stmt["sql"] for stmt in statements[lower + 1:clocks[0]]]
        account_rechecks = [i for i, sql in enumerate(between) if is_account_recheck(sql)]
        equipment_reads = [i for i, sql in enumerate(between) if f'{EQUIPMENT}."status"' in sql]
        require(len(account_rechecks) == len(equipment_reads) == 1 and account_rechecks[0] < equipment_reads[0],
                "Missing separate preclock account and equipment rechecks")
        if ids:
            reread_idx, reread = candidates[1]
            scoped(reread)
            projection = reread["sql"].partition(" FROM ")[0]
            require(lower + 1 + equipment_reads[0] < reread_idx < clocks[0]
                    and re.findall(r'"reservations_reservation"\."([a-z_]+)"', projection) == ["start_at", "end_at", "status"],
                    "Expected a separate, privacy-limited reread before the clock")
            for statement in statements[reread_idx:]:
                if RESERVATIONS not in statement["sql"]:
                    continue
                scoped(statement)
                match = re.search(r'"reservations_reservation"\."id" IN \((%s(?:, %s)*)\)', statement["sql"])
                require(match is not None, "Missing fixed candidate guard")
                offset = statement["sql"][:match.start()].count("%s")
                bound_ids = statement["bind"][offset:offset + match[1].count("%s")]
                require(set(bound_ids) == set(ids) and len(bound_ids) == len(ids), "Fixed candidate IDs changed")
        else:
            require(len(candidates) == 1, "Unexpected reread with no candidates")

    def authorization(self):
        dev = self.fixture()
        start, end = self.future()
        approved = self.make(dev, start, end, role="other-owner", status=Status.APPROVED)
        due = self.make(dev, self.now() - timedelta(hours=2), self.now() - timedelta(hours=1))
        due_day = due.start_at.astimezone(services.BEIJING).date()
        day = start.date()
        before = self.snapshot(dev)
        for role in Role:
            pair = self.pair(role)
            detail_path = url("equipment-detail", dev.pk)
            detail = self.http(pair[0], detail_path)
            path = url("equipment-occupancy", dev.pk)
            require(detail["status"] == 200 and f'action="{path}"' in detail["body"] and
                    'type="date"' in detail["body"], "Actual detail date control missing")
            result = self.one(dev.pk, day, role, pair=pair)
            self.expect(result, 200, self.interval(start, end))
            principal = result["server"]["principal"]
            require(principal["is_authenticated"] and principal["is_active"] and principal["role"] == role
                    and principal["user_id"] == self.users[role].pk and principal["user_id"] != approved.applicant_id,
                    "Wrong authenticated request principal or non-foreign occupancy fixture")
            require(not any(user.username in result["response"]["body"] for user in self.users.values()) and
                    url("reservation-result", approved.pk) not in result["response"]["body"], "Occupancy leaked identity/detail")
            self.scope(result, dev.pk, day, [approved.pk], locked=False)
            self.no_write(result)
            self.report(case=f"role-{role}", result=result, detail_path=detail_path, detail_status=detail["status"],
                        form_action=path, fixture_owner_id=approved.applicant_id)
        user = self.users[Role.STUDENT]
        inactive = self.pair(Role.STUDENT)
        User.objects.filter(pk=user.pk).update(is_active=False)
        try:
            negatives = (
                ("anonymous", self.one(dev.pk, due_day, None), 302, False),
                ("inactive-session", self.one(dev.pk, due_day, Role.STUDENT, pair=inactive), 302, False),
                ("invalid-date", self.one(dev.pk, "2025-02-29"), 400, True),
                ("missing-equipment", self.one(dev.pk + 10**12, due_day), 404, True),
            )
            for case, result, status, authenticated in negatives:
                self.expect(result, status)
                require(result["server"]["principal"]["is_authenticated"] == authenticated and
                        not result["server"]["decisions"] and not any(
                            RESERVATIONS in stmt["sql"] or "FOR UPDATE" in stmt["sql"]
                            for stmt in result["server"]["statements"]), "Denied request reached occupancy logic")
                self.no_write(result)
                require(self.unchanged(before, self.snapshot(dev)), "Denied request changed business rows")
                self.report(case=case, result=result, before=before, after=self.snapshot(dev))
        finally:
            User.objects.filter(pk=user.pk).update(is_active=True)

    def unlocked(self):
        start, end = self.future()
        for case in ("no-pending", "empty"):
            dev = self.fixture()
            ids = [self.make(dev, start, end, status=Status.APPROVED).pk] if case == "no-pending" else []
            execute, _ = self.occupancy(dev.pk, start.date())
            with ThreadPoolExecutor(1) as pool, transaction.atomic():
                blocker = self.hold_pid(dev)
                result = pool.submit(execute).result(timeout=8)
            self.expect(result, 200)
            self.scope(result, dev.pk, start.date(), ids, locked=False)
            self.no_write(result)
            self.report(case=case, result=result, concurrently_held_device_pid=blocker)

    def revoke(self):
        dev = self.fixture()
        end = self.now() - timedelta(minutes=1)
        old = self.make(dev, end - timedelta(minutes=5), end)
        before = self.snapshot(dev)
        execute, trace = self.occupancy(dev.pk, old.start_at.astimezone(services.BEIJING).date(), Role.STUDENT)
        user = self.users[Role.STUDENT]
        with ThreadPoolExecutor(1) as pool:
            try:
                with transaction.atomic():
                    blocker = self.hold_pid(dev)
                    task = pool.submit(execute)
                    blockers = self.wait_blocker(trace, blocker)
                    User.objects.filter(pk=user.pk).update(is_active=False)
                result = task.result()
                self.expect(result, 403)
                self.no_write(result)
                require(trace["principal"]["is_authenticated"] and not trace["decisions"] and not trace["commits"]
                        and any(is_account_recheck(stmt["sql"]) for stmt in trace["statements"]),
                        "Revoked request reached decision or missed lock-time account recheck")
                after = self.snapshot(dev)
                require(self.unchanged(before, after), "Revoked request changed business rows")
                self.report(case="revoked-while-waiting", result=result, blockers=blockers, before=before, after=after)
            finally:
                User.objects.filter(pk=user.pk).update(is_active=True)

    def freeze(self, *, legal):
        dev = self.fixture()
        future, end = self.future()
        if legal:
            base = self.make(dev, future - timedelta(hours=2), future - timedelta(hours=1))
            day = future.date()
            submit_path = url("reservation-submit", dev.pk)
            entered, release, control = self.hang_commit()
            writer, writer_trace = self.prepare(self.pair(Role.TEACHER, submit_path), submit_path, window(future, end),
                                                control=control, role=Role.TEACHER)
        else:
            now = self.now()
            start = (now - timedelta(minutes=10)).astimezone(services.BEIJING)
            end = start + timedelta(minutes=1)
            day = start.date()
            base = self.make(dev, start - timedelta(minutes=1), start + timedelta(minutes=2))
        reader, trace = self.occupancy(dev.pk, day)
        before = self.snapshot(dev)
        with ThreadPoolExecutor(2) as pool:
            if legal:
                task = pool.submit(writer)
                try:
                    require(entered.wait(10), "Legal writer did not reach pre-COMMIT while holding device")
                    read_task = pool.submit(reader)
                    blockers = self.wait_blocker(trace, writer_trace["pid"])
                finally:
                    release.set()
                written = task.result()
                self.expect(written, 201)
            else:
                with transaction.atomic():
                    blocker = self.hold_pid(dev)
                    read_task = pool.submit(reader)
                    blockers = self.wait_blocker(trace, blocker)
                    self.make(dev, start, end, role=Role.TEACHER)
                written = None
            first = read_task.result()
        middle = self.snapshot(dev)
        fresh, = [row for row in middle["rows"] if row["id"] != base.pk]
        self.expect(first, 200)
        self.scope(first, dev.pk, day, [base.pk], locked=True)
        require(fresh["status"] == Status.PENDING and all(row["reservation_id"] != fresh["id"] for row in middle["history"]),
                "First query mutated a new reservation outside the freeze")
        second = self.one(dev.pk, day)
        self.expect(second, 200)
        self.scope(second, dev.pk, day, [base.pk, fresh["id"]], locked=True)
        after = self.snapshot(dev)
        if legal:
            label = self.interval(future, end)
            require(label not in first["response"]["body"] and label in second["response"]["body"],
                    "New future occupancy was not excluded, then included")
        else:
            self.expiry(middle, base.pk, trace["decisions"][0])
            self.expiry(after, fresh["id"], second["server"]["decisions"][0])
            self.expiry(after, base.pk, trace["decisions"][0])
        self.report(case="frozen-legal" if legal else "frozen-due", before=before, middle=middle, after=after,
                    blockers=blockers, first=first, second=second, writer=written)

    def boundary(self):
        dev = self.fixture()
        pair = self.pair(Role.ADMIN)
        start = self.now() + timedelta(seconds=6)
        row = self.make(dev, start, start + timedelta(minutes=1))
        day = start.astimezone(services.BEIJING).date()
        execute, trace = self.occupancy(dev.pk, day, pair=pair)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                blocker = self.hold_pid(dev)
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                waiting_at = self.now()
                require(waiting_at < start and not trace["decisions"], "Fixture did not block before actual start")
                wait_for(lambda: self.now() >= start, "real database clock crossed start", timeout_seconds=20)
            result = task.result()
        self.expect(result, 200, "该日期无有效预约占用")
        self.scope(result, dev.pk, day, [row.pk], locked=True)
        after = self.snapshot(dev)
        decision, = trace["decisions"]
        require(waiting_at < start <= decision, "Real boundary ordering failed")
        self.expiry(after, row.pk, decision)
        self.report(case="real-start-boundary", pre_start_wait=waiting_at, start=start,
                    blockers=blockers, result=result, after=after)

    def post_decision_boundary(self):
        dev = self.fixture()
        pair = self.pair(Role.ADMIN)
        start = self.now() + timedelta(seconds=6)
        row = self.make(dev, start, start + timedelta(minutes=1))
        day = start.astimezone(services.BEIJING).date()
        entered, release, control = self.hang_commit()
        execute, trace = self.occupancy(dev.pk, day, pair=pair, control=control)
        before = self.snapshot(dev)
        with ThreadPoolExecutor(1) as pool:
            task = pool.submit(execute)
            try:
                require(entered.wait(10) and trace["decisions"][0] < start,
                        "Query did not reach decision before start")
                wait_for(lambda: self.now() >= start, "real database clock crossed start before COMMIT", timeout_seconds=15)
                at_commit_release = self.now()
            finally:
                release.set()
            first = task.result()
        self.expect(first, 200, "待审核（未开始）")
        self.scope(first, dev.pk, day, [row.pk], locked=True)
        self.no_write(first)
        middle = self.snapshot(dev)
        require(middle["rows"] == before["rows"] and middle["history"] == before["history"],
                "Late commit ignored the fixed pre-start decision")
        second = self.one(dev.pk, day, pair=pair)
        self.expect(second, 200, "该日期无有效预约占用")
        after = self.snapshot(dev)
        self.expiry(after, row.pk, second["server"]["decisions"][0])
        self.report(case="real-post-decision-boundary", before=before, middle=middle, after=after,
                    start=start, at_commit_release=at_commit_release, first=first, second=second)

    def submit_query_order(self, *, query_first):
        dev, peer = self.fixture(), self.fixture()
        start, end = self.future()
        now = self.now()
        due = self.make(dev, now - timedelta(minutes=1), end)
        day = start.date()
        submit_path = url("reservation-submit", dev.pk)
        peer_path = url("reservation-submit", peer.pk)
        entered, release, control = self.hang_commit()
        reader, read_trace = self.occupancy(dev.pk, day, control=control if query_first else None)
        writer, write_trace = self.prepare(self.pair(Role.TEACHER, submit_path), submit_path, window(start, end),
                                            control=None if query_first else control, role=Role.TEACHER)
        peer_writer, _ = self.prepare(self.pair(Role.STUDENT, peer_path), peer_path, window(start, end), role=Role.STUDENT)
        lead, lead_trace, follow, follow_trace = (reader, read_trace, writer, write_trace) if query_first else (
            writer, write_trace, reader, read_trace)
        before = self.snapshot(dev)
        with ThreadPoolExecutor(2) as pool:
            lead_task = pool.submit(lead)
            try:
                require(entered.wait(10), "Leading transaction did not reach pre-COMMIT")
                follow_task = pool.submit(follow)
                blockers = self.wait_blocker(follow_trace, lead_trace["pid"])
                during = self.snapshot(dev)
                require(self.unchanged(before, during), "Observer saw uncommitted expiry or submission")
                peer_result = peer_writer()
                self.expect(peer_result, 201)
            finally:
                release.set()
            leader, follower = lead_task.result(), follow_task.result()
        read, written = (leader, follower) if query_first else (follower, leader)
        self.expect(written, 201)
        self.expect(read, 200, "该日期无有效预约占用")
        self.scope(read, dev.pk, day, [due.pk], locked=True)
        after = self.snapshot(dev)
        self.expiry(after, due.pk, lead_trace["decisions"][0])
        require(len(after["effective"]) == len(after["history"]) == 1 and
                lead_trace["history_inserts"] == 1 and follow_trace["history_inserts"] == 0 and
                lead_trace["decisions"][0] < follow_trace["decisions"][0],
                "Transaction order or duplicate expiry mismatch")
        self.report(case="query-first" if query_first else "submit-first", before=before, during=during, after=after,
                    blockers=blockers, read=read, written=written, peer=peer_result)

    def conflict(self):
        dev = self.fixture()
        start, end = self.future()
        first = self.one(dev.pk, start.date(), Role.STUDENT)
        self.expect(first, 200, "该日期无有效预约占用")
        require("无占用不等于可预约" in first["response"]["body"], "Query overpromises availability")
        path = url("reservation-submit", dev.pk)
        accepted = self.prepare(self.pair(Role.TEACHER, path), path, window(start, end), role=Role.TEACHER)[0]()
        denied = self.prepare(self.pair(Role.STUDENT, path), path, window(start, end), role=Role.STUDENT)[0]()
        self.expect(accepted, 201)
        self.expect(denied, 409, CONFLICT_MESSAGE)
        after = self.snapshot(dev)
        require(len(after["rows"]) == len(after["effective"]) == 1 and not after["history"] and
                after["effective"][0]["applicant_id"] == self.users[Role.TEACHER].pk,
                "Stale query improperly influenced formal conflict check")
        self.report(case="stale-result-conflict", read=first, accepted=accepted, denied=denied, after=after)

    def faults(self):
        for fault in ("history-second", "commit-rejected", "commit-disconnected", "confirmation-lost"):
            dev = self.fixture()
            end = self.now() - timedelta(minutes=1)
            old = [self.make(dev, end - timedelta(minutes=i), end) for i in (1, 2)]
            day = (end - timedelta(microseconds=1)).astimezone(services.BEIJING).date()
            before = self.snapshot(dev)
            result = self.one(dev.pk, day, control={"fault": fault})
            response = result["response"]["body"]
            trace = result["server"]
            unknown = fault in ("commit-disconnected", "confirmation-lost")
            self.expect(result, 503, "待核查" if unknown else "未成功")
            require("被有效预约占用" not in response and ("已回滚" in response) != unknown
                    and len(trace["decisions"]) == 1 and trace["history_inserts"] == 2
                    and trace["commits"] == int(fault != "history-second"), "Wrong failure output or retried operation")
            after = self.snapshot(dev)
            if fault == "confirmation-lost":
                for row in old:
                    self.expiry(after, row.pk, trace["decisions"][0])
            else:
                require(self.unchanged(before, after), "Confirmed failure or pre-COMMIT disconnect left partial changes")
            expected_sqlstate = {"history-second": "23514", "commit-rejected": "23505"}.get(fault)
            require("sqlstate" in trace and (expected_sqlstate is None or trace["sqlstate"] == expected_sqlstate),
                    "Unexpected PostgreSQL fault code")
            self.report(case=fault, before=before, after=after, result=result,
                        driver_confirmation_simulated=fault == "confirmation-lost", retry=False)


class Command(BaseCommand):
    help = "Verify Story 2.2 via independent loopback HTTP and guarded PostgreSQL connections."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Story 2.2 requires the sole guarded test connection")
        app = connections["default"]
        observer = app.copy(alias="story22-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        try:
            identity = target(observer)
            app_identity = target(app)
            require(app_identity[-1] != identity[-1] and app.get_autocommit() and not app.in_atomic_block,
                    "Story 2.2 requires committed fixtures and an independent observer")
            schema = runner.setup_databases(aliases={"default": True})
            rows = baseline(observer)
            cases, completed = {}, []
            prefix = f"S22-{uuid4().hex[:18]}-"
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                def report(**record):
                    evidence.write(json.dumps(record, ensure_ascii=False, default=str, sort_keys=True) + "\n")
                    evidence.flush()
                    if "case" in record:
                        completed.append(record["case"])

                report(database=identity, before=rows, schema_before=schema)
                with make_server(HOST, 0, OccupancyWSGI(cases), server_class=ThreadedServer,
                                 handler_class=QuietHandler) as server:
                    probe = OccupancyExperiment(observer, server, cases, prefix, report)
                    thread = Thread(target=server.serve_forever, name="story22-loopback")
                    thread.start()
                    try:
                        for role in Role:
                            probe.users[role] = User.objects.create_user(
                                username=prefix + role, role=role, password=probe.password)
                        probe.users["other-owner"] = User.objects.create_user(username=prefix + "other-owner", role=Role.STUDENT)
                        with patch.object(services, "_decision_time", observe_decision):
                            probe.authorization()
                            probe.unlocked()
                            probe.revoke()
                            probe.freeze(legal=True)
                            probe.freeze(legal=False)
                            probe.boundary()
                            probe.post_decision_boundary()
                            probe.submit_query_order(query_first=False)
                            probe.submit_query_order(query_first=True)
                            probe.conflict()
                            probe.faults()
                    finally:
                        server.shutdown()
                        thread.join()
                        server.server_close()
                        with transaction.atomic():
                            devices = Equipment.objects.filter(number__startswith=prefix)
                            reservations = Reservation.objects.filter(equipment__in=devices)
                            Session.objects.filter(session_key__in=probe.session_keys).delete()
                            OperationHistory.objects.filter(reservation__in=reservations).delete()
                            reservations.delete()
                            devices.delete()
                            User.objects.filter(username__startswith=prefix).delete()
                        after, schema_after = baseline(observer), runner.database_state(observer)
                        report(cleanup=True, after=after, schema_after=schema_after)
                        require(rows == after and schema == schema_after, "Isolated baseline changed after cleanup")
                require(tuple(completed) == EXPECTED_CASES, "Actual probe denominator differs from the expected cases")
            self.stdout.write(f"STORY22_PROBE_OK cases={len(completed)}")
        finally:
            observer.close()
            app.close()
