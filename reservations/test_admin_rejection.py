import re
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status


NOW = datetime(2026, 11, 26, 16, tzinfo=UTC)
HOUR = timedelta(hours=1)


class AdminRejectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="reject-admin", role=Role.ADMIN)
        cls.student = User.objects.create_user(username="reject-student", role=Role.STUDENT)
        cls.staff = User.objects.create_user(username="reject-staff", role=Role.TEACHER,
                                             is_staff=True, is_superuser=True)
        cls.equipment = Equipment.objects.create(number="设备&A", name="Instrument", category="Lab",
                                                  location="Room", status=EquipmentStatus.AVAILABLE)

    def setUp(self):
        self.client.force_login(self.admin)
        self.clock = self.enterContext(patch.object(services, "_decision_time", return_value=NOW))

    def reservation(self, *, status=Status.PENDING, start=NOW + HOUR):
        return Reservation.objects.create(applicant=self.student, equipment=self.equipment, status=status,
                                          start_at=start, end_at=start + HOUR, applied_at=NOW - HOUR)

    @staticmethod
    def reject_url(pk):
        return reverse("admin-reservation-reject", args=[pk])

    @staticmethod
    def detail_url(pk):
        return reverse("admin-reservation-detail", args=[pk])

    @staticmethod
    def database_time():
        with connection.cursor() as cursor:
            cursor.execute("SELECT clock_timestamp()")
            return cursor.fetchone()[0]

    def assert_recording_time(self, entry, before, after):
        self.assertLessEqual(before, entry.recorded_at)
        self.assertLessEqual(entry.recorded_at, after)
        self.assertLessEqual(entry.decision_at, entry.recorded_at)

    def test_rendered_csrf_form_rejects_and_shows_reason_to_applicant(self):
        target = self.reservation()
        unrelated = self.reservation(start=NOW - HOUR)
        before = Reservation.objects.values().get(pk=target.pk)
        path = self.reject_url(target.pk)
        suffix = "?equipment=%E8%AE%BE%E5%A4%87%26A"
        detail = self.detail_url(target.pk) + suffix
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        page = client.get(detail)
        self.assertContains(page, f'action="{path}{suffix}"')
        token = re.search(r'name="csrfmiddlewaretoken" value="([A-Za-z0-9]+)"', page.content.decode())[1]
        self.assertEqual(client.post(path, {"reason": "拒绝原因"}).status_code, 403)
        self.assertEqual(client.get(path).status_code, 405)
        self.assertEqual(Reservation.objects.values().get(pk=target.pk), before)

        reason = "实验计划调整 <备注>"
        body = urlencode({"reason": f"  {reason}  ", "csrfmiddlewaretoken": token})
        before_recording = self.database_time()
        response = client.post(path + suffix, body, content_type="application/x-www-form-urlencoded")
        after_recording = self.database_time()
        self.assertRedirects(response, detail, fetch_redirect_response=False)
        self.assertEqual(Reservation.objects.values().get(pk=target.pk), {**before, "status": Status.REJECTED})
        unrelated.refresh_from_db()
        self.assertEqual(unrelated.status, Status.PENDING)
        entry = OperationHistory.objects.get()
        self.assertIsNone(entry.equipment_id)
        self.assert_recording_time(entry, before_recording, after_recording)
        self.assertEqual(
            (entry.object_type, entry.reservation_id, entry.action, entry.before_status, entry.after_status,
             entry.actor_type, entry.actor_id, entry.reason, entry.decision_at),
            (HistoryObject.RESERVATION, target.pk, "reject", Status.PENDING, Status.REJECTED,
             "admin", self.admin.pk, reason, NOW),
        )
        managed = client.get(detail)
        self.assertContains(managed, "已拒绝")
        self.assertContains(managed, escape(reason))
        self.assertNotContains(managed, f'action="{path}')
        self.assertContains(client.post(path, {"reason": "重复提交", "csrfmiddlewaretoken": token}),
                            "只有待审核的预约可以拒绝", status_code=409)
        self.assertEqual(OperationHistory.objects.count(), 1)

        client.force_login(self.student)
        result = client.get(reverse("reservation-result", args=[target.pk]))
        self.assertContains(result, "已拒绝")
        self.assertContains(result, escape(reason))
        self.assertNotContains(result, reason)
        self.assertContains(client.get(reverse("reservation-list")), escape(reason))
        client.force_login(self.staff)
        self.assertNotContains(client.get(reverse("reservation-list")), escape(reason))
        self.assertNotContains(client.get(reverse("reservation-result", args=[target.pk])),
                               escape(reason), status_code=404)

    def test_rejection_releases_slot_for_new_request(self):
        target = self.reservation()
        start = target.start_at.astimezone(services.BEIJING).strftime("%Y-%m-%dT%H:%M")
        end = target.end_at.astimezone(services.BEIJING).strftime("%Y-%m-%dT%H:%M")
        submit = services.submit_reservation
        self.assertEqual(submit(self.student, self.equipment.pk, start, end).outcome, "conflict")
        self.assertEqual(services.reject_reservation(self.admin, target.pk, "计划调整"), "rejected")
        self.assertEqual(submit(self.student, self.equipment.pk, start, end).outcome, "created")

    def test_invalid_payload_neither_rejects_nor_expires(self):
        target = self.reservation(start=NOW)
        path = self.reject_url(target.pk)
        with patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock:
            for fields in ({"reason": "含\0控制字符"}, {"reason": ["甲", "乙"]},
                           {"reason": "有效", "status": "approved"},
                           {"reason": "", "actor_id": self.admin.pk},
                           {"reason": "有效", "upload": SimpleUploadedFile("forged.txt", b"forged")}):
                with self.subTest(fields=fields):
                    self.assertEqual(self.client.post(path, fields).status_code, 400)
            self.assertEqual(self.client.post(path + "?reason=伪造", {"reason": "有效"}).status_code, 400)
            self.assertEqual(self.client.post(path, '{"reason":""}', content_type="application/json").status_code, 400)
        lock.assert_not_called()
        self.clock.assert_not_called()
        target.refresh_from_db()
        self.assertEqual(target.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_blank_reason_uses_locked_decision_for_future_and_due_targets(self):
        sibling = self.reservation(start=NOW - HOUR)
        sibling_before = Reservation.objects.values().get(pk=sibling.pk)
        for reason in ({}, {"reason": " \t\n　"}):
            for offset in (HOUR, timedelta(0), -HOUR):
                with self.subTest(reason=reason, start_offset=offset):
                    target = self.reservation(start=NOW + offset)
                    before = Reservation.objects.values().get(pk=target.pk)
                    self.clock.reset_mock()
                    with patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock:
                        def time_after_lock(conn):
                            lock.assert_called_once_with(self.equipment.pk)
                            return NOW

                        self.clock.side_effect = time_after_lock
                        earliest = self.database_time()
                        response = self.client.post(self.reject_url(target.pk), reason)
                        latest = self.database_time()
                        self.clock.assert_called_once_with(connection)
                    history = OperationHistory.objects.filter(reservation=target)
                    if offset > timedelta(0):
                        self.assertContains(response, "请输入拒绝原因", status_code=400)
                        self.assertEqual(Reservation.objects.values().get(pk=target.pk), before)
                        self.assertFalse(history.exists())
                    else:
                        self.assertContains(response, "该待审核预约已失效，未执行拒绝", status_code=409)
                        self.assertEqual(Reservation.objects.values().get(pk=target.pk), {**before, "status": Status.EXPIRED})
                        entry = history.get()
                        self.assertEqual((entry.object_type, entry.equipment_id, entry.action, entry.actor_type,
                                          entry.actor_id, entry.reason, entry.before_status, entry.after_status,
                                          entry.decision_at),
                                         (HistoryObject.RESERVATION, None, "expire", "system", None,
                                          "开始时间已到仍待审核", Status.PENDING, Status.EXPIRED, NOW))
                        self.assert_recording_time(entry, earliest, latest)
                    self.assertEqual(Reservation.objects.values().get(pk=sibling.pk), sibling_before)
                    self.assertFalse(OperationHistory.objects.filter(reservation=sibling).exists())

    def test_due_target_is_not_read_or_expired_on_authorization_or_csrf_failure(self):
        target = self.reservation(start=NOW)
        before = Reservation.objects.values().get(pk=target.pk)
        client = Client(enforce_csrf_checks=True)
        path = self.reject_url(target.pk)
        detail = self.detail_url(target.pk)
        for actor, csrf, status in ((None, "valid", 302), (self.student, "valid", 403),
                                    (self.staff, "valid", 403), (self.admin, "missing", 403),
                                    (self.admin, "invalid", 403)):
            with self.subTest(actor=actor, csrf=csrf):
                client.logout()
                if actor:
                    client.force_login(actor)
                client.get(reverse("login"))
                fields = {"reason": "私密原因"}
                if csrf != "missing":
                    fields["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value if csrf == "valid" else "invalid"
                with patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock, \
                        CaptureQueriesContext(connection) as captured:
                    response = client.post(path, fields)
                self.assertEqual(response.status_code, status)
                if status == 302:
                    self.assertRedirects(response, reverse("login") + "?next=" + path, fetch_redirect_response=False)
                for private in (detail, self.equipment.name, self.student.username, "私密原因"):
                    self.assertNotContains(response, private, status_code=status)
                lock.assert_not_called()
                self.assertFalse(any('"reservations_reservation"' in entry["sql"] for entry in captured))
                self.clock.assert_not_called()
                self.assertEqual(Reservation.objects.values().get(pk=target.pk), before)
                self.assertFalse(OperationHistory.objects.exists())

    def test_permissions_do_not_rely_on_django_staff_or_cached_admin_role(self):
        target = self.reservation()
        path = self.reject_url(target.pk)
        self.client.logout()
        self.assertEqual(self.client.post(path, {"reason": "有效"}).status_code, 302)
        for user in (self.student, self.staff):
            self.client.force_login(user)
            self.assertEqual(self.client.post(path, {"reason": "有效"}).status_code, 403)
        User.objects.filter(pk=self.admin.pk).update(is_active=False)
        with CaptureQueriesContext(connection) as captured, self.assertRaises(PermissionDenied):
            services.reject_reservation(self.admin, target.pk, "有效")
        self.assertFalse(any('"reservations_reservation"' in entry["sql"] for entry in captured))
        target.refresh_from_db()
        self.assertEqual(target.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_decision_at_start_expires_only_target_and_never_records_a_rejection(self):
        target = self.reservation(start=NOW)
        other = self.reservation(start=NOW - HOUR)
        path = self.reject_url(target.pk)

        def time_after_lock(conn):
            lock.assert_called_once_with(self.equipment.pk)
            return NOW

        with patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock:
            self.clock.side_effect = time_after_lock
            response = self.client.post(path, {"reason": "不会保存"})
        self.assertContains(response, "该待审核预约已失效，未执行拒绝", status_code=409)
        target.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual((target.status, other.status), (Status.EXPIRED, Status.PENDING))
        entry = OperationHistory.objects.get()
        self.assertEqual((entry.reservation_id, entry.action, entry.actor_id, entry.decision_at),
                         (target.pk, "expire", None, NOW))
        self.assertEqual(self.client.post(path, {"reason": "重复提交"}).status_code, 409)
        self.assertEqual(OperationHistory.objects.count(), 1)

    def test_missing_and_non_pending_states_are_never_changed(self):
        self.assertEqual(self.client.post(self.reject_url(2 ** 62), {"reason": "有效"}).status_code, 404)
        self.clock.assert_not_called()
        for status in (Status.APPROVED, Status.REJECTED, Status.CANCELLED, Status.EXPIRED):
            with self.subTest(status=status):
                target = self.reservation(status=status)
                before = Reservation.objects.values().get(pk=target.pk)
                self.clock.reset_mock()
                with CaptureQueriesContext(connection) as captured:
                    response = self.client.post(self.reject_url(target.pk), {"reason": "有效"})
                self.assertContains(response, "只有待审核的预约可以拒绝", status_code=409)
                self.clock.assert_called_once_with(connection)
                self.assertTrue(any("FOR UPDATE" in entry["sql"] for entry in captured))
                target.refresh_from_db()
                self.assertEqual(Reservation.objects.values().get(pk=target.pk), before)
        self.assertFalse(OperationHistory.objects.exists())

    def test_history_failure_rolls_back_status_and_does_not_report_success(self):
        target = self.reservation()
        path = self.reject_url(target.pk)

        def append_then_fail(*args):
            self.assertEqual(Reservation.objects.get(pk=target.pk).status, Status.REJECTED)
            append(*args)
            raise IntegrityError("simulated audit failure")

        append = services.append_reservation_rejection
        with patch.object(services, "append_reservation_rejection", side_effect=append_then_fail):
            response = self.client.post(path, {"reason": "有效"})
        self.assertContains(response, "数据库事务已回滚", status_code=503)
        target.refresh_from_db()
        self.assertEqual(target.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

        with patch("reservations.views.reject_reservation", side_effect=services.ReservationUnknown):
            response = self.client.post(path, {"reason": "有效"})
        self.assertContains(response, "拒绝结果待核查，请勿重复提交", status_code=503)
        self.assertNotContains(response, '<form method="post"', status_code=503)
