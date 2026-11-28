"""Story 2.6 evidence from separate HTTP, fixture, and observer connections."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Thread
from time import monotonic_ns
from unittest.mock import patch
from uuid import uuid4
from wsgiref.simple_server import make_server

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import connections, transaction

from accounts.models import Role, User
from audit.models import OperationHistory
from equipment.models import Equipment, EquipmentStatus
from lab_booking.database_config import HOST
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status
from reservations.views import CONFLICT_MESSAGE

from .verify_admin_reservations import database_snapshot
from .verify_own_reservations import CLOCK, EQUIPMENT, HISTORY, RESERVATIONS, OwnExperiment
from .verify_reservation_transactions import (
    PROBE, ProbeWSGI, QuietHandler, ThreadedServer, is_account_recheck, observe_decision, query,
    require, target, url, wait_for, window,
)


CASES = ("permissions", "legal-and-repeat", "stale-equipment", "revoked-while-waiting",
         "lock-crosses-start", "commit-crosses-start", "interleavings", "faults")
DECISION_RACE_CASES = ("approve-wins", "reject-wins")
EXPECTED = {
    "approved": (200, "预约已批准，原预约时段和占用已保留。"),
    "terminal": (409, "预约当前状态不允许批准。"),
    "expired": (409, "预约开始时间已到，不能批准。该待审核预约已失效。"),
    "unavailable": (409, "设备当前不可用，不能批准预约。"),
}


class ApprovalWSGI(ProbeWSGI):
    def get_response(self, request):
        case = self.cases.get(request.headers.get("X-Story21-Probe"))
        if case is None:
            return super().get_response(request)
        trace, control = case
        trace["bindings"] = []
        app = connections["default"]

        def capture(execute, sql, params, many, context):
            if PROBE.get() is trace and (any(table.strip('"') in sql for table in (RESERVATIONS, EQUIPMENT, HISTORY))
                                         or sql == CLOCK or is_account_recheck(sql)):
                actual = list(params or ())
                if control.get("fault") == "F1-history" and sql.startswith(f"INSERT INTO {HISTORY}"):
                    actual[0] = "invalid"  # Shared ProbeWSGI substitutes the first binding.
                entry = dict(sql=sql, executed=actual, at_ns=monotonic_ns(), pid=app.connection.info.backend_pid)
                trace["bindings"].append(entry)
                if control.get("lock_timeout") and "FOR UPDATE" in sql:
                    query(app, "SET LOCAL lock_timeout = '200ms'")
                result = execute(sql, params, many, context)
                entry["returned_ns"] = monotonic_ns()
                return result
            return execute(sql, params, many, context)

        with app.execute_wrapper(capture):
            return super().get_response(request)


class ApprovalExperiment(OwnExperiment):
    def approval(self, actor, row, *, pair=None, values=None, control=None, use_csrf=True):
        return self.prepare(pair or self.pair(actor), url("admin-reservation-approve", row.pk), values or {},
                            control={"capture_principal": True, **(control or {})}, use_csrf=use_csrf,
                            role=self.users[actor].role if actor else None)

    def result(self, request, expected):
        self.expect(request, *EXPECTED[expected])
        body = request["response"]["body"]
        role = "status" if expected == "approved" else "alert"
        require("<form" not in body and f'role="{role}"' in body, "Incorrect result status role or implicit retry")

    @staticmethod
    def lock_clock(trace, equipment_id):
        entries = trace["bindings"]
        lock, = (entry for entry in entries if "FOR UPDATE" in entry["sql"])
        clock, = (entry for entry in entries if entry["sql"] == CLOCK)
        returned = lock["returned_ns"]
        require(lock["pid"] == clock["pid"] == trace["pid"] and lock["executed"] == [equipment_id]
                and lock["at_ns"] <= returned < clock["at_ns"] <= clock["returned_ns"]
                and len(trace["decisions"]) == 1
                and any(entry.get("returned_ns", 0) > returned and entry["at_ns"] < clock["at_ns"]
                        and ".\"status\"" in entry["sql"] and entry["sql"].startswith("SELECT")
                        for entry in entries),
                "Expected one same-backend clock after a returned device lock and state reread")
        return returned

    def order(self, result, admin, row, *, writes=(), commits=1):
        trace = result["server"]
        bindings = trace["bindings"]

        def indexes(predicate):
            return [i for i, entry in enumerate(bindings) if predicate(entry["sql"])]

        account = indexes(is_account_recheck)
        pre = indexes(lambda sql: sql.startswith("SELECT") and f"FROM {RESERVATIONS}" in sql
                      and sql.split(" FROM ", 1)[0].startswith(f'SELECT {RESERVATIONS}."equipment_id"'))
        lock = indexes(lambda sql: "FOR UPDATE" in sql)
        row_read = indexes(lambda sql: sql.startswith(f'SELECT {RESERVATIONS}."status"')
                           and f'{RESERVATIONS}."start_at"' in sql.split(" FROM ", 1)[0])
        equipment = indexes(lambda sql: sql.startswith(f'SELECT {EQUIPMENT}."status"'))
        clock = indexes(lambda sql: sql == CLOCK)
        dml = indexes(lambda sql: sql.startswith(("UPDATE", "INSERT", "DELETE")))
        require(len(account) == 2 and len(pre) == len(lock) == len(row_read) == len(equipment) == len(clock)
                == len(trace["decisions"]) == 1 and trace["commit_attempts"] == commits,
                "Unexpected authorization, lock, reread, decision or COMMIT count")
        require(account[0] < pre[0] < lock[0] < account[1] < row_read[0] < equipment[0] < clock[0]
                and len(dml) == len(writes) and all(clock[0] < index for index in dml)
                and all(bindings[index]["sql"].startswith(prefix) for index, prefix in zip(dml, writes, strict=True)),
                "Approval SQL order changed, or unexpected writes were attempted")
        require(bindings[account[0]]["executed"] == bindings[account[1]]["executed"] == [self.users[admin].pk]
                and bindings[pre[0]]["executed"] == [row.pk]
                and bindings[lock[0]]["executed"] == bindings[equipment[0]]["executed"] == [row.equipment_id]
                and bindings[row_read[0]]["executed"] == [row.pk, row.equipment_id]
                and not any("FROM public.audit_operationhistory" in entry["sql"] for entry in bindings),
                "Wrong account or target scope, or result triggered a second detail query")
        self.lock_clock(trace, row.equipment_id)
        return trace["decisions"][0]

    def transition(self, before, after, row, decision, admin, *, expired=False):
        status = Status.EXPIRED if expired else Status.APPROVED
        require(after["rows"] == [{**item, "status": status} if item["id"] == row.pk else item
                                  for item in before["rows"]]
                and before["device"] == after["device"] and len(after["history"]) == len(before["history"]) + 1
                and after["history"][:-1] == before["history"], "Transition mutated other fields or history")
        if expired:
            self.expiry(after, row.pk, decision)
            require(not any(item["id"] == row.pk for item in after["effective"]), "Expired row still occupies the slot")
        else:
            approved_history = [item for item in after["history"] if item["reservation_id"] == row.pk
                                and item["action"] == "approve"]
            require(len(approved_history) == 1, "Expected exactly one approval history for the target reservation")
            history, = approved_history
            require((history["object_type"], history["equipment_id"], history["reservation_id"], history["action"],
                     history["actor_type"], history["actor_id"], history["before_status"], history["after_status"],
                     history["reason"], history["decision_at"]) ==
                    ("reservation", None, row.pk, "approve", "admin", self.users[admin].pk, Status.PENDING,
                     Status.APPROVED, "", decision) and decision < row.start_at
                    and decision <= history["recorded_at"] <= after["observed_at"], "Missing or incorrect approval audit")
            require([item["id"] for item in before["effective"]] == [item["id"] for item in after["effective"]],
                    "Approval did not retain exactly the existing effective occupation")

    def permissions(self, admin, student, teacher, flagged):
        device = self.fixture()
        row = self.put(student, device, self.now() - timedelta(minutes=10))
        User.objects.filter(pk=self.users[flagged].pk).update(is_staff=True, is_superuser=True)
        before = self.snapshot(device)
        results = []
        for actor, code, csrf in ((None, 302, "valid"), (student, 403, "valid"), (teacher, 403, "valid"),
                                  (flagged, 403, "valid"), (admin, 403, "missing"), (admin, 403, "invalid")):
            pair = self.pair(actor)
            if csrf == "invalid":
                pair = (pair[0], "invalid")
            request = self.approval(actor, row, pair=pair, use_csrf=csrf != "missing", values={
                "actor_id": self.users[admin].pk, "role": Role.ADMIN, "applicant_id": self.users[admin].pk,
            })[0]()
            self.expect(request, code)
            trace = request["server"]
            response = request["response"]
            output = response["body"] + (response["location"] or "")
            after = self.snapshot(device)
            results.append(dict(csrf=csrf, request=request, before=before, after=after))
            passed = (not trace["bindings"] and not trace["decisions"] and trace["commit_attempts"] == 0
                      and device.number not in output and self.users[student].username not in output
                      and f'href="{url("admin-reservation-detail", row.pk)}"' not in output
                      and self.unchanged(before, after))
            if not passed:
                self.report(permission_failure=results[-1])
            require(passed, "Unauthorized request read, disclosed or changed a fixture")
        self.report(case="permissions", unauthorized_count=len(results), denied_no_leak_no_write=len(results), results=results)

    def submitted(self, student, device, start, end):
        path = url("reservation-submit", device.pk)
        result = self.prepare(self.pair(student, path), path, window(start, end), role=self.users[student].role)[0]()
        self.expect(result, 201)
        row = Reservation.objects.get(applicant=self.users[student], equipment=device, start_at=start, end_at=end)
        require(row.status == Status.PENDING, "The normal submission route did not create a pending row")
        return row, result

    def legal(self, admin, student, teacher):
        device = self.fixture()
        start, end = self.future()
        row, submitted = self.submitted(student, device, start, end)
        peer, peer_submitted = self.submitted(student, device, end, end + timedelta(hours=1))
        detail_path = url("admin-reservation-detail", row.pk)
        path = url("admin-reservation-approve", row.pk)
        before = self.snapshot(device)
        pair = self.pair(admin, detail_path)
        detail_before = self.prepare(pair, detail_path)[0]()
        self.expect(detail_before, 200, f'action="{path}"')
        legal = self.approval(admin, row, pair=pair, values={"actor_id": self.users[teacher].pk, "status": Status.CANCELLED})[0]()
        self.result(legal, "approved")
        decision = self.order(legal, admin, row, writes=TRANSITION)
        after = self.snapshot(device)
        self.transition(before, after, row, decision, admin)
        detail = self.prepare(pair, detail_path)[0]()
        self.expect(detail, 200, "<dt>预约状态</dt><dd>已批准</dd>")
        item, = (record for record in after["history"] if record["reservation_id"] == row.pk)

        def beijing_text(value):
            local = value.astimezone(services.BEIJING)
            return local.strftime("%Y-%m-%d %H:%M") + (
                local.strftime(":%S.%f") if local.microsecond else local.strftime(":%S") if local.second else "")

        self.only_rows(detail, [[str(row.pk), f'业务管理员 · {self.users[admin].username}（账号 ID {item["actor_id"]}）',
                                "批准", "待审核", "已批准", beijing_text(item["recorded_at"]),
                                beijing_text(item["decision_at"]), item["reason"]]])
        require(any("FROM public.audit_operationhistory" in entry["sql"]
                    for entry in detail["server"]["bindings"]), "Authorization control did not observe the raw audit query")
        require([item for item in before["rows"] if item["id"] == peer.pk]
                == [item for item in after["rows"] if item["id"] == peer.pk]
                and [item for item in before["history"] if item["reservation_id"] == peer.pk]
                == [item for item in after["history"] if item["reservation_id"] == peer.pk],
                "Approval changed the same-device non-target control")
        repeat = self.approval(admin, row, pair=pair)[0]()
        self.result(repeat, "terminal")
        self.order(repeat, admin, row)
        final = self.snapshot(device)
        require(self.unchanged(after, final), "Repeated approval or detail mutated the approved record")
        self.report(case="legal-and-repeat", legal_control_count=1, before=before, detail_before=detail_before,
                    submitted=submitted, non_target_id=peer.pk, peer_submitted=peer_submitted,
                    approval=legal, after=after, detail=detail, repeat=repeat, final=final)

    def blocked_mutation(self, execute, trace, device, change):
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                writer = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, writer)
                observation = change()
            return task.result(), blockers, observation

    def stale_equipment(self, admin, student):
        results = []
        for offset, status in enumerate((EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED)):
            device = self.fixture()
            start = self.future()[0] + timedelta(hours=offset)
            row, submitted = self.submitted(student, device, start, start + timedelta(hours=1))
            detail_path = url("admin-reservation-detail", row.pk)
            pair = self.pair(admin, detail_path)
            before = self.snapshot(device)
            execute, trace = self.approval(admin, row, pair=pair)
            denied, blockers, _ = self.blocked_mutation(execute, trace, device, lambda: self.change_device(device, status))
            self.result(denied, "unavailable")
            self.order(denied, admin, row)
            after = self.snapshot(device)
            require(after["device"] == {**before["device"], "status": status}
                    and all(before[k] == after[k] for k in ("rows", "history", "effective"))
                    and [item["id"] for item in after["effective"]] == [row.pk],
                    "Approval relied on stale device state or wrote after rejection")
            detail = self.prepare(pair, detail_path)[0]()
            self.expect(detail, 200, f"<dt>设备当前状态</dt><dd>{status.label}</dd>")
            self.expect(detail, 200, "<dt>预约状态</dt><dd>待审核</dd>")
            require(f'action="{url("admin-reservation-approve", row.pk)}"' not in detail["response"]["body"],
                    "Latest unavailable-device detail still offers approval")
            with transaction.atomic():
                self.hold_device(device)
                self.change_device(device, EquipmentStatus.AVAILABLE)
            restored = self.snapshot(device)
            approved = self.approval(admin, row, pair=pair)[0]()
            self.result(approved, "approved")
            decision = self.order(approved, admin, row, writes=TRANSITION)
            final = self.snapshot(device)
            self.transition(restored, final, row, decision, admin)
            results.append(dict(submitted=submitted, before=before, denied=denied, after=after, blockers=blockers,
                                detail=detail, restored=restored, approved=approved, final=final))
        self.report(case="stale-equipment", results=results)

    @staticmethod
    def change_device(device, status):
        require(Equipment.objects.filter(pk=device.pk).update(status=status) == 1, "Fixture device not found")

    def revoked(self, admin, student):
        device = self.fixture()
        row = self.put(student, device, self.future()[0])
        before = self.snapshot(device)
        execute, trace = self.approval(admin, row)
        try:
            denied, blockers, _ = self.blocked_mutation(execute, trace, device, lambda: User.objects.filter(
                pk=self.users[admin].pk).update(role=Role.TEACHER))
        finally:
            User.objects.filter(pk=self.users[admin].pk).update(role=Role.ADMIN)
        self.expect(denied, 403, "无权批准预约。")
        body = denied["response"]["body"]
        after = self.snapshot(device)
        require(trace["principal"]["role"] == Role.ADMIN and trace["lock_acquired_ns"] > trace["lock_attempt_ns"]
                and is_account_recheck(trace["sql"][-1]) and not trace["decisions"] and trace["commit_attempts"] == 0
                and device.number not in body and self.users[student].username not in body
                and url("admin-reservation-detail", row.pk) not in body
                and not any(entry["sql"].startswith(("INSERT", "UPDATE", "DELETE"))
                            or HISTORY.strip('"') in entry["sql"] for entry in trace["bindings"])
                and self.unchanged(before, after), "Role revocation was not rechecked without disclosure or writes")
        self.report(case="revoked-while-waiting", before=before, after=after, request=denied, blockers=blockers)

    def boundary(self, admin, student, *, before_commit):
        device = self.fixture()
        pair = self.pair(admin)
        repeat_pair = self.pair(admin)
        start = self.now() + timedelta(seconds=5)
        row = self.put(student, device, start)
        peer = None if before_commit else self.put(student, device, start - timedelta(hours=2))
        before = self.snapshot(device)

        def cross():
            observed = self.now()
            require(observed < start, "Probe coordination missed the start boundary before observing a blocked backend")
            crossed = wait_for(lambda: (now := self.now()) >= start and now, "real PostgreSQL start boundary")
            return observed, crossed

        if before_commit:
            entered, release, hold = self.commit_latch()
            approve, trace = self.approval(admin, row, pair=pair, control=hold)
            with ThreadPoolExecutor(2) as pool:
                leader = pool.submit(approve)
                try:
                    require(entered.wait(10) and trace["decisions"][0] < start, "Approval did not decide before start")
                    duplicate, duplicate_trace = self.approval(admin, row, pair=repeat_pair)
                    follower = pool.submit(duplicate)
                    blockers = self.wait_blocker(duplicate_trace, trace["pid"])
                    during = self.snapshot(device)
                    require(before["rows"] == during["rows"] and before["history"] == during["history"],
                            "Uncommitted approval visible to the observer")
                    observed, crossed = cross()
                finally:
                    release.set()
                first, repeat = leader.result(), follower.result()
            expected = "approved"
        else:
            approve, trace = self.approval(admin, row, pair=pair)
            first, blockers, (observed, crossed) = self.blocked_mutation(approve, trace, device, cross)
            repeat = self.approval(admin, row, pair=repeat_pair)[0]()
            during = None
            expected = "expired"
        self.result(first, expected)
        self.result(repeat, "terminal")
        decision = self.order(first, admin, row, writes=TRANSITION)
        later = self.order(repeat, admin, row)
        require((decision < start if before_commit else decision >= crossed)
                and observed < start <= crossed <= later,
                "Independent database clocks did not cross start in the expected order")
        after = self.snapshot(device)
        self.transition(before, after, row, decision, admin, expired=not before_commit)
        if peer is not None:
            old, = (item for item in before["rows"] if item["id"] == peer.pk)
            new, = (item for item in after["rows"] if item["id"] == peer.pk)
            require(old == new and new["status"] == Status.PENDING and new["start_at"] < decision
                    and [item for item in before["history"] if item["reservation_id"] == peer.pk]
                    == [item for item in after["history"] if item["reservation_id"] == peer.pk],
                    "Approval expiry changed a non-target due row or its history")
        self.report(case="commit-crosses-start" if before_commit else "lock-crosses-start", start=start,
                    blocked_before_start=observed, crossed=crossed, before=before, during=during, after=after,
                    due_non_target_id=peer.pk if peer else None, first=first, repeat=repeat, blockers=blockers)

    def interleavings(self, admin, student, teacher):
        results = []
        for opponent in ("application", "admin-detail", "own-detail", "occupancy",
                         "due-admin-detail", "due-own-detail", "due-occupancy"):
            for approval_first in (True, False):
                device = self.fixture()
                due = opponent.startswith("due-")
                start, end = self.future()
                if due:
                    start = self.now() - timedelta(minutes=5)
                row = self.put(student, device, start)
                reader = admin if "admin-detail" in opponent else student if "own-detail" in opponent else teacher
                reader_pair, admin_pair = self.pair(reader), self.pair(admin)
                entered, release, hold = self.commit_latch()
                approve, approve_trace = self.approval(admin, row, pair=admin_pair, control=hold if approval_first else None)
                if opponent == "application":
                    path = url("reservation-submit", device.pk)
                elif "occupancy" in opponent:
                    day = start.astimezone(services.BEIJING).date().isoformat()
                    path = f'{url("equipment-occupancy", device.pk)}?date={day}'
                else:
                    path = url("admin-reservation-detail" if reader == admin else "reservation-result", row.pk)
                read, read_trace = self.prepare(reader_pair, path, window(start, end) if opponent == "application" else None,
                                                control=None if approval_first else hold, role=self.users[reader].role)
                before = self.snapshot(device)
                if approval_first:
                    first, second, blockers = self.simultaneous(approve, read, approve_trace, read_trace, entered, release)
                    approval, other = first, second
                else:
                    first, second, blockers = self.simultaneous(read, approve, read_trace, approve_trace, entered, release)
                    approval, other = second, first
                expected = ("expired" if approval_first else "terminal") if due else "approved"
                self.result(approval, expected)
                decision = self.order(approval, admin, row, writes=() if expected == "terminal" else TRANSITION)
                other_decision, = other["server"]["decisions"]
                lead, follower = first["server"], second["server"]
                self.lock_clock(other["server"], device.pk)
                require(lead["pid"] != follower["pid"] and lead["pid"] in blockers and "commit_return_ns" in lead
                        and lead["commit_enter_ns"] <= self.lock_clock(follower, device.pk)
                        and lead["decisions"][0] < follower["decisions"][0],
                        "The follower was not proven to wait for the leader's transaction")
                if opponent == "application":
                    self.expect(other, 409, CONFLICT_MESSAGE)
                elif "occupancy" in opponent:
                    label = "该日期无有效预约占用。" if due else "已批准（未开始）" if approval_first else "待审核（未开始）"
                    self.expect(other, 200, label)
                else:
                    self.expect(other, 200, "已失效" if due else "已批准" if approval_first else "待审核")
                after = self.snapshot(device)
                self.transition(before, after, row, other_decision if expected == "terminal" else decision, admin, expired=due)
                results.append(dict(opponent=opponent, approval_first=approval_first, approval=approval, other=other,
                                    blockers=blockers, before=before, after=after))
        self.report(case="interleavings", results=results)

    def decision_race(self, admin, other_admin, student, winner):
        """Verify the combined approve/reject actions on two actual request connections."""
        device = self.fixture()
        start, end = self.future()
        row, _ = self.submitted(student, device, start, end)
        self.submitted(student, device, end, end + (end - start))  # Same-device non-target.
        before = self.snapshot(device, start, end)
        entered, release, hold = self.commit_latch()
        approve_wins = winner == "approve"
        reason = "integration-decision-race"
        approve, approve_trace = self.approval(
            admin if approve_wins else other_admin, row, control=hold if approve_wins else None,
        )
        reject, reject_trace = self.prepare(
            self.pair(other_admin if approve_wins else admin), url("admin-reservation-reject", row.pk),
            {"reason": reason}, control={"capture_principal": True, **({} if approve_wins else hold)},
            role=Role.ADMIN,
        )
        first, second = (approve, reject) if approve_wins else (reject, approve)
        lead_trace, wait_trace = (approve_trace, reject_trace) if approve_wins else (reject_trace, approve_trace)
        with ThreadPoolExecutor(max_workers=2) as pool:
            lead_job = pool.submit(first)
            try:
                require(entered.wait(10), "Winning request did not reach held COMMIT")
                wait_job = pool.submit(second)
                blockers = self.wait_blocker(wait_trace, lead_trace["pid"])
                during = self.snapshot(device, start, end)
            finally:
                release.set()
            lead, follow = lead_job.result(), wait_job.result()
        if approve_wins:
            self.result(lead, "approved")
            self.expect(follow, 409, "只有待审核的预约可以拒绝")
        else:
            self.expect(lead, 302)
            self.result(follow, "terminal")
        require(self.unchanged(before, during), "The observer saw a partial transition before COMMIT")

        for trace in (lead_trace, wait_trace):
            lock_returned = self.lock_clock(trace, device.pk)
            rechecks = [entry for entry in trace["bindings"] if is_account_recheck(entry["sql"])]
            require(len(rechecks) == 2 and rechecks[0]["returned_ns"] < lock_returned < rechecks[1]["at_ns"]
                    and trace["commit_attempts"] == 1 and "commit_return_ns" in trace,
                    "Both authorized requests must recheck role after locking and finish one transaction")
        require(lead_trace["pid"] != wait_trace["pid"] and lead_trace["pid"] in blockers
                and lead_trace["commit_enter_ns"] <= wait_trace["lock_acquired_ns"]
                and lead_trace["decisions"][0] < wait_trace["decisions"][0],
                "The follower was not proven to wait for the winner")
        writes = lambda trace: [sql for sql in trace["sql"] if sql.startswith(("UPDATE ", "INSERT ", "DELETE "))]
        winning_writes = writes(lead_trace)
        require(len(winning_writes) == 2
                and all(sql.startswith(prefix) for sql, prefix in zip(winning_writes, TRANSITION, strict=True))
                and not writes(wait_trace), "Expected only one status write and one corresponding history")

        after = self.snapshot(device, start, end)
        state = Status.APPROVED if approve_wins else Status.REJECTED
        require(after["device"] == before["device"]
                and after["rows"] == [{**old, "status": state} if old["id"] == row.pk else old for old in before["rows"]]
                and len(after["history"]) == len(before["history"]) + 1
                and after["history"][:-1] == before["history"],
                "The race changed another row or did not append exactly one history")
        entry = after["history"][-1]
        require((entry["object_type"], entry["equipment_id"], entry["reservation_id"], entry["action"],
                 entry["actor_type"], entry["actor_id"], entry["before_status"], entry["after_status"],
                 entry["reason"], entry["decision_at"]) ==
                ("reservation", None, row.pk, winner, "admin", self.users[admin].pk, Status.PENDING,
                 state, "" if approve_wins else reason, lead_trace["decisions"][0])
                and entry["decision_at"] <= entry["recorded_at"] <= after["observed_at"]
                and [item["id"] for item in before["effective"]] == [row.pk]
                and [item["id"] for item in after["effective"]] == ([row.pk] if approve_wins else []),
                "Unexpected history or occupancy after the combined decision")
        path = url("reservation-submit", device.pk)
        retry = self.prepare(self.pair(student, path), path, window(start, end), role=Role.STUDENT)[0]()
        self.expect(retry, 409, CONFLICT_MESSAGE) if approve_wins else self.expect(retry, 201)
        self.report(case=f"{winner}-wins", blockers=blockers, before=before, during=during, after=after,
                    winner=lead, follower=follow, overlapping_application=retry["response"]["status"])

    def faults(self, admin, student):
        def terminate(pid):
            killer = connections["default"].copy(alias="story26-killer")
            try:
                killer_pid = target(killer)[-1]
                require(killer_pid != pid and query(killer, "SELECT pg_terminate_backend(%s, 3000)", [pid]) == (True,),
                        "Could not terminate the selected isolated request backend")
                terminated.append(dict(killer=killer_pid, request=pid))
            finally:
                killer.close()

        results = []
        for expired in (False, True):
            for fault in ("F1-history", "F2", "F3", "F4"):
                device = self.fixture()
                start = self.now() - timedelta(minutes=5) if expired else self.future()[0]
                row = self.put(student, device, start)
                before = self.snapshot(device)
                terminated = []
                result = self.approval(admin, row, control={"fault": fault, "terminate": terminate})[0]()
                unknown = fault in {"F3", "F4"}
                self.expect(result, 503, "批准结果待核查，请勿重复提交。" if unknown else "数据库事务已回滚。")
                body = result["response"]["body"]
                require("<form" not in body and all(message not in body for _, message in EXPECTED.values())
                        and url("admin-reservation-detail", row.pk) in body, "Fault result asserted an outcome or offered a retry")
                require(not unknown or not any(word in body for word in ("已回滚", "持久化", "未成功", "已批准")),
                        "Unknown result claimed success, failure or persistence")
                trace = result["server"]
                decision = self.order(result, admin, row, writes=TRANSITION, commits=int(fault != "F1-history"))
                require(trace["history_attempts"] == 1, "History was retried or bypassed")
                state = trace["sqlstate"]
                expected_state = {"F1-history": "23514", "F2": "23505"}.get(fault)
                require(state == expected_state if expected_state else
                        (state is None or state.startswith("08") or state == "57P01"), "Unexpected fault SQLSTATE")
                after = self.snapshot(device)
                if fault == "F4":
                    self.transition(before, after, row, decision, admin, expired=expired)
                else:
                    require(self.unchanged(before, after), "Failed operation partially persisted")
                require(fault != "F3" or (len(terminated) == 1 and terminated[0]["request"] == trace["pid"]),
                        "Missing actual targeted disconnection evidence")
                results.append(dict(fault=fault, expired_branch=expired, request=result, before=before, after=after,
                                    terminated=terminated, simulated_confirmation_loss=fault == "F4"))
        device = self.fixture()
        row = self.put(student, device, self.future()[0])
        pair = self.pair(admin)
        before = self.snapshot(device)
        with ThreadPoolExecutor(1) as pool, transaction.atomic():
            self.hold_device(device)
            execute, trace = self.approval(admin, row, pair=pair, control={"lock_timeout": True})
            failed = pool.submit(execute).result(timeout=10)
        self.expect(failed, 503, "数据库事务已回滚。")
        after = self.snapshot(device)
        require(trace["sqlstate"] == "55P03" and not trace["decisions"] and trace["history_attempts"] == 0
                and trace["commit_attempts"] == 0 and self.unchanged(before, after), "Lock timeout was not an atomic failure")
        results.append(dict(fault="lock-timeout", request=failed, before=before, after=after))
        self.report(case="faults", results=results)


TRANSITION = (f"UPDATE {RESERVATIONS}", f"INSERT INTO {HISTORY}")


class Command(BaseCommand):
    help = "Verify Story 2.6 against the guarded isolated PostgreSQL database and archive JSONL evidence."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)
        parser.add_argument("--decision-race-only", action="store_true",
                            help="Run only the integrated approve/reject races, in both orders.")

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Story 2.6 requires the sole guarded isolated test connection")
        app = connections["default"]
        observer = app.copy(alias="story26-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        decision_race_only = options["decision_race_only"]
        expected_cases = DECISION_RACE_CASES if decision_race_only else CASES
        try:
            identity = target(observer)
            app_pid = target(app)[-1]
            require(app_pid != identity[-1] and app.get_autocommit() and not app.in_atomic_block,
                    "Fixture writer and observer need separate guarded connections")
            require(query(observer, """SELECT count(*) FROM pg_stat_activity
                                       WHERE datname = current_database() AND backend_type = 'client backend'
                                         AND pid NOT IN (%s, %s) AND state IS DISTINCT FROM 'idle'""",
                          [app_pid, identity[-1]]) == (0,), "Another isolated database session is active")
            runner.setup_databases(aliases={"default": True})
            before = database_snapshot(observer, runner)
            cases, completed = {}, []
            prefix = f"S26-{uuid4().hex[:14]}-"
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                def report(**record):
                    evidence.write(json.dumps(record, sort_keys=True, default=str, ensure_ascii=False) + "\n")
                    evidence.flush()
                    if "case" in record:
                        completed.append(record["case"])

                report(database=identity, fixture_prefix=prefix, before=before)
                with make_server(HOST, 0, ApprovalWSGI(cases), server_class=ThreadedServer,
                                 handler_class=QuietHandler) as server:
                    probe = ApprovalExperiment(observer, server, cases, prefix, report)
                    thread = Thread(target=server.serve_forever, name="story26-loopback")
                    thread.start()
                    try:
                        with patch.object(services, "_decision_time", observe_decision):
                            if decision_race_only:
                                admin, other_admin, student = map(probe.actor, (Role.ADMIN, Role.ADMIN, Role.STUDENT))
                                for winner in ("approve", "reject"):
                                    probe.decision_race(admin, other_admin, student, winner)
                            else:
                                admin, student, teacher, flagged = map(
                                    probe.actor, (Role.ADMIN, Role.STUDENT, Role.TEACHER, Role.STUDENT),
                                )
                                probe.permissions(admin, student, teacher, flagged)
                                probe.legal(admin, student, teacher)
                                probe.stale_equipment(admin, student)
                                probe.revoked(admin, student)
                                probe.boundary(admin, student, before_commit=False)
                                probe.boundary(admin, student, before_commit=True)
                                probe.interleavings(admin, student, teacher)
                                probe.faults(admin, student)
                    finally:
                        server.shutdown()
                        thread.join()
                        with transaction.atomic():
                            devices = Equipment.objects.filter(number__startswith=prefix)
                            reservations = Reservation.objects.filter(equipment__in=devices)
                            Session.objects.filter(session_key__in=probe.session_keys).delete()
                            OperationHistory.objects.filter(reservation__in=reservations).delete()
                            OperationHistory.objects.filter(equipment__in=devices).delete()
                            reservations.delete()
                            devices.delete()
                            User.objects.filter(username__startswith=prefix).delete()
                        after = database_snapshot(observer, runner)
                        report(cleanup=before == after, after=after)
                        require(before == after, "Isolated rows, ACL or schema changed after cleanup")
                require(tuple(completed) == expected_cases, "Probe results do not exactly match the expected ledger")
            marker = "ADMIN_DECISION_RACES_OK" if decision_race_only else "STORY26_PROBE_OK"
            self.stdout.write(f"{marker} cases={len(completed)}")
        finally:
            observer.close()
            app.close()
