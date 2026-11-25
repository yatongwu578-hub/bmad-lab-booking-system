from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import IntegrityError, OperationalError, transaction
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import Role, User

from .forms import EquipmentCreateForm
from .models import Equipment, EquipmentStatus
from .services import (
    EquipmentCreationFailed,
    EquipmentCreationUnknown,
    EquipmentNumberConflict,
    create_equipment,
)


class EquipmentCreateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="equipment_admin", password="test-pass", role=Role.ADMIN)
        cls.student = User.objects.create_user(username="equipment_student", password="test-pass", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(username="equipment_teacher", password="test-pass", role=Role.TEACHER)

    def setUp(self):
        self.url = reverse("equipment-create")
        self.valid = {
            "number": "EQ-001",
            "name": "显微镜",
            "category": "光学设备",
            "location": "实验室 A",
            "description": "常规设备",
        }

    def login_as(self, user):
        self.client.force_login(user)

    def test_ac1_admin_creates_available_equipment_and_sees_saved_record(self):
        self.login_as(self.admin)
        form = self.client.get(self.url)
        self.assertContains(form, "初始状态：可用")
        self.assertNotContains(form, 'name="status"')
        response = self.client.post(self.url, {**self.valid, "status": EquipmentStatus.DISABLED})
        self.assertEqual(response.status_code, 201)
        equipment = Equipment.objects.get(number="EQ-001")
        self.assertEqual(equipment.status, EquipmentStatus.AVAILABLE)
        page = response.content.decode(response.charset)
        for field in ("number", "name", "category", "location", "description"):
            self.assertIn(getattr(equipment, field), page)
        self.assertIn("可用", page)
        self.assertEqual(Equipment.objects.filter(number="EQ-001").count(), 1)

    def test_ac2_duplicate_does_not_overwrite_existing_fields(self):
        existing = Equipment.objects.create(**self.valid)
        before = dict(Equipment.objects.values().get(pk=existing.pk))
        self.login_as(self.admin)
        response = self.client.post(self.url, {**self.valid, "name": "伪造覆盖"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("已存在", response.content.decode(response.charset))
        self.assertEqual(dict(Equipment.objects.values().get(pk=existing.pk)), before)
        self.assertEqual(Equipment.objects.count(), 1)

    def test_ac3_missing_and_blank_number_are_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        client.get(self.url)
        token = client.cookies["csrftoken"].value
        cases = {
            "empty body": ("", {"content_type": "application/x-www-form-urlencoded"}),
            "missing": ({key: value for key, value in self.valid.items() if key != "number"}, {}),
        }
        cases.update({
            label: ({**self.valid, "number": number}, {})
            for label, number in (("empty", ""), ("whitespace", "  "), ("too long", "x" * 33), ("NUL", "EQ\x00-001"))
        })
        for label, (data, options) in cases.items():
            with self.subTest(label=label):
                response = client.post(self.url, data, HTTP_X_CSRFTOKEN=token, **options)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors["number"])
                self.assertNotContains(response, "设备已新增")
                self.assertEqual(Equipment.objects.count(), 0)

    def test_number_validation_preserves_case_and_does_not_query_existing_records(self):
        Equipment.objects.create(**self.valid)
        form = EquipmentCreateForm({**self.valid, "number": " EQ-001 "})
        with self.assertNumQueries(0):
            self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["number"], self.valid["number"])
        self.login_as(self.admin)
        response = self.client.post(self.url, {**self.valid, "number": " eq-001 "})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Equipment.objects.filter(number="eq-001").exists())

    def test_service_rejects_an_ordinary_outer_atomic_block(self):
        with transaction.atomic():
            with self.assertRaises(RuntimeError):
                create_equipment(self.admin, self.valid)
        self.assertFalse(Equipment.objects.exists())

    def test_ac4_anonymous_student_and_teacher_are_rejected_on_get_and_post(self):
        for user in (None, self.student, self.teacher):
            with self.subTest(user=user):
                client = Client()
                if user is not None:
                    client.force_login(user)
                before = list(Equipment.objects.values())
                get_response = client.get(self.url)
                post_response = client.post(self.url, self.valid)
                self.assertIn(get_response.status_code, (302, 403))
                self.assertIn(post_response.status_code, (302, 403))
                if get_response.status_code == 200:
                    self.assertNotIn("新增具体设备档案", get_response.content.decode(get_response.charset))
                self.assertEqual(list(Equipment.objects.values()), before)

    def test_ac5_csrf_required_and_valid_token_control_succeeds(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        missing = client.post(self.url, self.valid)
        self.assertEqual(missing.status_code, 403)
        client.get(self.url)
        token = client.cookies["csrftoken"].value
        success = client.post(self.url, self.valid, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(success.status_code, 201)
        self.assertEqual(Equipment.objects.count(), 1)

    def test_only_named_equipment_unique_violation_is_duplicate(self):
        self.login_as(self.admin)
        with patch("equipment.views.create_equipment", side_effect=EquipmentNumberConflict):
            response = self.client.post(self.url, self.valid)
        self.assertIn("已存在", response.content.decode(response.charset))
        with patch("equipment.views.create_equipment", side_effect=EquipmentCreationFailed):
            response = self.client.post(self.url, {**self.valid, "number": "EQ-OTHER"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("编号已存在", response.content.decode(response.charset))

    def test_unknown_result_requests_verification_and_does_not_suggest_retry(self):
        self.login_as(self.admin)
        with patch("equipment.views.create_equipment", side_effect=EquipmentCreationUnknown) as service:
            response = self.client.post(self.url, self.valid)
        self.assertContains(response, "提交结果待核查", status_code=503)
        for text in ("设备已新增", "设备新增失败", "重试"):
            self.assertNotContains(response, text, status_code=503)
        service.assert_called_once()


class EquipmentCreationTransactionTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_authenticated=True, is_active=True, role=Role.ADMIN)
        self.values = dict(number="EQ-001", name="Name", category="Category", location="Lab", description="")
        self.connection = MagicMock(in_atomic_block=False, closed_in_transaction=False)
        self.connection.get_autocommit.return_value = True
        self.atomic = MagicMock()
        self.create = self.enterContext(patch.object(Equipment.objects, "create"))
        self.enterContext(patch("equipment.services.transaction.get_connection", return_value=self.connection))
        self.enterContext(patch("equipment.services.transaction.atomic", return_value=self.atomic))
        self.enterContext(patch("equipment.services.transaction.get_rollback", return_value=False))

    def test_rejects_manual_transaction_before_insert(self):
        self.connection.get_autocommit.return_value = False
        with self.assertRaises(RuntimeError):
            create_equipment(self.user, self.values)
        self.atomic.__enter__.assert_not_called()
        self.create.assert_not_called()

    def test_write_connection_loss_is_failed_because_commit_has_not_started(self):
        self.create.side_effect = OperationalError("connection lost")
        with self.assertRaises(EquipmentCreationFailed):
            create_equipment(self.user, self.values)
        self.create.assert_called_once()

    def test_commit_connection_loss_without_sqlstate_is_unknown(self):
        self.atomic.__exit__.side_effect = OperationalError("connection lost")
        with self.assertRaises(EquipmentCreationUnknown):
            create_equipment(self.user, self.values)
        self.create.assert_called_once()

    def test_named_unique_diagnostics_distinguish_duplicate_from_other_rejections(self):
        cases = (
            ("23505", Equipment._meta.db_table, "equipment_number_unique", EquipmentNumberConflict),
            ("23505", "another_table", "equipment_number_unique", EquipmentCreationFailed),
            ("23505", Equipment._meta.db_table, "another_constraint", EquipmentCreationFailed),
            ("23514", Equipment._meta.db_table, "equipment_number_unique", EquipmentCreationFailed),
        )
        for sqlstate, table, constraint, expected in cases:
            with self.subTest(sqlstate=sqlstate, table=table, constraint=constraint):
                error = IntegrityError()
                error.__cause__ = type("PostgresRejection", (Exception,), {
                    "sqlstate": sqlstate, "diag": SimpleNamespace(table_name=table, constraint_name=constraint),
                })()
                self.atomic.__exit__.side_effect = error
                with self.assertRaises(expected):
                    create_equipment(self.user, self.values)
