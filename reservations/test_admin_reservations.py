from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.db import connection, connections
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status
from .views import READ_FAILED, READ_UNKNOWN


LIST = "/reservations/manage/"
NOW = datetime(2026, 11, 26, 16, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)
BUSINESS = ("reservations_reservation", "equipment_equipment", "audit_operationhistory")


class AdminReservationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="lab-manager", role=Role.ADMIN)
        cls.student = User.objects.create_user(username="student-fixture", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="teacher-fixture", role=Role.TEACHER)
        cls.peer = User.objects.create_user(username="peer-fixture", role=Role.STUDENT,
                                           is_staff=True, is_superuser=True)
        cls.inactive = User.objects.create_user(username="inactive-manager", role=Role.ADMIN, is_active=False)
        cls.first, cls.second, cls.third = [
            Equipment.objects.create(number=code, name=name, category="Lab", location="Room", status=state)
            for code, name, state in [
                ("S25-A&甲", "Instrument A", EquipmentStatus.MAINTENANCE),
                ("S25-B", "Instrument B", EquipmentStatus.DISABLED),
                ("S25-C", "Instrument C", EquipmentStatus.AVAILABLE),
            ]
        ]

    def setUp(self):
        self.client.force_login(self.admin)

    def reservation(self, equipment=None, *, applicant=None, status=Status.PENDING, start=NOW, end=None):
        return Reservation.objects.create(
            equipment=equipment or self.first, applicant=applicant or self.student,
            status=status, start_at=start, end_at=end if end is not None else start + HOUR,
            applied_at=start - HOUR,
        )

    def history(self, row, action, after, *, actor=None, actor_type="admin", before=Status.PENDING,
                reason="", recorded=NOW):
        return OperationHistory.objects.create(
            object_type=HistoryObject.RESERVATION, reservation=row, action=action, actor_type=actor_type,
            actor=actor, before_status=before, after_status=after, reason=reason,
            recorded_at=recorded, decision_at=recorded - timedelta(seconds=3),
        )

    @staticmethod
    def detail(pk):
        return reverse("admin-reservation-detail", args=[pk])

    def record_ids(self, response):
        return {row["id"] for row in response.context["records"]}

    def test_identity_navigation_uses_business_role(self):
        self.assertContains(self.client.get("/identity/"), f'href="{LIST}">预约管理')
        for user in (self.student, self.teacher, self.peer):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertNotContains(self.client.get("/identity/"), "预约管理")

    def test_full_list_keeps_five_states_with_dual_status_and_persisted_reason(self):
        rows = [self.reservation(status=status, start=NOW + HOUR if status == Status.PENDING else NOW - 2 * HOUR,
                                 applicant=self.teacher if status == Status.APPROVED else self.student,
                                 equipment=self.second if status == Status.APPROVED else self.first)
                for status in Status.values]
        rejected = next(row for row in rows if row.status == Status.REJECTED)
        self.history(rejected, "reject", Status.REJECTED, actor=self.admin, reason="实际 <拒绝> 原因")
        self.history(rejected, "reject", Status.REJECTED, actor=self.admin, reason=" \t", recorded=NOW + HOUR)
        with patch.object(services, "_decision_time", return_value=NOW):
            response = self.client.get(LIST)
        self.assertEqual(self.record_ids(response), {row.pk for row in rows})
        for value in ("全部预约（含历史记录）", "student-fixture", "teacher-fixture", "Instrument B",
                      "2026-11-27", "2026-11-26 22:00", "2026-11-26 23:00", "维修", "停用",
                      escape("实际 <拒绝> 原因"), *Status.labels):
            self.assertContains(response, value)
        self.assertNotContains(response, "<拒绝>")
        self.assertEqual({row["id"]: row["reason"] for row in response.context["records"]}[rejected.pk], "实际 <拒绝> 原因")
        self.assertEqual(OperationHistory.objects.count(), 2)

    def test_filter_uses_exact_code_and_single_time_across_start_and_end_boundaries(self):
        future = self.reservation(start=NOW + HOUR)
        starting = self.reservation(start=NOW)
        past = self.reservation(start=NOW - 2 * HOUR)
        active = self.reservation(status=Status.APPROVED, start=NOW - HOUR, end=NOW + timedelta(microseconds=1))
        self.reservation(status=Status.APPROVED, start=NOW - HOUR, end=NOW)
        self.reservation(status=Status.APPROVED, start=NOW - HOUR, end=NOW - timedelta(microseconds=1))
        for status in (Status.CANCELLED, Status.REJECTED, Status.EXPIRED):
            self.reservation(status=status, start=NOW + HOUR)
        other = self.reservation(self.second, start=NOW - 2 * HOUR)
        with patch.object(services, "_decision_time", return_value=NOW) as time:
            response = self.client.get(LIST, {"equipment": f"  {self.first.number}  "})
        time.assert_called_once_with(connections["default"])
        self.assertEqual(self.record_ids(response), {future.pk, active.pk})
        self.assertContains(response, "受影响预约")
        self.assertContains(response, "清除筛选")
        self.assertContains(response, "?equipment=S25-A%26%E7%94%B2")
        self.assertNotContains(response, "全部预约（含历史记录）")
        for row in (starting, past):
            row.refresh_from_db()
            self.assertEqual(row.status, Status.EXPIRED)
            self.assertEqual(OperationHistory.objects.get(reservation=row).decision_at, NOW)
        other.refresh_from_db()
        self.assertEqual(other.status, Status.PENDING)

    def test_empty_invalid_and_absent_results_do_not_fall_back_or_write(self):
        self.assertContains(self.client.get(LIST), "暂无预约记录。")
        due = self.reservation(start=NOW - 2 * HOUR)
        for suffix in ("?equipment=", "?equipment=%20%20", "?equipment=a&equipment=b",
                       "?role=admin", "?equipment=" + "x" * 33, "?equipment=%00"):
            with self.subTest(suffix=suffix), CaptureQueriesContext(connection) as captured:
                self.assertEqual(self.client.get(LIST + suffix).status_code, 400)
                self.assertFalse(any(any(t in entry["sql"] for t in BUSINESS) for entry in captured))
        for code in ("no-such-device", self.first.number.lower(), self.second.number):
            self.assertContains(self.client.get(LIST, {"equipment": code}), "未找到符合筛选条件的预约。")
        self.assertContains(self.client.get(self.detail(2 ** 62)), "预约记录不存在", status_code=404)
        due.refresh_from_db()
        self.assertEqual(due.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_detail_keeps_history_order_actor_identity_and_validated_navigation(self):
        row = self.reservation(status=Status.CANCELLED, start=NOW - 3 * HOUR)
        reason = "实验 <关闭>"
        self.history(row, "cancel", Status.CANCELLED, actor=self.teacher, actor_type="student",
                     before=Status.APPROVED, reason=reason, recorded=NOW + HOUR)
        approve = self.history(row, "approve", Status.APPROVED, actor=self.admin)
        other = self.reservation(self.second, status=Status.REJECTED)
        self.history(other, "reject", Status.REJECTED, actor=self.admin, reason="另一条保密原因")
        with patch.object(services, "_decision_time") as time, CaptureQueriesContext(connection) as captured:
            response = self.client.get(self.detail(row.pk), {"equipment": self.second.number})
        time.assert_not_called()
        self.assertFalse(any("FOR UPDATE" in entry["sql"] for entry in captured))
        self.assertEqual([entry["action"] for entry in response.context["history"]], ["approve", "cancel"])
        self.assertEqual(response.context["history"][0]["id"], approve.pk)
        self.assertEqual(response.context["history"][0]["reason"], "")
        self.assertContains(response, f'href="{LIST}?equipment={self.second.number}"')
        self.assertContains(response, f"学生 · teacher-fixture（账号 ID {self.teacher.pk}）")
        self.assertContains(response, f"业务管理员 · lab-manager（账号 ID {self.admin.pk}）")
        self.assertContains(response, "2026-11-27 00:00")
        self.assertContains(response, "2026-11-26 23:59:57")
        self.assertContains(response, escape(reason))
        self.assertNotContains(response, "另一条保密原因")
        invalid = self.client.get(self.detail(row.pk) + "?equipment=x&equipment=y")
        self.assertContains(invalid, f'href="{LIST}">返回预约管理', status_code=400)
        self.assertNotContains(invalid, escape(reason), status_code=400)
        self.assertEqual(OperationHistory.objects.count(), 3)

    def test_due_detail_expires_once_with_persisted_system_reason(self):
        row = self.reservation(start=NOW - 2 * HOUR)
        path = self.detail(row.pk)
        original = Reservation.objects.values().get(pk=row.pk)
        with patch.object(services, "_decision_time", return_value=NOW) as time:
            for bad in ("?equipment=", "?equipment=%20", "?equipment=a&equipment=b",
                        "?equipment=" + "x" * 33, "?equipment=%00"):
                with self.subTest(input=bad), CaptureQueriesContext(connection) as captured:
                    response = self.client.get(path + bad)
                    self.assertContains(response, "设备编号参数无效。", status_code=400)
                    self.assertNotContains(response, "操作历史", status_code=400)
                    self.assertFalse(any(any(table in entry["sql"] for table in BUSINESS)
                                         or "FOR UPDATE" in entry["sql"] for entry in captured))
                self.assertEqual(Reservation.objects.values().get(pk=row.pk), original)
                self.assertFalse(OperationHistory.objects.filter(reservation=row).exists())
            time.assert_not_called()
            response = self.client.get(path, {"equipment": self.second.number})
            self.assertContains(response, f'href="{LIST}?equipment={self.second.number}">返回预约管理')
            self.assertContains(response, EXPIRY_REASON)
            self.assertContains(response, "<td>系统</td>", html=True)
            self.assertContains(response, "已失效")
            self.assertEqual(Reservation.objects.get(pk=row.pk).status, Status.EXPIRED)
            history = OperationHistory.objects.get(reservation=row)
            with CaptureQueriesContext(connection) as repeated:
                response = self.client.get(path)
            self.assertContains(response, f'href="{LIST}">返回预约管理')
            self.assertContains(response, EXPIRY_REASON)
            self.assertFalse(any("FOR UPDATE" in entry["sql"] or entry["sql"].startswith(("UPDATE ", "INSERT "))
                                 for entry in repeated))
            self.assertEqual(OperationHistory.objects.get(reservation=row).pk, history.pk)
        time.assert_called_once()
        entry = OperationHistory.objects.get(reservation=row)
        self.assertEqual((entry.actor_id, entry.action, entry.decision_at), (None, "expire", NOW))

    def test_list_locks_only_pending_device_ids_once_in_sorted_order(self):
        due_b = self.reservation(self.second, start=NOW - 2 * HOUR)
        self.reservation(self.first, start=NOW - 2 * HOUR)
        self.reservation(self.second, start=NOW + HOUR)
        self.reservation(self.third, status=Status.APPROVED)
        with patch.object(services, "_decision_time", return_value=NOW), \
                patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock:
            response = self.client.get(LIST)
        self.assertContains(response, "全部预约（含历史记录）")
        self.assertEqual([call.args[0] for call in lock.call_args_list], sorted((self.first.pk, self.second.pk)))
        self.assertEqual(OperationHistory.objects.get(reservation=due_b).decision_at, NOW)

    def test_approved_only_filter_has_clock_but_no_lock(self):
        row = self.reservation(status=Status.APPROVED, start=NOW + HOUR)
        with patch.object(services, "_decision_time", return_value=NOW) as time, \
                patch.object(services, "lock_equipment") as lock:
            self.assertEqual(self.record_ids(self.client.get(LIST)), {row.pk})
            time.assert_not_called()
            self.assertEqual(self.record_ids(self.client.get(LIST, {"equipment": self.first.number})), {row.pk})
            time.assert_called_once()
            lock.assert_not_called()

    def test_unauthorized_requests_never_touch_business_tables(self):
        due = self.reservation(start=NOW - 2 * HOUR)
        paths = (LIST, LIST + "?equipment=" + self.second.number, self.detail(due.pk), LIST + "?role=admin",
                 self.detail(due.pk) + "?equipment=a&equipment=b")
        for user, expected in ((None, 302), (self.inactive, 302),
                               (self.student, 403), (self.peer, 403), (self.teacher, 403)):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for path in paths:
                with self.subTest(user=user, path=path), CaptureQueriesContext(connection) as captured:
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, expected)
                    self.assertNotIn(b"Instrument A", response.content)
                    self.assertFalse(any(any(t in entry["sql"] for t in BUSINESS) for entry in captured))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(LIST).status_code, 405)
        due.refresh_from_db()
        self.assertEqual(due.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_stale_effective_role_is_rejected_before_business_scope(self):
        self.reservation(start=NOW - 2 * HOUR)
        User.objects.filter(pk=self.admin.pk).update(role=Role.TEACHER)
        with CaptureQueriesContext(connection) as captured, self.assertRaises(PermissionDenied):
            services.get_admin_reservations(self.admin, self.first.number)
        self.assertTrue(any("accounts_user" in entry["sql"] for entry in captured))
        self.assertFalse(any(any(t in entry["sql"] for t in BUSINESS) for entry in captured))

    def test_late_history_projection_failure_rolls_back_expiry(self):
        row = self.reservation(start=NOW - 2 * HOUR)

        def fail_history(execute, sql, params, many, context):
            if "h.actor_id" in sql and "public.audit_operationhistory" in sql:
                return execute("SELECT nonexistent_column FROM public.audit_operationhistory", [], many, context)
            return execute(sql, params, many, context)

        with patch.object(services, "_decision_time", return_value=NOW), connection.execute_wrapper(fail_history):
            response = self.client.get(self.detail(row.pk))
        self.assertContains(response, READ_FAILED, status_code=503)
        self.assertNotContains(response, "操作历史", status_code=503)
        row.refresh_from_db()
        self.assertEqual(row.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_unknown_and_confirmed_failures_have_distinct_unsuccessful_pages(self):
        row = self.reservation(status=Status.APPROVED)
        for name, path in (("get_admin_reservations", LIST), ("get_admin_reservation", self.detail(row.pk))):
            for failure, message in ((services.ReservationFailed, READ_FAILED),
                                     (services.ReservationUnknown, READ_UNKNOWN)):
                with self.subTest(path=path, failure=failure), patch(f"reservations.views.{name}", side_effect=failure) as call:
                    response = self.client.get(path)
                    call.assert_called_once()
                    self.assertContains(response, message, status_code=503)
                    self.assertNotContains(response, "Instrument A", status_code=503)
