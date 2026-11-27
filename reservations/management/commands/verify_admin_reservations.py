import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4
from wsgiref.simple_server import make_server

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus
from lab_booking.database_config import HOST
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status
from reservations.views import READ_FAILED, READ_UNKNOWN, RESULT_NOT_FOUND, _beijing_text

from .verify_own_reservations import CLOCK, EQUIPMENT, FAULTS, HISTORY, RESERVATIONS, OwnExperiment, OwnWSGI
from .verify_reservation_transactions import (
    PROBE, QuietHandler, ThreadedServer, baseline, is_account_recheck, observe_decision,
    query, require, target, url, wait_for, window,
)


LIST = "admin-reservation-list"
DETAIL = "admin-reservation-detail"
CASES = ("navigation-history", "filtered-affected", "ordered-locks", "no-pending-clock", "edge-input",
         "permissions", "revoked-while-waiting", "frozen-concurrent-additions", "crossed-start",
         "submit-first", "query-first", "commit-after-end", "late-projection-failed", *FAULTS)


def database_snapshot(observer, runner):
    with observer.cursor() as cursor:
        cursor.execute("""SELECT nspname, nspowner, nspacl::text
                          FROM pg_namespace WHERE nspname = 'public'""")
        namespaces = cursor.fetchall()
        cursor.execute("""SELECT c.relname, c.relowner, c.relacl::text
                          FROM pg_class AS c JOIN pg_namespace AS n ON n.oid = c.relnamespace
                          WHERE n.nspname = 'public' ORDER BY c.relname""")
        tables = cursor.fetchall()
        cursor.execute("""SELECT c.relname, a.attname, a.attacl::text
                          FROM pg_attribute AS a JOIN pg_class AS c ON c.oid = a.attrelid
                          JOIN pg_namespace AS n ON n.oid = c.relnamespace
                          WHERE n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped
                          ORDER BY c.relname, a.attnum""")
        columns = cursor.fetchall()
    return {"rows": baseline(observer), "schema": runner.database_state(observer), "role": target(observer)[:-1],
            "acl": {"namespaces": namespaces, "relations": tables, "columns": columns}}


class AdminExperiment(OwnExperiment):
    def fixture(self, status=EquipmentStatus.AVAILABLE):
        self.counter += 1
        return Equipment.objects.create(number=f"{self.prefix}{self.counter}", name=f"Story25 fixture {self.counter}",
                                        category="probe", location="loopback", status=status)

    def listing(self, key, *, pair=None, path=None, control=None):
        return self.prepare(pair or self.pair(key), path or reverse(LIST), control=control,
                            role=self.users[key].role if key else None)

    @staticmethod
    def detail_path(pk):
        return url(DETAIL, pk)

    @staticmethod
    def filter_path(device):
        return reverse(LIST) + "?" + urlencode({"equipment": device.number})

    def links(self, result):
        return list(map(int, re.findall(r'href="/reservations/manage/([0-9]+)/(?:\?[^"]*)?"',
                                       result["response"]["body"])))

    def assert_scope(self, result, key, rows, devices, *, selected=None, detail=None, clock=True, commits=1):
        trace = result["server"]
        require(trace["pid"] != self.observer_pid and trace["principal"]["user_id"] == self.users[key].pk,
                "Request principal/backend does not match its independently verified fixture")
        statements = trace["statements"]
        confirmations = [i for i, stmt in enumerate(statements) if is_account_recheck(stmt["sql"])]
        reads = [(i, stmt) for i, stmt in enumerate(statements)
                 if stmt["sql"].startswith("SELECT ") and f"FROM {RESERVATIONS}" in stmt["sql"]]
        locks = [(i, stmt) for i, stmt in enumerate(statements) if "FOR UPDATE" in stmt["sql"]]
        clocks = [i for i, stmt in enumerate(statements) if stmt["sql"] == CLOCK]
        first, candidate = reads[0]
        first_check, after_lock = confirmations
        restriction = [obj.pk for obj in (selected, detail) if obj is not None]
        require(first_check == 0 and first_check < first < after_lock and
                candidate["bind"] == restriction and "JOIN" not in candidate["sql"] and
                "start_at" not in candidate["sql"] and "end_at" not in candidate["sql"],
                "Role or fixed candidate scope was not established before locks/time")
        if selected is not None:
            lookups = [stmt for stmt in statements[first_check + 1:first]
                       if f'FROM {EQUIPMENT}' in stmt["sql"]]
            require(len(lookups) == 1 and lookups[0]["bind"] == [selected.number] and
                    f'{EQUIPMENT}."number" = %s' in lookups[0]["sql"],
                    "Equipment number was not resolved by exact authorized lookup")
        require([stmt["bind"] for _, stmt in locks] == [[device.pk] for device in devices] and
                all(first < i < after_lock and f'{EQUIPMENT}."id" = %s' in stmt["sql"] for i, stmt in locks),
                "Device locks did not match the expected primary-key order")
        require(len(clocks) == len(trace["decisions"]) == int(clock) and len(trace["commits"]) == commits,
                "Unexpected number of sampled clocks or commit attempts")
        writes = [(i, stmt) for i, stmt in enumerate(statements)
                  if stmt["sql"].startswith((f"UPDATE {RESERVATIONS}", f"INSERT INTO {HISTORY}"))]
        if writes:
            require(len(clocks) == 1 and clocks[0] < writes[0][0] and
                    all(stmt["sql"].startswith(f"UPDATE {RESERVATIONS}" if i % 2 == 0 else f"INSERT INTO {HISTORY}")
                        for i, (_, stmt) in enumerate(writes)) and len(writes) % 2 == 0 and
                    (not commits or writes[-1][1]["at_ns"] < trace["commits"][0]),
                    "Status and history writes must pair after one clock and before COMMIT")
        if rows:
            reread_i, fixed = reads[1]
            require(after_lock < reread_i and (not clocks or reread_i < clocks[0]) and
                    f'{RESERVATIONS}."id" IN (' in fixed["sql"] and
                    fixed["bind"][:len(restriction)] == restriction and
                    set(fixed["bind"][len(restriction):]) == {row.pk for row in rows},
                    "Fixed reread did not retain original restrictions and exact IDs")
        else:
            require(len(reads) == 1, "Empty candidate set was not kept empty")

    def navigation_history(self, admin, student, teacher):
        a, b = self.fixture(EquipmentStatus.DISABLED), self.fixture(EquipmentStatus.MAINTENANCE)
        old = self.now() - timedelta(hours=4)
        future, _ = self.future()
        pending = self.put(student, a, future)
        approved = self.put(teacher, a, old, Status.APPROVED)
        rejected = self.put(student, b, old, Status.REJECTED)
        self_cancelled = self.put(student, a, old, Status.CANCELLED)
        admin_cancelled = self.put(teacher, b, old, Status.CANCELLED)
        expired = self.put(teacher, b, old, Status.EXPIRED)
        a_row = self.history(approved, "approve", "", actor=self.users[admin])
        self.history(rejected, "reject", "拒绝 <保留>", actor=self.users[admin])
        self.history(self_cancelled, "cancel", "", actor_type=Role.STUDENT, actor=self.users[student])
        self.history(admin_cancelled, "cancel", "管理员取消 <设备影响>", actor=self.users[admin])
        self.history(expired, "expire", EXPIRY_REASON, actor_type="system")
        decision = a_row.recorded_at - timedelta(seconds=3)
        OperationHistory.objects.filter(pk=a_row.pk).update(decision_at=decision)
        OperationHistory.objects.create(object_type=HistoryObject.EQUIPMENT, equipment=a, action="cancel",
                                        before_status="available", after_status="disabled", actor_type="admin",
                                        actor=self.users[admin], reason="do-not-show-equipment-history",
                                        recorded_at=old, decision_at=old)
        before = self.snapshots((a, b))
        rows = (pending, approved, rejected, self_cancelled, admin_cancelled, expired)
        identity = self.list_for(admin, path=reverse("identity"))
        self.expect(identity, 200, f'href="{reverse(LIST)}">预约管理')
        listing = self.list_for(admin)
        self.expect(listing, 200, "全部预约（含历史记录）")
        require(set(self.links(listing)) == {row.pk for row in rows}, "Historical listing omitted a fixture")
        self.assert_scope(listing, admin, rows, (a,))
        cells = re.findall(r"<tr>(.*?)</tr>", listing["response"]["body"].split("<tbody>", 1)[1], re.S)
        reasons = {rejected.pk: "拒绝 <保留>", admin_cancelled.pk: "管理员取消 <设备影响>", expired.pk: EXPIRY_REASON}
        for row, actual in zip(sorted(rows, key=lambda r: (r.start_at, r.pk), reverse=True), cells, strict=True):
            expected = [f'<a href="{self.detail_path(row.pk)}">{row.pk}</a>', row.applicant.username,
                        f"{row.equipment.number} · {row.equipment.name}",
                        row.start_at.astimezone(services.BEIJING).date().isoformat(),
                        f"{_beijing_text(row.start_at)} 至 {_beijing_text(row.end_at)}", Status(row.status).label,
                        EquipmentStatus(row.equipment.status).label, escape(reasons.get(row.pk, ""))]
            require(re.findall(r"<td>(.*?)</td>", actual, re.S) == expected, "Administrator list has wrong row fields")
        details = []
        details_cases = (
            (approved, "批准", f"业务管理员 · {self.users[admin].username}", "", a_row.recorded_at, decision, "待审核", "已批准"),
            (rejected, "拒绝", f"业务管理员 · {self.users[admin].username}", reasons[rejected.pk], None, None, "待审核", "已拒绝"),
            (self_cancelled, "取消", f"学生 · {self.users[student].username}", "", None, None, "待审核", "已取消"),
            (admin_cancelled, "取消", f"业务管理员 · {self.users[admin].username}", reasons[admin_cancelled.pk], None, None, "待审核", "已取消"),
            (expired, "失效", "系统", EXPIRY_REASON, None, None, "待审核", "已失效"),
        )
        for row, action, actor, reason, recorded, decided, old_status, new_status in details_cases:
            entry = next(item for snapshot in before for item in snapshot["history"] if item["reservation_id"] == row.pk)
            detail = self.list_for(admin, path=self.detail_path(row.pk) + "?" + urlencode({"equipment": a.number}))
            self.expect(detail, 200, f'href="{self.filter_path(a)}">返回预约管理')
            self.assert_scope(detail, admin, (row,), (), detail=row, clock=False)
            require(self.no_writes(detail), "Read-only history wrote business data")
            actor_cell = (f"{actor}（账号 ID {entry['actor_id']}）" if entry["actor_id"] is not None else actor)
            detail_cells = re.findall(r"<td>(.*?)</td>", detail["response"]["body"], re.S)
            require(detail_cells == [str(row.pk), actor_cell, action, old_status, new_status,
                                     _beijing_text(recorded or entry["recorded_at"]),
                                     _beijing_text(decided or entry["decision_at"]), escape(reason)],
                    "Detail did not display the one stored history row and exact fields")
            details.append(detail)
        after = self.snapshots((a, b))
        require(self.unchanged_all(before, after), "List or history changed a non-due fixture")
        self.report(case="navigation-history", identity=identity, listing=listing, details=details, before=before, after=after)

    def filtered(self, admin, student):
        a, b = self.fixture(EquipmentStatus.DISABLED), self.fixture()
        now = self.now()
        future, _ = self.future()
        due, other = [self.put(student, device, now - timedelta(hours=2)) for device in (a, b)]
        pending = self.put(student, a, future)
        current = self.put(student, a, now - timedelta(minutes=10), Status.APPROVED)
        ended = self.put(student, a, now - timedelta(hours=2), Status.APPROVED)
        before = self.snapshots((a, b))
        result = self.list_for(admin, path=self.filter_path(a))
        self.expect(result, 200, "受影响预约")
        self.assert_scope(result, admin, (due, pending, current, ended), (a,), selected=a)
        require(set(self.links(result)) == {pending.pk, current.pk}, "Wrong filtered result set")
        after = self.snapshots((a, b))
        self.expiry(after[0], due.pk, result["server"]["decisions"][0])
        require(self.unchanged(before[1], after[1]), "Filtering changed another device")
        self.report(case="filtered-affected", result=result, other_id=other.pk, before=before, after=after)
        # Finalize the intentionally retained unrelated overdue fixture before later all-list probes.
        self.expect(self.details(admin, other), 200, EXPIRY_REASON)

    def order(self, admin, student):
        a, b, c = [self.fixture() for _ in range(3)]
        old = self.now() - timedelta(hours=2)
        due = [self.put(student, device, old) for device in (b, a, b)]
        terminal = self.put(student, c, old, Status.CANCELLED)
        existing = list(Reservation.objects.exclude(pk__in=[row.pk for row in (*due, terminal)]))
        old_locks = {row.equipment_id: row.equipment for row in existing if row.status == Status.PENDING}
        devices = {**old_locks, a.pk: a, b.pk: b}
        before = self.snapshots((a, b, c))
        result = self.list_for(admin)
        self.expect(result, 200)
        self.assert_scope(result, admin, (*existing, *due, terminal), tuple(devices[k] for k in sorted(devices)))
        after = self.snapshots((a, b, c))
        for row in due:
            snap = after[0 if row.equipment_id == a.pk else 1]
            scoped = {**snap, "history": [entry for entry in snap["history"] if entry["reservation_id"] == row.pk]}
            self.expiry(scoped, row.pk, result["server"]["decisions"][0])
        require(self.unchanged(before[2], after[2]), "All-history query touched a terminal-only device")
        self.report(case="ordered-locks", result=result, before=before, after=after)

        alive, _ = self.future()
        approved = self.put(student, c, alive, Status.APPROVED)
        execute, _ = self.listing(admin, path=self.filter_path(c))
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(c)
                no_pending = pool.submit(execute).result(timeout=12)
        self.assert_scope(no_pending, admin, (terminal, approved), (), selected=c)
        require(self.no_writes(no_pending) and self.links(no_pending) == [approved.pk],
                "No-pending filter blocked, wrote or lost its approved result")
        self.report(case="no-pending-clock", result=no_pending)

    def m01_detail(self, admin, student):
        device = self.fixture()
        due, = self.approved_or_due(student, device)
        path = self.detail_path(due.pk)
        pair = self.pair(admin)
        before = self.snapshot(device)
        require(len(before["rows"]) == 1 and before["rows"][0]["status"] == Status.PENDING
                and not before["effective"] and not before["history"], "M01 fixture is not an overdue pending row")
        invalid = []
        for suffix in ("?equipment=", "?equipment=%20", "?equipment=a&equipment=b",
                       "?equipment=" + "x" * 33, "?equipment=%00"):
            result = self.list_for(admin, pair=pair, path=path + suffix)
            self.expect(result, 400, "设备编号参数无效。")
            after = self.snapshot(device)
            trace = result["server"]
            require(trace["principal"]["user_id"] == self.users[admin].pk and trace["pid"] != self.observer_pid
                    and not trace["statements"] and not trace["decisions"] and not trace["commits"]
                    and not trace["history_attempts"] and self.unchanged(before, after)
                    and "操作历史" not in result["response"]["body"], "M01 invalid detail touched or exposed business data")
            invalid.append({"result": result, "after": after})

        back_query = "?" + urlencode({"equipment": device.number})
        legal = self.list_for(admin, pair=pair, path=path + back_query)
        self.expect(legal, 200, f'href="{self.filter_path(device)}">返回预约管理')
        self.expect(legal, 200, EXPIRY_REASON)
        self.assert_scope(legal, admin, (due,), (device,), detail=due)
        after_legal = self.snapshot(device)
        self.expiry(after_legal, due.pk, legal["server"]["decisions"][0])
        require(not after_legal["effective"] and len(after_legal["history"]) == 1
                and legal["server"]["history_attempts"] == 1, "M01 legal control must persist just one expiry")
        repeated = self.list_for(admin, pair=pair, path=path)
        self.expect(repeated, 200, f'href="{reverse(LIST)}">返回预约管理')
        self.assert_scope(repeated, admin, (due,), (), detail=due, clock=False)
        after_repeat = self.snapshot(device)
        require(self.no_writes(repeated) and self.unchanged(after_legal, after_repeat), "M01 repeat duplicated expiry")
        return dict(reservation_id=due.pk, before=before, invalid=invalid, legal=legal, after_legal=after_legal,
                    repeated=repeated, after_repeat=after_repeat)

    def edge_inputs(self, admin, student):
        empty = self.fixture()
        empty_filter = self.list_for(admin, path=self.filter_path(empty))
        self.expect(empty_filter, 200, "未找到符合筛选条件的预约。")
        self.assert_scope(empty_filter, admin, (), (), selected=empty)
        missing = self.list_for(admin, path=reverse(LIST) + "?equipment=not-an-existing-number")
        self.expect(missing, 200, "未找到符合筛选条件的预约。")
        absent = self.list_for(admin, path=self.detail_path(2 ** 62))
        self.expect(absent, 404, RESULT_NOT_FOUND)
        bad = [self.list_for(admin, path=reverse(LIST) + suffix) for suffix in
               ("?equipment=", "?equipment=%20", "?equipment=a&equipment=b", "?role=admin", "?equipment=%00",
                "?equipment=" + "x" * 33)]
        for result in bad:
            self.expect(result, 400)
            require(not result["server"]["statements"], "Bad input reached a table")
        require(all(not self.links(result) and self.no_writes(result) for result in (empty_filter, missing, absent, *bad))
                and not missing["server"]["decisions"] and not absent["server"]["decisions"],
                "Empty or missing case performed unrelated operations")
        self.report(case="edge-input", empty_filter=empty_filter, missing=missing, absent=absent, invalid=bad,
                    m01=self.m01_detail(admin, student))

    def verify_permissions(self, admin, student, teacher):
        peer, inactive = self.actor(Role.STUDENT), self.actor(Role.ADMIN)
        User.objects.filter(pk=self.users[peer].pk).update(is_staff=True, is_superuser=True)
        inactive_pair = self.pair(inactive)
        User.objects.filter(pk=self.users[inactive].pk).update(is_active=False)
        device = self.fixture()
        due, = self.approved_or_due(student, device)
        terminal = self.put(teacher, device, self.now(), Status.REJECTED)
        self.history(terminal, "reject", "restricted-approval-reason", actor=self.users[admin])
        before = self.snapshot(device)
        denied = []
        for key, status in ((None, 302), (student, 403), (peer, 403), (teacher, 403), (inactive, 302)):
            pair = inactive_pair if key == inactive else self.pair(key)
            for path in (reverse(LIST), self.filter_path(device), self.detail_path(due.pk),
                         self.detail_path(terminal.pk) + "?role=admin"):
                case_before = self.snapshot(device)
                result = self.list_for(key, pair=pair, path=path)
                self.expect(result, status)
                case_after = self.snapshot(device)
                response = result["response"]
                require(not result["server"]["statements"] and not result["server"]["decisions"] and
                        self.unchanged(case_before, case_after) and
                        all(text not in response["body"] for text in
                            (device.name, device.number, self.users[student].username,
                             self.users[teacher].username, "restricted-approval-reason")),
                        "Unauthorized request touched business data, effective occupancy or exposed data")
                if status == 302:
                    redirect = urlsplit(response["location"])
                    require(redirect.path == reverse("login") and parse_qs(redirect.query) == {"next": [path]},
                            "Login redirect did not preserve the attempted path")
                denied.append({**result, "requested_fixture_role": key, "before": case_before, "after": case_after})
        after = self.snapshot(device)
        require(self.unchanged(before, after), "Denied requests affected business rows or occupancy")
        positive = self.details(admin, terminal)
        self.expect(positive, 200, "restricted-approval-reason")
        require(self.unchanged(after, self.snapshot(device)), "Terminal positive control changed data")
        self.report(case="permissions", denied=denied, denied_count=len(denied), before=before, after=after, positive=positive)
        self.expect(self.details(admin, due), 200, EXPIRY_REASON)

    def revoke_admin(self, student):
        admin = self.actor(Role.ADMIN)
        device = self.fixture()
        due, = self.approved_or_due(student, device)
        before = self.snapshot(device)
        execute, trace = self.listing(admin, path=self.detail_path(due.pk))
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                User.objects.filter(pk=self.users[admin].pk).update(role=Role.TEACHER)
            result = task.result()
        self.expect(result, 403)
        after = self.snapshot(device)
        statements = trace["statements"]
        require(len(statements) == 4 and is_account_recheck(statements[0]["sql"]) and
                "FOR UPDATE" in statements[2]["sql"] and is_account_recheck(statements[3]["sql"]) and
                not trace["decisions"] and not trace["commits"] and self.no_writes(result) and
                self.unchanged(before, after), "Post-lock revocation did not stop reading/writes")
        self.report(case="revoked-while-waiting", result=result, blockers=blockers, before=before, after=after)

    def freeze_admin(self, admin, student):
        device, other = self.fixture(), self.fixture()
        due, = self.approved_or_due(student, device)
        before = self.snapshots((device, other))
        execute, trace = self.listing(admin, path=self.filter_path(device))
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                start, _ = self.future()
                new = self.put(student, device, start)
                unrelated = self.put(student, other, start)
            first = task.result()
        self.assert_scope(first, admin, (due,), (device,), selected=device)
        self.expect(first, 200, "未找到符合筛选条件的预约。")
        second = self.list_for(admin, path=self.filter_path(device))
        self.assert_scope(second, admin, (due, new), (device,), selected=device)
        require(not self.links(first) and self.links(second) == [new.pk], "Concurrent insert escaped frozen device scope")
        after = self.snapshots((device, other))
        require({row["id"] for row in after[1]["rows"]} == {unrelated.pk} and not after[1]["history"],
                "Target filter affected unrelated concurrent insert")
        self.expiry(after[0], due.pk, trace["decisions"][0])
        self.report(case="frozen-concurrent-additions", first=first, second=second, blockers=blockers,
                    before=before, after=after)

    def crossed_start(self, admin, student):
        device = self.fixture()
        pair = self.pair(admin)
        start = self.now() + timedelta(seconds=5)
        row = self.put(student, device, start)
        execute, trace = self.listing(admin, pair=pair, path=self.detail_path(row.pk))
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                waiting_at = self.now()
                require(waiting_at < start and not trace["decisions"], "No genuine before-start lock wait")
                wait_for(lambda: self.now() >= start, "database crossed appointment start")
            result = task.result()
        self.expect(result, 200, EXPIRY_REASON)
        self.assert_scope(result, admin, (row,), (device,), detail=row)
        after = self.snapshot(device)
        self.expiry(after, row.pk, trace["decisions"][0])
        self.report(case="crossed-start", result=result, blockers=blockers, after=after, start=start, waiting_at=waiting_at)

    def interleave_admin(self, admin, student, teacher, *, query_first):
        device = self.fixture()
        due, = self.approved_or_due(student, device)
        start, end = self.future()
        submit_path = url("reservation-submit", device.pk)
        entered, release = Event(), Event()

        def before_commit():
            entered.set()
            require(release.wait(20), "Leading request did not get the release signal")

        controls = {"before_commit": before_commit}
        reader, read_trace = self.listing(admin, path=self.filter_path(device),
                                          control=controls if query_first else None)
        writer, write_trace = self.prepare(self.pair(teacher, submit_path), submit_path, window(start, end),
                                           role=Role.TEACHER, control=None if query_first else controls)
        lead, follower, lead_trace, follower_trace = (
            (reader, writer, read_trace, write_trace) if query_first else (writer, reader, write_trace, read_trace)
        )
        before = self.snapshot(device)
        with ThreadPoolExecutor(2) as pool:
            lead_task = pool.submit(lead)
            try:
                require(entered.wait(10), "Leading transaction never reached COMMIT")
                follow_task = pool.submit(follower)
                blockers = self.wait_blocker(follower_trace, lead_trace["pid"])
                during = self.snapshot(device)
                require(self.unchanged(before, during), "Observer saw uncommitted expiry or submission")
            finally:
                release.set()
            lead_result, follow_result = lead_task.result(), follow_task.result()
        listing, submitted = (lead_result, follow_result) if query_first else (follow_result, lead_result)
        self.expect(listing, 200, "未找到符合筛选条件的预约。")
        self.expect(submitted, 201)
        self.assert_scope(listing, admin, (due,), (device,), selected=device)
        after = self.snapshot(device)
        self.expiry(after, due.pk, lead_trace["decisions"][0])
        fresh, = [row["id"] for row in after["rows"] if row["id"] != due.pk]
        repeat = self.list_for(admin, path=self.filter_path(device))
        require(self.links(repeat) == [fresh] and lead_trace["history_attempts"] == 1 and
                follower_trace["history_attempts"] == 0 and lead_trace["decisions"][0] < follower_trace["decisions"][0],
                "Interleaving duplicated expiry or included an unfrozen reservation")
        self.report(case="query-first" if query_first else "submit-first", blockers=blockers,
                    before=before, during=during, after=after, listing=listing, submitted=submitted, repeat=repeat)

    def commit_after_end(self, admin, student):
        device = self.fixture()
        pair = self.pair(admin)
        end = self.now() + timedelta(seconds=5)
        row = self.put(student, device, end - timedelta(hours=1), Status.APPROVED)
        entered, release = Event(), Event()

        def cross_end():
            entered.set()
            require(release.wait(15), "Timed out holding COMMIT across approved end")

        execute, _ = self.listing(admin, pair=pair, path=self.filter_path(device), control={"before_commit": cross_end})
        with ThreadPoolExecutor(1) as pool:
            task = pool.submit(execute)
            try:
                require(entered.wait(8), "Filtered request did not reach COMMIT")
                wait_for(lambda: self.now() > end, "database crossed approved end before COMMIT")
            finally:
                release.set()
            result = task.result()
        self.assert_scope(result, admin, (row,), (), selected=device)
        require(result["server"]["decisions"][0] < end < self.now() and self.links(result) == [row.pk],
                "Commit crossing incorrectly substituted a new decision time")
        next_result = self.list_for(admin, path=self.filter_path(device))
        self.expect(next_result, 200, "未找到符合筛选条件的预约。")
        self.report(case="commit-after-end", end=end, result=result, next_result=next_result)

    def failures(self, admin, student):
        device = self.fixture()
        due, = self.approved_or_due(student, device)
        before = self.snapshot(device)

        def fail_projection(connection, pk):
            trace = PROBE.get()
            trace["projection_fault_reservation"] = pk
            query(connection, "SELECT h.no_such_column FROM public.audit_operationhistory AS h WHERE h.reservation_id = %s", [pk])

        with patch.object(services, "read_reservation_history", side_effect=fail_projection):
            result = self.details(admin, due)
        self.expect(result, 503, READ_FAILED)
        trace = result["server"]
        self.assert_scope(result, admin, (due,), (device,), detail=due, commits=0)
        after = self.snapshot(device)
        require(trace["sqlstate"] == "42703" and trace["projection_fault_reservation"] == due.pk and
                trace["history_attempts"] == 1 and self.unchanged(before, after) and
                "操作历史" not in result["response"]["body"], "Late database projection failure did not roll back")
        self.report(case="late-projection-failed", result=result, before=before, after=after)

        for fault in FAULTS:
            device = self.fixture()
            rows = self.approved_or_due(student, device, device)
            before = self.snapshot(device)
            result = self.list_for(admin, path=self.filter_path(device), control={"fault": fault})
            trace = result["server"]
            unknown = fault in ("commit-disconnected", "confirmation-lost")
            self.expect(result, 503, READ_UNKNOWN if unknown else READ_FAILED)
            self.assert_scope(result, admin, rows, (device,), selected=device, commits=int(fault != "history-second"))
            after = self.snapshot(device)
            require(trace["history_attempts"] == 2 and not self.links(result) and
                    "未找到符合筛选条件" not in result["response"]["body"] and
                    ("已回滚" in result["response"]["body"]) != unknown, "Failure was retried or reported as success")
            if fault == "confirmation-lost":
                require("commit_return_ns" in trace, "Driver confirmation loss did not follow an actual COMMIT")
                for row in rows:
                    scoped = {**after, "history": [item for item in after["history"] if item["reservation_id"] == row.pk]}
                    self.expiry(scoped, row.pk, trace["decisions"][0])
            else:
                require(self.unchanged(before, after), "Failed transaction partially persisted")
            expected = {"history-second": "23514", "commit-rejected": "23505"}.get(fault)
            state = trace["sqlstate"]
            require(state == expected if expected else (state is None or state.startswith("08") or state == "57P01"),
                    "Unexpected PostgreSQL failure classification")
            self.report(case=fault, result=result, before=before, after=after, retry=False,
                        driver_confirmation_simulated=fault == "confirmation-lost")


class Command(BaseCommand):
    help = "Verify Story 2.5 through guarded PostgreSQL and real loopback HTTP, and archive raw evidence."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)
        parser.add_argument("--baseline-only", action="store_true")
        parser.add_argument("--m01-only", action="store_true")

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Story 2.5 requires the sole guarded test connection")
        require(not (options["baseline_only"] and options["m01_only"]), "Choose only one verification mode")
        app = connections["default"]
        observer = app.copy(alias="story25-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        try:
            identity = target(observer)
            app_pid = target(app)[-1]
            require(app_pid != identity[-1] and app.get_autocommit() and not app.in_atomic_block,
                    "Fixture writer and observer must use independent guarded connections")
            require(query(observer, """SELECT count(*) FROM pg_stat_activity
                                       WHERE datname = current_database() AND backend_type = 'client backend'
                                         AND pid NOT IN (%s, %s) AND state IS DISTINCT FROM 'idle'""",
                          [app_pid, identity[-1]]) == (0,), "Another isolated database session is active")
            runner.setup_databases(aliases={"default": True})
            before = database_snapshot(observer, runner)
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                if options["baseline_only"]:
                    evidence.write(json.dumps(before, sort_keys=True, ensure_ascii=False) + "\n")
                    self.stdout.write("STORY25_BASELINE_OK")
                    return
                completed, cases = [], {}

                def report(**record):
                    evidence.write(json.dumps(record, sort_keys=True, ensure_ascii=False, default=str) + "\n")
                    evidence.flush()
                    if "case" in record:
                        completed.append(record["case"])

                prefix = f"S25-{uuid4().hex[:14]}-"
                report(database=identity, fixture_prefix=prefix, before=before)
                with make_server(HOST, 0, OwnWSGI(cases), server_class=ThreadedServer, handler_class=QuietHandler) as server:
                    probe = AdminExperiment(observer, server, cases, prefix, report)
                    probe.observer_pid = identity[-1]
                    thread = Thread(target=server.serve_forever, name="story25-loopback")
                    thread.start()
                    try:
                        admin, student = map(probe.actor, (Role.ADMIN, Role.STUDENT))
                        with patch.object(services, "_decision_time", observe_decision):
                            if options["m01_only"]:
                                report(case="m01-detail", m01=probe.m01_detail(admin, student))
                            else:
                                teacher = probe.actor(Role.TEACHER)
                                probe.navigation_history(admin, student, teacher)
                                probe.filtered(admin, student)
                                probe.order(admin, student)
                                probe.edge_inputs(admin, student)
                                probe.verify_permissions(admin, student, teacher)
                                probe.revoke_admin(student)
                                probe.freeze_admin(admin, student)
                                probe.crossed_start(admin, student)
                                probe.interleave_admin(admin, student, teacher, query_first=False)
                                probe.interleave_admin(admin, student, teacher, query_first=True)
                                probe.commit_after_end(admin, student)
                                probe.failures(admin, student)
                    finally:
                        server.shutdown()
                        thread.join()
                        with transaction.atomic():
                            devices = Equipment.objects.filter(number__startswith=prefix)
                            records = Reservation.objects.filter(equipment__in=devices)
                            Session.objects.filter(session_key__in=probe.session_keys).delete()
                            OperationHistory.objects.filter(reservation__in=records).delete()
                            OperationHistory.objects.filter(equipment__in=devices).delete()
                            records.delete()
                            devices.delete()
                            User.objects.filter(username__startswith=prefix).delete()
                        after = database_snapshot(observer, runner)
                        require(before == after, "Isolated rows, ACL or schema changed after cleanup")
                        report(cleanup=True, after=after)
                expected = ("m01-detail",) if options["m01_only"] else CASES
                require(tuple(completed) == expected, "Probe count or identity does not match its case ledger")
            self.stdout.write(f"STORY25_PROBE_OK cases={len(completed)}")
        finally:
            observer.close()
            app.close()
