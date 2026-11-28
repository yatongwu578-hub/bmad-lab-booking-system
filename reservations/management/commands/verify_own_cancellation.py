"""Guarded Story 2.4 verification through real PostgreSQL, HTTP and Chrome."""

import base64
import json
import platform
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib.metadata import version
from pathlib import Path
from threading import Thread
from time import monotonic_ns
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request
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
from reservations.views import RESULT_NOT_FOUND

from ._chrome_probe import chrome
from .verify_admin_reservations import database_snapshot
from .verify_own_reservations import CLOCK, EQUIPMENT, HISTORY, RESERVATIONS, OwnExperiment
from .verify_reservation_transactions import (
    PROBE, ProbeWSGI, QuietHandler, ThreadedServer, is_account_recheck, observe_decision, query,
    require, scrub, target, url, wait_for, window,
)


CASES = ("A01-A05", "A06", "P01-P07-V01", "P08-off", "P08-role", "I01", "I02", "I03",
         "I04", "I05", "I06", "I07", "I08", "I09", "A08", "V01-M01", "Chrome")
M01_CASES = ("V01-M01", "Chrome")
STARTED = "预约开始时间已到，不能取消"
CANCELLED = "预约已取消"
TERMINAL = "预约当前状态不允许取消"


class CancellationWSGI(ProbeWSGI):
    def get_response(self, request):
        app = connections["default"]
        case = self.cases.get(request.headers.get("X-Story21-Probe"))
        if case is None:
            return super().get_response(request)
        trace, control = case
        trace["bindings"] = []

        def capture(execute, sql, params, many, context):
            if PROBE.get() is trace and (
                any(table in sql for table in (RESERVATIONS, EQUIPMENT, HISTORY))
                or sql == CLOCK or is_account_recheck(sql)
            ):
                intended = list(params or ())
                actual = intended
                if control.get("fault") == "status" and sql.startswith(f"UPDATE {RESERVATIONS}"):
                    params = ("invalid_status", *params[1:])
                    actual = list(params)
                if control.get("fault") == "F1-history" and sql.startswith(f"INSERT INTO {HISTORY}"):
                    # The inner, shared ProbeWSGI replaces the first binding with the invalid object type.
                    actual = ["invalid", *intended[1:]]
                trace["bindings"].append(dict(sql=sql, intended=intended, executed=actual, at_ns=monotonic_ns()))
            return execute(sql, params, many, context)

        with app.execute_wrapper(capture):
            return super().get_response(request)


class CancellationExperiment(OwnExperiment):
    @staticmethod
    def cancel_path(row):
        return url("reservation-cancel", row.pk)

    def cancel(self, actor, row, *, pair=None, control=None):
        return self.prepare(pair or self.pair(actor), self.cancel_path(row), {},
                            control={"capture_principal": True, **(control or {})}, role=self.users[actor].role)

    @staticmethod
    def confirmation_body(pair):
        return urlencode({"csrfmiddlewaretoken": pair[1]}).encode("ascii")

    def raw(self, pair, path, method, *, body=None, content_type="application/x-www-form-urlencoded", csrf=True):
        opener, token = pair
        trace = {}
        case = uuid4().hex
        self.cases[case] = (trace, {"capture_principal": True})
        headers = {"X-Story21-Probe": case, "Content-Type": content_type}
        if csrf:
            headers["X-CSRFToken"] = token
        request = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            try:
                response = opener.open(request, timeout=65)
            except HTTPError as error:
                response = error
            with response:
                return dict(path=path, request_method=method, response=dict(
                    status=response.code, body=scrub(response.read().decode("utf-8")), location=response.headers.get("Location"),
                ), server=trace)
        finally:
            self.cases.pop(case)

    def assert_order(self, result, actor, row, *, writes, commits=1):
        trace = result["server"]
        bindings = trace["bindings"]
        one = lambda predicate: [i for i, entry in enumerate(bindings) if predicate(entry["sql"])]
        pre = one(lambda sql: sql.startswith("SELECT") and f"FROM {RESERVATIONS}" in sql
                  and f'{RESERVATIONS}."equipment_id" AS "equipment_id"' in sql and '"equipment_equipment"' not in sql)
        where = self.users[actor].pk
        lock = one(lambda sql: "FOR UPDATE" in sql)
        account = one(is_account_recheck)
        reread = one(lambda sql: sql.startswith("SELECT") and f"FROM {RESERVATIONS}" in sql and "INNER JOIN" in sql)
        clock = one(lambda sql: sql == CLOCK)
        write = one(lambda sql: sql.startswith(("UPDATE", "INSERT", "DELETE")))
        require(len(pre) == len(lock) == len(reread) == len(clock) == len(trace["decisions"]) == 1
                and len(account) == 2 and len(write) == writes and trace["commit_attempts"] == commits,
                "Wrong lock, account, target, clock, write or commit count")
        require(account[0] < pre[0] < lock[0] < account[1] < reread[0] < clock[0]
                and all(clock[0] < index for index in write), "Required cancellation statement order changed")
        require(bindings[pre[0]]["executed"] == [where, row.pk] and
                bindings[lock[0]]["executed"] == [row.equipment_id] and
                bindings[account[0]]["executed"] == bindings[account[1]]["executed"] == [where] and
                bindings[reread[0]]["executed"] == [where, row.pk, row.equipment_id],
                "Cancellation did not use exact owner, reservation and locked equipment scopes")

    def transition(self, previous, current, row, decision):
        if row.status == Status.PENDING and decision >= row.start_at:
            require(not [item for item in previous["effective"] if item["id"] == row.pk],
                    "Due pending record was incorrectly treated as effectively occupying its slot")
            self.expiry(current, row.pk, decision)
            status = Status.EXPIRED
        else:
            old_ids = {item["id"] for item in previous["history"]}
            history, = [item for item in current["history"] if item["id"] not in old_ids]
            require(
                (history["object_type"], history["reservation_id"], history["equipment_id"], history["action"],
                 history["actor_type"], history["actor_id"], history["before_status"], history["after_status"],
                 history["reason"], history["decision_at"]) ==
                ("reservation", row.pk, None, "cancel", "applicant", row.applicant_id, row.status, Status.CANCELLED, "", decision)
                and decision < row.start_at and decision <= history["recorded_at"] <= current["observed_at"],
                "Cancellation history attribution, prior state or time does not match its decision",
            )
            status = Status.CANCELLED
        old_row = next(item for item in previous["rows"] if item["id"] == row.pk)
        new_row = next(item for item in current["rows"] if item["id"] == row.pk)
        require(new_row == {**old_row, "status": status} and
                current["history"][:len(previous["history"])] == previous["history"] and
                len(current["history"]) == len(previous["history"]) + 1 and
                current["device"] == previous["device"] and
                not [item for item in current["effective"] if item["id"] == row.pk],
                "Original fields/history changed or the transition did not release the active slot")

    def legal(self, student, teacher, admin):
        results = []
        for actor in (student, teacher):
            for state in (Status.PENDING, Status.APPROVED):
                device = self.fixture()
                start, _ = self.future()
                row = self.put(actor, device, start, state)
                self.history(row, "fixture", "保留的历史", actor=self.users[admin])
                before = self.snapshot(device)
                pair = self.pair(actor)
                get, _ = self.prepare(pair, self.cancel_path(row))
                confirmation = get()
                self.expect(confirmation, 200, "确认取消预约")
                require(not confirmation["server"]["decisions"] and confirmation["server"]["commit_attempts"] == 0
                        and not any("FOR UPDATE" in sql or sql.startswith(("UPDATE", "INSERT", "DELETE"))
                                    for sql in confirmation["server"]["sql"])
                        and self.unchanged(before, self.snapshot(device)), "Confirmation GET performed business writes or locks")
                result = self.cancel(actor, row, pair=pair)[0]()
                self.expect(result, 200, CANCELLED)
                self.assert_order(result, actor, row, writes=2)
                after = self.snapshot(device)
                self.transition(before, after, row, result["server"]["decisions"][0])
                require(len(before["effective"]) == 1 and len(after["effective"]) == 0,
                        "Cancellation did not release the sole occupant")
                detail = self.list_for(admin, path=url("admin-reservation-detail", row.pk))
                self.expect(detail, 200, self.users[actor].username)
                self.expect(detail, 200, "申请人")
                results.append(dict(confirmation=confirmation, result=result, before=before, after=after, admin_detail=detail))
        self.report(case="A01-A05", results=results)

    def due(self, student, peer):
        device = self.fixture()
        row, other = self.approved_or_due(student, device, device)
        foreign, = self.approved_or_due(peer, device)
        before = self.snapshot(device)
        first = self.cancel(student, row)[0]()
        self.expect(first, 409, "该待审核预约已失效")
        self.assert_order(first, student, row, writes=2)
        after = self.snapshot(device)
        self.transition(before, after, row, first["server"]["decisions"][0])
        require({item["id"]: item["status"] for item in after["rows"]} ==
                {row.pk: Status.EXPIRED, other.pk: Status.PENDING, foreign.pk: Status.PENDING},
                "Cancellation expired rows outside the single target")
        repeat = self.cancel(student, row)[0]()
        self.expect(repeat, 409, TERMINAL)
        self.assert_order(repeat, student, row, writes=0)
        require(self.unchanged(after, self.snapshot(device)), "Repeated expired cancellation wrote data")
        self.report(case="A06", first=first, repeat=repeat, before=before, after=after)

    def verify_permissions(self, student, peer, teacher, admin):
        actors = (student, peer, teacher)
        devices = [self.fixture() for _ in actors]
        rows = [self.put(actor, device, self.now() - timedelta(hours=2)) for actor, device in zip(actors, devices, strict=True)]
        before = self.snapshots(devices)
        denied, invalid, missing = [], [], []

        def check(result, code, destination, *, foreign=False):
            self.expect(result, code, RESULT_NOT_FOUND if foreign else None)
            if code == 302:
                require(result["response"]["location"] == reverse("login") + "?" + urlencode({"next": destination}, safe="/"),
                        "Anonymous request did not use the authorized login redirect")
            for field in ("body", "location"):
                output = result["response"][field] or ""
                require(not any(device.number in output or device.name in output for device in devices) and
                        not any(self.detail_path(row.pk) in output for row in rows),
                        "Denied response disclosed a fixture or an object link")
                if code != 302:
                    require(destination not in output, "Denied response disclosed a cancellation link")
            trace = result["server"]
            statements = [entry for entry in trace["bindings"]
                          if any(table in entry["sql"] for table in (RESERVATIONS, HISTORY, EQUIPMENT))]
            if foreign:
                scoped, = statements
                principal = trace["principal"]["user_id"]
                require(scoped["sql"].startswith("SELECT") and "FOR UPDATE" not in scoped["sql"] and
                        f'{RESERVATIONS}."applicant_id" = %s' in scoped["sql"] and
                        f'{RESERVATIONS}."id" = %s' in scoped["sql"] and
                        scoped["executed"] == [principal, int(destination.split("/")[2])],
                        "Missing or foreign read escaped the owner and URL target scope")
            require((foreign or not statements)
                    and not trace["decisions"] and trace["commit_attempts"] == 0
                    and self.unchanged_all(before, self.snapshots(devices)), "Rejected request reached business data")

        admin_user = self.users[admin]
        User.objects.filter(pk=admin_user.pk).update(is_staff=True, is_superuser=True)
        path = self.cancel_path(rows[0])
        for actor, code in ((None, 302), (admin, 403)):
            pair = self.pair(actor)
            for method in ("GET", "POST"):
                result = self.raw(pair, path, method, body=self.confirmation_body(pair) if method == "POST" else None)
                check(result, code, path)
                denied.append(result)
        for actor, row in zip(actors, (*rows[1:], rows[0]), strict=True):
            pair = self.pair(actor)
            path = self.cancel_path(row)
            absent = url("reservation-cancel", max(item.pk for item in rows) + 10**6)
            for method in ("GET", "POST"):
                data = self.confirmation_body(pair) if method == "POST" else None
                result, control = (self.raw(pair, candidate, method, body=data) for candidate in (path, absent))
                check(result, 404, path, foreign=True)
                check(control, 404, absent, foreign=True)
                require(result["response"]["body"] == control["response"]["body"], "Missing and foreign responses differ")
                denied.append(result)
                missing.append(control)

        pair = self.pair(student)
        path = self.cancel_path(rows[0])
        User.objects.filter(pk=self.users[student].pk).update(is_active=False)
        try:
            for method in ("GET", "POST"):
                result = self.raw(pair, path, method, body=self.confirmation_body(pair) if method == "POST" else None)
                check(result, 302, path)
                denied.append(result)
        finally:
            User.objects.filter(pk=self.users[student].pk).update(is_active=True)
        pair = self.pair(student)
        for token in (b"", b"csrfmiddlewaretoken=invalid"):
            result = self.raw(pair, path, "POST", body=token, csrf=False)
            check(result, 403, path)
            denied.append(result)
        valid = pair[1].encode("ascii")
        for body, media in (
            (b"unexpected=1", "application/x-www-form-urlencoded"),
            (b"csrfmiddlewaretoken=" + valid + b"&csrfmiddlewaretoken=" + valid, "application/x-www-form-urlencoded"),
            (b"applicant_id=1", "application/x-www-form-urlencoded"),
            (b"role=teacher", "application/x-www-form-urlencoded"),
            (b"equipment_id=1", "application/x-www-form-urlencoded"),
            (b"status=approved", "application/x-www-form-urlencoded"),
            (b"start_at=1900", "application/x-www-form-urlencoded"),
            (b'{"status":"approved"}', "application/json"),
        ):
            result = self.raw(pair, path, "POST", body=body, content_type=media)
            check(result, 400, path)
            if body.startswith(b"csrfmiddlewaretoken="):
                # Neither request values nor the CSRF header is added to the receipt.
                require("确认取消预约" not in result["response"]["body"], "Duplicate CSRF fields were accepted")
            invalid.append(result)
        for method in ("HEAD", "PUT", "DELETE", "OPTIONS"):
            result = self.raw(pair, path, method)
            check(result, 405, path)
            invalid.append(result)
        confirmation = self.raw(pair, path, "GET")
        self.expect(confirmation, 200, "确认取消预约")
        require(self.unchanged_all(before, self.snapshots(devices)) and not confirmation["server"]["decisions"]
                and not any("FOR UPDATE" in sql for sql in confirmation["server"]["sql"]),
                "GET confirmation changed an already-due pending reservation")
        self.report(case="P01-P07-V01", denied=denied, rejected_count=len(denied), invalid=invalid, missing=missing,
                    confirmation=confirmation, before=before, after=self.snapshots(devices))

    def m01(self, student):
        pair = self.pair(student)
        token = pair[1].encode("ascii")
        form = self.confirmation_body(pair)
        urlencoded = "application/x-www-form-urlencoded"
        multipart = "multipart/form-data; boundary=s24m01"
        inputs = (
            ("multipart-with-token", multipart, b"--s24m01\r\nContent-Disposition: form-data; "
             b'name="csrfmiddlewaretoken"\r\n\r\n' + token + b"\r\n--s24m01--\r\n"),
            ("multipart-unnamed-part", multipart, b"--s24m01\r\nContent-Disposition: form-data\r\n"
             b"\r\nignored\r\n--s24m01--\r\n"),
            ("missing-body", urlencoded, b""),
            ("empty-token-field", urlencoded, b"csrfmiddlewaretoken="),
            ("trailing-separator", urlencoded, form + b"&"),
            ("incomplete-trailing-field", urlencoded, form + b"&unfinished"),
            ("dangling-percent", urlencoded, b"csrfmiddlewaretoke%=" + token),
            ("non-hex-escape", urlencoded, b"%GG=" + token),
            ("invalid-utf8-escape", urlencoded, b"%FF=" + token),
            ("duplicate-token", urlencoded, form + b"&" + form),
        )
        runs = []
        for state in ("future", "due"):
            device = self.fixture()
            start = self.future()[0] if state == "future" else self.now() - timedelta(hours=2)
            row = self.put(student, device, start)
            path = self.cancel_path(row)
            before = self.snapshot(device)
            require(len(before["effective"]) == int(state == "future") and not before["history"],
                    "M01 fixtures must prove both occupied future and uncollected due pending paths")

            def reject(label, media, body, *, csrf=True):
                result = self.raw(pair, path, "POST", body=body, content_type=media, csrf=csrf)
                self.expect(result, 400 if csrf else 403, "取消预约请求格式无效" if csrf else None)
                trace = result["server"]
                require(trace["principal"]["user_id"] == row.applicant_id and not trace["sql"]
                        and not trace["bindings"] and not trace["decisions"] and trace["commit_attempts"] == 0
                        and trace["history_attempts"] == 0, "M01 rejection reached business SQL or lost fixture identity")
                after = self.snapshot(device)
                require(self.unchanged(before, after), "Rejected M01 request changed reservation, occupancy or history")
                return dict(input=label, content_type=media, bytes=len(body), csrf_header=csrf,
                            request_body=body.replace(token, b"[redacted]").decode("ascii"), result=result, after=after)

            invalid = [reject(*entry) for entry in inputs]
            csrf_denied = [reject("missing-csrf", urlencoded, b"", csrf=False),
                           reject("invalid-csrf", urlencoded, b"csrfmiddlewaretoken=invalid", csrf=False)]
            legal = self.raw(pair, path, "POST", body=form, csrf=False)
            self.expect(legal, 200 if state == "future" else 409, CANCELLED if state == "future" else STARTED)
            self.assert_order(legal, student, row, writes=2)
            after = self.snapshot(device)
            self.transition(before, after, row, legal["server"]["decisions"][0])
            repeat = self.raw(pair, path, "POST", body=form, csrf=False)
            self.expect(repeat, 409, TERMINAL)
            self.assert_order(repeat, student, row, writes=0)
            require(self.unchanged(after, self.snapshot(device)), "M01 legal control repeated a history write")
            runs.append(dict(state=state, before=before, invalid=invalid, csrf_denied=csrf_denied,
                             legal=legal, repeat=repeat, after=after))
        self.report(case="V01-M01", runs=runs)

    def revoke(self, *, deactivate):
        actor = self.actor(Role.STUDENT)
        device = self.fixture()
        row = self.put(actor, device, self.now() - timedelta(hours=2))
        execute, trace = self.cancel(actor, row)
        before = self.snapshot(device)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                changed = {"is_active": False} if deactivate else {"role": Role.ADMIN}
                # Observer is independent of the uncommitted device lock and commits the fixture-only revocation.
                sql = ("UPDATE accounts_user SET is_active = %s WHERE id = %s" if deactivate else
                       "UPDATE accounts_user SET role = %s WHERE id = %s")
                query(self.observer, sql, [next(iter(changed.values())), self.users[actor].pk])
            result = task.result()
        self.expect(result, 403)
        after = self.snapshot(device)
        require(self.unchanged(before, after) and not trace["decisions"] and trace["commit_attempts"] == 0
                and trace["history_attempts"] == 0 and trace["principal"]["user_id"] == self.users[actor].pk,
                "Account revocation did not stop the transaction after device-lock acquisition")
        locks = [i for i, item in enumerate(trace["sql"]) if "FOR UPDATE" in item]
        require(len(locks) == 1 and [sql for sql in trace["sql"][locks[0] + 1:]] ==
                [sql for sql in trace["sql"][locks[0] + 1:] if is_account_recheck(sql)] and
                len(trace["sql"][locks[0] + 1:]) == 1, "Unexpected post-lock operations on a revoked account")
        self.report(case="P08-off" if deactivate else "P08-role", result=result, blockers=blockers, changed=changed,
                    before=before, after=after)

    def competition(self, student, teacher, *, case):
        device = self.fixture()
        start, end = self.future()
        row = self.put(student, device, start)
        before = self.snapshot(device, start, end)
        entered, release, controls = self.commit_latch()
        a = self.cancel(student, row, control=controls if case != "I02" else None)
        if case == "I03":
            b = self.cancel(student, row)
        else:
            path = url("reservation-submit", device.pk)
            b = self.prepare(self.pair(teacher, path), path, window(start, end),
                             control=controls if case == "I02" else None)
        first, second = (b, a) if case == "I02" else (a, b)
        lead, follow, blockers = self.simultaneous(first[0], second[0], first[1], second[1], entered, release)
        cancelled, other = (follow, lead) if case == "I02" else (lead, follow)
        self.expect(cancelled, 200, CANCELLED)
        self.assert_order(cancelled, student, row, writes=2)
        self.expect(other, 201 if case == "I01" else 409)
        after = self.snapshot(device, start, end)
        self.transition(before, after, row, cancelled["server"]["decisions"][0])
        if case == "I01":
            effective, = after["effective"]
            require(effective["id"] != row.pk and effective["applicant_id"] == self.users[teacher].pk
                    and effective["start_at"] == start and effective["end_at"] == end,
                    "Waiting submit did not become the sole occupant")
        else:
            require(not after["effective"] and len(after["rows"]) == 1,
                    "Conflict or second cancellation unexpectedly created occupancy")
        repeat = None
        if case == "I03":
            self.assert_order(other, student, row, writes=0)
            repeat = self.cancel(student, row)[0]()
            self.expect(repeat, 409, TERMINAL)
            self.assert_order(repeat, student, row, writes=0)
            require(self.unchanged(after, self.snapshot(device)), "Repeated cancellation changed state")
        self.report(case=case, before=before, after=after, lead=lead, follow=follow, repeat=repeat, blockers=blockers)

    def query_interleavings(self, *, query_first, due):
        runs = []
        for reader in ("occupancy", "list", "detail"):
            student = self.actor(Role.STUDENT)
            lower = self.fixture() if reader == "list" else None
            device = self.fixture()
            start = self.now() - timedelta(minutes=10) if due else self.future()[0]
            row = self.put(student, device, start)
            earlier_device = self.put(student, lower, self.future()[0]) if lower is not None else None
            path = {
                "occupancy": url("equipment-occupancy", device.pk) + "?" + urlencode({"date": start.astimezone(services.BEIJING).date()}),
                "list": reverse("reservation-list"),
                "detail": self.detail_path(row.pk),
            }[reader]
            before = self.snapshot(device)
            entered, release, hold = self.commit_latch()
            reading = self.prepare(self.pair(student), path, control=hold if query_first else None)
            cancelling = self.cancel(student, row, control=None if query_first else hold)
            first, second = (reading, cancelling) if query_first else (cancelling, reading)
            lead, follow, blockers = self.simultaneous(first[0], second[0], first[1], second[1], entered, release)
            read, cancel = (lead, follow) if query_first else (follow, lead)
            self.expect(read, 200)
            self.expect(cancel, 409 if due else 200, (TERMINAL if query_first else STARTED) if due else CANCELLED)
            self.assert_order(cancel, student, row, writes=0 if due and query_first else 2)
            read_locks = [item["executed"][0] for item in read["server"]["bindings"] if "FOR UPDATE" in item["sql"]]
            require(read_locks == sorted(set(read_locks)) and device.pk in read_locks
                    and (not earlier_device or lower.pk in read_locks), "Reader did not keep canonical device lock order")
            if reader == "occupancy":
                expectation = "待审核（未开始）" if query_first and not due else "该日期无有效预约占用"
            elif reader == "detail":
                expectation = "已失效" if due else ("待审核" if query_first else "已取消")
            else:
                # Avoid matching unrelated pending rows that are deliberately present for lock order.
                allowed = ("已失效" if due else ("待审核" if query_first else "已取消"))
                article = read["response"]["body"].split(f'href="{self.detail_path(row.pk)}"', 1)
                require(len(article) == 2 and allowed in article[1].split("</tr>", 1)[0], "List did not show the locked target state")
                expectation = allowed
            self.expect(read, 200, expectation)
            after = self.snapshot(device)
            self.transition(before, after, row, lead["server"]["decisions"][0] if due else cancel["server"]["decisions"][0])
            require(lead["server"]["decisions"][0] < follow["server"]["decisions"][0],
                    "Follower did not decide after the lock holder")
            repeat = self.prepare(self.pair(student), path)[0]()
            self.expect(repeat, 200, "该日期无有效预约占用" if reader == "occupancy" else ("已失效" if due else "已取消"))
            duplicate = self.cancel(student, row)[0]()
            self.expect(duplicate, 409, TERMINAL)
            require(self.unchanged(after, self.snapshot(device)), "Readback or repeated cancellation wrote a duplicate transition")
            runs.append(dict(reader=reader, lead=lead, follow=follow, blockers=blockers, before=before, after=after,
                             repeat=repeat, duplicate=duplicate))
        if due:
            device = self.fixture()
            approved = self.put(student, device, self.now() - timedelta(minutes=5), Status.APPROVED)
            before = self.snapshot(device)
            path = url("equipment-occupancy", device.pk) + "?" + urlencode({"date": approved.start_at.astimezone(services.BEIJING).date()})
            read = self.prepare(self.pair(student), path)[0]()
            self.expect(read, 200, "已批准（进行中）")
            require(not any("FOR UPDATE" in sql for sql in read["server"]["sql"]), "Approved-only query unexpectedly locked")
            cancel = self.cancel(student, approved)[0]()
            self.expect(cancel, 409, STARTED)
            self.assert_order(cancel, student, approved, writes=0)
            after = self.snapshot(device)
            require(self.unchanged(before, after), "Started approved control changed or released its active slot")
            runs.append(dict(approved_control=True, read=read, cancel=cancel, before=before, after=after))
        case = ("I06" if query_first else "I07") if due else ("I04" if query_first else "I05")
        self.report(case=case, runs=runs)

    def cross_boundary(self, student, *, commit_after):
        runs = []
        for state in (Status.PENDING, Status.APPROVED):
            device = self.fixture()
            pair = self.pair(student)
            checking_pair = self.pair(student) if commit_after else None
            start = self.now() + timedelta(seconds=5)
            row = self.put(student, device, start, state)
            before = self.snapshot(device)
            repeat = None
            with ThreadPoolExecutor(2 if commit_after else 1) as pool:
                if commit_after:
                    entered, release, hold = self.commit_latch()
                    execute, trace = self.cancel(student, row, pair=pair, control=hold)
                    task = pool.submit(execute)
                    try:
                        require(entered.wait(10) and len(trace["decisions"]) == 1 and trace["decisions"][0] < start,
                                "Cancellation did not reach COMMIT with a pre-start decision")
                        challenger, challenge_trace = self.cancel(student, row, pair=checking_pair)
                        checking = pool.submit(challenger)
                        blockers = self.wait_blocker(challenge_trace, trace["pid"])
                        during = self.snapshot(device)
                        require(before["rows"] == during["rows"] and before["history"] == during["history"],
                                "Uncommitted state or history became visible")
                        crossed = wait_for(lambda: (now := self.now()) >= start and now, "held COMMIT crossed appointment start")
                    finally:
                        release.set()
                    repeat = checking.result()
                    self.expect(repeat, 409, TERMINAL)
                    self.assert_order(repeat, student, row, writes=0)
                else:
                    execute, trace = self.cancel(student, row, pair=pair)
                    with transaction.atomic():
                        self.hold_device(device)
                        blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                        task = pool.submit(execute)
                        blockers = self.wait_blocker(trace, blocker)
                        during = self.snapshot(device)
                        require(during["observed_at"] < start and not trace["decisions"],
                                "Request did not verifiably wait before start without sampling")
                        crossed = wait_for(lambda: (now := self.now()) >= start and now, "waiting request crossed appointment start")
                        before = self.snapshot(device)
                result = task.result()
            self.expect(result, 200 if commit_after else 409, CANCELLED if commit_after else STARTED)
            after = self.snapshot(device)
            self.assert_order(result, student, row, writes=2 if commit_after or state == Status.PENDING else 0)
            decision, = trace["decisions"]
            if commit_after or state == Status.PENDING:
                self.transition(before, after, row, decision)
            else:
                require(self.unchanged(before, after), "Started approved record changed")
            require((decision < start <= crossed) if commit_after else (start <= crossed <= decision),
                    "Recorded timing did not straddle the appointment boundary as expected")
            runs.append(dict(state=state, result=result, start=start, crossed=crossed, blockers=blockers, repeat=repeat,
                             before=before, during=during, after=after))
        self.report(case="I09" if commit_after else "I08", runs=runs)

    def faults(self, student):
        cases = []
        faults = ("status", "F1-history", "F2", "F3", "F4")
        for branch in ("cancel", "expire"):
            for fault in faults:
                device = self.fixture()
                start = self.now() - timedelta(hours=2) if branch == "expire" else self.future()[0]
                row = self.put(student, device, start)
                before = self.snapshot(device)
                terminated = []

                def terminate(pid):
                    killer = connections["default"].copy(alias="story24-killer")
                    try:
                        killer_pid = target(killer)[-1]
                        require(pid != killer_pid and
                                query(killer, "SELECT pg_terminate_backend(%s, 3000)", [pid]) == (True,),
                                "Independent backend did not terminate the targeted isolated request")
                        terminated.append({"request": pid, "killer": killer_pid})
                    finally:
                        killer.close()

                controls = {"fault": fault}
                if fault == "F3":
                    controls["terminate"] = terminate
                result = self.cancel(student, row, control=controls)[0]()
                trace = result["server"]
                unknown = fault in {"F3", "F4"}
                self.expect(result, 503, "取消结果待核查" if unknown else "数据库事务已回滚")
                body = result["response"]["body"]
                require(CANCELLED not in body and "<form" not in body and self.cancel_path(row) not in body
                        and "该待审核预约已失效" not in body and "返回我的预约" in body,
                        "Failure response reported a transition or offered a replay")
                self.assert_order(result, student, row, writes=1 if fault == "status" else 2,
                                  commits=int(fault in {"F2", "F3", "F4"}))
                require(trace["history_attempts"] == int(fault != "status"), "History was retried or executed after bad status")
                expected_sqlstate = {"status": "23514", "F1-history": "23514", "F2": "23505"}.get(fault)
                state = trace["sqlstate"]
                require(state == expected_sqlstate if expected_sqlstate else
                        (state is None or state.startswith("08") or state == "57P01"),
                        "Unexpected PostgreSQL error state")
                after = self.snapshot(device)
                if fault == "F4":
                    # The shared probe intentionally raises after real COMMIT. This is a simulation, not an outage.
                    self.transition(before, after, row, trace["decisions"][0])
                else:
                    require(self.unchanged(before, after), "Unsuccessful transaction partially persisted")
                require(fault != "F3" or len(terminated) == 1 and terminated[0]["request"] == trace["pid"],
                        "Missing real targeted disconnection evidence")
                cases.append(dict(branch=branch, fault=fault, result=result, before=before, after=after,
                                  killed_pids=terminated, simulated_confirmation_loss=fault == "F4", retry=False))
        self.report(case="A08", cases=cases)

    def browser(self, student, teacher, evidence):
        results = []
        with chrome() as browser:
            product = browser.call("Browser.getVersion")["product"]
            for actor in (student, teacher):
                device = self.fixture()
                role = self.users[actor].role
                status = Status.PENDING if role == Role.STUDENT else Status.APPROVED
                row = self.put(actor, device, self.future()[0], status)
                before = self.snapshot(device)
                opener, _ = self.pair(actor)
                jar, = (handler.cookiejar for handler in opener.handlers if isinstance(handler, HTTPCookieProcessor))
                session, = (cookie for cookie in jar if cookie.name == settings.SESSION_COOKIE_NAME)
                browser.call("Network.clearBrowserCookies")
                require(browser.call("Network.setCookie", name=session.name, value=session.value, url=self.base,
                                     httpOnly=True, path="/").get("success"), "Could not select the fixture browser session")
                browser.documents.clear()
                listing, detail, cancel = reverse("reservation-list"), self.detail_path(row.pk), self.cancel_path(row)
                first_path = listing if status == Status.PENDING else detail
                cancel_link = f'a[href="{cancel}"]'
                button = 'form[method="post"] button[type="submit"]'
                browser.call("Page.navigate", url=self.base + first_path)
                browser.document(self.base + first_path, 200, f"!!document.querySelector({json.dumps(cancel_link)})")
                browser.click(cancel_link)
                confirmation = browser.document(self.base + cancel, 200, """(() => {
                    const form = document.querySelector('form[method="post"]');
                    return form ? {hasCsrf: !!form.elements.namedItem('csrfmiddlewaretoken')?.value, enctype: form.enctype,
                        fields: [...document.querySelectorAll('dd')].map(el => el.textContent)} : null;
                })()""")
                fields = [str(row.pk), f"{device.number} · {device.name}",
                          f"{row.start_at.astimezone(services.BEIJING):%Y-%m-%d %H:%M} 至 "
                          f"{row.end_at.astimezone(services.BEIJING):%Y-%m-%d %H:%M}", status.label]
                require(confirmation == {"hasCsrf": True, "enctype": "application/x-www-form-urlencoded", "fields": fields},
                        "Wrong browser confirmation fields, encoding or CSRF")

                def screenshot(label):
                    output = evidence.with_name(f"chrome-{role}-{label}.png")
                    pixels = browser.call("Page.captureScreenshot", format="png")["data"]
                    with output.open("xb") as image:
                        image.write(base64.b64decode(pixels, validate=True))
                    return output.name

                confirm_image = screenshot("confirm")
                browser.click(f'a[href="{detail}"]')
                browser.document(self.base + detail, 200, f"!!document.querySelector({json.dumps(cancel_link)})")
                left = self.snapshot(device)
                require(self.unchanged(before, left), "Leaving confirmation performed business DML")
                browser.click(cancel_link)
                browser.document(self.base + cancel, 200, f"!!document.querySelector({json.dumps(button)})")
                browser.click(button)
                result = browser.document(self.base + cancel, 200, """(() => {
                    const title = document.querySelector('h1')?.textContent;
                    return title === '预约已取消' ? {title, status: document.querySelector('[role="status"]')?.textContent,
                        fields: [...document.querySelectorAll('dd')].map(el => el.textContent),
                        hasForm: !!document.querySelector('form')} : null;
                })()""")
                require(result == {"title": CANCELLED, "status": "预约已取消，原记录已保留。",
                                   "fields": [*fields[:-1], Status.CANCELLED.label], "hasForm": False},
                        "Browser result did not show a completed cancellation")
                result_image = screenshot("result")
                after = self.snapshot(device)
                history, = after["history"]
                self.transition(before, after, row, history["decision_at"])
                browser.click(f'a[href="{listing}"]')
                browser.document(self.base + listing, 200, f"""(() => {{
                    const row = document.querySelector('a[href="{detail}"]')?.closest('tr');
                    return !!row && row.textContent.includes('已取消') &&
                        !document.querySelector({json.dumps(cancel_link)});
                }})()""")
                expected = [(self.base + path, 200) for path in (first_path, cancel, detail, cancel, cancel, listing)]
                require([(item["url"], item["status"]) for item in browser.documents] == expected
                        and self.unchanged(after, self.snapshot(device)), "Unexpected browser requests or repeat writes")
                results.append(dict(role=role, confirmation=confirmation, result=result, before=before, left=left,
                                    after=after, documents=list(browser.documents), screenshots=[confirm_image, result_image]))
        self.report(case="Chrome", product=product, results=results)


class Command(BaseCommand):
    help = "Verify Story 2.4 against the guarded isolated PostgreSQL database and archive evidence."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)
        parser.add_argument("--m01-only", action="store_true")

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Story 2.4 requires the sole guarded isolated test connection")
        app = connections["default"]
        observer = app.copy(alias="story24-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
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
            prefix = f"S24-{uuid4().hex[:14]}-"
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                def report(**record):
                    evidence.write(json.dumps(record, sort_keys=True, default=str, ensure_ascii=False) + "\n")
                    evidence.flush()
                    if "case" in record:
                        completed.append(record["case"])

                report(database=identity, fixture_prefix=prefix, before=before,
                       versions={"python": platform.python_version(), "django": version("Django")})
                with make_server(HOST, 0, CancellationWSGI(cases), server_class=ThreadedServer,
                                 handler_class=QuietHandler) as server:
                    probe = CancellationExperiment(observer, server, cases, prefix, report)
                    thread = Thread(target=server.serve_forever, name="story24-loopback")
                    thread.start()
                    try:
                        student = probe.actor(Role.STUDENT)
                        with patch.object(services, "_decision_time", observe_decision):
                            if not options["m01_only"]:
                                peer, teacher, admin = map(probe.actor, (Role.STUDENT, Role.TEACHER, Role.ADMIN))
                                probe.legal(student, teacher, admin)
                                probe.due(student, peer)
                                probe.verify_permissions(student, peer, teacher, admin)
                                probe.revoke(deactivate=True)
                                probe.revoke(deactivate=False)
                                for case in ("I01", "I02", "I03"):
                                    probe.competition(student, teacher, case=case)
                                for due in (False, True):
                                    for query_first in (True, False):
                                        probe.query_interleavings(query_first=query_first, due=due)
                                probe.cross_boundary(student, commit_after=False)
                                probe.cross_boundary(student, commit_after=True)
                                probe.faults(student)
                            probe.m01(student)
                            probe.browser(probe.actor(Role.STUDENT), probe.actor(Role.TEACHER), options["evidence"])
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
                expected = M01_CASES if options["m01_only"] else CASES
                require(tuple(completed) == expected, "Probe results do not exactly match the Story 2.4 ledger")
            self.stdout.write(f"STORY24_PROBE_OK cases={len(completed)}")
        finally:
            observer.close()
            app.close()
