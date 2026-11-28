import re
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.db.models.query import QuerySet
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status


HOUR = timedelta(hours=1)
TICK = timedelta(microseconds=1)
FORM = "application/x-www-form-urlencoded"
REASON = "实验安排调整 <备注>&确认"


class AdminCancellationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="cancel-admin", role=Role.ADMIN)
        cls.disabled = User.objects.create_user(username="cancel-disabled", role=Role.ADMIN, is_active=False)
        cls.student = User.objects.create_user(username="cancel-applicant", role=Role.STUDENT)
        cls.peer = User.objects.create_user(username="cancel-peer", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="cancel-teacher", role=Role.TEACHER)
        cls.flagged = User.objects.create_user(username="cancel-flagged", role=Role.STUDENT,
                                               is_staff=True, is_superuser=True)
        cls.device = Equipment.objects.create(number="设备&A", name="Scope-Private", category="Lab", location="Room")

    def setUp(self):
        self.client.force_login(self.admin)
        with connection.cursor() as cursor:
            cursor.execute("SELECT clock_timestamp()")
            self.at = cursor.fetchone()[0].astimezone(services.BEIJING).replace(minute=0, second=0, microsecond=0)
        self.clock = self.enterContext(patch.object(services, "_decision_time", return_value=self.at))
        self.enterContext(patch("reservations.views.timezone.now", return_value=self.at))

    def reservation(self, *, status=Status.PENDING, start=None):
        start = start if start is not None else self.at.replace(hour=10) + timedelta(days=1)
        return Reservation.objects.create(applicant=self.student, equipment=self.device, status=status,
                                          start_at=start, end_at=start + HOUR, applied_at=start - HOUR)

    @staticmethod
    def url(pk):
        return reverse("admin-reservation-cancel", args=[pk])

    def post_form(self, url, fields, client=None):
        return (client or self.client).post(url, urlencode(fields, doseq=True), content_type=FORM)

    def assert_transition(self, row, before, status, *, action, actor, reason):
        self.assertEqual(Reservation.objects.values().get(pk=row.pk), {**before, "status": status})
        entry = OperationHistory.objects.get(reservation=row)
        self.assertIsNone(entry.equipment_id)
        self.assertEqual((entry.object_type, entry.action, entry.before_status, entry.after_status, entry.actor_type,
                          entry.actor_id, entry.reason, entry.decision_at),
                         (HistoryObject.RESERVATION, action, before["status"], status,
                          "system" if actor is None else "admin", actor, reason, self.at))
        self.assertLessEqual(entry.decision_at, entry.recorded_at)

    def snapshot(self):
        return [list(model.objects.order_by("pk").values()) for model in (Equipment, Reservation, OperationHistory)]

    def test_confirmation_successful_post_and_authorized_history_with_filter(self):
        row = self.reservation()
        before = Reservation.objects.values().get(pk=row.pk)
        listing = reverse("admin-reservation-list")
        detail = reverse("admin-reservation-detail", args=[row.pk])
        url = self.url(row.pk)
        suffix = "?" + urlencode({"equipment": self.device.number})
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertContains(client.get(listing), f'href="{url}"')
        self.assertContains(client.get(listing + suffix), f'href="{url + suffix}"')
        self.assertContains(client.get(detail + suffix), f'href="{url + suffix}"')
        self.clock.reset_mock()
        with CaptureQueriesContext(connection) as queries:
            confirmation = client.get(url + suffix)
        self.clock.assert_not_called()
        self.assertFalse(any("FOR UPDATE" in q["sql"] for q in queries))
        for expected in (self.device.name, self.student.username, "取消原因", f'action="{url + suffix}"',
                         f'href="{listing + suffix}"', f'href="{detail + suffix}"'):
            self.assertContains(confirmation, expected)
        self.assertEqual(Reservation.objects.values().get(pk=row.pk), before)
        self.assertFalse(OperationHistory.objects.exists())

        token = re.search(r'name="csrfmiddlewaretoken" value="([A-Za-z0-9]+)"', confirmation.content.decode())[1]
        response = self.post_form(url + suffix, {"reason": f"  {REASON}　", "csrfmiddlewaretoken": token}, client)
        self.assertContains(response, "预约已取消")
        self.assertNotContains(response, '<form method="post"')
        self.assertContains(response, f'href="{listing + suffix}"')
        self.assertContains(response, f'href="{detail + suffix}"')
        self.assert_transition(row, before, Status.CANCELLED, action="cancel", actor=self.admin.pk, reason=REASON)
        self.assertNotContains(client.get(listing + suffix), self.student.username)
        self.assertContains(client.get(listing), escape(REASON))
        page = client.get(detail + suffix)
        self.assertContains(page, escape(REASON), count=2)
        self.assertContains(page, self.admin.username)
        self.assertNotContains(page, f'href="{url}')
        self.assertNotContains(client.get(url + suffix), '<form method="post"', status_code=409)

        own_list = reverse("reservation-list")
        own_detail = reverse("reservation-result", args=[row.pk])
        occupancy = reverse("equipment-occupancy", args=[self.device.pk]) + "?date=" + row.start_at.date().isoformat()
        client.force_login(self.student)
        for path in (own_detail, own_list):
            result = client.get(path)
            self.assertContains(result, "已取消")
            self.assertContains(result, escape(REASON))
            self.assertNotContains(result, REASON)
            self.assertNotContains(result, self.admin.username)
        self.assertNotContains(client.get(occupancy), escape(REASON))
        client.force_login(self.peer)
        self.assertNotContains(client.get(own_list), escape(REASON))
        self.assertNotContains(client.get(own_detail), escape(REASON), status_code=404)

    def test_pending_cancel_releases_future_slot_and_approved_running_slot_projects_unoccupied(self):
        row = self.reservation()
        start, end = (value.strftime("%Y-%m-%dT%H:%M") for value in (row.start_at, row.end_at))
        submit = services.submit_reservation
        self.assertEqual(submit(self.peer, self.device.pk, start, end).outcome, "conflict")
        self.assertEqual(services.cancel_admin_reservation(self.admin, row.pk, REASON).outcome, "cancelled")
        self.assertEqual(submit(self.peer, self.device.pk, start, end).outcome, "created")

        midday = self.at.replace(hour=12)
        running = self.reservation(status=Status.APPROVED, start=midday - HOUR / 2)
        with patch.object(services, "_decision_time", return_value=midday):
            before = services.get_daily_occupancy(self.student, self.device.pk, running.start_at.date())
            self.assertTrue(any(slot.end_at == running.end_at for slot in before.occupied))
            self.assertEqual(services.cancel_admin_reservation(self.admin, running.pk, REASON).outcome, "cancelled")
            after = services.get_daily_occupancy(self.student, self.device.pk, running.start_at.date())
        self.assertFalse(any(slot.end_at == running.end_at for slot in after.occupied))

    def test_locked_start_end_boundaries_and_device_status(self):
        cases = (
            (Status.PENDING, TICK, EquipmentStatus.AVAILABLE, 200, Status.CANCELLED),
            (Status.PENDING, timedelta(0), EquipmentStatus.MAINTENANCE, 409, Status.EXPIRED),
            (Status.PENDING, -2 * HOUR, EquipmentStatus.DISABLED, 409, Status.EXPIRED),
            (Status.APPROVED, HOUR, EquipmentStatus.AVAILABLE, 200, Status.CANCELLED),
            (Status.APPROVED, timedelta(0), EquipmentStatus.MAINTENANCE, 200, Status.CANCELLED),
            (Status.APPROVED, -HOUR + TICK, EquipmentStatus.DISABLED, 200, Status.CANCELLED),
            (Status.APPROVED, -HOUR, EquipmentStatus.AVAILABLE, 409, Status.APPROVED),
            (Status.APPROVED, -HOUR - TICK, EquipmentStatus.MAINTENANCE, 409, Status.APPROVED),
        )
        sibling = self.reservation(start=self.at - 2 * HOUR)
        for status, offset, device_status, response_code, final in cases:
            with self.subTest(status=status, offset=offset, device_status=device_status):
                Equipment.objects.filter(pk=self.device.pk).update(status=device_status)
                row = self.reservation(status=status, start=self.at + offset)
                before = Reservation.objects.values().get(pk=row.pk)
                self.clock.reset_mock()
                response = self.post_form(self.url(row.pk), {"reason": REASON})
                self.assertEqual(response.status_code, response_code)
                self.clock.assert_called_once_with(connection)
                if final == Status.CANCELLED:
                    self.assert_transition(row, before, final, action="cancel", actor=self.admin.pk, reason=REASON)
                elif final == Status.EXPIRED:
                    self.assertContains(response, "已失效，未执行取消", status_code=409)
                    self.assert_transition(row, before, final, action="expire", actor=None, reason=EXPIRY_REASON)
                else:
                    self.assertContains(response, "结束时间已到", status_code=409)
                    self.assertNotContains(self.client.get(self.url(row.pk)), '<form method="post"', status_code=409)
                    self.assertEqual(Reservation.objects.values().get(pk=row.pk), before)
                    self.assertFalse(OperationHistory.objects.filter(reservation=row).exists())
                self.assertEqual(Equipment.objects.get(pk=self.device.pk).status, device_status)
        self.assertEqual(Reservation.objects.get(pk=sibling.pk).status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.filter(reservation=sibling).exists())

    def test_blank_reason_preserves_legal_expiry_without_rendering_stale_form(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        candidate = self.reservation()
        confirmation = client.get(self.url(candidate.pk))
        self.assertContains(confirmation, "取消原因")
        token = re.search(r'name="csrfmiddlewaretoken" value="([A-Za-z0-9]+)"', confirmation.content.decode())[1]
        for fields in ({}, {"reason": ""}, {"reason": " \t\n　"}):
            for start in (self.at + HOUR, self.at, self.at - HOUR):
                with self.subTest(fields=fields, start=start):
                    row = self.reservation(start=start)
                    before = Reservation.objects.values().get(pk=row.pk)
                    # With no reason, a native submission still carries the confirmation form's CSRF field.
                    response = self.post_form(self.url(row.pk), {**fields, "csrfmiddlewaretoken": token}, client)
                    self.assertContains(response, "请输入取消原因", status_code=400)
                    if start > self.at:
                        self.assertContains(response, '<form method="post"', status_code=400)
                        self.assertEqual(Reservation.objects.values().get(pk=row.pk), before)
                        self.assertFalse(OperationHistory.objects.filter(reservation=row).exists())
                    else:
                        self.assertContains(response, "已失效，未执行取消", status_code=400)
                        self.assertNotContains(response, '<form method="post"', status_code=400)
                        self.assert_transition(row, before, Status.EXPIRED, action="expire", actor=None, reason=EXPIRY_REASON)

    def test_confirmation_never_expires_due_target_and_terminal_or_missing_never_changes(self):
        due = self.reservation(start=self.at - 2 * HOUR)
        before = self.snapshot()
        self.assertNotContains(self.client.get(self.url(due.pk)), '<form method="post"', status_code=409)
        self.clock.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        for status in (Status.REJECTED, Status.CANCELLED, Status.EXPIRED):
            row = self.reservation(status=status)
            before = self.snapshot()
            self.assertNotContains(self.client.get(self.url(row.pk)), '<form method="post"', status_code=409)
            self.assertContains(self.post_form(self.url(row.pk), {"reason": REASON}), "不允许取消", status_code=409)
            self.assertEqual(self.snapshot(), before)
        before = self.snapshot()
        missing = self.url(2 ** 62)
        self.assertEqual(self.client.get(missing).status_code, 404)
        self.assertEqual(self.post_form(missing, {"reason": REASON}).status_code, 404)
        self.assertEqual(self.snapshot(), before)

    def test_permissions_and_csrf_fail_before_target_access_or_expiry(self):
        due = self.reservation(start=self.at)
        before = self.snapshot()
        client = Client(enforce_csrf_checks=True)
        scenarios = ((None, "valid", 302), (self.student, "valid", 403), (self.teacher, "valid", 403),
                     (self.flagged, "valid", 403), (self.disabled, "valid", 302),
                     (self.admin, "missing", 403), (self.admin, "invalid", 403))
        for actor, csrf, expected in scenarios:
            client.logout()
            if actor:
                client.force_login(actor)
            client.get(reverse("login"))
            for pk in (due.pk, 2 ** 62):
                with self.subTest(actor=actor, csrf=csrf, pk=pk):
                    path = self.url(pk)
                    fields = {"reason": REASON}
                    if csrf != "missing":
                        fields["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value if csrf == "valid" else "invalid"
                    with CaptureQueriesContext(connection) as queries:
                        response = self.post_form(path, fields, client)
                        self.assertEqual(response.status_code, expected)
                        if actor != self.admin:
                            self.assertEqual(client.get(path).status_code, expected)
                    for private in (self.device.name, self.student.username, escape(REASON)):
                        self.assertNotContains(response, private, status_code=expected)
                    self.assertFalse(any('"reservations_reservation"' in q["sql"] for q in queries))
                    self.assertEqual(self.snapshot(), before)
        self.clock.assert_not_called()

    def test_stale_admin_role_denied_before_target_access(self):
        row = self.reservation(start=self.at)
        before = self.snapshot()
        User.objects.filter(pk=self.admin.pk).update(role=Role.STUDENT)
        for operation in (lambda: services.cancel_admin_reservation(self.admin, row.pk, REASON),
                          lambda: services.get_admin_cancellation_candidate(self.admin, row.pk)):
            with CaptureQueriesContext(connection) as queries, self.assertRaises(PermissionDenied):
                operation()
            self.assertFalse(any('"reservations_reservation"' in q["sql"] for q in queries))
        self.clock.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_malformed_submissions_and_methods_do_not_expire_target(self):
        row = self.reservation(start=self.at)
        before = self.snapshot()
        for pk in (row.pk, 2 ** 62):
            path = self.url(pk)
            with patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock:
                for fields in ({"reason": "含\0字符"}, {"reason": ["甲", "乙"]}, {"actor_id": self.admin.pk},
                               {"next": "https://example.com"}, {"status": Status.APPROVED},
                               {"csrfmiddlewaretoken": ["a", "b"]}):
                    self.assertEqual(self.post_form(path, fields).status_code, 400)
                for body in ("reason=%", "reason=%C3%28", "reason", "&reason=", "=reason"):
                    self.assertEqual(self.client.post(path, body, content_type=FORM).status_code, 400)
                self.assertEqual(self.client.post(path, '{"reason":""}', content_type="application/json").status_code, 400)
                self.assertEqual(self.client.post(path, {"reason": "", "file": SimpleUploadedFile("x.txt", b"x")}).status_code, 400)
                for query in ("?next=https://example.com", "?equipment=X&equipment=Y", "?equipment="):
                    self.assertEqual(self.post_form(path + query, {"reason": REASON}).status_code, 400)
                self.assertEqual(self.client.put(path, "reason=", content_type=FORM).status_code, 405)
                lock.assert_not_called()
        self.clock.assert_not_called()
        self.assertEqual(self.snapshot(), before)

        future = self.reservation()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        query = urlencode({"equipment": self.device.number})
        path = self.url(future.pk)
        confirmation = client.get(path + "?" + query)
        self.assertContains(confirmation, f'action="{path}?{query}"')
        token = re.search(r'name="csrfmiddlewaretoken" value="([A-Za-z0-9]+)"', confirmation.content.decode())[1]

        def post_raw(target_path, raw_query, fields):
            body = urlencode({"csrfmiddlewaretoken": token, **fields})
            return client.post(target_path, body, content_type=FORM, QUERY_STRING=raw_query)

        def business_snapshot():
            devices, reservations, history = self.snapshot()
            occupied = [entry["id"] for entry in reservations if entry["end_at"] > self.at and (
                entry["status"] == Status.APPROVED
                or (entry["status"] == Status.PENDING and entry["start_at"] > self.at)
            )]
            return devices, reservations, history, occupied

        before = business_snapshot()
        with patch.object(services, "lock_equipment", wraps=services.lock_equipment) as lock:
            for pk in (future.pk, row.pk):
                for raw_query in ("equipment=%", "equipment=%2", "equipment=%GG", "equipment=%FF",
                                  "equipment=%C3%28", "equipment=\xff", "equip%ment=private"):
                    with self.subTest(pk=pk, raw_query=raw_query):
                        with CaptureQueriesContext(connection) as captured:
                            responses = (client.get(self.url(pk), QUERY_STRING=raw_query),
                                         post_raw(self.url(pk), raw_query, {"reason": REASON}))
                        for response in responses:
                            self.assertContains(response, "设备编号参数无效。", status_code=400)
                            for private in (self.device.name, self.student.username, REASON, '<form method="post"'):
                                self.assertNotContains(response, private, status_code=400)
                            self.assertNotIn("Location", response)
                        self.assertFalse(any(any(table in item["sql"] for table in (
                            '"reservations_reservation"', '"equipment_equipment"', '"audit_operationhistory"', "FOR UPDATE",
                        )) for item in captured))
                        self.assertEqual(business_snapshot(), before)
            lock.assert_not_called()
        self.clock.assert_not_called()

        self.assertContains(post_raw(path, "", {}), "请输入取消原因", status_code=400)
        self.assertEqual(business_snapshot(), before)
        due_before = Reservation.objects.values().get(pk=row.pk)
        expired = post_raw(self.url(row.pk), query, {"reason": " \t　"})
        self.assertContains(expired, "请输入取消原因", status_code=400)
        self.assertContains(expired, "已失效，未执行取消", status_code=400)
        self.assert_transition(row, due_before, Status.EXPIRED, action="expire", actor=None, reason=EXPIRY_REASON)
        future_before = Reservation.objects.values().get(pk=future.pk)
        cancelled = post_raw(path, query, {"reason": REASON})
        self.assertContains(cancelled, "预约已取消")
        self.assertContains(cancelled, f'href="{reverse("admin-reservation-list")}?{query}"')
        self.assert_transition(future, future_before, Status.CANCELLED, action="cancel", actor=self.admin.pk, reason=REASON)

    def test_history_or_status_failure_rolls_back_and_unknown_displays_no_submit_form(self):
        future, due = self.reservation(), self.reservation(start=self.at)
        before = self.snapshot()
        for row, method in ((future, "append_admin_reservation_cancellation"), (due, "append_reservation_expiry")):
            append = getattr(services, method)

            def append_then_fail(*args):
                append(*args)
                raise IntegrityError("injected audit failure")

            with patch.object(services, method, side_effect=append_then_fail):
                self.assertContains(self.post_form(self.url(row.pk), {"reason": REASON}), "已回滚", status_code=503)
            self.assertEqual(self.snapshot(), before)
        update = QuerySet.update

        def fail_update(queryset, **kwargs):
            if queryset.model is Reservation:
                raise IntegrityError("injected status failure")
            return update(queryset, **kwargs)

        with patch.object(QuerySet, "update", fail_update):
            self.assertContains(self.post_form(self.url(future.pk), {"reason": REASON}), "已回滚", status_code=503)
        self.assertEqual(self.snapshot(), before)
        with patch("reservations.views.cancel_admin_reservation", side_effect=services.ReservationUnknown) as cancel:
            result = self.post_form(self.url(future.pk), {"reason": REASON})
        cancel.assert_called_once()
        self.assertContains(result, "结果待核查，请勿重复提交", status_code=503)
        self.assertNotContains(result, '<form method="post"', status_code=503)
