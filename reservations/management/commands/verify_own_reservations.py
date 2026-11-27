import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
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
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from equipment.models import Equipment, EquipmentStatus
from lab_booking.database_config import HOST
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status
from reservations.views import READ_FAILED, READ_UNKNOWN, RESULT_NOT_FOUND

from .verify_reservation_transactions import (
    PROBE, Experiment, ProbeWSGI, QuietHandler, ThreadedServer, baseline, is_account_recheck,
    observe_decision, query, require, sqlstate, target, url, wait_for, window,
)


RESERVATIONS = '"reservations_reservation"'
EQUIPMENT = '"equipment_equipment"'
HISTORY = '"audit_operationhistory"'
REASON_SOURCE = "public.audit_operationhistory"
CLOCK = "SELECT clock_timestamp() AS decision_at"
FAULTS = ("history-second", "commit-rejected", "commit-disconnected", "confirmation-lost")
CASES = ("history-navigation", "current-equipment", "projected-reasons", "ordered-scope",
         "no-pending", "permissions", "revoked-while-waiting", "frozen-new-row", "crossed-start",
         "submit-first", "query-first", *FAULTS)


class OwnWSGI(ProbeWSGI):
    def get_response(self, request):
        app = connections["default"]
        identity = target(app)
        case = self.cases.get(request.headers.get("X-Story21-Probe"))
        if case is None:
            return WSGIHandler.get_response(self, request)
        trace, controls = case
        trace.update(identity=identity, pid=identity[-1], principal=None, statements=[], decisions=[], commits=[],
                     history_attempts=0)
        fault = controls.get("fault")
        actual_commit = app._commit

        def intercept(execute, sql, params, many, context):
            if sql.startswith(f"INSERT INTO {HISTORY}"):
                trace["history_attempts"] += 1
                if fault == "history-second" and trace["history_attempts"] == 2:
                    params = ("invalid", *params[1:])
            if (any(table in sql for table in (RESERVATIONS, EQUIPMENT, HISTORY, REASON_SOURCE))
                    or sql == CLOCK or is_account_recheck(sql) or "pg_temp.story23_fault" in sql):
                trace["statements"].append(dict(sql=sql, bind=list(params or ()), at_ns=monotonic_ns()))
            try:
                return execute(sql, params, many, context)
            except Error as error:
                trace["sqlstate"] = sqlstate(error)
                raise

        def commit():
            trace["commits"].append(monotonic_ns())
            if "before_commit" in controls:
                controls["before_commit"]()
            if fault == "commit-rejected":
                query(app, "CREATE TEMP TABLE story23_fault(n int UNIQUE DEFERRABLE INITIALLY DEFERRED) ON COMMIT DROP")
                query(app, "INSERT INTO pg_temp.story23_fault VALUES (1), (1)")
            if fault == "commit-disconnected":
                killer = app.copy(alias="story23-killer")
                try:
                    trace["killer_pid"] = target(killer)[-1]
                    require(trace["killer_pid"] != trace["pid"] and
                            query(killer, "SELECT pg_terminate_backend(%s, 3000)", [trace["pid"]]) == (True,),
                            "Independent isolated backend did not disconnect request before COMMIT")
                finally:
                    killer.close()
            try:
                actual_commit()
                trace["commit_return_ns"] = monotonic_ns()
                if fault == "confirmation-lost":
                    app.connection.close()
                    raise OperationalError("Story 2.3 simulated lost successful COMMIT confirmation")
            except Error as error:
                trace["sqlstate"] = sqlstate(error)
                raise

        token = PROBE.set(trace)
        try:
            with app.execute_wrapper(intercept), patch.object(app, "_commit", side_effect=commit):
                return WSGIHandler.get_response(self, request)
        finally:
            PROBE.reset(token)


class OwnExperiment(Experiment):
    def fixture(self, status=EquipmentStatus.AVAILABLE):
        self.counter += 1
        return Equipment.objects.create(number=f"{self.prefix}{self.counter}", name=f"Story23 fixture {self.counter}",
                                        category="probe", location="loopback", status=status)

    def actor(self, role):
        key = f"{role}-{len(self.users)}"
        self.users[key] = User.objects.create_user(username=self.prefix + key, role=role, password=self.password)
        return key

    def listing(self, key, *, pair=None, path=None, control=None):
        return self.prepare(pair or self.pair(key), path or reverse("reservation-list"),
                            control=control, role=self.users[key].role if key else None)

    def list_for(self, key, **kwargs):
        return self.listing(key, **kwargs)[0]()

    def details(self, key, row):
        return self.list_for(key, path=self.detail_path(row.pk))

    @staticmethod
    def detail_path(pk):
        return url("reservation-result", pk)

    def links(self, result):
        return list(map(int, re.findall(r'href="/reservations/([0-9]+)/result/"', result["response"]["body"])))

    def put(self, key, device, start, status=Status.PENDING, duration=timedelta(hours=1)):
        return self.make(device, start, start + duration, role=key, status=status)

    def approved_or_due(self, key, *devices, status=Status.PENDING):
        return [self.put(key, dev, self.now() - timedelta(hours=2), status) for dev in devices]

    def history(self, row, action, reason, actor_type="admin", actor=None):
        now = self.now()
        return OperationHistory.objects.create(
            object_type=HistoryObject.RESERVATION, reservation=row, action=action,
            before_status=Status.PENDING, after_status=row.status, actor_type=actor_type,
            actor=actor, reason=reason, decision_at=now, recorded_at=now,
        )

    @staticmethod
    def only_rows(result, allowed):
        body = result["response"]["body"]
        require("<tbody>" in body, "Successful list has no table")
        rows = re.findall(r"<tr>(.*?)</tr>", body.split("<tbody>", 1)[1], re.S)
        require(len(rows) == len(allowed), "List row count does not match authorized data")
        for actual, expected in zip(rows, allowed, strict=True):
            cells = re.findall(r"<td>(.*?)</td>", actual, re.S)
            require(cells == expected, "Incorrect visible cells in list row")

    def cells(self, row, current_device, *, reason=""):
        start, end = (time.astimezone(services.BEIJING) for time in (row.start_at, row.end_at))
        return [f'<a href="{self.detail_path(row.pk)}">{row.pk}</a>',
                f"{row.equipment.number} · {row.equipment.name}",
                f"{start:%Y-%m-%d}", f"{start:%Y-%m-%d %H:%M} 至 {end:%Y-%m-%d %H:%M}",
                Status(row.status).label, EquipmentStatus(current_device).label, reason]

    def scope(self, result, key, rows, lock_devices, *, expect_clock=True, expect_commit=True):
        trace = result["server"]
        statements = trace["statements"]
        require(trace["principal"]["user_id"] == self.users[key].pk and trace["pid"] != self.observer_pid,
                "HTTP request lacks its independently verified principal or backend")
        reads = [(i, stmt) for i, stmt in enumerate(statements) if stmt["sql"].startswith("SELECT ")
                 and f"FROM {RESERVATIONS}" in stmt["sql"]]
        locks = [(i, stmt) for i, stmt in enumerate(statements) if "FOR UPDATE" in stmt["sql"]]
        recheck, = [i for i, stmt in enumerate(statements) if is_account_recheck(stmt["sql"])]
        clocks = [i for i, stmt in enumerate(statements) if stmt["sql"] == CLOCK]
        require(len(clocks) == len(trace["decisions"]) == int(expect_clock) and
                len(trace["commits"]) == int(expect_commit), "Unexpected number of decision clocks or commits")
        first, candidate = reads[0]
        require(candidate["bind"] == [self.users[key].pk] and "JOIN" not in candidate["sql"] and
                f'{RESERVATIONS}."applicant_id" = %s' in candidate["sql"] and
                len(candidate["sql"].partition(" FROM ")[0].split(", ")) == 3,
                "First SQL did not freeze exactly the owner candidate tuple")
        for col in ("id", "equipment_id", "status"):
            require(f'{RESERVATIONS}."{col}"' in candidate["sql"].partition(" FROM ")[0],
                    f"Missing frozen column {col}")
        require([stmt["bind"] for _, stmt in locks] == [[dev.pk] for dev in lock_devices],
                "Device locks did not match the expected ascending pending-device scope")
        require(all(first < i < recheck and f'{EQUIPMENT}."id" = %s' in stmt["sql"] for i, stmt in locks),
                "Device lock was not the required primary-key statement")
        if rows:
            fixed_i, fixed = reads[1]
            require(recheck < fixed_i and (not clocks or fixed_i < clocks[0]) and
                    f'{RESERVATIONS}."id" IN (' in fixed["sql"] and f'{EQUIPMENT}."status"' in fixed["sql"] and
                    fixed["bind"][0] == self.users[key].pk and set(fixed["bind"][1:]) == {row.pk for row in rows},
                    "Fixed projection did not reread precisely the authorized IDs after the recheck")
        else:
            require(len(reads) == 1, "Empty candidate set unexpectedly performed a reservation reread")

    @staticmethod
    def no_writes(result):
        return not any(stmt["sql"].startswith(("UPDATE ", "INSERT ", "DELETE "))
                       for stmt in result["server"]["statements"])

    def snapshots(self, devices):
        return [self.snapshot(dev) for dev in devices]

    def unchanged_all(self, before, after):
        return all(self.unchanged(left, right) for left, right in zip(before, after, strict=True))

    def positive(self):
        student, teacher, admin = map(self.actor, (Role.STUDENT, Role.TEACHER, Role.ADMIN))
        a, b = self.fixture(), self.fixture(EquipmentStatus.DISABLED)
        submit_path = url("reservation-submit", a.pk)
        start, end = self.future()
        pair = self.pair(student, submit_path)
        listings = reverse("reservation-list")
        identities = {key: self.list_for(key, path=reverse("identity")) for key in (student, teacher, admin)}
        require(all(item["response"]["status"] == 200 and
                    (f'href="{listings}"' in item["response"]["body"]) == (key != admin)
                    for key, item in identities.items()), "Role-based identity links are incorrect")
        submitted = self.prepare(pair, submit_path, window(start, end), role=Role.STUDENT)[0]()
        pending = Reservation.objects.get(applicant=self.users[student], equipment=a)
        pending.equipment = a
        self.expect(submitted, 201, f'href="{listings}"')
        require(f'href="{self.detail_path(pending.pk)}"' in submitted["response"]["body"],
                "Existing successful application detail link was lost")
        rows = [pending] + [
            self.put(student, b if i % 2 == 0 else a, start - timedelta(days=i + 3), state)
            for i, state in enumerate((Status.APPROVED, Status.REJECTED, Status.CANCELLED, Status.EXPIRED))
        ]
        newcomer = self.put(teacher, a, start + timedelta(hours=2), Status.APPROVED)
        received, teacher_only = self.list_for(student), self.list_for(teacher)
        self.expect(received, 200)
        self.expect(teacher_only, 200)
        self.only_rows(received, [self.cells(row, row.equipment.status) for row in rows])
        self.only_rows(teacher_only, [self.cells(newcomer, a.status)])
        details = []
        for row in rows:
            detail = self.details(student, row)
            fields = self.cells(row, row.equipment.status)[1:6]
            self.expect(detail, 200)
            require(all(f"<dd>{field}</dd>" in detail["response"]["body"] for field in fields)
                    and f'<a href="{listings}">返回我的预约</a>' in detail["response"]["body"],
                    "Details did not show the same scoped fields or return link")
            details.append(detail)
        self.report(case="history-navigation", identities=identities, submitted=submitted, listing=received,
                    teacher=teacher_only, details=details, rows=self.snapshots((a, b)))

        approved = rows[1]
        before = self.snapshot(b)
        checks = []
        for state in EquipmentStatus:
            Equipment.objects.filter(pk=b.pk).update(status=state)
            listing, detail = self.list_for(student), self.details(student, approved)
            self.expect(listing, 200)
            self.expect(detail, 200, f"<dt>设备当前状态</dt><dd>{state.label}</dd>")
            require("<dt>预约状态</dt><dd>已批准</dd>" in detail["response"]["body"],
                    "Device transition changed the reservation state")
            self.only_rows(listing, [self.cells(row, state if row.equipment_id == b.pk else a.status) for row in rows])
            observed = self.snapshot(b)
            require(observed["rows"] == before["rows"] and observed["history"] == before["history"],
                    "Reading current equipment mutated unrelated business rows")
            checks.append(dict(state=state, listing=listing, detail=detail, observed=observed))
        self.report(case="current-equipment", before=before, checks=checks)

        rejected, cancelled, expired = rows[2:]
        self.history(rejected, "reject", "older-hidden")
        self.history(rejected, "reject", "<script>证据</script>", actor=self.users[admin])
        self.history(rejected, "cancel", "wrong-action")
        self.history(cancelled, "cancel", "管理员取消", actor=self.users[admin])
        self.history(expired, "expire", "hidden-expiry", actor_type="system")
        self_cancelled = self.put(student, a, start - timedelta(days=10), Status.CANCELLED)
        unmatched = self.put(student, a, start - timedelta(days=11), Status.REJECTED)
        foreign = self.put(teacher, b, start - timedelta(days=12), Status.REJECTED)
        self.history(self_cancelled, "cancel", "self-private", actor_type="student", actor=self.users[student])
        self.history(unmatched, "reject", "wrong-actor", actor_type="system")
        self.history(foreign, "reject", "foreign-private", actor=self.users[admin])
        listing = self.list_for(student)
        self.expect(listing, 200)
        expected = {rejected.pk: str(escape("<script>证据</script>")), cancelled.pk: "管理员取消"}
        self.only_rows(listing, [self.cells(row, EquipmentStatus.DISABLED if row.equipment_id == b.pk else a.status,
                                           reason=expected.get(row.pk, "")) for row in (*rows, self_cancelled, unmatched)])
        statement, = [stmt for stmt in listing["server"]["statements"] if REASON_SOURCE in stmt["sql"]]
        require(statement["bind"] == ["admin", "reject", [rejected.pk, unmatched.pk],
                                      "cancel", [cancelled.pk, self_cancelled.pk]]
                and not re.search(r"actor_id|recorded_at|object_type|decision_at|SELECT\s+\*", statement["sql"]),
                "Reason query touched unauthorized scope or columns")
        details = [self.details(student, item) for item in (rejected, cancelled, self_cancelled, unmatched, expired)]
        for item, detail in zip((rejected, cancelled, self_cancelled, unmatched, expired), details, strict=True):
            self.expect(detail, 200, expected.get(item.pk))
            require(("处理原因" in detail["response"]["body"]) == (item.pk in expected),
                    "Details showed a reason for a nonmatching action/actor")
        self.report(case="projected-reasons", listing=listing, details=details, fixture=self.snapshots((a, b)))

    def order(self):
        owner, peer = self.actor(Role.STUDENT), self.actor(Role.TEACHER)
        a, b, unrelated = [self.fixture() for _ in range(3)]
        old_b, old_a, second_a = self.approved_or_due(owner, b, a, a)
        approved, = self.approved_or_due(owner, unrelated, status=Status.APPROVED)
        foreign, = self.approved_or_due(peer, a)
        devices = (a, b, unrelated)
        before = self.snapshots(devices)
        execute, trace = self.listing(owner)
        app = connections["default"]
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(b)
                self.hold_device(unrelated)
                blocker = query(app, "SELECT pg_backend_pid()")[0]
                pending = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                require(self.unchanged_all(before, self.snapshots(devices)), "Observer saw changes before all locks")
                held_at = self.now()
            result = pending.result()
        self.expect(result, 200)
        self.scope(result, owner, (old_a, second_a, old_b, approved), (a, b))
        decision, = trace["decisions"]
        first_write = next(s["at_ns"] for s in trace["statements"] if s["sql"].startswith(f"UPDATE {RESERVATIONS}"))
        require(held_at <= decision and first_write < trace["commits"][0] < trace["commit_return_ns"],
                "Writes were not completed after locks and before returned commit")
        after = self.snapshots(devices)
        for snapshot, rows in ((after[0], (old_a, second_a)), (after[1], (old_b,))):
            for row in rows:
                # Compare the row to the original, changing only the status.
                original = next(item for snap in before for item in snap["rows"] if item["id"] == row.pk)
                current = next(item for item in snapshot["rows"] if item["id"] == row.pk)
                require(current == {**original, "status": Status.EXPIRED} and current not in snapshot["effective"],
                        "Expiry modified data besides reservation status or kept occupancy")
                self.expiry({**snapshot, "history": [item for item in snapshot["history"] if item["reservation_id"] == row.pk]},
                            row.pk, decision)
        require(next(item for item in after[0]["rows"] if item["id"] == foreign.pk)["status"] == Status.PENDING and
                self.unchanged(before[2], after[2]), "Query affected a foreign row or unrelated device")
        repeat = self.list_for(owner)
        self.expect(repeat, 200)
        self.scope(repeat, owner, (old_a, second_a, old_b, approved), (), expect_clock=False)
        require(self.no_writes(repeat) and self.unchanged_all(after, self.snapshots(devices)), "Repeated read wrote history")
        self.report(case="ordered-scope", blockers=blockers, before=before, after=after, result=result, repeat=repeat)

        execute, _ = self.listing(owner)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                for device in devices:
                    self.hold_device(device)
                no_pending = pool.submit(execute).result(timeout=10)
        self.expect(no_pending, 200)
        self.scope(no_pending, owner, (old_a, second_a, old_b, approved), (), expect_clock=False)
        require(self.no_writes(no_pending), "No-pending query wrote")
        self.report(case="no-pending", result=no_pending)

    def permissions(self):
        owner, peer, teacher, admin, inactive = map(self.actor, (Role.STUDENT, Role.STUDENT, Role.TEACHER, Role.ADMIN, Role.STUDENT))
        device = self.fixture()
        old, = self.approved_or_due(owner, device)
        fresh, = self.approved_or_due(teacher, device, status=Status.APPROVED)
        detail = self.detail_path(old.pk)
        absent = self.detail_path(2 ** 62)
        listing = reverse("reservation-list")
        inactive_pair = self.pair(inactive)
        User.objects.filter(pk=self.users[inactive].pk).update(is_active=False)
        before = self.snapshot(device)
        denied = []
        for key, status in ((None, 302), (admin, 403), (inactive, 302)):
            pair = inactive_pair if key == inactive else self.pair(key)
            for path in (listing, detail):
                outcome = self.list_for(key, pair=pair, path=path)
                self.expect(outcome, status)
                require(not outcome["server"]["statements"], "Denied role reached business tables")
                denied.append(outcome)
        for key in (peer, teacher):
            true, missing = [self.list_for(key, path=path) for path in (detail, absent)]
            for outcome in (true, missing):
                self.expect(outcome, 404, RESULT_NOT_FOUND)
                require(self.no_writes(outcome) and not outcome["server"]["decisions"], "A denied object read wrote")
            require(true["response"]["body"] == missing["response"]["body"], "Missing and foreign detail differ")
            denied.extend((true, missing))
        for path in (listing, detail):
            response = self.prepare(self.pair(owner), path, {}, role=Role.STUDENT)[0]()
            self.expect(response, 405)
            require(not response["server"]["statements"], "Non-GET reached business tables")
            denied.append(response)
        forged = listing + "?" + urlencode({"applicant_id": self.users[owner].pk, "pk": old.pk})
        teacher_result = self.list_for(teacher, path=forged)
        empty = self.list_for(peer, path=forged)
        self.expect(teacher_result, 200)
        self.expect(empty, 200, "暂无本人预约记录。")
        after = self.snapshot(device)
        require(self.links(teacher_result) == [fresh.pk] and not self.links(empty) and
                self.unchanged(before, after), "Tampered owner request widened scope or changed state")
        require(all(device.name not in result["response"]["body"] and detail not in result["response"]["body"]
                    for result in denied), "Unauthorized response leaked a record")
        self.report(case="permissions", denied=denied, denied_count=len(denied), before=before, after=after,
                    tampered_allowed=[teacher_result, empty])

    def revoke(self):
        owner = self.actor(Role.STUDENT)
        dev = self.fixture()
        self.approved_or_due(owner, dev)
        before = self.snapshot(dev)
        execute, trace = self.listing(owner)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(dev)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                User.objects.filter(pk=self.users[owner].pk).update(is_active=False)
            result = task.result()
        self.expect(result, 403)
        after = self.snapshot(dev)
        require(self.no_writes(result) and trace["principal"]["is_authenticated"] and not trace["decisions"]
                and not trace["commits"] and self.unchanged(before, after), "Revoked query continued after recheck")
        self.report(case="revoked-while-waiting", result=result, blockers=blockers, before=before, after=after)

    def freeze(self):
        owner = self.actor(Role.STUDENT)
        dev = self.fixture()
        original, = self.approved_or_due(owner, dev)
        before = self.snapshot(dev)
        execute, trace = self.listing(owner)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(dev)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                new, = self.approved_or_due(owner, dev)
            first = task.result()
        self.expect(first, 200)
        self.scope(first, owner, (original,), (dev,))
        self.expiry(self.snapshot(dev), original.pk, trace["decisions"][0])
        middle = self.snapshot(dev)
        require(self.links(first) == [original.pk] and
                next(row for row in middle["rows"] if row["id"] == new.pk)["status"] == Status.PENDING and
                not any(row["reservation_id"] == new.pk for row in middle["history"]),
                "Frozen query leaked or finalized a newly committed record")
        second = self.list_for(owner)
        self.expect(second, 200)
        after = self.snapshot(dev)
        require(set(self.links(second)) == {original.pk, new.pk}, "Next query did not include the newly committed record")
        self.expiry(after, new.pk, second["server"]["decisions"][0])
        self.report(case="frozen-new-row", blockers=blockers, before=before, middle=middle, after=after, first=first, second=second)

    def boundary(self):
        owner = self.actor(Role.TEACHER)
        dev = self.fixture()
        pair = self.pair(owner)
        start = self.now() + timedelta(seconds=8)
        row = self.put(owner, dev, start)
        execute, trace = self.listing(owner, pair=pair, path=self.detail_path(row.pk))
        before = self.snapshot(dev)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(dev)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                waiting_at = self.now()
                require(waiting_at < start and not trace["decisions"], "Detail did not block before start")
                wait_for(lambda: self.now() >= start, "database clock crossed appointment start", timeout_seconds=18)
            result = task.result()
        self.expect(result, 200, "已失效")
        decision, = trace["decisions"]
        after = self.snapshot(dev)
        require(waiting_at < start <= decision, "Detail decision clock did not follow lock wait")
        self.expiry(after, row.pk, decision)
        self.report(case="crossed-start", before=before, after=after, start=start, waiting_at=waiting_at,
                    result=result, blockers=blockers)

    def interleave(self, query_first):
        owner, other = self.actor(Role.STUDENT), self.actor(Role.TEACHER)
        dev, unrelated = self.fixture(), self.fixture()
        due, = self.approved_or_due(owner, dev)
        start, end = self.future()
        path, peer_path = url("reservation-submit", dev.pk), url("reservation-submit", unrelated.pk)
        entered, release = Event(), Event()

        def latch():
            entered.set()
            require(release.wait(25), "Timed out holding the leading transaction")

        controls = {"before_commit": latch}
        read, rtrace = self.listing(owner, control=controls if query_first else None)
        who = other if query_first else owner
        write, wtrace = self.prepare(self.pair(who, path), path, window(start, end),
                                     role=self.users[who].role, control=None if query_first else controls)
        peer, _ = self.prepare(self.pair(other, peer_path), peer_path, window(start, end), role=Role.TEACHER)
        lead, follower, lead_trace, follow_trace = ((read, write, rtrace, wtrace) if query_first else
                                                   (write, read, wtrace, rtrace))
        before = self.snapshot(dev)
        with ThreadPoolExecutor(2) as pool:
            lead_task = pool.submit(lead)
            try:
                require(entered.wait(10), "Leading HTTP transaction did not reach COMMIT")
                follower_task = pool.submit(follower)
                blockers = self.wait_blocker(follow_trace, lead_trace["pid"])
                during = self.snapshot(dev)
                require(self.unchanged(before, during), "Observer saw uncommitted writes")
                unrelated_result = peer()
                self.expect(unrelated_result, 201)
            finally:
                release.set()
            results = [lead_task.result(), follower_task.result()]
        listing, submitted = results if query_first else results[::-1]
        self.expect(listing, 200, "已失效")
        self.expect(submitted, 201)
        self.scope(listing, owner, (due,), (dev,))
        after = self.snapshot(dev)
        self.expiry(after, due.pk, lead_trace["decisions"][0])
        require(self.links(listing) == [due.pk] and len(after["effective"]) == 1
                and lead_trace["history_attempts"] == 1 and follow_trace["history_attempts"] == 0
                and lead_trace["decisions"][0] < follow_trace["decisions"][0], "Incorrect interleaving/duplicate history")
        next_list = self.list_for(owner)
        require((len(self.links(next_list)) == 1) == query_first, "Next request did not respect applicant ownership")
        self.report(case="query-first" if query_first else "submit-first", blockers=blockers, before=before, during=during,
                    after=after, listing=listing, submitted=submitted, unrelated=unrelated_result, next_list=next_list)

    def faults(self):
        for fault in FAULTS:
            owner = self.actor(Role.TEACHER)
            devices = (self.fixture(), self.fixture())
            old = self.approved_or_due(owner, *devices)
            before = self.snapshots(devices)
            result = self.list_for(owner, control={"fault": fault})
            trace = result["server"]
            unknown = fault in ("commit-disconnected", "confirmation-lost")
            self.expect(result, 503, READ_UNKNOWN if unknown else READ_FAILED)
            body = result["response"]["body"]
            require(("已回滚" in body) != unknown and not self.links(result)
                    and "<tbody>" not in body and trace["history_attempts"] == 2, "Wrong failure output or retried operation")
            self.scope(result, owner, old, devices, expect_commit=fault != "history-second")
            inserted = [stmt["bind"] for stmt in trace["statements"] if stmt["sql"].startswith(f"INSERT INTO {HISTORY}")]
            require([bind[1] for bind in inserted] == [row.pk for row in old] and
                    [bind[0] for bind in inserted] == ["reservation", "invalid" if fault == "history-second" else "reservation"],
                    "Did not record the actually executed history insert parameters")
            after = self.snapshots(devices)
            if fault == "confirmation-lost":
                require("commit_return_ns" in trace, "Simulated confirmation loss lacked actual commit")
                for snapshot, row in zip(after, old, strict=True):
                    self.expiry(snapshot, row.pk, trace["decisions"][0])
            else:
                require(self.unchanged_all(before, after), "Failed or disconnected transaction partially persisted")
            expected = {"history-second": "23514", "commit-rejected": "23505"}.get(fault)
            code = trace["sqlstate"]
            require(code == expected if expected else (code is None or code.startswith("08") or code == "57P01"),
                    "Unexpected injected database failure")
            self.report(case=fault, result=result, before=before, after=after,
                        driver_confirmation_simulated=fault == "confirmation-lost", retry=False)


class Command(BaseCommand):
    help = "Verify Story 2.3 using independent HTTP/DB sessions against the guarded PostgreSQL test database."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Story 2.3 requires the sole guarded test connection")
        app = connections["default"]
        observer = app.copy(alias="story23-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        try:
            identity = target(observer)
            require(target(app)[-1] != identity[-1] and app.get_autocommit() and not app.in_atomic_block,
                    "Fixture and observer must use independent guarded connections")
            schema = runner.setup_databases(aliases={"default": True})
            before = baseline(observer)
            cases, completed = {}, []
            prefix = f"S23-{uuid4().hex[:14]}-"
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                def report(**record):
                    evidence.write(json.dumps(record, sort_keys=True, ensure_ascii=False, default=str) + "\n")
                    evidence.flush()
                    if "case" in record:
                        completed.append(record["case"])

                report(database=identity, fixture_prefix=prefix, before=before, schema_before=schema)
                with make_server(HOST, 0, OwnWSGI(cases), server_class=ThreadedServer, handler_class=QuietHandler) as server:
                    probe = OwnExperiment(observer, server, cases, prefix, report)
                    probe.observer_pid = identity[-1]
                    thread = Thread(target=server.serve_forever, name="story23-loopback")
                    thread.start()
                    try:
                        with patch.object(services, "_decision_time", observe_decision):
                            probe.positive()
                            probe.order()
                            probe.permissions()
                            probe.revoke()
                            probe.freeze()
                            probe.boundary()
                            probe.interleave(query_first=False)
                            probe.interleave(query_first=True)
                            probe.faults()
                    finally:
                        server.shutdown()
                        thread.join()
                        with transaction.atomic():
                            devices = Equipment.objects.filter(number__startswith=prefix)
                            records = Reservation.objects.filter(equipment__in=devices)
                            Session.objects.filter(session_key__in=probe.session_keys).delete()
                            OperationHistory.objects.filter(reservation__in=records).delete()
                            records.delete()
                            devices.delete()
                            User.objects.filter(username__startswith=prefix).delete()
                        after, schema_after = baseline(observer), runner.database_state(observer)
                        require(before == after and schema == schema_after, "Isolated baseline changed after cleanup")
                        report(cleanup=True, after=after, schema_after=schema_after)
                require(tuple(completed) == CASES, "Probe denominator does not match its expected case ledger")
            self.stdout.write(f"STORY23_PROBE_OK cases={len(completed)}")
        finally:
            observer.close()
            app.close()
