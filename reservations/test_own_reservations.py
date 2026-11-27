from datetime import datetime, timedelta
from unittest.mock import patch

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status
from .views import READ_FAILED, READ_UNKNOWN, RESULT_NOT_FOUND


class OwnReservationsTests(TestCase):
    decision = datetime(2026, 11, 27, 10, tzinfo=services.BEIJING)

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="my-student", role=Role.STUDENT)
        cls.peer = User.objects.create_user(username="peer-student-private", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="other-teacher-private", role=Role.TEACHER)
        cls.admin = User.objects.create_user(username="admin-operator-private", role=Role.ADMIN)
        cls.devices = [Equipment.objects.create(number=code, name=f"Device {code}", category="test", location="lab")
                       for code in ("S23-A", "S23-B", "S23-C")]

    def setUp(self):
        self.client.force_login(self.owner)
        self.list_url = reverse("reservation-list")

    def row(self, hours=0, *, status=Status.PENDING, applicant=None, device=None, duration=1):
        start = self.decision + timedelta(hours=hours)
        return Reservation.objects.create(
            applicant=applicant or self.owner, equipment=device or self.devices[0],
            start_at=start, end_at=start + timedelta(hours=duration), status=status,
            applied_at=start - timedelta(days=1),
        )

    @staticmethod
    def result(row):
        return reverse("reservation-result", args=[row.pk])

    def history(self, row, action, reason, *, actor_type="admin"):
        return OperationHistory.objects.create(
            object_type=HistoryObject.RESERVATION, reservation=row, action=action, reason=reason,
            before_status=Status.PENDING, after_status=row.status, actor_type=actor_type,
            actor=self.admin if actor_type == "admin" else None,
            decision_at=self.decision, recorded_at=self.decision,
        )

    def assert_uncached(self, response):
        self.assertTrue({"no-store", "no-cache", "private"}.issubset(
            {directive.strip() for directive in response.headers["Cache-Control"].split(",")}))

    def assert_list_row(self, response, row, *, status=None, equipment_status=None, reason=""):
        start = row.start_at.astimezone(services.BEIJING)
        end = row.end_at.astimezone(services.BEIJING)
        label = Status(status or row.status).label
        device_label = EquipmentStatus(equipment_status or row.equipment.status).label
        self.assertContains(response, f"""
            <tr>
                <td><a href="{self.result(row)}">{row.pk}</a></td>
                <td>{row.equipment.number} · {row.equipment.name}</td>
                <td>{start:%Y-%m-%d}</td>
                <td>{start:%Y-%m-%d %H:%M} 至 {end:%Y-%m-%d %H:%M}</td>
                <td>{label}</td><td>{device_label}</td><td>{reason}</td>
            </tr>
        """, html=True)

    def test_ac1_five_states_and_complete_fields_on_both_pages(self):
        rows = [self.row(offset, status=status, device=self.devices[index % 2])
                for index, (offset, status) in enumerate(zip([26, -25, -26, -27, -28], Status.values))]
        foreign = self.row(2, applicant=self.peer, device=self.devices[2])
        Equipment.objects.filter(pk=self.devices[1].pk).update(status=EquipmentStatus.DISABLED)
        with patch.object(services, "_decision_time", return_value=self.decision):
            response = self.client.get(self.list_url)
            self.assert_uncached(response)
            self.assertEqual([entry["id"] for entry in response.context["records"]], [row.pk for row in rows])
            for index, row in enumerate(rows):
                with self.subTest(status=row.status):
                    current_device = EquipmentStatus.DISABLED if index % 2 else EquipmentStatus.AVAILABLE
                    self.assert_list_row(response, row, equipment_status=current_device)
                    detail = self.client.get(self.result(row))
                    self.assert_uncached(detail)
                    self.assertContains(detail, f"<dt>记录编号</dt><dd>{row.pk}</dd>", html=True)
                    self.assertContains(detail, f"<dt>设备</dt><dd>{row.equipment.number} · {row.equipment.name}</dd>", html=True)
                    self.assertContains(detail, f'<dt>预约日期（北京时间）</dt><dd>{row.start_at:%Y-%m-%d}</dd>', html=True)
                    self.assertContains(detail, row.start_at.strftime("%Y-%m-%d %H:%M"))
                    self.assertContains(detail, row.end_at.strftime("%Y-%m-%d %H:%M"))
                    self.assertContains(detail, f"<dt>预约状态</dt><dd>{Status(row.status).label}</dd>", html=True)
                    self.assertContains(detail, f"<dt>设备当前状态</dt><dd>{current_device.label}</dd>", html=True)
                    self.assertContains(detail, f'<a href="{self.list_url}">返回我的预约</a>', html=True)
        self.assertNotContains(response, self.result(foreign))
        self.assertNotContains(response, foreign.equipment.number)

    def test_ac1_role_navigation_and_actual_201_contract(self):
        for role, user in ((Role.STUDENT, self.owner), (Role.TEACHER, self.teacher), (Role.ADMIN, self.admin)):
            with self.subTest(role=role):
                self.client.force_login(user)
                identity = self.client.get(reverse("identity"))
                if role == Role.ADMIN:
                    self.assertNotContains(identity, self.list_url)
                    continue
                self.assertContains(identity, f'<a href="{self.list_url}">我的预约</a>', html=True)
                start = self.decision + timedelta(days=1)
                device = self.devices[0 if role == Role.STUDENT else 1]
                with patch.object(services, "_decision_time", return_value=self.decision):
                    submitted = self.client.post(reverse("reservation-submit", args=[device.pk]), {
                        "start_at": start.strftime("%Y-%m-%dT%H:%M"),
                        "end_at": (start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
                    })
                    row = Reservation.objects.get(applicant=user)
                    self.assertContains(submitted, self.result(row), status_code=201)
                    self.assertContains(submitted, self.list_url, status_code=201)
                    self.assertContains(submitted, "<dt>提交时状态</dt><dd>待审核</dd>", html=True, status_code=201)
                    self.assertNotContains(submitted, "设备当前状态", status_code=201)
                    self.assert_list_row(self.client.get(self.list_url), row)

    def test_ac2_reads_current_equipment_state_without_mutating_approval(self):
        approved = self.row(-3, status=Status.APPROVED)
        for state in EquipmentStatus:
            with self.subTest(state=state):
                Equipment.objects.filter(pk=approved.equipment_id).update(status=state)
                self.assert_list_row(self.client.get(self.list_url), approved, equipment_status=state)
                detail = self.client.get(self.result(approved))
                self.assertContains(detail, f"<dt>设备当前状态</dt><dd>{state.label}</dd>", html=True)
                self.assertContains(detail, "<dt>预约状态</dt><dd>已批准</dd>", html=True)
                approved.refresh_from_db()
                self.assertEqual(approved.status, Status.APPROVED)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac3_projects_only_latest_matching_admin_reason_and_escapes_it(self):
        rejected = self.row(-10, status=Status.REJECTED)
        cancelled = self.row(-10, status=Status.CANCELLED)
        self_cancelled = self.row(-10, status=Status.CANCELLED)
        unmatched = self.row(-10, status=Status.REJECTED)
        blank = self.row(-10, status=Status.REJECTED)
        expired = self.row(-10, status=Status.EXPIRED)
        foreign = self.row(-10, status=Status.REJECTED, applicant=self.peer)
        self.history(rejected, "reject", "old-hidden-reason")
        self.history(rejected, "reject", "<script>授权原因</script>")
        self.history(rejected, "cancel", "wrong-action")
        self.history(cancelled, "cancel", "管理员取消原因")
        self.history(self_cancelled, "cancel", "private-self-cancel", actor_type="student")
        self.history(unmatched, "reject", "private-system-rejection", actor_type="system")
        self.history(blank, "reject", "   ")
        self.history(expired, "expire", "private-system-expiry", actor_type="system")
        self.history(foreign, "reject", "private-foreign-reason")
        with CaptureQueriesContext(connection) as captured:
            listing = self.client.get(self.list_url)
        projection, = [q["sql"] for q in captured if "public.audit_operationhistory" in q["sql"]]
        self.assertNotRegex(projection, r"actor_id|object_type|recorded_at|decision_at|SELECT\s+\*")
        self.assert_list_row(listing, rejected, reason="&lt;script&gt;授权原因&lt;/script&gt;")
        self.assert_list_row(listing, cancelled, reason="管理员取消原因")
        self.assertContains(self.client.get(self.result(rejected)), "&lt;script&gt;授权原因&lt;/script&gt;")
        self.assertContains(self.client.get(self.result(cancelled)), "管理员取消原因")
        for row in (self_cancelled, unmatched, blank, expired):
            self.assertNotContains(self.client.get(self.result(row)), "处理原因")
        for secret in ("private-", "old-hidden-reason", "wrong-action", "<script>"):
            self.assertNotContains(listing, secret)

    def test_ac4_exact_start_and_ended_expire_once_but_future_and_foreign_do_not(self):
        at_start, ongoing, ended = self.row(0), self.row(-1, duration=2), self.row(-2)
        future = self.row(1)
        foreign = self.row(0, applicant=self.peer)
        approved = self.row(0, status=Status.APPROVED)
        with patch.object(services, "_decision_time", return_value=self.decision):
            self.assertContains(self.client.get(self.result(at_start)), "已失效")
            for _ in range(2):
                response = self.client.get(self.list_url)
                for row in (at_start, ongoing, ended):
                    self.assert_list_row(response, row, status=Status.EXPIRED)
                self.assert_list_row(response, future)
                self.assert_list_row(response, approved)
        for row in (at_start, ongoing, ended):
            self.assertEqual(Reservation.objects.filter(pk=row.pk).values_list(
                "status", "applicant_id", "equipment_id", "start_at", "end_at", "applied_at",
            ).get(), (Status.EXPIRED, row.applicant_id, row.equipment_id, row.start_at, row.end_at, row.applied_at))
            self.assertEqual(OperationHistory.objects.filter(reservation=row).values_list(
                "action", "actor_type", "actor_id", "decision_at",
            ).get(), ("expire", "system", None, self.decision))
        for row in (future, foreign, approved):
            self.assertEqual(Reservation.objects.get(pk=row.pk).status, row.status)
            self.assertFalse(OperationHistory.objects.filter(reservation=row).exists())

    def test_ac5_orders_only_pending_devices_and_rereads_after_account_check(self):
        self.row(-2, device=self.devices[1])
        self.row(-3, device=self.devices[0])
        self.row(-4, device=self.devices[0])
        self.row(-5, device=self.devices[2], status=Status.APPROVED)
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        sql = [q["sql"] for q in captured]
        scoped = [i for i, statement in enumerate(sql) if 'FROM "reservations_reservation"' in statement]
        locks = [i for i, statement in enumerate(sql) if "FOR UPDATE" in statement]
        clock, = [i for i, statement in enumerate(sql) if "clock_timestamp() AS decision_at" in statement]
        self.assertEqual(len(locks), 2)
        self.assertLess(scoped[0], locks[0])
        self.assertLess(locks[-1], scoped[1])
        self.assertLess(scoped[1], clock)
        self.assertNotIn("JOIN", sql[scoped[0]])
        self.assertIn('"equipment_equipment"."status"', sql[scoped[1]])
        self.assertIn('"reservations_reservation"."id" IN (', sql[scoped[1]])
        for lock, device in zip(locks, self.devices):
            self.assertIn(f'WHERE "equipment_equipment"."id" = {device.pk}', sql[lock])
        self.assertTrue(any('FROM "accounts_user"' in s and '"accounts_user"."is_active"' in s
                            for s in sql[locks[-1] + 1:scoped[1]]))

    def test_ac5_no_pending_or_no_candidates_does_not_lock_or_take_time(self):
        for populated in (False, True):
            if populated:
                row = self.row(-5, status=Status.APPROVED)
            urls = [self.list_url, self.result(row)] if populated else [self.list_url]
            for path in urls:
                with patch.object(services, "lock_equipment") as lock, patch.object(services, "_decision_time") as clock:
                    response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                lock.assert_not_called()
                clock.assert_not_called()
                if not populated:
                    self.assertContains(response, "暂无本人预约记录。")

    def test_ac6_unauthorized_and_tampered_requests_never_touch_foreign_rows(self):
        foreign = self.row(-2, applicant=self.peer, device=self.devices[2])
        urls = (self.list_url, self.result(foreign))
        for user, status in ((None, 302), (self.admin, 403)):
            client = Client()
            if user:
                client.force_login(user)
            for path in urls:
                with CaptureQueriesContext(connection) as captured:
                    response = client.get(path)
                self.assertEqual(response.status_code, status)
                self.assertFalse(any('"reservations_reservation"' in q["sql"] for q in captured))
        for user in (self.owner, self.teacher):
            self.client.force_login(user)
            with patch.object(services, "_decision_time") as clock:
                listing = self.client.get(self.list_url, {"owner": self.peer.pk, "applicant_id": self.peer.pk})
                mismatched = self.client.get(urls[1])
                missing = self.client.get(reverse("reservation-result", args=[2**62]))
            self.assertContains(listing, "暂无本人预约记录。")
            self.assertContains(mismatched, RESULT_NOT_FOUND, status_code=404)
            self.assertEqual(mismatched.content, missing.content)
            self.assertNotContains(mismatched, foreign.equipment.name, status_code=404)
            self.assert_uncached(mismatched)
            self.assertEqual(self.client.post(urls[0]).status_code, 405)
            self.assertEqual(self.client.post(urls[1]).status_code, 405)
            clock.assert_not_called()
        self.client.force_login(self.owner)
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.list_url).status_code, 302)
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac7_candidate_insert_during_lock_is_visible_only_on_next_read(self):
        first = self.row(-3)
        added = []
        lock = services.lock_equipment

        def insert_after_freeze(pk):
            added.append(self.row(-4))
            return lock(pk)

        with patch.object(services, "_decision_time", return_value=self.decision):
            with patch.object(services, "lock_equipment", side_effect=insert_after_freeze):
                response = self.client.get(self.list_url)
            self.assertContains(response, self.result(first))
            self.assertNotContains(response, self.result(added[0]))
            self.assertEqual(Reservation.objects.get(pk=added[0].pk).status, Status.PENDING)
            self.assertFalse(OperationHistory.objects.filter(reservation=added[0]).exists())
            self.assert_list_row(self.client.get(self.list_url), added[0], status=Status.EXPIRED)

    def test_ac8_actual_history_failure_rolls_back_and_unknown_has_no_stale_payload(self):
        first, second = self.row(-3), self.row(-2, device=self.devices[1])
        append = services.append_reservation_expiry

        def fail_second(pk, time):
            if pk == second.pk:
                OperationHistory.objects.create(
                    object_type="invalid", action="expire", actor_type="system",
                    reservation_id=pk, decision_at=time, recorded_at=time,
                )
            else:
                append(pk, time)

        with (patch.object(services, "_decision_time", return_value=self.decision),
              patch.object(services, "append_reservation_expiry", side_effect=fail_second) as attempt):
            response = self.client.get(self.list_url)
        self.assertContains(response, READ_FAILED, status_code=503)
        self.assertNotContains(response, self.result(first), status_code=503)
        self.assert_uncached(response)
        self.assertEqual(attempt.call_count, 2)
        self.assertEqual(Reservation.objects.filter(pk__in=[first.pk, second.pk], status=Status.PENDING).count(), 2)
        self.assertFalse(OperationHistory.objects.exists())
        with patch("reservations.views.get_own_reservations", side_effect=services.ReservationUnknown) as read:
            unknown = self.client.get(self.list_url)
        read.assert_called_once()
        self.assertContains(unknown, READ_UNKNOWN, status_code=503)
        self.assertNotContains(unknown, "已回滚", status_code=503)
        self.assertNotContains(unknown, self.result(first), status_code=503)
