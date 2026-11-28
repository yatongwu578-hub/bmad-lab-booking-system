"""Focused rejection evidence using the existing isolated PostgreSQL and HTTP harness."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from uuid import uuid4
from wsgiref.simple_server import make_server

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import connections, transaction

from accounts.models import Role, User
from audit.models import OperationHistory
from equipment.models import Equipment
from lab_booking.database_config import HOST
from lab_booking.test_runner import IsolatedPostgresRunner
from reservations import services
from reservations.models import Reservation, ReservationStatus as Status

from .verify_admin_reservations import database_snapshot
from .verify_own_reservations import OwnExperiment
from .verify_reservation_transactions import (
    ProbeWSGI, QuietHandler, ThreadedServer, is_account_recheck, observe_decision, query, require, target, url,
)


class RejectionExperiment(OwnExperiment):
    def reject(self, admin, row, fields, *, control=None):
        return self.prepare(self.pair(admin), url("admin-reservation-reject", row.pk), fields,
                            control={"capture_principal": True, **(control or {})})

    def transition(self, before, after, row, status):
        require(after["rows"] == [{**item, "status": status} if item["id"] == row.pk else item
                                  for item in before["rows"]]
                and before["device"] == after["device"] and after["history"][:-1] == before["history"]
                and len(after["history"]) == len(before["history"]) + 1,
                "Transition did not preserve unrelated state and append exactly one history")
        entry = after["history"][-1]
        require(entry["reservation_id"] == row.pk and entry["before_status"] == Status.PENDING
                and entry["after_status"] == status and entry["object_type"] == "reservation"
                and entry["equipment_id"] is None
                and before["observed_at"] <= entry["decision_at"] <= entry["recorded_at"] <= after["observed_at"],
                "History identity or timestamps differ")
        return entry

    def blank(self, admin, student):
        for due, fields in ((False, {}), (True, {"reason": " \t "})):
            device = self.fixture()
            now = self.now()
            row = self.put(student, device, now + timedelta(hours=-1 if due else 1))
            self.put(student, device, now - timedelta(hours=3))
            before = self.snapshot(device)
            result = self.reject(admin, row, fields)[0]()
            self.expect(result, 409 if due else 400, "该待审核预约已失效" if due else "请输入拒绝原因")
            self.check_order(result)
            after = self.snapshot(device)
            if due:
                self.transition(before, after, row, Status.EXPIRED)
                self.expiry(after, row.pk, result["server"]["decisions"][0])
            else:
                require(self.unchanged(before, after), "Future blank reason caused a write")
            self.report(case="blank-due" if due else "blank-future", result=result, before=before, after=after)

    def revoke(self, student):
        admin = self.actor(Role.ADMIN)
        device = self.fixture()
        row = self.put(student, device, self.now() - timedelta(hours=1))
        execute, trace = self.reject(admin, row, {"reason": "private-revocation"})
        before = self.snapshot(device)
        with ThreadPoolExecutor(1) as pool:
            with transaction.atomic():
                self.hold_device(device)
                blocker = query(connections["default"], "SELECT pg_backend_pid()")[0]
                task = pool.submit(execute)
                blockers = self.wait_blocker(trace, blocker)
                query(self.observer, "UPDATE accounts_user SET role = %s WHERE id = %s",
                      [Role.STUDENT, self.users[admin].pk])
            result = task.result()
        self.expect(result, 403)
        after = self.snapshot(device)
        lock, = (i for i, sql in enumerate(trace["sql"]) if "FOR UPDATE" in sql)
        post_lock = trace["sql"][lock + 1:]
        require(len(post_lock) == 1 and is_account_recheck(post_lock[0]) and not trace["decisions"]
                and trace["history_attempts"] == trace["commit_attempts"] == 0
                and self.unchanged(before, after), "Revocation failed to stop business work after lock")
        body = result["response"]["body"]
        require(not any(value in body for value in (device.name, self.users[student].username,
                                                      "private-revocation", url("admin-reservation-detail", row.pk))),
                "Revoked requester was shown private data")
        self.report(case="revoked-while-waiting", result=result, blockers=blockers, before=before, after=after)

    def interleave(self, admin, student, leader):
        device = self.fixture()
        row = self.put(student, device, self.now() + timedelta(hours=-1 if leader == "expire" else 1))
        before = self.snapshot(device)
        entered, release, control = self.commit_latch()
        if leader == "cancel":
            first, a = self.prepare(self.pair(student), url("reservation-cancel", row.pk), {}, control=control)
            status, expected_http = Status.CANCELLED, 200
        elif leader == "expire":
            first, a = self.listing(student, path=self.detail_path(row.pk), control=control)
            status, expected_http = Status.EXPIRED, 200
        else:
            first, a = self.reject(admin, row, {"reason": "leader-only"}, control=control)
            status, expected_http = Status.REJECTED, 302
        second, b = self.reject(admin, row, {"reason": "must-not-overwrite"})
        lead, follow, blockers = self.simultaneous(first, second, a, b, entered, release)
        self.expect(lead, expected_http)
        self.expect(follow, 409, "只有待审核的预约可以拒绝")
        self.check_order(follow)
        after = self.snapshot(device)
        entry = self.transition(before, after, row, status)
        require(entry["action"] == leader and a["pid"] != b["pid"] and a["pid"] in blockers
                and not b["history_attempts"] and not any(sql.startswith(("UPDATE", "INSERT", "DELETE")) for sql in b["sql"])
                and a["decisions"][0] == entry["decision_at"] <= b["decisions"][0]
                and (leader != "reject" or entry["reason"] == "leader-only"),
                "Waiting rejection did not observe the winner without writing")
        self.report(case=f"{leader}-wins", lead=lead, follow=follow, blockers=blockers, before=before, after=after)

    def fault(self, admin, student, fault):
        device = self.fixture()
        row = self.put(student, device, self.now() + timedelta(hours=1))
        before = self.snapshot(device)
        result = self.reject(admin, row, {"reason": "commit-probe"}, control={"fault": fault})[0]()
        self.expect(result, 503, "数据库事务已回滚" if fault == "F2" else "拒绝结果待核查，请勿重复提交")
        self.check_order(result)
        trace = result["server"]
        require(trace["history_attempts"] == 1 and "<form" not in result["response"]["body"],
                "Fault retried history or offered a repeat submission")
        after = self.snapshot(device)
        if fault == "F2":
            require(trace["sqlstate"] == "23505" and self.unchanged(before, after),
                    "Real deferred COMMIT rejection left partial writes")
        else:
            entry = self.transition(before, after, row, Status.REJECTED)
            require((entry["action"], entry["actor_type"], entry["actor_id"], entry["reason"], entry["decision_at"])
                    == ("reject", "admin", self.users[admin].pk, "commit-probe", trace["decisions"][0]),
                    "Committed history does not match the unknown response's request")
        self.report(case=fault, result=result, before=before, after=after,
                    simulated_confirmation_loss=fault == "F4")


class Command(BaseCommand):
    help = "Record rejection lock and COMMIT evidence on the isolated test database."

    def add_arguments(self, parser):
        parser.add_argument("--evidence", required=True, type=Path)

    def handle(self, *args, **options):
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "Run in the preconfigured test-only environment under the shared exclusive test slot")
        app = connections["default"]
        observer = app.copy(alias="rejection-observer")
        runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
        try:
            identity = target(observer)
            app_pid = target(app)[-1]
            require(app_pid != identity[-1] and query(observer, """SELECT count(*) FROM pg_stat_activity
                WHERE datname = current_database() AND backend_type = 'client backend' AND pid NOT IN (%s, %s)
                """, [app_pid, identity[-1]]) == (0,), "Unexpected isolated test connection")
            runner.setup_databases(aliases={"default": True})
            before = database_snapshot(observer, runner)
            require(all(item["count"] == 0 for item in before["rows"].values()), "Unexpected existing test fixtures")
            cases, prefix = {}, f"Y27-{uuid4().hex[:12]}-"
            with options["evidence"].open("x", encoding="utf-8") as evidence:
                def report(**record):
                    evidence.write(json.dumps(record, sort_keys=True, default=str, ensure_ascii=False) + "\n")
                    evidence.flush()

                report(database=identity, writer_pid=app_pid, fixture_prefix=prefix, before=before)
                with make_server(HOST, 0, ProbeWSGI(cases), server_class=ThreadedServer,
                                 handler_class=QuietHandler) as server:
                    probe = RejectionExperiment(observer, server, cases, prefix, report)
                    thread = Thread(target=server.serve_forever, name="rejection-loopback")
                    thread.start()
                    try:
                        admin, student = probe.actor(Role.ADMIN), probe.actor(Role.STUDENT)
                        with patch.object(services, "_decision_time", observe_decision):
                            probe.blank(admin, student)
                            probe.revoke(student)
                            for leader in ("cancel", "expire", "reject"):
                                probe.interleave(admin, student, leader)
                            for fault in ("F2", "F4"):
                                probe.fault(admin, student, fault)
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
                        report(cleanup=before == after, after=after)
                        require(before == after, "Test database baseline changed")
            self.stdout.write("Y27_PROBE_OK cases=8 (F4 is simulated confirmation loss after real COMMIT)")
        finally:
            observer.close()
            app.close()
