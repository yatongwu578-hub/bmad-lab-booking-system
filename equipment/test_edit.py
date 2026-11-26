import json
import re
from hashlib import sha256
from html import unescape
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import Resolver404, resolve, reverse
from django.utils.html import escape

from accounts.models import Role, User

from .models import Equipment, EquipmentStatus
from .services import EquipmentEditFailed, EquipmentEditUnknown, edit_equipment


class EquipmentEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username="edit-admin", role=Role.ADMIN)
        cls.student = User.objects.create_user(username="edit-student", role=Role.STUDENT)
        cls.teacher = User.objects.create_user(
            username="edit-teacher", role=Role.TEACHER, is_staff=True, is_superuser=True,
        )
        cls.target = Equipment.objects.create(
            number="EDIT-001", name="原设备名称", category="原类别",
            location="原位置", description="原说明",
        )
        cls.other = Equipment.objects.create(
            number="EDIT-002", name="其他设备", category="其他类别", location="其他位置",
        )

    def setUp(self):
        self.edit_url = reverse("equipment-edit", args=[self.target.pk])
        self.detail_url = reverse("equipment-detail", args=[self.target.pk])
        self.values = {
            "name": "新设备名称", "category": "新类别",
            "location": "新位置", "description": "新说明第一行\n第二行",
        }

    def client_as(self, user=None):
        client = Client(enforce_csrf_checks=True)
        if user is not None:
            client.force_login(user)
        return client

    def admin_form(self):
        client = self.client_as(self.admin)
        response = client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        # Use the masked token rendered in the form, as a browser does.
        match = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', response.content)
        self.assertIsNotNone(match)
        return client, response, match[1].decode("ascii")

    @staticmethod
    def snapshot():
        return list(Equipment.objects.order_by("pk").values())

    @staticmethod
    def snapshot_evidence(rows):
        payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {"count": len(rows), "sha256": sha256(payload).hexdigest()}

    def expected_edit(self, baseline):
        return [{**row, **self.values} if row["id"] == self.target.pk else row for row in baseline]

    @staticmethod
    def equipment_sql(queries):
        return [entry["sql"] for entry in queries if '"equipment_equipment"' in entry["sql"]]

    def assert_only_read(self, queries):
        equipment_sql = self.equipment_sql(queries)
        self.assertTrue(all(sql.startswith("SELECT") and "FOR UPDATE" not in sql for sql in equipment_sql))
        self.assertFalse(any("reservation" in entry["sql"].lower() or "audit_" in entry["sql"].lower()
                             for entry in queries))

    def test_ac1_admin_get_and_valid_csrf_post_preserve_identity(self):
        baseline = self.snapshot()
        client, form, token = self.admin_form()
        self.assertEqual(tuple(form.context["form"].fields), tuple(self.values))
        for value in (self.target.number, self.target.name, self.target.category,
                      self.target.location, self.target.description, "可用"):
            self.assertContains(form, value)
        for name in ("id", "number", "status"):
            self.assertNotContains(form, f'name="{name}"')
        self.assertContains(client.get(self.detail_url), f'href="{self.edit_url}"')
        response = client.post(self.edit_url, {**self.values, "csrfmiddlewaretoken": token})
        self.assertRedirects(response, self.detail_url)
        detail = client.get(self.detail_url)
        for value in self.values.values():
            self.assertContains(detail, value)
        self.assertEqual(self.snapshot(), self.expected_edit(baseline))
        print("合法对照（非 T-03 拒绝分母）：admin GET 200、有效 CSRF POST 302，重读四字段与身份一致。")

    def test_r2_description_preserves_submitted_and_unchanged_whitespace(self):
        client, _, token = self.admin_form()
        baseline = self.snapshot()
        description = '\n  第一行  <strong>literal & text</strong>\n\n  第二行  \n  '

        def assert_saved_and_rendered(values):
            self.assertEqual(
                self.snapshot(),
                [{**row, **values} if row["id"] == self.target.pk else row for row in baseline],
            )
            detail = client.get(self.detail_url)
            self.assertEqual(detail.status_code, 200)
            match = re.search(r'<dd id="equipment-description"[^>]*>(.*?)</dd>',
                              detail.content.decode(detail.charset), re.DOTALL)
            self.assertIsNotNone(match)
            self.assertEqual(match[1], escape(description))
            self.assertEqual(unescape(match[1]), description)

        first = {**self.values, "description": description}
        self.assertRedirects(client.post(self.edit_url, {**first, "csrfmiddlewaretoken": token}),
                             self.detail_url)
        assert_saved_and_rendered(first)

        form = client.get(self.edit_url)
        self.assertEqual(form.status_code, 200)
        match = re.search(r'<textarea\b[^>]*\bname="description"[^>]*>(.*?)</textarea>',
                          form.content.decode(form.charset), re.DOTALL)
        self.assertIsNotNone(match)
        # Django renders one initial newline that HTML ignores; the remaining text is the field value.
        self.assertEqual(match[1], "\n" + escape(description))
        kept = {**first, "name": "仅修改名称"}
        browser_description = unescape(match[1][1:]).replace("\n", "\r\n")
        self.assertNotEqual(browser_description, description)
        self.assertRedirects(client.post(self.edit_url, {
            **kept, "description": browser_description, "csrfmiddlewaretoken": token,
        }), self.detail_url)
        assert_saved_and_rendered(kept)
        print("R2 whitespace preserved: new description and unchanged textarea with CRLF; detail auto-escaped.")

    def test_ac2_forged_number_rejected_and_real_unique_constraint_preserved(self):
        baseline = self.snapshot()
        client, _, token = self.admin_form()
        with CaptureQueriesContext(connection) as queries:
            response = client.post(self.edit_url, {**self.values, "number": self.other.number},
                                   HTTP_X_CSRFTOKEN=token)
        self.assertContains(response, "设备编号不可修改", status_code=400)
        self.assert_only_read(queries)
        self.assertEqual(self.snapshot(), baseline)
        with self.assertRaises(IntegrityError) as caught, transaction.atomic():
            Equipment.objects.filter(pk=self.other.pk).update(number=self.target.number)
        self.assertEqual(caught.exception.__cause__.diag.constraint_name, "equipment_number_unique")
        self.assertEqual(self.snapshot(), baseline)

    def test_ac3_forging_each_status_from_every_other_status_is_rejected(self):
        client, _, token = self.admin_form()
        for current in EquipmentStatus.values:
            Equipment.objects.filter(pk=self.target.pk).update(status=current)
            baseline = self.snapshot()
            for forged in set(EquipmentStatus.values) - {current}:
                with self.subTest(current=current, forged=forged):
                    with CaptureQueriesContext(connection) as queries:
                        response = client.post(self.edit_url, {**self.values, "status": forged},
                                               HTTP_X_CSRFTOKEN=token)
                    self.assertContains(response, "设备状态不可在此修改", status_code=400)
                    self.assert_only_read(queries)
                    self.assertEqual(self.snapshot(), baseline)

    def test_ac4_t03_six_role_denials_with_valid_post_csrf_do_not_read_target(self):
        baseline = self.snapshot()
        for user in (None, self.student, self.teacher):
            client = self.client_as(user)
            if user is None:
                self.assertEqual(client.get(reverse("login")).status_code, 200)
            else:
                self.assertNotContains(client.get(self.detail_url), f'href="{self.edit_url}"')
                self.assertEqual(client.get(reverse("identity")).status_code, 200)
            token = client.cookies["csrftoken"].value
            role = getattr(user, "role", "anonymous")
            expected_status = 302 if user is None else 403
            expected_location = f"/login/?next={self.edit_url}" if user is None else None
            private_values = (self.target.number, self.target.name, self.target.description,
                              "编辑设备基础信息", 'name="description"')
            for method in ("GET", "POST"):
                with self.subTest(role=role, method=method):
                    before = self.snapshot()
                    with CaptureQueriesContext(connection) as queries:
                        response = (client.get(self.edit_url) if method == "GET" else
                                    client.post(self.edit_url, {**self.values, "csrfmiddlewaretoken": token}))
                    after = self.snapshot()
                    body = response.content.decode(response.charset)
                    record = {
                        "role": role, "method": method, "route": self.edit_url, "target": self.target.number,
                        "request": {} if method == "GET" else {**self.values, "csrf": "valid-redacted"},
                        "expected_status": expected_status, "actual_status": response.status_code,
                        "denied": response.status_code == expected_status and (
                            expected_location is None or response.get("Location") == expected_location
                        ),
                        "no_leak": all(value not in body for value in private_values),
                        "before": self.snapshot_evidence(before), "after": self.snapshot_evidence(after),
                    }
                    print("T-03 record " + json.dumps(record, sort_keys=True))
                    self.assertEqual(response.status_code, expected_status)
                    if user is None:
                        self.assertEqual(response["Location"], expected_location)
                    for value in private_values:
                        self.assertNotIn(value, body)
                    self.assertEqual(self.equipment_sql(queries), [])
                    self.assertEqual(after, before)
                    self.assertEqual(after, baseline)
                    print(f"T-03 {getattr(user, 'role', 'anonymous')} {method} {response.status_code}，"
                          f"无设备读取或泄露，{len(baseline)} 行全字段不变。")

    def test_ac4_missing_and_mismatched_admin_csrf_are_distinct_denials(self):
        baseline = self.snapshot()
        client, _, token = self.admin_form()
        mismatch = ("a" if token[0] != "a" else "b") + token[1:]
        for reason, headers in (("missing", {}), ("mismatch", {"HTTP_X_CSRFTOKEN": mismatch})):
            with self.subTest(reason=reason):
                with CaptureQueriesContext(connection) as queries:
                    response = client.post(self.edit_url, self.values, **headers)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(self.target.number, response.content.decode(response.charset))
                self.assertEqual(self.equipment_sql(queries), [])
                self.assertEqual(self.snapshot(), baseline)
                print(f"CSRF 单列（非 T-03 角色拒绝分母）：admin {reason} 403，无设备读取或变更。")

    def test_ac5_missing_target_is_404_for_get_and_both_valid_and_invalid_post(self):
        baseline = self.snapshot()
        client, _, token = self.admin_form()
        missing = reverse("equipment-edit", args=[max(row["id"] for row in baseline) + 10000])
        for method, data in (("get", None), ("post", self.values), ("post", {**self.values, "id": "1"})):
            with self.subTest(method=method, data=data), CaptureQueriesContext(connection) as queries:
                response = (client.get(missing) if method == "get" else
                            client.post(missing, data, HTTP_X_CSRFTOKEN=token))
                self.assertContains(response, "设备不存在", status_code=404)
                self.assertNotContains(response, self.other.number, status_code=404)
            self.assertTrue(all(sql.startswith("SELECT") for sql in self.equipment_sql(queries)))
            self.assertEqual(self.snapshot(), baseline)

    def test_ac6_actual_sql_locks_then_rereads_then_updates_exactly_four_columns(self):
        client, _, token = self.admin_form()
        for status in (EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED):
            Equipment.objects.filter(pk=self.target.pk).update(status=status)
            baseline = self.snapshot()
            with self.subTest(status=status), CaptureQueriesContext(connection) as queries:
                response = client.post(self.edit_url, self.values, HTTP_X_CSRFTOKEN=token)
                self.assertEqual(response.status_code, 302)
            lock_sql, read_sql, update_sql = self.equipment_sql(queries)
            self.assertIn('SELECT "equipment_equipment"."id"', lock_sql)
            self.assertIn("FOR UPDATE", lock_sql)
            self.assertIn('"equipment_equipment"."status"', read_sql)
            self.assertNotIn("FOR UPDATE", read_sql)
            self.assertEqual(set(re.findall(r'"(\w+)"\s*=', update_sql.split(" WHERE ")[0])), set(self.values))
            self.assertTrue(all('"equipment_equipment"."id" =' in sql for sql in (lock_sql, read_sql, update_sql)))
            self.assertEqual(self.snapshot(), self.expected_edit(baseline))

    def test_ac7_no_delete_method_route_or_form_action(self):
        baseline = self.snapshot()
        client, form, token = self.admin_form()
        self.assertNotContains(form, "删除")
        self.assertNotContains(client.get(self.detail_url), "删除")
        for base in (self.edit_url, self.detail_url):
            self.assertEqual(client.delete(base, HTTP_X_CSRFTOKEN=token).status_code, 405)
        for url in (f"{self.detail_url}delete/", "/admin/"):
            with self.assertRaises(Resolver404):
                resolve(url)
            self.assertEqual(client.post(url, self.values, HTTP_X_CSRFTOKEN=token).status_code, 404)
        self.assertEqual(self.snapshot(), baseline)

    def test_ac8_distinct_http_failures_do_not_offer_a_retry_or_claim_success(self):
        baseline = self.snapshot()
        client, _, token = self.admin_form()
        for error, heading in ((EquipmentEditFailed, "设备编辑失败"), (EquipmentEditUnknown, "提交结果待核查")):
            with self.subTest(error=error), patch("equipment.views.edit_equipment", side_effect=error) as edit:
                response = client.post(self.edit_url, self.values, HTTP_X_CSRFTOKEN=token)
                edit.assert_called_once()
            self.assertContains(response, heading, status_code=503)
            self.assertNotContains(response, "<form", status_code=503)
            self.assertNotContains(response, "已保存", status_code=503)
            self.assertNotContains(response, "编号已存在", status_code=503)
            self.assertNotIn("Location", response)
            if error is EquipmentEditUnknown:
                self.assertContains(response, "请先核查设备记录", status_code=503)
                self.assertNotContains(response, "未保存", status_code=503)
            self.assertEqual(self.snapshot(), baseline)

    def test_invalid_extra_duplicate_and_file_keys_reject_wording_and_do_not_lock(self):
        baseline = self.snapshot()
        client, _, token = self.admin_form()
        cases = (
            ({**self.values, "id": str(self.other.pk)}, "不允许"),
            ({**self.values, "unexpected": ""}, "不允许"),
            ({**self.values, "name": ["first", "second"]}, "重复字段"),
            ({**self.values, "csrfmiddlewaretoken": [token, token]}, "重复字段"),
            ({**self.values, "description": SimpleUploadedFile("edit.txt", b"content")}, "不允许"),
            ({**self.values, "name": " "}, "必填"),
            ({key: value for key, value in self.values.items() if key != "description"}, "说明字段"),
        )
        for data, message in cases:
            with self.subTest(message=message), CaptureQueriesContext(connection) as queries:
                response = client.post(self.edit_url, data, HTTP_X_CSRFTOKEN=token)
                self.assertContains(response, message, status_code=400)
            self.assert_only_read(queries)
            self.assertEqual(self.snapshot(), baseline)
        protected = urlencode({**self.values, "number": self.target.number})
        response = client.post(self.edit_url, protected, content_type="application/x-www-form-urlencoded",
                               HTTP_X_CSRFTOKEN=token)
        self.assertContains(response, "设备编号不可修改", status_code=400)
        self.assertEqual(self.snapshot(), baseline)

    def test_service_enforces_active_admin_and_allowlist_before_database_access(self):
        baseline = self.snapshot()
        with self.assertNumQueries(0):
            for user in (self.teacher, SimpleNamespace(is_authenticated=True, is_active=False, role=Role.ADMIN)):
                with self.assertRaises(PermissionDenied):
                    edit_equipment(user, self.target.pk, self.values)
            with self.assertRaises(ValueError):
                edit_equipment(self.admin, self.target.pk, {**self.values, "status": EquipmentStatus.DISABLED})
        self.assertEqual(self.snapshot(), baseline)

    def test_service_rejects_ordinary_outer_transaction_without_writes(self):
        baseline = self.snapshot()
        with transaction.atomic(), self.assertRaisesRegex(RuntimeError, "durable"):
            edit_equipment(self.admin, self.target.pk, self.values)
        self.assertEqual(self.snapshot(), baseline)
