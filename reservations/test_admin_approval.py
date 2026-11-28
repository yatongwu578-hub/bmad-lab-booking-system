from datetime import timedelta
from html.parser import HTMLParser
from unittest.mock import patch

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Role, User
from audit.models import HistoryObject, OperationHistory
from audit.services import EXPIRY_REASON
from equipment.models import Equipment, EquipmentStatus

from . import services
from .models import Reservation, ReservationStatus as Status


class ApprovalForms(HTMLParser):
    def __init__(self, body):
        super().__init__()
        self.forms = []
        self.current = None
        self.feed(body)
        self.close()

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == "form":
            self.current = (fields, [])
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            self.current[1].append(fields)

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


class AdminApprovalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="approval-admin", role=Role.ADMIN)
        cls.student = User.objects.create_user(username="approval-student", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="approval-teacher", role=Role.TEACHER)
        cls.staff = User.objects.create_user(
            username="approval-staff", role=Role.STUDENT, is_staff=True, is_superuser=True,
        )
        cls.equipment = Equipment.objects.create(number="APP-1", name="Private approval fixture",
                                                 category="test", location="lab")
        cls.now = services._decision_time(connection)
        cls.start = (cls.now.astimezone(services.BEIJING) + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0,
        )

    def make_reservation(self, *, status=Status.PENDING, start=None):
        start = self.start if start is None else start
        return Reservation.objects.create(applicant=self.student, equipment=self.equipment, start_at=start,
                                          end_at=start + timedelta(hours=1), status=status, applied_at=self.now)

    def path(self, pk, *, detail=False):
        return reverse("admin-reservation-detail" if detail else "admin-reservation-approve", args=[pk])

    def snapshot(self):
        return tuple(list(model.objects.order_by("pk").values()) for model in (Equipment, Reservation, OperationHistory))

    def csrf_client(self, user):
        client = Client(enforce_csrf_checks=True)
        if user is not None:
            client.force_login(user)
        client.get(reverse("login"))
        return client, client.cookies["csrftoken"].value

    def test_approval_retains_original_and_projects_history(self):
        row = self.make_reservation()
        client, _ = self.csrf_client(self.admin)
        detail = client.get(self.path(row.pk, detail=True))
        self.assertEqual(detail.status_code, 200)
        (form, fields), = [entry for entry in ApprovalForms(detail.content.decode()).forms
                            if entry[0].get("action") == self.path(row.pk)]
        self.assertEqual(form.get("method"), "post")
        csrf, = [item for item in fields if item.get("name") == "csrfmiddlewaretoken"]
        self.assertEqual(csrf.get("type"), "hidden")
        self.assertTrue(csrf.get("value"))
        before_device, before_rows, _ = self.snapshot()
        self.assertEqual(client.get(self.path(row.pk)).status_code, 405)
        with CaptureQueriesContext(connection) as queries:
            response = client.post(form["action"], {
                "csrfmiddlewaretoken": csrf["value"],
                "applicant_id": self.teacher.pk, "actor_id": self.student.pk, "equipment_id": -1,
                "reservation_id": -1, "status": Status.CANCELLED,
            })
        self.assertContains(response, "预约已批准")
        self.assertNotContains(response, "<form")
        self.assertFalse(any("LEFT JOIN public.accounts_user" in entry["sql"] for entry in queries))
        after_device, after_rows, _ = self.snapshot()
        self.assertEqual(after_device, before_device)
        self.assertEqual(after_rows, [{**before_rows[0], "status": Status.APPROVED}])
        history = OperationHistory.objects.get()
        self.assertEqual((history.object_type, history.reservation_id, history.equipment_id, history.action,
                          history.before_status, history.after_status, history.actor_type, history.actor_id, history.reason),
                         (HistoryObject.RESERVATION, row.pk, None, "approve", Status.PENDING, Status.APPROVED,
                          "admin", self.admin.pk, ""))
        self.assertLess(history.decision_at, row.start_at)
        self.assertLessEqual(history.decision_at, history.recorded_at)
        detail = client.get(self.path(row.pk, detail=True))
        self.assertContains(detail, self.admin.username)
        self.assertContains(detail, "批准")
        self.assertContains(detail, "已批准")
        self.assertNotContains(detail, "批准预约</button>")
        self.assertContains(client.post(self.path(row.pk), HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value),
                            "当前状态不允许批准", status_code=409)
        self.assertEqual(OperationHistory.objects.count(), 1)

    def test_unauthorized_csrf_and_forged_principal_leave_all_data_untouched(self):
        row = self.make_reservation(start=self.now - timedelta(hours=1))
        before = self.snapshot()
        for user, code in ((None, 302), (self.student, 403), (self.teacher, 403), (self.staff, 403)):
            with self.subTest(user=user):
                client, token = self.csrf_client(user)
                response = client.post(self.path(row.pk), {"actor_id": self.admin.pk, "role": Role.ADMIN,
                                                          "csrfmiddlewaretoken": token})
                self.assertNotContains(response, self.equipment.name, status_code=code)
                self.assertNotContains(response, self.path(row.pk, detail=True), status_code=code)
                self.assertEqual(self.snapshot(), before)
        client, _ = self.csrf_client(self.admin)
        for token in (None, "invalid"):
            fields = {} if token is None else {"csrfmiddlewaretoken": token}
            self.assertNotContains(client.post(self.path(row.pk), fields), self.equipment.name, status_code=403)
            self.assertEqual(self.snapshot(), before)

    def test_exact_start_expires_even_with_unavailable_equipment(self):
        for status in EquipmentStatus.values:
            with self.subTest(equipment_status=status):
                self.equipment.status = status
                self.equipment.save(update_fields=["status"])
                row = self.make_reservation()
                with patch.object(services, "_decision_time", return_value=row.start_at) as clock:
                    self.assertEqual(services.approve_reservation(self.admin, row.pk), "expired")
                    clock.assert_called_once()
                row.refresh_from_db()
                self.assertEqual(row.status, Status.EXPIRED)
                item = OperationHistory.objects.get(reservation=row)
                self.assertEqual((item.action, item.actor_type, item.actor_id, item.reason, item.decision_at),
                                 ("expire", "system", None, EXPIRY_REASON, row.start_at))
                self.assertEqual(services.approve_reservation(self.admin, row.pk), "terminal")
                self.assertEqual(OperationHistory.objects.filter(reservation=row).count(), 1)

    def test_maintenance_and_disabled_deny_then_restore_rechecks(self):
        self.client.force_login(self.admin)
        for offset, status in enumerate((EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED)):
            with self.subTest(equipment_status=status):
                start = self.start + timedelta(hours=2 * offset)
                row = self.make_reservation(start=start)
                due_after_restore = self.make_reservation(start=start + timedelta(hours=1))
                self.equipment.status = status
                self.equipment.save(update_fields=["status"])
                before = self.snapshot()
                self.assertContains(self.client.post(self.path(row.pk)), "设备当前不可用，不能批准预约。", status_code=409)
                self.assertEqual(self.snapshot(), before)
                self.equipment.status = EquipmentStatus.AVAILABLE
                self.equipment.save(update_fields=["status"])
                self.assertEqual(services.approve_reservation(self.admin, row.pk), "approved")
                with patch.object(services, "_decision_time", return_value=due_after_restore.start_at) as clock:
                    self.assertContains(self.client.post(self.path(due_after_restore.pk)),
                                        "该待审核预约已失效。", status_code=409)
                    clock.assert_called_once()
                due_after_restore.refresh_from_db()
                self.assertEqual(due_after_restore.status, Status.EXPIRED)
                self.assertEqual(OperationHistory.objects.get(reservation=due_after_restore).action, "expire")

    def test_all_nonpending_and_missing_never_mutate(self):
        rows = [self.make_reservation(status=value, start=self.now - timedelta(hours=1))
                for value in Status.values if value != Status.PENDING]
        self.client.force_login(self.admin)
        before = self.snapshot()
        for row in rows:
            self.assertContains(self.client.post(self.path(row.pk)), "当前状态不允许批准", status_code=409)
        self.assertContains(self.client.post(self.path(rows[-1].pk + 1)), "预约记录不存在", status_code=404)
        self.assertEqual(self.snapshot(), before)

    def test_failure_and_unknown_do_not_reload_or_offer_post_retry(self):
        self.client.force_login(self.admin)
        row = self.make_reservation()
        for error, message in ((services.ReservationFailed, "数据库事务已回滚。"),
                               (services.ReservationUnknown, "批准结果待核查，请勿重复提交。")):
            with (self.subTest(error=error), patch("reservations.views.approve_reservation", side_effect=error) as approve,
                  patch("reservations.views.get_admin_reservation") as read):
                response = self.client.post(self.path(row.pk))
                self.assertContains(response, message, status_code=503)
                if error is services.ReservationUnknown:
                    for word in ("已回滚", "持久化", "未成功", "已批准"):
                        self.assertNotContains(response, word, status_code=503)
                self.assertNotContains(response, "<form", status_code=503)
                self.assertContains(response, f'href="{self.path(row.pk, detail=True)}"', status_code=503)
                approve.assert_called_once()
                read.assert_not_called()
