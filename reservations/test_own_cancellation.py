import re
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import patch
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.db import connection, connections
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status


FORM_MEDIA_TYPE = "application/x-www-form-urlencoded"


class UnreadableConfirmationBody(BytesIO):
    def read(self, size=-1):
        raise OSError("fixture body stream failed")


class OwnCancellationTests(TestCase):
    start = datetime(2026, 12, 1, 10, tzinfo=services.BEIJING)
    before = start - timedelta(microseconds=1)

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(username="s24-student", role=Role.STUDENT)
        cls.peer = User.objects.create_user(username="s24-peer", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="s24-teacher", role=Role.TEACHER)
        cls.admin = User.objects.create_superuser(username="s24-admin", role=Role.ADMIN, password="s24-fixture")
        cls.device = Equipment.objects.create(number="S24", name="<private device>", category="test", location="lab")

    def row(self, *, owner=None, status=Status.PENDING, start=None):
        start = start or self.start
        return Reservation.objects.create(applicant=owner or self.student, equipment=self.device, status=status,
                                          start_at=start, end_at=start + timedelta(hours=1),
                                          applied_at=start - timedelta(days=1))

    @staticmethod
    def path(row):
        return reverse("reservation-cancel", args=[row.pk])

    def confirmation_token(self, client, row):
        confirmation = client.get(self.path(row))
        self.assertEqual(confirmation.status_code, 200)
        field = re.search(rb'name="csrfmiddlewaretoken" value="([A-Za-z0-9]+)"', confirmation.content)
        self.assertIsNotNone(field)
        return field[1].decode("ascii")

    @staticmethod
    def post_confirmation(client, path, token="A" * 64):
        # The default placeholder is for tests that use Django's non-enforcing client.
        return client.post(path, urlencode({"csrfmiddlewaretoken": token}), content_type=FORM_MEDIA_TYPE)

    def action(self, row, instant):
        with patch.object(services, "_decision_time", return_value=instant) as clock:
            result = services.cancel_own_reservation(row.applicant, row.pk)
            clock.assert_called_once_with(connections["default"])
        row.refresh_from_db()
        return result.outcome

    def test_legal_cancellation_retains_record_and_history_and_releases_slot(self):
        for owner in (self.student, self.teacher):
            for status in (Status.PENDING, Status.APPROVED):
                with self.subTest(owner=owner.role, status=status):
                    row = self.row(owner=owner, status=status, start=self.start + timedelta(days=Reservation.objects.count()))
                    original = Reservation.objects.values().get(pk=row.pk)
                    old = OperationHistory.objects.create(
                        reservation=row, object_type=HistoryObject.RESERVATION, action="approve",
                        before_status=Status.PENDING, after_status=status, actor_type="admin", actor=self.admin,
                        decision_at=self.before, recorded_at=self.before, reason="既有历史",
                    )
                    old_before = OperationHistory.objects.values().get(pk=old.pk)
                    with patch.object(services, "_decision_time", return_value=self.before):
                        request = (self.peer, self.device.pk, *_window(row))
                        self.assertEqual(services.submit_reservation(*request).outcome, "conflict")
                        self.assertEqual(self.action(row, self.before), "cancelled")
                        self.assertEqual(services.submit_reservation(*request).outcome, "created")
                    self.assertEqual(Reservation.objects.values().get(pk=row.pk), {**original, "status": Status.CANCELLED})
                    self.assertEqual(OperationHistory.objects.values().get(pk=old.pk), old_before)
                    audit = OperationHistory.objects.exclude(pk=old.pk).get(reservation=row)
                    self.assertEqual((audit.object_type, audit.equipment_id, audit.action, audit.actor_type, audit.actor_id,
                                      audit.before_status, audit.after_status, audit.reason, audit.decision_at),
                                     (HistoryObject.RESERVATION, None, "cancel", "applicant", owner.pk,
                                      status, Status.CANCELLED, "", self.before))
                    self.assertNotEqual(audit.recorded_at, audit.decision_at)

    def test_locked_status_and_exact_start_boundary(self):
        timings = (self.before, self.start, self.start + timedelta(microseconds=1))
        for status in Status.values:
            for instant in timings:
                with self.subTest(status=status, instant=instant):
                    row = self.row(status=status)
                    if status not in (Status.PENDING, Status.APPROVED):
                        expected = ("terminal", status, 0)
                    elif instant < self.start:
                        expected = ("cancelled", Status.CANCELLED, 1)
                    elif status == Status.PENDING:
                        expected = ("expired", Status.EXPIRED, 1)
                    else:
                        expected = ("started", Status.APPROVED, 0)
                    outcome = self.action(row, instant)
                    self.assertEqual((outcome, row.status, OperationHistory.objects.filter(reservation=row).count()), expected)
        for state in (EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED):
            Equipment.objects.filter(pk=self.device.pk).update(status=state)
            self.assertEqual(self.action(self.row(status=Status.APPROVED), self.before), "cancelled")
            self.assertEqual(self.action(self.row(status=Status.APPROVED), self.start), "started")

    def test_elapsed_pending_expiry_is_target_only_and_repeat_does_not_write(self):
        due = self.row(start=self.start - timedelta(hours=2))
        unrelated = [self.row(owner=user) for user in (self.student, self.peer)]
        self.assertEqual(self.action(due, self.start), "expired")
        history = OperationHistory.objects.get(reservation=due)
        self.assertEqual((history.action, history.actor_type, history.actor_id, history.reason, history.decision_at),
                         ("expire", "system", None, EXPIRY_REASON, self.start))
        self.assertEqual(self.action(due, self.start), "terminal")
        self.assertEqual(OperationHistory.objects.filter(reservation=due).count(), 1)
        self.assertEqual(list(Reservation.objects.filter(pk__in=[row.pk for row in unrelated])
                              .values_list("status", flat=True)), [Status.PENDING, Status.PENDING])

    def test_confirmation_is_read_only_and_exposes_actions_only_for_candidates(self):
        self.client.force_login(self.student)
        due = self.row()
        approved = self.row(status=Status.APPROVED)
        terminal = self.row(status=Status.CANCELLED)
        with patch.object(services, "_decision_time") as clock, CaptureQueriesContext(connection) as sql:
            confirmation = self.client.get(self.path(due))
            clock.assert_not_called()
        self.assertContains(confirmation, "确认取消")
        self.assertContains(confirmation, "不取消，返回详情")
        self.assertContains(confirmation, "&lt;private device&gt;")
        self.assertIn("no-store", confirmation.headers["Cache-Control"])
        self.assertFalse(any("FOR UPDATE" in item["sql"] or item["sql"].startswith(("UPDATE", "INSERT", "DELETE")) for item in sql))
        due.refresh_from_db()
        self.assertEqual(due.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())
        self.assertNotContains(self.client.get(self.path(terminal)), "<form")
        with patch.object(services, "_decision_time", return_value=self.before):
            listing = self.client.get(reverse("reservation-list"))
            detail = self.client.get(reverse("reservation-result", args=[approved.pk]))
        for response in (listing, detail):
            self.assertContains(response, f'href="{self.path(approved)}"')
            self.assertNotContains(response, self.path(terminal))

    def test_request_guards_and_same_shape_missing_responses(self):
        row = self.row()
        path = self.path(row)
        missing = reverse("reservation-cancel", args=[row.pk + 10**6])
        self.assertEqual(self.client.get(path).status_code, 302)
        self.assertEqual(self.post_confirmation(self.client, path).status_code, 302)
        for role, account in ((Role.ADMIN, self.admin), (Role.STUDENT, self.peer), (Role.TEACHER, self.teacher)):
            self.client.force_login(account)
            for method in ("GET", "POST"):
                with self.subTest(role=role, method=method):
                    if method == "GET":
                        match, absent = self.client.get(path), self.client.get(missing)
                    else:
                        match, absent = (self.post_confirmation(self.client, candidate) for candidate in (path, missing))
                    self.assertEqual(match.status_code, 403 if role == Role.ADMIN else 404)
                    self.assertEqual(match.content, absent.content)
                    self.assertNotIn(b"private device", match.content)
                    self.assertNotIn(path.encode(), match.content)
        self.client.force_login(self.student)
        for response in (
            self.client.post(path, {"applicant_id": self.peer.pk}),
            self.client.post(path, "csrfmiddlewaretoken=a&csrfmiddlewaretoken=b",
                             content_type=FORM_MEDIA_TYPE),
            self.client.post(path, {"status": "approved"}, content_type="application/json"),
            self.client.get(path + "?role=teacher"),
            self.client.put(path),
            self.client.head(path),
        ):
            self.assertIn(response.status_code, (400, 405))
        row.refresh_from_db()
        self.assertEqual(row.status, Status.PENDING)
        self.assertFalse(OperationHistory.objects.exists())

    def test_csrf_and_expiry_and_retry_feedback(self):
        row = self.row()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        token = self.confirmation_token(client, row)
        path = self.path(row)
        self.assertEqual(client.post(path, b"", content_type=FORM_MEDIA_TYPE).status_code, 403)
        self.assertEqual(self.post_confirmation(client, path, "bad").status_code, 403)
        with patch.object(services, "_decision_time", return_value=self.start):
            first = self.post_confirmation(client, path, token)
            again = self.post_confirmation(client, path, token)
        self.assertContains(first, "该待审核预约已失效", status_code=409)
        self.assertContains(again, "预约当前状态不允许取消", status_code=409)
        self.assertNotContains(first, "<form", status_code=409)
        self.assertEqual(OperationHistory.objects.filter(reservation=row, action="expire").count(), 1)

    def test_m01_rejects_non_native_or_incomplete_forms_before_business_queries(self):
        due, future = (self.row(start=self.start + timedelta(hours=offset)) for offset in (-2, 1))
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        token = self.confirmation_token(client, future)
        payload = urlencode({"csrfmiddlewaretoken": token}).encode("ascii")
        headers = {"X-CSRFToken": token}
        multipart = "multipart/form-data; boundary=story24"
        named_part = (b'--story24\r\nContent-Disposition: form-data; name="csrfmiddlewaretoken"\r\n\r\n'
                      + token.encode("ascii") + b"\r\n--story24--\r\n")
        nameless_part = b"--story24\r\nContent-Disposition: form-data\r\n\r\nignored\r\n--story24--\r\n"

        def snapshot():
            return (list(Reservation.objects.order_by("pk").values()),
                    list(Equipment.objects.order_by("pk").values()),
                    list(Reservation.objects.filter(status=Status.PENDING, start_at__gt=self.start)
                         .order_by("pk").values_list("pk", flat=True)),
                    list(OperationHistory.objects.order_by("pk").values()))

        before = snapshot()
        self.assertEqual(before[2], [future.pk])
        for row in (due, future):
            for case, body, media, extra in (
                ("multipart", named_part, multipart, {}),
                ("nameless multipart", nameless_part, multipart, {}),
                ("nonform media type", payload, "text/plain", {}),
                ("header only", b"", FORM_MEDIA_TYPE, {"CONTENT_TYPE": FORM_MEDIA_TYPE, "CONTENT_LENGTH": "0"}),
                ("empty token", b"csrfmiddlewaretoken=", FORM_MEDIA_TYPE, {}),
                ("missing delimiter", b"csrfmiddlewaretoken", FORM_MEDIA_TYPE, {}),
                ("extra field", payload + b"&status=approved", FORM_MEDIA_TYPE, {}),
                ("duplicate token", payload + b"&" + payload, FORM_MEDIA_TYPE, {}),
                ("trailing separator", payload + b"&", FORM_MEDIA_TYPE, {}),
                ("bad percent escape", b"%G0" + payload, FORM_MEDIA_TYPE, {}),
                ("incomplete percent escape", b"%6", FORM_MEDIA_TYPE, {}),
                ("no length", payload, FORM_MEDIA_TYPE, {"CONTENT_LENGTH": ""}),
                ("short body", payload, FORM_MEDIA_TYPE,
                 {"CONTENT_LENGTH": str(len(payload) + 1), "wsgi.input": BytesIO(payload)}),
                ("unreadable body", payload, FORM_MEDIA_TYPE, {"wsgi.input": UnreadableConfirmationBody(payload)}),
            ):
                with self.subTest(target=row.pk, case=case):
                    with (
                        patch("reservations.views.cancel_own_reservation", wraps=services.cancel_own_reservation) as cancel,
                        patch.object(services, "_decision_time", return_value=self.start) as clock,
                        CaptureQueriesContext(connection) as queries,
                    ):
                        response = client.post(self.path(row), body, content_type=media, headers=headers, **extra)
                    self.assertContains(response, "取消预约请求格式无效。", status_code=400)
                    cancel.assert_not_called()
                    clock.assert_not_called()
                    self.assertFalse(any(marker in query["sql"] for query in queries for marker in (
                        "reservations_reservation", "equipment_equipment", "audit_operationhistory", "clock_timestamp",
                        "FOR UPDATE",
                    )))
                    self.assertEqual(snapshot(), before)

    def test_m01_native_confirmation_form_cancels_with_django_csrf(self):
        for account, percent_encoded in ((self.student, False), (self.teacher, True)):
            with self.subTest(role=account.role):
                row = self.row(owner=account)
                client = Client(enforce_csrf_checks=True)
                client.force_login(account)
                path = self.path(row)
                token = self.confirmation_token(client, row)
                wrong = ("B" if token.startswith("A") else "A") + token[1:]
                with patch("reservations.views.cancel_own_reservation", wraps=services.cancel_own_reservation) as cancel:
                    response = client.post(path, urlencode({"csrfmiddlewaretoken": wrong}), content_type=FORM_MEDIA_TYPE,
                                           headers={"X-CSRFToken": token})
                    self.assertEqual(response.status_code, 403)
                    cancel.assert_not_called()
                with patch.object(services, "_decision_time", return_value=self.before):
                    if percent_encoded:
                        body = f"%63srfmiddlewaretoken=%{ord(token[0]):02X}" + token[1:]
                        response = client.post(path, body, content_type=FORM_MEDIA_TYPE)
                    else:
                        response = self.post_confirmation(client, path, token)
                self.assertContains(response, "预约已取消")
                row.refresh_from_db()
                self.assertEqual(row.status, Status.CANCELLED)
                self.assertEqual(OperationHistory.objects.get(reservation=row, action="cancel").actor_id, account.pk)

    def test_stale_account_stops_before_business_query(self):
        row = self.row()
        User.objects.filter(pk=self.student.pk).update(is_active=False)
        for operation in (services.get_cancellation_candidate, services.cancel_own_reservation):
            with CaptureQueriesContext(connection) as sql, self.assertRaises(PermissionDenied):
                operation(self.student, row.pk)
            self.assertTrue(sql.captured_queries)
            self.assertFalse(any("reservations_reservation" in item["sql"] or "FOR UPDATE" in item["sql"] for item in sql))
        self.assertFalse(OperationHistory.objects.exists())

    def test_database_failure_responses_have_no_success_or_replay(self):
        row = self.row()
        self.client.force_login(self.student)
        for failure, message in ((services.ReservationFailed, "数据库事务已回滚"),
                                 (services.ReservationUnknown, "取消结果待核查")):
            with patch("reservations.views.cancel_own_reservation", side_effect=failure) as cancel:
                response = self.post_confirmation(self.client, self.path(row))
                cancel.assert_called_once()
            self.assertContains(response, message, status_code=503)
            self.assertNotContains(response, "预约已取消", status_code=503)
            self.assertNotContains(response, self.path(row), status_code=503)
            self.assertNotContains(response, "<form", status_code=503)
            self.assertContains(response, "返回我的预约", status_code=503)


def _window(row):
    return tuple(value.astimezone(services.BEIJING).strftime("%Y-%m-%dT%H:%M")
                 for value in (row.start_at, row.end_at))
