import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase
from django.urls import Resolver404, resolve, reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from .models import Role, User
from .views import identity


def seed_row(username, role):
    return {"username": username, "role": role, "password": get_random_string(24)}


def seed_accounts(rows):
    with TemporaryDirectory() as folder:
        path = Path(folder) / "accounts.json"
        path.write_text(json.dumps(rows), encoding="utf-8")
        output = StringIO()
        call_command("seed_accounts", manifest=path, stdout=output)
    return output.getvalue().strip()


class AccountLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rows = [seed_row(f"example_{role}", role.value) for role in Role]
        seed_accounts(cls.rows)

    def setUp(self):
        self.login_url = reverse("login")
        self.identity_url = reverse("identity")

    def credentials(self, row):
        return {"username": row["username"], "password": row["password"]}

    def account_state(self):
        return list(User.objects.order_by("pk").values())

    def assert_no_access(self, client, response):
        self.assertNotContains(response, "我的身份", status_code=response.status_code)
        for row in self.rows:
            self.assertNotContains(response, row["username"], status_code=response.status_code)
        if settings.SESSION_COOKIE_NAME in client.cookies:
            self.assertNotIn(SESSION_KEY, client.session)

    def assert_redirect_to_login(self, client):
        response = client.get(self.identity_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.identity_url}", fetch_redirect_response=False)
        self.assert_no_access(client, response)

    def test_ac1_preset_roles_log_in_and_refresh(self):
        for row in self.rows:
            with self.subTest(role=row["role"]):
                client = Client()
                login_page = client.get(self.login_url)
                self.assertContains(login_page, "登录实验室设备预约系统")
                user = User.objects.get(username=row["username"])
                self.assertIsNone(user.last_login)
                response = client.post(self.login_url, self.credentials(row))
                self.assertRedirects(response, self.identity_url, fetch_redirect_response=False)
                self.assertEqual(client.session[SESSION_KEY], str(user.pk))
                for _ in range(2):
                    result = client.get(self.identity_url)
                    self.assertContains(result, row["username"])
                    self.assertContains(result, Role(row["role"]).label)
                    self.assertIn("no-store", result["Cache-Control"])
                user.refresh_from_db()
                self.assertIsNotNone(user.last_login)
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)

    def test_ac2_unknown_wrong_and_missing_credentials_are_denied(self):
        row = self.rows[0]
        cases = {
            "unknown_username": {"username": "unregistered_example", "password": row["password"]},
            "wrong_password": {"username": row["username"], "password": get_random_string(30)},
            "missing_username": {"password": row["password"]},
            "missing_password": {"username": row["username"]},
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                client = Client()
                before = self.account_state()
                response = client.post(self.login_url, payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertNotContains(response, "我的身份")
                self.assertNotIn(settings.SESSION_COOKIE_NAME, client.cookies)
                self.assert_redirect_to_login(client)
                self.assertTrue(self.account_state() == before, "拒绝登录后账号数据有变化")

    def test_ac3_anonymous_and_invalid_session_are_redirected(self):
        before = self.account_state()
        client = Client()
        self.assert_redirect_to_login(client)
        client.cookies[settings.SESSION_COOKIE_NAME] = get_random_string(32)
        self.assert_redirect_to_login(client)
        self.assertTrue(self.account_state() == before, "未认证访问后账号数据有变化")

    def test_identity_rejects_disabled_accounts_and_invalid_roles(self):
        row = self.rows[0]
        user = User.objects.get(username=row["username"])
        client = Client()
        client.force_login(user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        before = self.account_state()
        result = client.get(self.identity_url)
        self.assertRedirects(result, f"{self.login_url}?next={self.identity_url}", fetch_redirect_response=False)
        self.assertNotContains(result, user.username, status_code=302)
        self.assertTrue(self.account_state() == before, "已禁用账号访问后账号数据有变化")

        user.is_active = True
        user.role = "invalid"
        request = RequestFactory().get(self.identity_url)
        request.user = user
        with self.assertRaises(PermissionDenied):
            identity(request)

    def test_ac4_server_role_ignores_forged_values_and_management_flags(self):
        student = User.objects.get(role=Role.STUDENT)
        student.is_staff = True
        student.is_superuser = True
        student.save(update_fields=["is_staff", "is_superuser"])
        target = User.objects.get(role=Role.ADMIN)
        forged = {"role": target.role, "user_id": target.pk}
        student_row = next(row for row in self.rows if row["role"] == Role.STUDENT)
        self.client.post(self.login_url, {**self.credentials(student_row), **forged})
        response = self.client.get(self.identity_url, forged)
        self.assertContains(response, student.username)
        self.assertContains(response, Role.STUDENT.label)
        self.assertNotContains(response, target.username)
        self.assertNotContains(response, Role.ADMIN.label)
        student.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual(student.role, Role.STUDENT)
        self.assertEqual(target.role, Role.ADMIN)
        self.assertIsNone(target.last_login)

    def test_identity_rejects_post_without_account_changes(self):
        user = User.objects.get(role=Role.STUDENT)
        self.client.force_login(user)
        before = self.account_state()
        result = self.client.post(self.identity_url, {"role": Role.ADMIN})
        self.assertNotContains(result, user.username, status_code=405)
        self.assertTrue(self.account_state() == before, "拒绝身份页写请求后账号数据有变化")

    def test_ac5_csrf_valid_token_authenticates(self):
        client = Client(enforce_csrf_checks=True)
        token = str(client.get(self.login_url).context["csrf_token"])
        response = client.post(self.login_url, {**self.credentials(self.rows[0]), "csrfmiddlewaretoken": token})
        self.assertRedirects(response, self.identity_url)
        self.assertIn(SESSION_KEY, client.session)

    def test_ac5_missing_and_invalid_csrf_tokens_are_denied(self):
        for payload in ({}, {"csrfmiddlewaretoken": get_random_string(64)}):
            with self.subTest(has_token=bool(payload)):
                client = Client(enforce_csrf_checks=True)
                client.get(self.login_url)
                before = self.account_state()
                session_count = Session.objects.count()
                response = client.post(self.login_url, {**self.credentials(self.rows[0]), **payload})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(Session.objects.count(), session_count)
                self.assert_no_access(client, response)
                self.assertTrue(self.account_state() == before, "拒绝 CSRF 请求后账号数据有变化")

    def test_ac6_admin_and_self_registration_routes_are_absent(self):
        before = self.account_state()
        for path in ("/admin/", "/register/", "/accounts/register/"):
            with self.subTest(path=path):
                with self.assertRaises(Resolver404):
                    resolve(path)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assert_no_access(self.client, response)
        self.assertTrue(self.account_state() == before, "未匹配的路由修改了账号数据")


class AccountStorageTests(TestCase):
    def test_role_is_required_and_constrained_by_database(self):
        for label, fields in (
            ("omitted", {}),
            ("null", {"role": None}),
            ("empty", {"role": ""}),
            ("unknown", {"role": "other"}),
        ):
            with self.subTest(role=label):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    User.objects.create(username="bad_role", **fields)
        self.assertEqual(User.objects.count(), 0)

    def test_seed_first_run_and_rerun_preserve_existing_fields_and_permissions(self):
        row = seed_row("  Ｐreset  ", Role.TEACHER)
        self.assertEqual(seed_accounts([row]), "新增 1，跳过 0。")
        account = User.objects.get(username="Preset")
        self.assertTrue(account.password != row["password"], "预置密码未以哈希存储")
        self.assertTrue(account.check_password(row["password"]))
        self.assertFalse(account.is_staff)
        self.assertFalse(account.is_superuser)
        self.assertFalse(account.groups.exists())
        self.assertFalse(account.user_permissions.exists())

        account.is_active = False
        account.is_staff = True
        account.is_superuser = True
        account.last_login = now()
        account.save()
        group = Group.objects.create(name="existing_group")
        permission = Permission.objects.get(content_type__app_label="accounts", codename="view_user")
        account.groups.add(group)
        account.user_permissions.add(permission)
        before = User.objects.filter(pk=account.pk).values().get()
        self.assertEqual(seed_accounts([seed_row("Preset", Role.TEACHER)]), "新增 0，跳过 1。")
        self.assertTrue(User.objects.filter(pk=account.pk).values().get() == before, "重跑后已有账号字段有变化")
        self.assertEqual(list(account.groups.all()), [group])
        self.assertEqual(list(account.user_permissions.all()), [permission])

    def test_seed_role_conflict_rolls_back_whole_batch(self):
        seed_accounts([seed_row("z_existing", Role.TEACHER)])
        before = list(User.objects.values())
        with self.assertRaisesMessage(CommandError, "已有同名账号的业务角色不同"):
            seed_accounts([seed_row("a_missing", Role.ADMIN), seed_row("z_existing", Role.STUDENT)])
        self.assertTrue(list(User.objects.values()) == before, "冲突后本批没有完整回滚")

    def test_seed_duplicate_normalized_username_or_invalid_row_rejects_batch(self):
        for bad_row in (
            seed_row(" Ｂatch ", Role.TEACHER),
            seed_row("invalid username", Role.TEACHER),
            seed_row("b_invalid_role", "other"),
            {"username": "b_missing_password", "role": Role.STUDENT},
        ):
            with self.subTest(case=len(bad_row)):
                with self.assertRaises(CommandError) as error:
                    seed_accounts([seed_row("Batch", Role.STUDENT), bad_row])
                for value in bad_row.values():
                    self.assertTrue(value not in str(error.exception), "清单校验错误泄露输入字段")
                self.assertEqual(User.objects.count(), 0)
