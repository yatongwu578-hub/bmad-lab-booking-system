"""Story 2.8 lock, authorization and COMMIT evidence through isolated PostgreSQL and HTTP."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4
from wsgiref.simple_server import make_server

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.urls import reverse

from accounts.models import Role, User
from audit.models import OperationHistory
from equipment.models import Equipment
from lab_booking.database_config import HOST
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status

from .verify_admin_reservations import database_snapshot
from .verify_own_cancellation import CancellationExperiment, CancellationWSGI
from .verify_own_reservations import CLOCK, RESERVATIONS
from .verify_reservation_transactions import (
    QuietHandler, ThreadedServer, is_account_recheck, observe_decision, query, require, target, url, wait_for, window,
)


REASON = "变更实验安排"
SUCCESS = "预约已取消"
TERMINAL = "预约当前状态不允许取消"
EXPIRED = "已失效，未执行取消"
ENDED = "结束时间已到，未执行取消"
HOUR = timedelta(hours=1)


class AdminCancellationExperiment(CancellationExperiment):
    @staticmethod
    def cancel_path(row):
        return url("admin-reservation-cancel", row.pk)

    def cancel(self, actor, row, *, pair=None, control=None, reason=REASON):
        return self.prepare(pair or self.pair(actor), self.cancel_path(row), {"reason": reason},
                            control={"capture_principal": True, **(control or {})})

    def assert_order(self, result, actor, row, *, writes, commits=1):
        trace = result["server"]
        entries = trace["bindings"]

        def indexes(test):
            return [i for i, item in enumerate(entries) if test(item["sql"])]

        accounts = indexes(is_account_recheck)
        pre, = indexes(lambda sql: sql.startswith(f'SELECT {RESERVATIONS}."equipment_id"'))
        lock, = indexes(lambda sql: "FOR UPDATE" in sql)
        read, = indexes(lambda sql: sql.startswith(f'SELECT {RESERVATIONS}."id"') and "INNER JOIN" in sql)
        clock, = indexes(lambda sql: sql == CLOCK)
        dml = indexes(lambda sql: sql.startswith(("UPDATE ", "INSERT ", "DELETE ")))
        require(len(accounts) == 2 and len(trace["decisions"]) == 1 and len(dml) == writes
                and trace["commit_attempts"] == commits and trace["pid"] != self.observer_pid
                and trace["principal"]["user_id"] == self.users[actor].pk,
                "Unexpected principal, clock, write or COMMIT count")
        require(accounts[0] < pre < lock < accounts[1] < read < clock
                and trace["lock_acquired_ns"] < entries[clock]["at_ns"] and all(clock < i for i in dml),
                "Expected authorization, scoped lookup, device lock, recheck, reread and one clock")
        require(entries[accounts[0]]["executed"] == entries[accounts[1]]["executed"] == [self.users[actor].pk]
                and entries[pre]["executed"] == [row.pk] and entries[lock]["executed"] == [row.equipment_id]
                and entries[read]["executed"] == [row.pk, row.equipment_id], "Incorrect target or device scope")
        return trace["decisions"][0]

    def storage(self, before, after, row, final, events, *, actor_type="admin"):
        old = next(item for item in before["rows"] if item["id"] == row.pk)
        rows = [item for item in after["rows"] if item["id"] == row.pk]
        require(rows == [{**old, "status": final}] and before["device"] == after["device"]
                and all(item in after["rows"] for item in before["rows"] if item["id"] != row.pk)
                and before["history"] == after["history"][:len(before["history"])],
                "Reservation identity, unrelated device or historical rows changed")
        new = after["history"][len(before["history"]):]
        require(len(new) == len(events), "Unexpected transition count")
        for history, (action, prior, next_status, actor, reason, decision) in zip(new, events, strict=True):
            require((history["object_type"], history["reservation_id"], history["equipment_id"], history["action"],
                     history["before_status"], history["after_status"], history["actor_type"], history["actor_id"],
                     history["reason"], history["decision_at"]) ==
                    ("reservation", row.pk, None, action, prior, next_status, actor_type if actor else "system",
                     self.users[actor].pk if actor else None, reason, decision)
                    and decision <= history["recorded_at"] <= after["observed_at"], "Incorrect history or recorded clock")
        if final in (Status.CANCELLED, Status.REJECTED, Status.EXPIRED):
            require(all(item["id"] != row.pk for item in after["effective"]), "Terminal row occupies the slot")

    def overlap(self, first, second, entered, release, device, before):
        with ThreadPoolExecutor(max_workers=2) as pool:
            lead = pool.submit(first[0])
            try:
                require(entered.wait(10), "First request did not reach COMMIT")
                follow = pool.submit(second[0])
                blockers = self.wait_blocker(second[1], first[1]["pid"])
                during = self.snapshot(device)
                require(len({first[1]["pid"], second[1]["pid"], self.observer_pid}) == 3 and not second[1]["decisions"]
                        and all(during[key] == before[key] for key in ("device", "rows", "history")),
                        "Observed partial data or the follower sampled before taking the lock")
            finally:
                release.set()
            return lead.result(), follow.result(), blockers, during

    def interleave(self, admin, other_admin, student, peer, operation, *, cancel_first, due=False):
        device = self.fixture()
        start, end = self.future()
        row = self.put(student, device, self.now() - HOUR if due else start)
        before = self.snapshot(device)
        entered, release, hold = self.commit_latch()
        cancel = self.cancel(admin, row, control=hold if cancel_first else None)
        control = None if cancel_first else hold
        if operation == "cancel":
            other = self.cancel(other_admin, row, control=control)
        elif operation in {"approve", "reject"}:
            other = self.prepare(self.pair(other_admin), url(f"admin-reservation-{operation}", row.pk),
                                 {"reason": REASON} if operation == "reject" else {}, control=control)
        elif operation == "submit":
            path = url("reservation-submit", device.pk)
            other = self.prepare(self.pair(peer, path), path, window(start, end), control=control)
        elif operation == "admin-detail":
            other = self.prepare(self.pair(other_admin), url("admin-reservation-detail", row.pk), control=control)
        else:
            other = self.listing(student, path=self.detail_path(row.pk), control=control)
        first, second = (cancel, other) if cancel_first else (other, cancel)
        lead, follow, blockers, during = self.overlap(first, second, entered, release, device, before)
        cancelled, counterpart = (lead, follow) if cancel_first else (follow, lead)
        successful = not due and (cancel_first or operation != "reject")
        cancel_message = SUCCESS if successful else (EXPIRED if due and cancel_first else TERMINAL)
        self.expect(cancelled, 200 if successful else 409, cancel_message)
        cancel_at = self.assert_order(cancelled, admin, row, writes=2 if successful or (due and cancel_first) else 0)
        other_at, = counterpart["server"]["decisions"]
        lead_at, = lead["server"]["decisions"]
        follow_at, = follow["server"]["decisions"]
        require(lead_at < follow_at, "Follower did not sample behind the actual lock holder")
        prior = Status.APPROVED if operation == "approve" and not cancel_first else Status.PENDING
        events = []
        if due:
            final = Status.EXPIRED
            events.append(("expire", Status.PENDING, final, None, "开始时间已到仍待审核", lead_at))
        elif successful:
            final = Status.CANCELLED
            if prior == Status.APPROVED:
                events.append(("approve", Status.PENDING, Status.APPROVED, other_admin, "", other_at))
            events.append(("cancel", prior, final, admin, REASON, cancel_at))
        else:
            final = Status.REJECTED
            events.append(("reject", Status.PENDING, final, other_admin, REASON, other_at))

        if operation == "cancel":
            self.expect(counterpart, 409, TERMINAL)
            self.assert_order(counterpart, other_admin, row, writes=0)
        elif operation in {"approve", "reject"}:
            self.expect(counterpart, 409 if cancel_first else (200 if operation == "approve" else 302))
        elif operation == "submit":
            self.expect(counterpart, 201 if cancel_first else 409)
        else:
            label = "已失效" if due else ("已取消" if cancel_first else "待审核")
            self.expect(counterpart, 200, label)
        after = self.snapshot(device)
        self.storage(before, after, row, final, events)
        if cancel_first and operation == "submit":
            effective, = after["effective"]
            require(effective["id"] != row.pk and effective["applicant_id"] == self.users[peer].pk
                    and effective["start_at"] == start and effective["end_at"] == end,
                    "Follower did not become the sole effective occupant")
        else:
            require(not after["effective"] and len(after["rows"]) == len(before["rows"]),
                    "Unexpected reservation or overlap exists")
        self.report(case=f"{operation}-{'cancel-first' if cancel_first else 'other-first'}{'-due' if due else ''}",
                    before=before, during=during, after=after, lead=lead, follow=follow, blockers=blockers)

    def owner_cancel_race(self, admin, student, *, admin_first):
        device = self.fixture()
        row = self.put(student, device, self.future()[0])
        before = self.snapshot(device)
        entered, release, hold = self.commit_latch()
        admin_request = self.cancel(admin, row, control=hold if admin_first else None)
        owner_path = url("reservation-cancel", row.pk)
        owner_request = self.prepare(self.pair(student, owner_path), owner_path, {}, control={
            "capture_principal": True, **({} if admin_first else hold),
        })
        first, second = (admin_request, owner_request) if admin_first else (owner_request, admin_request)
        lead, follow, blockers, during = self.overlap(first, second, entered, release, device, before)
        admin_result, owner_result = (lead, follow) if admin_first else (follow, lead)
        self.expect(lead, 200, SUCCESS)
        self.expect(follow, 409, TERMINAL)
        for result, actor, path in ((admin_result, admin, self.cancel_path(row)), (owner_result, student, owner_path)):
            principal = result["server"]["principal"]
            require(principal["method"] == "POST" and principal["path"] == path
                    and principal["user_id"] == self.users[actor].pk and principal["role"] == self.users[actor].role,
                    "Race was not exercised by the required authenticated POST route")
        admin_at = self.assert_order(admin_result, admin, row, writes=2 if admin_first else 0)
        CancellationExperiment.assert_order(self, owner_result, student, row, writes=0 if admin_first else 2)
        owner_at, = owner_result["server"]["decisions"]
        lead_at, follow_at = (admin_at, owner_at) if admin_first else (owner_at, admin_at)
        require(lead_at < follow_at < row.start_at and lead["server"]["pid"] in blockers
                and [item["id"] for item in before["effective"]] == [row.pk] and during["effective"] == before["effective"],
                "Follower did not wait for the valid cancellation or uncommitted occupancy changed")
        after = self.snapshot(device)
        winner, reason = (admin, REASON) if admin_first else (student, "")
        self.storage(before, after, row, Status.CANCELLED,
                     [("cancel", Status.PENDING, Status.CANCELLED, winner, reason, lead_at)],
                     actor_type="admin" if admin_first else "applicant")
        require(len(after["rows"]) == 1 and not after["effective"], "Cancellation did not release the original reservation")
        self.report(case=f"owner-cancel-{'admin-first' if admin_first else 'owner-first'}",
                    before=before, during=during, after=after, lead=lead, follow=follow, blockers=blockers)

    def boundary(self, admin, student, status, *, commit_after):
        device = self.fixture()
        pair, follower_pair = self.pair(admin), self.pair(admin)
        boundary = self.now() + timedelta(seconds=4)
        start = boundary if status == Status.PENDING else boundary - HOUR
        row = self.put(student, device, start, status)
        before = self.snapshot(device)
        follower = None
        with ThreadPoolExecutor(max_workers=2) as pool:
            if commit_after:
                entered, release, hold = self.commit_latch()
                execute, trace = self.cancel(admin, row, pair=pair, control=hold)
                task = pool.submit(execute)
                try:
                    require(entered.wait(10) and trace["decisions"][0] < boundary, "No pre-boundary decision before COMMIT")
                    run_follower, follower_trace = self.cancel(admin, row, pair=follower_pair)
                    waiting = pool.submit(run_follower)
                    blockers = self.wait_blocker(follower_trace, trace["pid"])
                    during = self.snapshot(device)
                    require(before["rows"] == during["rows"] and before["history"] == during["history"],
                            "Uncommitted change became visible")
                    crossed = wait_for(lambda: (now := self.now()) >= boundary and now, "COMMIT crosses appointment boundary")
                finally:
                    release.set()
                follower = waiting.result()
                self.expect(follower, 409, TERMINAL)
                self.assert_order(follower, admin, row, writes=0)
            else:
                execute, trace = self.cancel(admin, row, pair=pair)
                with transaction.atomic():
                    self.hold_device(device)
                    pid = query(connections["default"], "SELECT pg_backend_pid()")[0]
                    task = pool.submit(execute)
                    blockers = self.wait_blocker(trace, pid)
                    during = self.snapshot(device)
                    require(during["observed_at"] < boundary and not trace["decisions"], "No pre-boundary wait without sampling")
                    crossed = wait_for(lambda: (now := self.now()) >= boundary and now, "lock wait crosses appointment boundary")
            result = task.result()
        self.expect(result, 200 if commit_after else 409, SUCCESS if commit_after else (EXPIRED if status == Status.PENDING else ENDED))
        decision = self.assert_order(result, admin, row, writes=2 if commit_after or status == Status.PENDING else 0)
        require(decision < boundary <= crossed if commit_after else boundary <= crossed <= decision,
                "Database clock did not straddle the appointment boundary as specified")
        after = self.snapshot(device)
        if commit_after:
            self.storage(before, after, row, Status.CANCELLED, [("cancel", status, Status.CANCELLED, admin, REASON, decision)])
        elif status == Status.PENDING:
            self.storage(before, after, row, Status.EXPIRED,
                         [("expire", status, Status.EXPIRED, None, "开始时间已到仍待审核", decision)])
        else:
            require(self.unchanged(before, after), "Ended approved row was changed or expired")
        self.report(case=f"{'commit' if commit_after else 'wait'}-crosses-{status}", result=result, follower=follower,
                    boundary=boundary, crossed=crossed, blockers=blockers, before=before, during=during, after=after)

    def approval_ends_while_cancellation_waits(self, admin, other_admin, student):
        device = self.fixture()
        admin_pair, other_pair = self.pair(admin), self.pair(other_admin)
        start = self.now() + timedelta(seconds=4)
        row = self.put(student, device, start, duration=timedelta(seconds=2))
        before = self.snapshot(device)
        entered, release, hold = self.commit_latch()
        approving, approved_trace = self.prepare(other_pair, url("admin-reservation-approve", row.pk), {}, control=hold)
        cancelling, cancel_trace = self.cancel(admin, row, pair=admin_pair)
        with ThreadPoolExecutor(max_workers=2) as pool:
            approve = pool.submit(approving)
            try:
                require(entered.wait(10), "Approval did not hold COMMIT")
                cancel = pool.submit(cancelling)
                blockers = self.wait_blocker(cancel_trace, approved_trace["pid"])
                during = self.snapshot(device)
                require(during["observed_at"] < row.end_at and not cancel_trace["decisions"]
                        and before["rows"] == during["rows"] and before["history"] == during["history"],
                        "No pre-end blocked cancellation or partial approval was visible")
                crossed = wait_for(lambda: (now := self.now()) >= row.end_at and now, "waiting cancel crosses approved end")
            finally:
                release.set()
            lead, follow = approve.result(), cancel.result()
        self.expect(lead, 200)
        self.expect(follow, 409, ENDED)
        approved_at, = approved_trace["decisions"]
        cancelled_at = self.assert_order(follow, admin, row, writes=0)
        require(approved_at < row.start_at < row.end_at <= crossed <= cancelled_at,
                "Approval and cancellation did not straddle intended boundaries")
        after = self.snapshot(device)
        self.storage(before, after, row, Status.APPROVED,
                     [("approve", Status.PENDING, Status.APPROVED, other_admin, "", approved_at)])
        self.report(case="approve-first-wait-crosses-end", before=before, during=during, after=after,
                    lead=lead, follow=follow, blockers=blockers, crossed=crossed)

    def permissions(self, admin, student, teacher):
        device = self.fixture()
        row = self.put(student, device, self.now() - HOUR)
        disabled, flagged = self.actor(Role.ADMIN), self.actor(Role.STUDENT)
        User.objects.filter(pk=self.users[flagged].pk).update(is_staff=True, is_superuser=True)
        disabled_pair = self.pair(disabled)
        User.objects.filter(pk=self.users[disabled].pk).update(is_active=False)
        before = self.snapshot(device)
        paths = (self.cancel_path(row), url("admin-reservation-cancel", 2 ** 62))
        detail = url("admin-reservation-detail", row.pk)
        detail_link = re.compile(r'(?:href|action)="' + re.escape(detail) + r'[?"#]')
        runs = []
        for name, actor, pair, expected in (
            ("anonymous", None, self.pair(None), 302), ("student", student, self.pair(student), 403),
            ("teacher", teacher, self.pair(teacher), 403), ("flagged", flagged, self.pair(flagged), 403),
            ("disabled-session", disabled, disabled_pair, 302),
        ):
            for path in paths:
                for fields in (None, {"reason": REASON}):
                    result = self.prepare(pair, path, fields, control={"capture_principal": True})[0]()
                    self.expect(result, expected)
                    response, trace = result["response"], result["server"]
                    location = urlsplit(response["location"] or "")
                    if expected == 302:
                        # Django puts the requested cancel path in `next`; sharing a prefix with
                        # the detail route does not turn it into a detail redirect.
                        require(not (location.scheme or location.netloc or location.fragment)
                                and location.path == reverse("login") and parse_qs(location.query) == {"next": [path]},
                                "Unauthorized redirect did not preserve only the requested cancellation route")
                    else:
                        require(not response["location"], "Forbidden response exposed a redirect")
                    require(not trace["sql"] and not detail_link.search(response["body"])
                            and not any(private in response["body"] or private in (response["location"] or "")
                                        for private in (device.name, self.users[student].username, REASON)),
                            "Authorization exposed or read private business data")
                    after = self.snapshot(device)
                    require(self.unchanged(before, after), "Unauthorized request changed business data")
                    runs.append(dict(scenario=name, actor_id=self.users[actor].pk if actor else None, result=result, after=after))
        self.report(case="permissions", passed=len(runs), total=len(runs), before=before, runs=runs)

        invalid = []
        pair = self.pair(admin)
        for path in paths:
            for kind, result in (
                ("csrf-missing", self.prepare(pair, path, {"reason": REASON}, use_csrf=False)[0]()),
                ("csrf-invalid", self.raw(pair, path, "POST", body=b"reason=&csrfmiddlewaretoken=invalid")),
                ("duplicate", self.raw(pair, path, "POST", body=b"reason=&reason=again")),
                ("bad-encoding", self.raw(pair, path, "POST", body=b"reason=%C3%28")),
                ("wrong-media-type", self.raw(pair, path, "POST", body=b"{}", content_type="application/json")),
                ("bad-query", self.raw(pair, path + "?next=https://example.com", "POST", body=b"reason=")),
                ("bad-method", self.raw(pair, path, "PUT", body=b"reason=")),
            ):
                self.expect(result, 403 if kind.startswith("csrf") else 405 if kind == "bad-method" else 400)
                after = self.snapshot(device)
                require(not result["server"]["sql"] and self.unchanged(before, after)
                        and device.name not in result["response"]["body"], "Invalid request touched business data")
                invalid.append(dict(scenario=kind, result=result, after=after))
        self.report(case="invalid-requests", passed=len(invalid), total=len(invalid), before=before, runs=invalid)

    def revoke_admin(self, student, *, deactivate):
        admin = self.actor(Role.ADMIN)
        device = self.fixture()
        row = self.put(student, device, self.now() - HOUR)
        execute, trace = self.cancel(admin, row)
        before = self.snapshot(device)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                if deactivate:
                    query(self.observer, "UPDATE accounts_user SET is_active = %s WHERE id = %s", [False, self.users[admin].pk])
                else:
                    query(self.observer, "UPDATE accounts_user SET role = %s WHERE id = %s", [Role.STUDENT, self.users[admin].pk])
            result = task.result()
        self.expect(result, 403)
        lock, = (i for i, sql in enumerate(trace["sql"]) if "FOR UPDATE" in sql)
        post_lock = trace["sql"][lock + 1:]
        after = self.snapshot(device)
        require(len(post_lock) == 1 and is_account_recheck(post_lock[0]) and not trace["decisions"]
                and trace["history_attempts"] == trace["commit_attempts"] == 0 and self.unchanged(before, after)
                and device.name not in result["response"]["body"], "Revoked authority could still access or mutate the target")
        self.report(case="revoke-active" if deactivate else "revoke-role", result=result, blockers=blockers, before=before, after=after)

    def faults(self, admin, student):
        for branch in ("cancel", "expire"):
            for fault in ("status", "F1-history", "F2", "F3", "F4"):
                device = self.fixture()
                start = self.future()[0] if branch == "cancel" else self.now() - 2 * HOUR
                row = self.put(student, device, start)
                before = self.snapshot(device)
                killed = []

                def terminate(pid):
                    killer = connections["default"].copy(alias="story28-killer")
                    try:
                        killer_pid = target(killer)[-1]
                        require(killer_pid != pid and query(killer, "SELECT pg_terminate_backend(%s, 3000)", [pid]) == (True,),
                                "Independent backend did not cause the targeted disconnection")
                        killed.append(dict(request=pid, killer=killer_pid))
                    finally:
                        killer.close()

                control = {"fault": fault}
                if fault == "F3":
                    control["terminate"] = terminate
                result = self.cancel(admin, row, control=control)[0]()
                unknown = fault in {"F3", "F4"}
                self.expect(result, 503, "取消结果待核查，请勿重复提交" if unknown else "数据库事务已回滚")
                body, trace = result["response"]["body"], result["server"]
                require(SUCCESS not in body and EXPIRED not in body and "<form" not in body
                        and self.cancel_path(row) not in body and "返回预约管理" in body,
                        "Failure result disclosed success or an automatic replay")
                decision = self.assert_order(result, admin, row, writes=1 if fault == "status" else 2,
                                             commits=int(fault in {"F2", "F3", "F4"}))
                require(trace["history_attempts"] == int(fault != "status"), "Unexpected audit retries")
                expected_state = {"status": "23514", "F1-history": "23514", "F2": "23505"}.get(fault)
                actual_state = trace["sqlstate"]
                require(actual_state == expected_state if expected_state else
                        (actual_state is None or actual_state.startswith("08") or actual_state == "57P01"),
                        "Unexpected database SQLSTATE for the tested failure")
                after = self.snapshot(device)
                if fault == "F4":
                    if branch == "cancel":
                        self.storage(before, after, row, Status.CANCELLED,
                                     [("cancel", Status.PENDING, Status.CANCELLED, admin, REASON, decision)])
                    else:
                        self.storage(before, after, row, Status.EXPIRED,
                                     [("expire", Status.PENDING, Status.EXPIRED, None, "开始时间已到仍待审核", decision)])
                else:
                    require(self.unchanged(before, after), "Failed transaction partially persisted")
                require(fault != "F3" or len(killed) == 1 and killed[0]["request"] == trace["pid"], "Missing real disconnection evidence")
                self.report(case=f"{branch}-{fault}", result=result, before=before, after=after,
                            killed_pids=killed, simulated_confirmation_loss=fault == "F4", automatic_retry=False)


class Command(BaseCommand):
    help = "Record administrator cancellation evidence on the isolated test database."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)
        parser.add_argument("--remediation-only", action="store_true", help="Run only the two D-062 owner cancellation races.")

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Run in the configured test-only environment with exclusive use of the isolated test slot")
        app = connections["default"]
        observer = app.copy(alias="story28-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        try:
            identity = target(observer)
            app_pid = target(app)[-1]
            require(app_pid != identity[-1] and app.get_autocommit() and not app.in_atomic_block,
                    "Fixture writer and observer must use distinct guarded sessions")
            require(query(observer, """SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND backend_type = 'client backend' AND pid NOT IN (%s, %s)
                """, [app_pid, identity[-1]]) == (0,), "Unexpected connection to isolated test database")
            runner.setup_databases(aliases={"default": True})
            before = database_snapshot(observer, runner)
            require(all(item["count"] == 0 for item in before["rows"].values()), "Unexpected existing test fixtures")
            cases, completed, prefix = {}, [], f"S28-{uuid4().hex[:12]}-"
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                def report(**record):
                    evidence.write(json.dumps(record, sort_keys=True, default=str, ensure_ascii=False) + "\n")
                    evidence.flush()
                    if "case" in record:
                        completed.append(record["case"])

                report(database=identity, writer_pid=app_pid, fixture_prefix=prefix, before=before)
                with make_server(HOST, 0, CancellationWSGI(cases), server_class=ThreadedServer,
                                 handler_class=QuietHandler) as server:
                    probe = AdminCancellationExperiment(observer, server, cases, prefix, report)
                    probe.observer_pid = identity[-1]
                    thread = Thread(target=server.serve_forever, name="story28-loopback")
                    thread.start()
                    try:
                        admin, student = map(probe.actor, (Role.ADMIN, Role.STUDENT))
                        with patch.object(services, "_decision_time", observe_decision):
                            if not options["remediation_only"]:
                                other, peer = map(probe.actor, (Role.ADMIN, Role.TEACHER))
                                probe.permissions(admin, student, peer)
                                for deactivate in (False, True):
                                    probe.revoke_admin(student, deactivate=deactivate)
                                probe.interleave(admin, other, student, peer, "cancel", cancel_first=True)
                                for cancel_first in (False, True):
                                    for operation in ("approve", "reject", "submit", "admin-detail", "own-detail"):
                                        probe.interleave(admin, other, student, peer, operation, cancel_first=cancel_first)
                                    for operation in ("admin-detail", "own-detail"):
                                        probe.interleave(admin, other, student, peer, operation, cancel_first=cancel_first, due=True)
                                for state in (Status.PENDING, Status.APPROVED):
                                    for commit_after in (False, True):
                                        probe.boundary(admin, student, state, commit_after=commit_after)
                                probe.approval_ends_while_cancellation_waits(admin, other, student)
                                probe.faults(admin, student)
                            for admin_first in (True, False):
                                probe.owner_cancel_race(admin, student, admin_first=admin_first)
                    finally:
                        server.shutdown()
                        thread.join()
                        with transaction.atomic():
                            devices = Equipment.objects.filter(number__startswith=prefix)
                            rows = Reservation.objects.filter(equipment__in=devices)
                            Session.objects.filter(session_key__in=probe.session_keys).delete()
                            OperationHistory.objects.filter(reservation__in=rows).delete()
                            rows.delete()
                            devices.delete()
                            User.objects.filter(username__startswith=prefix).delete()
                        after = database_snapshot(observer, runner)
                        report(cleanup=before == after, after=after, completed=completed)
                        require(before == after, "Isolated test database baseline changed")
            note = "" if options["remediation_only"] else " (F4 simulates confirmation loss after real COMMIT)"
            self.stdout.write(f"STORY28_PROBE_OK cases={len(completed)}{note}")
        finally:
            observer.close()
            app.close()
