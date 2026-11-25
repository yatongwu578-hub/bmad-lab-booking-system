import json
import os
import re
import subprocess
from html import unescape
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

from django.conf import settings
from django.db import IntegrityError, OperationalError, connection, transaction
from django.test import Client, SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import escape

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


class EquipmentCatalogTests(TestCase):
    ROLE_LABELS = {
        Role.STUDENT: "学生",
        Role.TEACHER: "教师",
        Role.ADMIN: "业务管理员",
    }
    STATUS_LABELS = {
        EquipmentStatus.AVAILABLE: "可用",
        EquipmentStatus.MAINTENANCE: "维修",
        EquipmentStatus.DISABLED: "停用",
    }
    CATALOG_COLUMNS = {"id", "number", "name", "category", "location", "status"}
    DETAIL_COLUMNS = (CATALOG_COLUMNS - {"id"}) | {"description"}
    BOUNDARY_TEXT = "这里显示的是设备当前状态，不是预约状态。「可用」不代表指定时段可预约，也不保证预约成功。"

    @classmethod
    def setUpTestData(cls):
        cls.passwords = {role: get_random_string(24) for role in cls.ROLE_LABELS}
        cls.users = {
            role: User.objects.create_user(
                username=f"catalog_{role}", password=cls.passwords[role], role=role,
            )
            for role in cls.ROLE_LABELS
        }

    def setUp(self):
        self.catalog_url = reverse("equipment-catalog")

    def make_three_equipment(self):
        equipment = [
            Equipment.objects.create(
                number=f"CAT-{suffix}",
                name=f"目录夹具名称-{suffix}",
                category=f"目录夹具类别-{suffix}",
                location=f"目录夹具位置-{suffix}",
                description=f"目录夹具说明-{suffix}",
                status=status,
            )
            for suffix, status in (
                ("C", EquipmentStatus.AVAILABLE),
                ("A", EquipmentStatus.MAINTENANCE),
                ("B", EquipmentStatus.DISABLED),
            )
        ]
        return sorted(equipment, key=lambda item: item.number)

    def snapshot(self):
        return list(Equipment.objects.order_by("pk").values())

    def read(self, client, url, method="get", **request_options):
        before = self.snapshot()
        with CaptureQueriesContext(connection) as captured:
            response = getattr(client, method)(url, **request_options)
        self.assertEqual(self.snapshot(), before)
        return response, [query["sql"] for query in captured]

    def client_as(self, role):
        client = Client()
        client.force_login(self.users[role])
        return client

    def assert_identity(self, response, role):
        self.assertContains(response, f"当前身份：{self.users[role].username}（{self.ROLE_LABELS[role]}）")
        self.assertContains(response, self.BOUNDARY_TEXT)

    def assert_no_equipment_disclosure(self, response, equipment):
        for item in equipment:
            for field in ("number", "name", "category", "location", "description"):
                self.assertNotContains(response, getattr(item, field), status_code=response.status_code)

    def assert_not_cached(self, response):
        directives = {directive.strip() for directive in response.headers.get("Cache-Control", "").split(",")}
        self.assertTrue({"no-store", "no-cache", "private"} <= directives)

    def assert_read_sql(self, queries, equipment_columns=None):
        # The only business table in this story is equipment. Session and account
        # selects are permitted for authentication, but no reservation/audit SQL is.
        table = Equipment._meta.db_table
        equipment_reads = []
        for sql in queries:
            self.assertRegex(sql, r"^SELECT\s")
            self.assertNotRegex(sql, r"\bFOR\s+(?:NO\s+KEY\s+UPDATE|KEY\s+SHARE|UPDATE|SHARE)\b")
            tables = set(re.findall(r'\b(?:FROM|JOIN)\s+"([^"]+)"', sql))
            self.assertTrue(tables <= {table, "accounts_user", "django_session"}, sql)
            if table in tables:
                equipment_reads.append(sql)
        if equipment_columns is None:
            self.assertEqual(equipment_reads, [])
        else:
            self.assertEqual(len(equipment_reads), 1)
            sql = equipment_reads[0]
            projection = sql.split(" FROM ", 1)[0]
            columns = re.findall(rf'"{table}"\."([^"]+)"', projection)
            self.assertCountEqual(columns, equipment_columns)
            return sql

    def test_ac1_catalog_rows_match_three_statuses_for_each_role(self):
        equipment = self.make_three_equipment()
        for role in self.ROLE_LABELS:
            with self.subTest(role=role):
                client = Client(enforce_csrf_checks=True)
                login_url = reverse("login")
                login, _ = self.read(client, login_url)
                self.assertContains(login, 'name="csrfmiddlewaretoken"')
                identity, _ = self.read(
                    client, login_url, "post", follow=True,
                    data={
                        "username": self.users[role].username,
                        "password": self.passwords[role],
                        "csrfmiddlewaretoken": client.cookies[settings.CSRF_COOKIE_NAME].value,
                    },
                )
                self.assertRedirects(identity, reverse("identity"), fetch_redirect_response=False)
                self.assertContains(identity, f"<dd>{self.users[role].username}</dd>", html=True)
                self.assertContains(identity, f"<dd>{self.ROLE_LABELS[role]}</dd>", html=True)
                self.assertContains(identity, f'<a href="{self.catalog_url}">查看设备目录</a>', html=True)
                response, queries = self.read(client, self.catalog_url)
                self.assert_identity(response, role)
                self.assert_not_cached(response)
                self.assertEqual(
                    [row["number"] for row in response.context["equipment_items"]],
                    [item.number for item in equipment],
                )
                self.assertContains(response, '<th scope="row">', count=3)
                self.assert_read_sql(queries, self.CATALOG_COLUMNS)
                for item in equipment:
                    detail_url = reverse("equipment-detail", args=[item.pk])
                    row = (
                        f'<tr><th scope="row"><a href="{detail_url}">{item.number}</a></th>'
                        f"<td>{item.name}</td><td>{item.category}</td><td>{item.location}</td>"
                        f"<td>{self.STATUS_LABELS[item.status]}</td></tr>"
                    )
                    self.assertContains(response, row, count=1, html=True)
                    self.assertNotContains(response, item.description)

    def test_ac2_catalog_links_and_direct_detail_match_each_target_for_each_role(self):
        equipment = self.make_three_equipment()
        for role in self.ROLE_LABELS:
            client = self.client_as(role)
            catalog, _ = self.read(client, self.catalog_url)
            for item in equipment:
                detail_url = reverse("equipment-detail", args=[item.pk])
                self.assertContains(catalog, f'<a href="{detail_url}">{item.number}</a>', html=True)
                visits = (
                    ("catalog link", {"HTTP_REFERER": self.catalog_url}),
                    ("direct", {}),
                )
                for visit, headers in visits:
                    with self.subTest(role=role, number=item.number, visit=visit):
                        response, queries = self.read(client, detail_url, **headers)
                        self.assert_identity(response, role)
                        self.assert_not_cached(response)
                        self.assert_read_sql(queries, self.DETAIL_COLUMNS)
                        details = (
                            ("设备编号", item.number), ("名称", item.name),
                            ("类别", item.category), ("位置", item.location),
                            ("说明", item.description), ("当前状态", self.STATUS_LABELS[item.status]),
                        )
                        description_attrs = ' id="equipment-description" style="white-space: pre-wrap"'
                        html = "<dl>" + "".join(
                            f'<dt>{label}</dt><dd{description_attrs if label == "说明" else ""}>{value}</dd>'
                            for label, value in details
                        ) + "</dl>"
                        self.assertContains(response, html, count=1, html=True)
                        self.assert_no_equipment_disclosure(response, [other for other in equipment if other != item])

    def test_ac2_description_keeps_multiline_literal_text_in_chrome(self):
        description = '第一行  保留连续空格\n第二行 <em>字面标签</em> & "引号"\n<script>/* 字面脚本 */</script>'
        item = Equipment.objects.create(
            number="CAT-R1", name="说明夹具", category="演示", location="实验室", description=description,
        )
        item.refresh_from_db(fields=["description"])
        self.assertEqual(item.description, description)
        response, _ = self.read(self.client_as(Role.STUDENT), reverse("equipment-detail", args=[item.pk]))
        self.assertContains(response, escape(description))

        chrome = os.environ.get("LAB_BOOKING_R1_CHROME")
        if not chrome:
            self.skipTest("Set LAB_BOOKING_R1_CHROME to opt in to the installed Chrome rendering check.")

        # Run a probe on the synthetic response from disk, without serving the Django app.
        probe = """<script>
        const description = document.getElementById("equipment-description");
        const lineTop = offset => {
            const range = document.createRange();
            range.setStart(description.firstChild, offset);
            range.setEnd(description.firstChild, offset + 1);
            return range.getBoundingClientRect().top;
        };
        const result = document.createElement("pre");
        result.id = "r1-measurement";
        result.textContent = JSON.stringify({
            whiteSpace: getComputedStyle(description).whiteSpace,
            text: description.innerText,
            lineTops: [lineTop(0), lineTop(description.textContent.indexOf("\\n") + 1)],
            children: description.childElementCount
        });
        document.body.append(result);
        </script>"""
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            snapshot = folder / "equipment-detail.html"
            snapshot.write_bytes(response.content.replace(b"</body>", probe.encode("utf-8") + b"</body>", 1))
            browser = subprocess.run(
                [
                    chrome, "--headless", "--no-first-run", "--disable-background-networking",
                    "--window-size=1024,768", f"--user-data-dir={folder / 'profile'}",
                    "--dump-dom", snapshot.as_uri(),
                ],
                capture_output=True, encoding="utf-8", errors="replace", timeout=30,
            )
        self.assertEqual(browser.returncode, 0, browser.stderr)
        result = re.search(r'<pre id="r1-measurement">(.*?)</pre>', browser.stdout, re.DOTALL)
        self.assertIsNotNone(result, "Chrome did not emit the layout measurements.")
        measurement = json.loads(unescape(result.group(1)))
        self.assertEqual(measurement["whiteSpace"], "pre-wrap")
        self.assertEqual(measurement["text"], description)
        self.assertGreater(measurement["lineTops"][1], measurement["lineTops"][0])
        self.assertEqual(measurement["children"], 0)

    def test_ac3_empty_catalog_returns_200_without_placeholder_rows(self):
        response, queries = self.read(self.client_as(Role.STUDENT), self.catalog_url)
        self.assertContains(response, "暂无设备")
        self.assertNotContains(response, "<tbody>")
        self.assertEqual(response.context["equipment_items"], [])
        self.assert_read_sql(queries, self.CATALOG_COLUMNS)

    def test_ac4_absent_equipment_returns_404_without_a_substitute(self):
        equipment = self.make_three_equipment()
        missing_pk = max(item.pk for item in equipment) + 1
        response, queries = self.read(self.client_as(Role.TEACHER), reverse("equipment-detail", args=[missing_pk]))
        self.assertContains(response, "<h1>设备不存在</h1>", html=True, status_code=404)
        self.assert_no_equipment_disclosure(response, equipment)
        self.assert_not_cached(response)
        self.assert_read_sql(queries, self.DETAIL_COLUMNS)

    def test_ac5_t03_anonymous_and_unknown_sessions_are_denied_on_both_routes(self):
        equipment = self.make_three_equipment()
        urls = (self.catalog_url, reverse("equipment-detail", args=[equipment[0].pk]))
        for session in ("absent", "unknown"):
            for url in urls:
                for method in ("get", "head"):
                    with self.subTest(session=session, url=url, method=method):
                        client = Client()
                        if session == "unknown":
                            client.cookies[settings.SESSION_COOKIE_NAME] = get_random_string(32)
                        response, queries = self.read(client, url, method)
                        login_url = f'{reverse("login")}?{urlencode({"next": url}, safe="/")}'
                        self.assertRedirects(response, login_url, fetch_redirect_response=False)
                        self.assert_no_equipment_disclosure(response, equipment)
                        self.assert_not_cached(response)
                        self.assert_read_sql(queries)

    def test_ac5_t03_active_roles_are_legal_controls_on_both_routes(self):
        equipment = self.make_three_equipment()
        target = equipment[0]
        endpoints = (
            (self.catalog_url, "设备目录", self.CATALOG_COLUMNS),
            (reverse("equipment-detail", args=[target.pk]), "设备详情", self.DETAIL_COLUMNS),
        )
        for role in self.ROLE_LABELS:
            client = self.client_as(role)
            for url, heading, columns in endpoints:
                for method in ("get", "head"):
                    with self.subTest(role=role, url=url, method=method):
                        response, queries = self.read(client, url, method)
                        self.assertEqual(response.status_code, 200)
                        self.assert_not_cached(response)
                        self.assert_read_sql(queries, columns)
                        if method == "head":
                            self.assertEqual(response.content, b"")
                        else:
                            self.assertContains(response, f"<h1>{heading}</h1>", html=True)
                            self.assertContains(response, target.number)
                            self.assert_identity(response, role)

    def test_inactive_or_invalid_role_cannot_read_even_with_django_admin_flags(self):
        equipment = self.make_three_equipment()
        urls = (self.catalog_url, reverse("equipment-detail", args=[equipment[0].pk]))
        for active, role in ((False, Role.ADMIN), (True, "invalid")):
            user = SimpleNamespace(is_authenticated=True, is_active=active, role=role, is_staff=True, is_superuser=True)
            # Invalid roles cannot be persisted. Inject the identity at the middleware boundary.
            with patch("django.contrib.auth.middleware.get_user", return_value=user):
                for url in urls:
                    with self.subTest(active=active, role=role, url=url):
                        response, queries = self.read(Client(), url)
                        self.assertContains(response, "无权查看设备资料", status_code=403)
                        self.assert_no_equipment_disclosure(response, equipment)
                        self.assert_not_cached(response)
                        self.assert_read_sql(queries)

    def test_catalog_and_detail_reject_post_without_querying_equipment(self):
        equipment = self.make_three_equipment()
        client = self.client_as(Role.ADMIN)
        for url in (self.catalog_url, reverse("equipment-detail", args=[equipment[0].pk])):
            with self.subTest(url=url):
                response, queries = self.read(client, url, "post")
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["Allow"], "GET, HEAD")
                self.assert_not_cached(response)
                self.assert_read_sql(queries)

    def test_ac6_repeat_reads_use_only_unlocked_selects_with_exact_projection(self):
        equipment = self.make_three_equipment()
        client = self.client_as(Role.STUDENT)
        baseline = self.snapshot()
        for round_number in range(3):
            with self.subTest(round=round_number):
                response, queries = self.read(client, self.catalog_url)
                self.assertEqual(response.status_code, 200)
                self.assert_read_sql(queries, self.CATALOG_COLUMNS)
                self.assertEqual(
                    [row["number"] for row in response.context["equipment_items"]],
                    [item.number for item in equipment],
                )
                for item in equipment:
                    response, queries = self.read(client, reverse("equipment-detail", args=[item.pk]))
                    self.assertContains(response, item.number)
                    sql = self.assert_read_sql(queries, self.DETAIL_COLUMNS)
                    self.assertRegex(sql, r'WHERE "equipment_equipment"\."id"\s*=')
        self.assertEqual(self.snapshot(), baseline)
