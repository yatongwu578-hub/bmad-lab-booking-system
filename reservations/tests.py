from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import re
from types import SimpleNamespace
from unittest.mock import patch

from django.db import IntegrityError, OperationalError, connection, transaction
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus
from lab_booking.transactions import transaction_rejected

from . import services
from .models import Reservation, ReservationStatus as Status
from .services import BEIJING, valid_window
from .views import CONFLICT_MESSAGE, INVALID_TIME_MESSAGE, UNAVAILABLE_MESSAGE


DECISION = datetime(2030, 2, 3, 9, tzinfo=BEIJING)


def local(hour, day=3):
    return datetime(2030, 2, day, hour, tzinfo=BEIJING)


def raw(moment):
    return moment.isoformat(timespec="minutes")[:16]


@contextmanager
def rollback_subcase():
    # A manual savepoint does not wrap the service's durable block in another atomic block.
    savepoint = transaction.savepoint()
    try:
        yield
    finally:
        transaction.savepoint_rollback(savepoint)


class TimeRulesTests(SimpleTestCase):
    def test_b1_microsecond_boundaries(self):
        start, end = local(10), local(11)
        delta = timedelta(microseconds=1)
        for decision, accepted in [(start - delta, True), (start, False), (start + delta, False)]:
            with self.subTest(decision=decision):
                self.assertEqual(valid_window(raw(start), raw(end), decision) is not None, accepted)

    def test_b2_beijing_legal_and_utc_round_trip(self):
        for start, end in [(local(10), local(11)), (local(22, 4), local(23, 4)), (local(0, 4), local(1, 4)),
                           (datetime(2099, 1, 2, 10, tzinfo=BEIJING), datetime(2099, 1, 2, 11, tzinfo=BEIJING))]:
            with self.subTest(start=start):
                actual = valid_window(raw(start), raw(end), DECISION.astimezone(timezone.utc))
                self.assertEqual(actual, (start, end))
                self.assertEqual(actual[0].astimezone(timezone.utc).astimezone(BEIJING), start)
        self.assertEqual(valid_window(raw(local(10)) + ':00.000', raw(local(11)), DECISION), (local(10), local(11)))

    def test_b2_rejects_invalid_dates_precision_windows_and_zone_suffixes(self):
        hour = raw(local(10))
        end = raw(local(11))
        for start, stop in [(None, end), ("", end), (hour, hour), (end, hour), (raw(local(9)), end),
                            (hour + "Z", end), (hour + "+08:00", end), (hour + ":01", end),
                            (hour + ":00.000001", end), (hour[:-2] + "30", end[:-2] + "30"),
                            ("2030-02-30T10:00", end), (raw(local(23)), raw(local(0, 4))),
                            (raw(local(22)), raw(local(1, 4))), (hour, raw(local(23)) + ":01")]:
            with self.subTest(start=start, end=stop):
                self.assertIsNone(valid_window(start, stop, DECISION))

    def test_ac9_commit_server_cancellation_is_confirmed_but_disconnect_is_unknown(self):
        db = SimpleNamespace(in_atomic_block=False, get_autocommit=lambda: True, closed_in_transaction=False)

        @contextmanager
        def commit_error(error):
            yield
            raise error

        for code, expected in [("55P03", services.ReservationFailed), ("57014", services.ReservationFailed),
                               ("08006", services.ReservationUnknown), ("40003", services.ReservationUnknown),
                               (None, services.ReservationUnknown)]:
            with self.subTest(sqlstate=code):
                cause = Exception()
                cause.sqlstate = code
                error = OperationalError()
                error.__cause__ = cause
                self.assertFalse(transaction_rejected(error))  # The Epic 1 classification is unchanged.
                with (patch.object(transaction, "get_connection", return_value=db),
                      patch.object(transaction, "atomic", return_value=commit_error(error)),
                      patch.object(transaction, "get_rollback", return_value=False),
                      self.assertRaises(expected)):
                    services._durable_operation(lambda connection: None)


class ReservationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(username="story21-student", password="Student-pass-21!", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="story21-teacher", role=Role.TEACHER)
        cls.admin = User.objects.create_user(username="story21-admin", role=Role.ADMIN)
        cls.inactive = User.objects.create_user(username="story21-inactive", role=Role.STUDENT, is_active=False)
        cls.equipment = Equipment.objects.create(number="21-device", name="私有预约测试设备", category="显微镜", location="实验室")
        cls.other = Equipment.objects.create(number="21-other", name="第二台设备", category="显微镜", location="实验室")

    def setUp(self):
        clock = patch("reservations.services._decision_time", return_value=DECISION)
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.url = reverse("reservation-submit", args=[self.equipment.pk])

    def login_client(self, user, *, protected=False):
        client = Client(enforce_csrf_checks=protected)
        client.force_login(user)
        return client

    def make(self, start=local(8), end=local(11), *, user=None, equipment=None, status=Status.PENDING):
        return Reservation.objects.create(applicant=user or self.student, equipment=equipment or self.equipment,
                                          start_at=start, end_at=end, status=status, applied_at=start - timedelta(days=1))

    def form_data(self, start=local(10), end=local(11), **extra):
        return {"start_at": raw(start), "end_at": raw(end), **extra}

    def token(self, response):
        return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())[1]

    def result_url(self, row):
        return reverse("reservation-result", args=[row.pk])

    def snapshot(self):
        return list(Reservation.objects.order_by("pk").values()), list(OperationHistory.objects.order_by("pk").values())

    def assert_expired_once(self, row, decision=DECISION):
        row.refresh_from_db()
        self.assertEqual(row.status, Status.EXPIRED)
        history = OperationHistory.objects.get(reservation=row)
        self.assertEqual((history.object_type, history.equipment_id, history.action, history.before_status,
                          history.after_status, history.actor_type, history.actor_id, history.reason, history.decision_at),
                         (HistoryObject.RESERVATION, None, "expire", Status.PENDING, Status.EXPIRED, "system", None,
                          EXPIRY_REASON, decision))
        self.assertIsNotNone(history.recorded_at)

    def test_ac1_both_roles_follow_detail_submit_with_csrf_and_read_own_result(self):
        for index, user in enumerate((self.student, self.teacher)):
            with self.subTest(role=user.role):
                client = self.login_client(user, protected=True)
                detail = client.get(reverse("equipment-detail", args=[self.equipment.pk]))
                self.assertContains(detail, f'href="{self.url}"')
                form = client.get(self.url)
                self.assertContains(form, 'type="datetime-local"', count=2)
                start, end = local(10 + index), local(11 + index)
                response = client.post(self.url, self.form_data(start, end, csrfmiddlewaretoken=self.token(form)))
                row = Reservation.objects.get(applicant=user)
                self.assertContains(response, "预约申请提交成功", status_code=201)
                self.assertContains(response, self.result_url(row), status_code=201)
                self.assertEqual((row.equipment_id, row.start_at, row.end_at, row.applied_at, row.status),
                                 (self.equipment.pk, start, end, DECISION, Status.PENDING))
                result = client.get(self.result_url(row))
                self.assertContains(result, "待审核")
                self.assertContains(result, raw(start).replace("T", " "))
                self.assertContains(client.post(self.url, self.form_data(start, end, csrfmiddlewaretoken=self.token(form))),
                                    CONFLICT_MESSAGE, status_code=409)

    def test_ac3_rejected_half_hour_can_be_corrected_on_bound_form(self):
        client = self.login_client(self.student, protected=True)
        form = client.get(self.url)
        start = (datetime.now(BEIJING) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        self.clock.return_value = start - timedelta(hours=1)
        half = timedelta(minutes=30)
        before = self.snapshot()
        rejected = client.post(self.url, self.form_data(start + half, end + half, csrfmiddlewaretoken=self.token(form)))
        self.assertContains(rejected, INVALID_TIME_MESSAGE, status_code=400)
        inputs = re.findall(r'<input\b[^>]*\btype="datetime-local"[^>]*>', rejected.content.decode())
        self.assertEqual(len(inputs), 2)
        for name, value in (("start_at", start + half), ("end_at", end + half)):
            matching = [tag for tag in inputs if f'name="{name}"' in tag]
            self.assertEqual(len(matching), 1)
            self.assertIn('step="any"', matching[0])
            self.assertIn(f'value="{raw(value)}"', matching[0])
        self.assertEqual(self.snapshot(), before)

        corrected = client.post(self.url, self.form_data(start, end, csrfmiddlewaretoken=self.token(rejected)))
        row = Reservation.objects.get()
        self.assertContains(corrected, self.result_url(row), status_code=201)
        self.assertContains(client.get(self.result_url(row)), "待审核")
        self.assertEqual((row.applicant_id, row.equipment_id, row.start_at, row.end_at, row.status),
                         (self.student.pk, self.equipment.pk, start, end, Status.PENDING))
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac2_unauthorized_or_csrf_failures_do_not_expire(self):
        self.make()
        student = self.login_client(self.student, protected=True)
        admin = self.login_client(self.admin, protected=True)
        # An admin detail response has no form, so mint a valid token via the normal login view.
        token = self.token(admin.get(reverse("login")))
        admin_detail = admin.get(reverse("equipment-detail", args=[self.equipment.pk]))
        self.assertNotContains(admin_detail, self.url)
        self.assertEqual(admin.get(self.url).status_code, 403)
        anon = Client(enforce_csrf_checks=True)
        anon_token = self.token(anon.get(reverse("login")))
        self.assertRedirects(anon.get(self.url), f'/login/?next={self.url}', fetch_redirect_response=False)
        inactive = self.login_client(self.inactive, protected=True)
        inactive_token = self.token(inactive.get(reverse("login")))
        student.get(self.url)
        for client, extra, status in [(admin, {"csrfmiddlewaretoken": token}, 403),
                                      (anon, {"csrfmiddlewaretoken": anon_token}, 302),
                                      (inactive, {"csrfmiddlewaretoken": inactive_token}, 302),
                                      (student, {}, 403), (student, {"csrfmiddlewaretoken": token}, 403)]:
            before = self.snapshot()
            response = client.post(self.url, self.form_data(**extra))
            self.assertNotContains(response, self.equipment.name, status_code=status)
            self.assertEqual(self.snapshot(), before)
        self.clock.assert_not_called()

    def test_ac2_tampered_identity_device_and_timezone_are_ignored(self):
        client = self.login_client(self.student, protected=True)
        token = self.token(client.get(self.url))
        response = client.post(self.url, self.form_data(csrfmiddlewaretoken=token, applicant=self.teacher.pk,
                                                       applicant_id=self.admin.pk, equipment=self.other.pk,
                                                       equipment_id=self.other.pk, timezone="UTC"))
        self.assertEqual(response.status_code, 201)
        row = Reservation.objects.get()
        self.assertEqual((row.applicant_id, row.equipment_id, row.start_at), (self.student.pk, self.equipment.pk, local(10)))

    def test_ac4_both_unavailable_statuses_report_unavailability(self):
        client = self.login_client(self.student)
        later = self.make(local(15), local(16))
        for status in (EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED):
            Equipment.objects.filter(pk=self.equipment.pk).update(status=status)
            self.assertContains(client.post(self.url, self.form_data()), UNAVAILABLE_MESSAGE, status_code=409)
        later.refresh_from_db()
        self.assertEqual(later.status, Status.PENDING)
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertFalse(OperationHistory.objects.exists())

    def test_ac5_overlap_matrix_for_both_effective_states(self):
        client = self.login_client(self.student)
        for status in (Status.PENDING, Status.APPROVED):
            for start, end in [(11, 13), (10, 12), (12, 14), (10, 14), (11, 12)]:
                with self.subTest(status=status, start=start, end=end), rollback_subcase():
                    self.make(local(11), local(13), user=self.teacher, status=status)
                    response = client.post(self.url, self.form_data(local(start), local(end)))
                    self.assertContains(response, CONFLICT_MESSAGE, status_code=409)
                    self.assertNotContains(response, self.teacher.username, status_code=409)
                    self.assertEqual(Reservation.objects.count(), 1)

    def test_ac5_adjacency_both_directions_cross_device_and_terminal_states(self):
        client = self.login_client(self.student)
        self.make(local(11), local(13), status=Status.APPROVED)
        for status in (Status.REJECTED, Status.CANCELLED, Status.EXPIRED):
            self.make(local(10), local(11), status=status)
        for url, start, end in [(self.url, 10, 11), (self.url, 13, 14),
                                (reverse("reservation-submit", args=[self.other.pk]), 11, 13)]:
            self.assertEqual(client.post(url, self.form_data(local(start), local(end))).status_code, 201)

    def test_ac6_expiry_boundary_and_approved_record_never_expires(self):
        owner = self.login_client(self.student)
        start, end = local(10), local(11)
        old = self.make(start, end)
        approved = self.make(start, end, status=Status.APPROVED)
        for decision in (start - timedelta(microseconds=1), start, start + timedelta(microseconds=1),
                         end - timedelta(microseconds=1), end, end + timedelta(microseconds=1)):
            with self.subTest(decision=decision), rollback_subcase():
                self.clock.return_value = decision
                self.assertContains(owner.get(self.result_url(old)), "待审核" if decision < start else "已失效")
                if decision >= start:
                    self.assert_expired_once(old, decision)
                self.assertContains(owner.get(self.result_url(approved)), "已批准")
                self.assertFalse(OperationHistory.objects.filter(reservation=approved).exists())

    def test_ac6_submit_expiry_is_scoped_and_only_once(self):
        client = self.login_client(self.student)
        old = self.make(user=self.teacher)
        unrelated = self.make(equipment=self.other)
        approved = self.make(local(7), local(10), status=Status.APPROVED)
        self.assertEqual(client.post(self.url, self.form_data()).status_code, 201)
        self.assert_expired_once(old)
        self.assertEqual(client.post(self.url, self.form_data()).status_code, 409)
        self.assert_expired_once(old)
        unrelated.refresh_from_db()
        approved.refresh_from_db()
        self.assertEqual((unrelated.status, approved.status), (Status.PENDING, Status.APPROVED))

    def test_ac8_business_rejections_keep_expiry_and_preserve_other_rows(self):
        client = self.login_client(self.student)
        for kind, expected in [("unavailable", 409), ("invalid", 400), ("conflict", 409)]:
            with self.subTest(kind=kind), rollback_subcase():
                old = self.make()
                other = self.make(local(10), local(11), status=Status.APPROVED) if kind == "conflict" else None
                if kind == "unavailable":
                    Equipment.objects.filter(pk=self.equipment.pk).update(status=EquipmentStatus.DISABLED)
                values = self.form_data() if kind != "invalid" else {"start_at": "not-a-time"}
                self.assertEqual(client.post(self.url, values).status_code, expected)
                self.assert_expired_once(old)
                self.assertEqual(Reservation.objects.count(), 2 if other else 1)

    def test_ac8_business_rejections_render_locked_equipment_without_another_read(self):
        client = self.login_client(self.student)
        with patch("reservations.views.get_equipment_detail", side_effect=AssertionError("POST must not reread the device")) as detail:
            self.assertContains(client.post(self.url, {"start_at": "bad"}), self.equipment.name, status_code=400)
            self.make(local(10), local(11), status=Status.APPROVED)
            self.assertContains(client.post(self.url, self.form_data()), CONFLICT_MESSAGE, status_code=409)
            Equipment.objects.filter(pk=self.equipment.pk).update(status=EquipmentStatus.DISABLED)
            self.assertContains(client.post(self.url, self.form_data()), UNAVAILABLE_MESSAGE, status_code=409)
            detail.assert_not_called()

    def test_ac10_foreign_and_missing_are_equal_and_post_is_disallowed(self):
        old = self.make()
        before = self.snapshot()
        url = self.result_url(old)
        for client, status in [(self.login_client(self.teacher), 404), (self.login_client(self.admin), 403),
                               (Client(), 302), (self.login_client(self.inactive), 302)]:
            response = client.get(url)
            self.assertNotContains(response, self.equipment.name, status_code=status)
            if status == 404:
                self.assertEqual(response.content, client.get(reverse("reservation-result", args=[old.pk + 1])).content)
            self.assertEqual(self.snapshot(), before)
        student = self.login_client(self.student, protected=True)
        self.assertEqual(student.post(url, {"csrfmiddlewaretoken": self.token(student.get(self.url))}).status_code, 405)
        self.assertEqual(self.snapshot(), before)
        self.clock.assert_not_called()

    def test_ac10_expired_ended_result_only_updates_fixed_owned_row(self):
        old = self.make(local(6), local(7))
        foreign = self.make(user=self.teacher)
        same_owner_other = self.make()
        student = self.login_client(self.student)
        for _ in range(2):
            self.assertContains(student.get(self.result_url(old)), "已失效")
            self.assert_expired_once(old)
        self.clock.assert_called_once()
        for row in (foreign, same_owner_other):
            row.refresh_from_db()
            self.assertEqual(row.status, Status.PENDING)
            self.assertFalse(OperationHistory.objects.filter(reservation=row).exists())

    def test_own_result_login_redirect_returns_to_target_form(self):
        client = Client(enforce_csrf_checks=True)
        login = client.get(self.url, follow=True)
        response = client.post(login.redirect_chain[-1][0], {"username": self.student.username,
                               "password": "Student-pass-21!", "next": self.url, "csrfmiddlewaretoken": self.token(login)})
        self.assertRedirects(response, self.url)

    def test_r04_database_checks_both_fk_and_protects_referenced_rows(self):
        reservation = self.make()
        values = dict(action="fixture", before_status="pending", after_status="expired", actor_type="system",
                      reason="isolated fixture", decision_at=DECISION, recorded_at=DECISION)
        for object_type, reservation_id, equipment_id in [
            (None, reservation.pk, None), ("reservation", None, None), ("equipment", None, None),
            ("reservation", reservation.pk, self.equipment.pk), ("equipment", reservation.pk, self.equipment.pk),
            ("equipment", reservation.pk, None), ("reservation", None, self.equipment.pk),
            ("unknown", reservation.pk, None), ("reservation", 2**62, None), ("equipment", None, 2**62),
        ]:
            with self.subTest(object_type=object_type, reservation_id=reservation_id, equipment_id=equipment_id):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    OperationHistory.objects.create(object_type=object_type, reservation_id=reservation_id, equipment_id=equipment_id, **values)
                    with connection.cursor() as cursor:
                        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        OperationHistory.objects.create(object_type="reservation", reservation=reservation, **values)
        OperationHistory.objects.create(object_type="equipment", equipment=self.other, **values)
        for table, pk in [("reservations_reservation", reservation.pk), ("equipment_equipment", self.other.pk)]:
            with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM {table} WHERE id = %s", [pk])
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        self.assertEqual(OperationHistory.objects.count(), 2)
