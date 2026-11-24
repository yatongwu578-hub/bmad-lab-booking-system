import json
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import Resolver404, resolve, reverse
from django.utils.crypto import get_random_string
from django.utils.html import escape
from django.utils.timezone import now

from .models import Role, User
from .views import identity


ROLE_LABELS = {"student": "学生", "teacher": "教师", "admin": "业务管理员"}
FORM_URLENCODED = "application/x-www-form-urlencoded"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.fields = None
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            self.fields = {}
            self.forms.append((attributes, self.fields))
        if tag == "input" and self.fields is not None and "name" in attributes:
            self.fields[attributes["name"]] = attributes

    def handle_endtag(self, tag):
        if tag == "form":
            self.fields = None


def seed_row(username, role):
    return {"username": username, "role": role, "password": get_random_string(24)}


def seed_accounts(rows):
    return seed_manifest(json.dumps(rows))


def seed_manifest(contents):
    with TemporaryDirectory() as folder:
        path = Path(folder) / "accounts.json"
        path.write_text(contents, encoding="utf-8")
        output = StringIO()
        call_command("seed_accounts", manifest=path, stdout=output)
    return output.getvalue().strip()


def submit_login_form(client, action, fields):
    return client.post(action, urlencode(fields), content_type=FORM_URLENCODED)


class AccountLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rows = [seed_row(f"example_{role}", role) for role in ROLE_LABELS]
        # Preserve whitespace and UTF-8 in a legal, single-line password.
        cls.rows[0]["password"] = f' 密{cls.rows[0]["password"]} '
        seed_accounts(cls.rows)

    def setUp(self):
        self.login_url = reverse("login")
        self.identity_url = reverse("identity")

    def credentials(self, row):
        return {"username": row["username"], "password": row["password"]}

    def account_state(self):
        return list(User.objects.order_by("pk").values())

    def rendered_form(self, response, expected_path, is_login=False):
        self.assertEqual(response.status_code, 200)
        parser = PageParser()
        parser.feed(response.content.decode(response.charset))
        self.assertEqual(len(parser.forms), 1)
        form, fields = parser.forms[0]
        self.assertEqual(form.get("method", "").lower(), "post")
        action = form.get("action") or response.wsgi_request.path
        self.assertEqual(action, expected_path)
        if is_login:
            self.assertEqual(form.get("enctype", FORM_URLENCODED), FORM_URLENCODED)
            for name, input_type in (("username", "text"), ("password", "password")):
                attrs = fields.get(name, {})
                self.assertEqual(attrs.get("type"), input_type)
                self.assertFalse("maxlength" in attrs, "登录输入可能在浏览器中被截断")
                self.assertFalse("data-max-code-points" in attrs, "登录输入仍启用脚本截断")
        csrf = fields.get("csrfmiddlewaretoken", {})
        self.assertEqual(csrf.get("type"), "hidden")
        self.assertTrue(bool(csrf.get("value")), "页面缺少 CSRF 字段值")
        return action, {"csrfmiddlewaretoken": csrf["value"]}

    def login_form(self, client):
        return self.rendered_form(client.get(self.login_url), self.login_url, is_login=True)

    def assert_rejected(self, response, status_code, before):
        self.assertEqual(response.status_code, status_code)
        content = response.content.decode(response.charset)
        protected_labels = ("我的身份", "业务角色", *ROLE_LABELS.values())
        self.assertFalse(any(value in content for value in protected_labels), "拒绝响应包含受保护的身份标签")
        parser = PageParser()
        parser.feed(content)
        page_text = "".join(parser.text)
        self.assertFalse(
            any(row["username"] in page_text for row in self.rows),
            "拒绝响应展示了受保护的账号",
        )
        self.assertTrue(self.account_state() == before, "拒绝请求改变了账号数据")

    def session_keys(self):
        return set(Session.objects.values_list("session_key", flat=True))

    def assert_sessions_unchanged(self, before):
        self.assertTrue(self.session_keys() == before, "拒绝请求改变了服务端会话集合")

    def assert_no_session_cookie(self, client):
        self.assertFalse(settings.SESSION_COOKIE_NAME in client.cookies, "拒绝请求设置了会话 Cookie")

    def assert_no_authenticated_user(self, response):
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def assert_session_user(self, client, session_key, user):
        cookie = client.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertTrue(cookie is not None and cookie.value == session_key, "认证会话标识未保留")
        self.assertTrue(Session.objects.filter(session_key=session_key).exists(), "服务端会话不存在")
        self.assertTrue(
            SessionStore(session_key=session_key).get(SESSION_KEY) == str(user.pk),
            "服务端会话身份不符",
        )

    def assert_redirect_to_login(self, client):
        before = self.account_state()
        response = client.get(self.identity_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.identity_url}", fetch_redirect_response=False)
        self.assert_rejected(response, 302, before)
        self.assert_no_authenticated_user(response)

    def test_ac1_preset_roles_log_in_and_refresh(self):
        for row in self.rows:
            with self.subTest(role=row["role"]):
                client = Client(enforce_csrf_checks=True)
                action, fields = self.login_form(client)
                user = User.objects.get(username=row["username"])
                self.assertIsNone(user.last_login)
                response = submit_login_form(client, action, {**fields, **self.credentials(row)})
                self.assertRedirects(response, self.identity_url, fetch_redirect_response=False)
                self.assertTrue(client.cookies[settings.SESSION_COOKIE_NAME]["httponly"])
                self.assert_session_user(client, client.cookies[settings.SESSION_COOKIE_NAME].value, user)
                for _ in range(2):
                    result = client.get(self.identity_url)
                    self.assertContains(result, row["username"])
                    self.assertContains(result, f"<dd>{ROLE_LABELS[row['role']]}</dd>", html=True)
                    self.assertIn("no-store", result["Cache-Control"])
                user.refresh_from_db()
                self.assertEqual(user.role, row["role"])
                self.assertIsNotNone(user.last_login)
                self.assertFalse(user.is_staff)
                self.assertFalse(user.is_superuser)

    def test_ac1_rendered_login_supports_76_supplementary_username_code_points(self):
        username = "\U00020000" * 76
        row = seed_row(username, Role.STUDENT)
        seed_accounts([row])
        user = User.objects.get(username=username)
        client = Client(enforce_csrf_checks=True)
        action, fields = self.login_form(client)
        login = submit_login_form(client, action, {**fields, **self.credentials(row)})
        self.assertRedirects(login, self.identity_url, fetch_redirect_response=False)
        identity_page = client.get(self.identity_url)
        self.assertContains(identity_page, username)
        self.assertContains(identity_page, f"<dd>{ROLE_LABELS[Role.STUDENT]}</dd>", html=True)
        self.assertEqual(client.session[SESSION_KEY], str(user.pk))

    def test_ac1_username_at_code_point_limit_keeps_whitespace_for_django(self):
        cases = (
            ("supplementary", "\U00020000" * 150, "\U00020000" * 150, 300),
            ("mixed", "\U00020000Ａ" * 75, "\U00020000A" * 75, 225),
        )
        for case, raw, normalized, utf16_units in cases:
            with self.subTest(case=case):
                self.assertEqual(len(raw), 150)
                self.assertEqual(len(raw.encode("utf-16-le")) // 2, utf16_units)
                row = seed_row(f" \u3000{raw} ", Role.TEACHER)
                self.assertEqual(seed_accounts([row]), "新增 1，跳过 0。")
                user = User.objects.get(username=normalized)
                client = Client(enforce_csrf_checks=True)
                action, fields = self.login_form(client)
                response = submit_login_form(client, action, {**fields, **self.credentials(row)})
                self.assertRedirects(response, self.identity_url, fetch_redirect_response=False)
                self.assert_session_user(client, client.cookies[settings.SESSION_COOKIE_NAME].value, user)
                self.assertContains(client.get(self.identity_url), normalized)

    def test_invalid_usernames_are_rejected_from_rendered_form_and_seed(self):
        cases = (
            ("151_code_points", "\U00020000a" * 75 + "b", "max_length"),
            ("nfkc_expansion", "\ufb00" + "a" * 149, "max_length"),
            ("internal_space", "invalid username", "invalid"),
            ("forbidden_character", "invalid/username", "invalid"),
        )
        for case, username, error_code in cases:
            with self.subTest(case=case):
                row = seed_row(username, Role.ADMIN)
                before = self.account_state()
                sessions = self.session_keys()
                with self.assertRaisesMessage(CommandError, "用户名或密码无效") as failure:
                    seed_accounts([seed_row("a_new", Role.STUDENT), row])
                self.assertFalse(username in str(failure.exception), "清单校验错误泄露用户名")
                self.assertTrue(self.account_state() == before, "非法用户名改变了账号数据")

                client = Client(enforce_csrf_checks=True)
                action, fields = self.login_form(client)
                response = submit_login_form(client, action, {**fields, **self.credentials(row)})
                self.assert_rejected(response, 200, before)
                form = response.context["form"]
                self.assertTrue(form.has_error("username", error_code), "用户名缺少预期字段错误")
                self.assertContains(response, escape(form.errors["username"][0]))
                self.assert_no_session_cookie(client)
                self.assert_no_authenticated_user(response)
                self.assert_sessions_unchanged(sessions)

    def test_login_form_rejects_password_over_shared_maximum(self):
        password = "\U00020000" * 4096
        row = {**seed_row("valid_password_prefix", Role.TEACHER), "password": password}
        seed_accounts([row])
        client = Client(enforce_csrf_checks=True)
        action, fields = self.login_form(client)
        before = self.account_state()
        sessions = self.session_keys()
        payload = {**fields, "username": row["username"], "password": password + "x"}
        with patch("django.contrib.auth.forms.authenticate") as authenticate:
            response = submit_login_form(client, action, payload)
        self.assertFalse(authenticate.called, "超限密码仍触发了认证")
        self.assert_rejected(response, 200, before)
        self.assert_no_session_cookie(client)
        self.assert_no_authenticated_user(response)
        self.assert_sessions_unchanged(sessions)
        form = response.context["form"]
        self.assertTrue(form.has_error("password", "max_length"), "超限密码缺少长度错误")
        self.assertContains(response, escape(form.errors["password"][0]))

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
                client = Client(enforce_csrf_checks=True)
                action, fields = self.login_form(client)
                before = self.account_state()
                sessions = self.session_keys()
                response = client.post(action, {**fields, **payload})
                self.assert_rejected(response, 200, before)
                self.assert_no_session_cookie(client)
                self.assert_no_authenticated_user(response)
                self.assert_sessions_unchanged(sessions)
                self.assertContains(response, 'class="errorlist')
                errors = [error for group in response.context["form"].errors.values() for error in group]
                self.assertTrue(bool(errors), "失败表单缺少校验消息")
                for error in errors:
                    self.assertContains(response, escape(error))
                self.assert_redirect_to_login(client)

    def test_ac3_anonymous_and_invalid_session_are_redirected(self):
        for invalid_cookie in (False, True):
            with self.subTest(invalid_cookie=invalid_cookie):
                client = Client()
                if invalid_cookie:
                    client.cookies[settings.SESSION_COOKIE_NAME] = get_random_string(32)
                sessions = self.session_keys()
                self.assert_redirect_to_login(client)
                self.assert_sessions_unchanged(sessions)

    def test_identity_rejects_disabled_account(self):
        row = self.rows[0]
        user = User.objects.get(username=row["username"])
        client = Client()
        client.force_login(user)
        user.is_active = False
        user.save(update_fields=["is_active"])
        sessions = self.session_keys()
        self.assert_redirect_to_login(client)
        self.assert_sessions_unchanged(sessions)

    def test_identity_direct_view_rejects_invalid_role(self):
        user = User.objects.get(role=Role.STUDENT)
        user.role = "invalid"
        before = self.account_state()
        request = RequestFactory().get(self.identity_url)
        request.user = user
        with self.assertRaises(PermissionDenied):
            identity(request)
        self.assertTrue(self.account_state() == before, "拒绝非法角色后账号数据有变化")

    def test_ac4_server_role_ignores_forged_values_and_management_flags(self):
        student = User.objects.get(role=Role.STUDENT)
        student.is_staff = True
        student.is_superuser = True
        student.save(update_fields=["is_staff", "is_superuser"])
        target = User.objects.get(role=Role.ADMIN)
        forged = {"role": target.role, "user_id": target.pk}
        student_row = next(row for row in self.rows if row["role"] == Role.STUDENT)
        client = Client(enforce_csrf_checks=True)
        action, fields = self.login_form(client)
        login = client.post(action, {**fields, **self.credentials(student_row), **forged})
        self.assertRedirects(login, self.identity_url, fetch_redirect_response=False)
        response = client.get(self.identity_url, forged)
        self.assertContains(response, student.username)
        self.assertContains(response, ROLE_LABELS["student"])
        self.assertNotContains(response, target.username)
        self.assertNotContains(response, ROLE_LABELS["admin"])
        student.refresh_from_db()
        target.refresh_from_db()
        self.assertEqual(student.role, Role.STUDENT)
        self.assertEqual(target.role, Role.ADMIN)
        self.assertIsNone(target.last_login)

    def test_identity_rejects_post_without_account_changes(self):
        user = User.objects.get(role=Role.STUDENT)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        key = client.cookies[settings.SESSION_COOKIE_NAME].value
        _, fields = self.rendered_form(client.get(self.identity_url), reverse("logout"))
        before = self.account_state()
        result = client.post(self.identity_url, {**fields, "role": Role.ADMIN})
        self.assert_rejected(result, 405, before)
        self.assert_session_user(client, key, user)

    def test_ac5_rendered_logout_ends_server_session_with_or_without_next(self):
        user = User.objects.get(role=Role.STUDENT)
        for extra_fields in ({}, {"next": reverse("logout")}):
            with self.subTest(has_next=bool(extra_fields)):
                client = Client(enforce_csrf_checks=True)
                action, fields = self.login_form(client)
                response = client.post(action, {**fields, **self.credentials(self.rows[0])})
                self.assertRedirects(response, self.identity_url, fetch_redirect_response=False)
                key = client.cookies[settings.SESSION_COOKIE_NAME].value
                self.assert_session_user(client, key, user)
                action, fields = self.rendered_form(client.get(self.identity_url), reverse("logout"))
                before = self.account_state()
                result = client.post(action, {**fields, **extra_fields})
                self.assertRedirects(result, self.login_url, fetch_redirect_response=False)
                self.assertFalse(Session.objects.filter(session_key=key).exists(), "退出后原服务端会话仍存在")
                self.assertTrue(self.account_state() == before, "退出改变了账号数据")
                self.assert_redirect_to_login(client)
                client.cookies[settings.SESSION_COOKIE_NAME] = key
                self.assert_redirect_to_login(client)

    def test_ac5_logout_refuses_get_and_missing_or_invalid_csrf(self):
        user = User.objects.get(role=Role.STUDENT)
        for method, fields, expected in (
            ("get", {}, 405),
            ("post", {}, 403),
            ("post", {"csrfmiddlewaretoken": "invalid"}, 403),
        ):
            with self.subTest(method=method, has_token=bool(fields)):
                client = Client(enforce_csrf_checks=True)
                client.force_login(user)
                key = client.cookies[settings.SESSION_COOKIE_NAME].value
                action, _ = self.rendered_form(client.get(self.identity_url), reverse("logout"))
                before = self.account_state()
                result = getattr(client, method)(action, fields)
                self.assert_rejected(result, expected, before)
                self.assert_session_user(client, key, user)
                self.assertEqual(client.get(self.identity_url).status_code, 200)

    def test_ac5_missing_and_invalid_csrf_tokens_are_denied(self):
        for payload in ({}, {"csrfmiddlewaretoken": get_random_string(64)}):
            with self.subTest(has_token=bool(payload)):
                client = Client(enforce_csrf_checks=True)
                action, _ = self.login_form(client)
                before = self.account_state()
                sessions = self.session_keys()
                response = client.post(action, {**self.credentials(self.rows[0]), **payload})
                self.assert_rejected(response, 403, before)
                self.assert_sessions_unchanged(sessions)
                self.assert_no_session_cookie(client)
                self.assert_no_authenticated_user(response)

    def test_ac6_admin_and_self_registration_routes_are_absent(self):
        for path in ("/admin/", "/register/", "/accounts/register/"):
            with self.subTest(path=path):
                before = self.account_state()
                sessions = self.session_keys()
                client = Client()
                with self.assertRaises(Resolver404):
                    resolve(path)
                response = client.get(path)
                self.assert_rejected(response, 404, before)
                self.assert_no_session_cookie(client)
                self.assert_sessions_unchanged(sessions)

    def test_failed_cookie_assertion_does_not_disclose_value(self):
        client = Client()
        marker = get_random_string(32)
        client.cookies[settings.SESSION_COOKIE_NAME] = marker
        with self.assertRaises(AssertionError) as failure:
            self.assert_no_session_cookie(client)
        self.assertTrue(marker not in str(failure.exception), "失败断言泄露会话标识")


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
        for label, bad_row in (
            ("duplicate_normalized_username", seed_row(" Ｂatch ", Role.TEACHER)),
            ("invalid_username", seed_row("invalid username", Role.TEACHER)),
            ("invalid_role", seed_row("b_invalid_role", "other")),
            ("missing_password", {"username": "b_missing_password", "role": Role.STUDENT}),
        ):
            with self.subTest(case=label):
                before = list(User.objects.order_by("pk").values())
                with self.assertRaises(CommandError) as error:
                    seed_accounts([seed_row("Batch", Role.STUDENT), bad_row])
                for value in bad_row.values():
                    self.assertTrue(value not in str(error.exception), "清单校验错误泄露输入字段")
                self.assertEqual(list(User.objects.order_by("pk").values()), before)

    def test_seed_rejects_unusable_login_passwords_without_changing_existing_hash(self):
        seed_accounts([seed_row("existing", Role.STUDENT)])
        before = list(User.objects.values())
        for label, character in (("nul", "\x00"), ("cr", "\r"), ("lf", "\n"), ("surrogate", "\ud800")):
            with self.subTest(case=label):
                invalid = f"{get_random_string(24)}{character}"
                with self.assertRaisesMessage(CommandError, "用户名或密码无效") as failure:
                    seed_accounts([
                        seed_row("a_new", Role.TEACHER),
                        {**seed_row("existing", Role.STUDENT), "password": invalid},
                    ])
                self.assertTrue(invalid[:-1] not in str(failure.exception), "密码校验错误泄露输入")
                self.assertTrue(list(User.objects.values()) == before, "密码错误时账号或哈希有变化")

    def test_seed_password_maximum_is_shared_with_rendered_login_form(self):
        existing = seed_row("password_boundary", Role.STUDENT)
        seed_accounts([existing])
        first = User.objects.get(username=existing["username"])
        original = first.password
        max_password = "\U00020000" * 4096
        self.assertEqual(len(max_password.encode("utf-16-le")) // 2, 8192)
        boundary = {**seed_row("password_limit", Role.TEACHER), "password": max_password}
        self.assertEqual(seed_accounts([boundary]), "新增 1，跳过 0。")
        boundary_user = User.objects.get(username=boundary["username"])
        boundary_hash = boundary_user.password

        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse("login"))
        parser = PageParser()
        parser.feed(response.content.decode(response.charset))
        form_attrs, rendered_fields = parser.forms[0]
        action = form_attrs.get("action") or response.wsgi_request.path
        csrf_value = rendered_fields["csrfmiddlewaretoken"]["value"]
        login = submit_login_form(client, action, {
            "csrfmiddlewaretoken": csrf_value,
            "username": boundary["username"],
            "password": max_password,
        })
        self.assertRedirects(login, reverse("identity"), fetch_redirect_response=False)
        self.assertEqual(client.session[SESSION_KEY], str(User.objects.get(username=boundary["username"]).pk))

        before = list(User.objects.order_by("pk").values())
        over_limit = {**boundary, "password": max_password + "x"}
        with self.assertRaisesMessage(CommandError, "用户名或密码无效"):
            seed_accounts([over_limit])
        first.refresh_from_db()
        self.assertEqual(first.password, original, "超长输入改变了原有账号哈希")
        self.assertEqual(list(User.objects.order_by("pk").values()), before)
        self.assertEqual(seed_accounts([boundary]), "新增 0，跳过 1。")
        boundary_user.refresh_from_db()
        self.assertEqual(boundary_user.password, boundary_hash, "重复初始化改变了原有账号哈希")
        first.refresh_from_db()
        self.assertEqual(first.password, original, "重复初始化改变了其他已有账号哈希")

    def test_seed_rejects_password_that_exceeds_shared_form_maximum(self):
        existing = seed_row("z_existing", Role.ADMIN)
        seed_accounts([existing])
        before = list(User.objects.order_by("pk").values())
        invalid = {**existing, "password": "x" * 4097}
        with (
            patch("accounts.management.commands.seed_accounts.transaction.atomic") as atomic,
            self.assertRaisesMessage(CommandError, "用户名或密码无效") as failure,
        ):
            seed_accounts([seed_row("a_new", Role.STUDENT), invalid])
        atomic.assert_not_called()
        self.assertFalse(invalid["password"] in str(failure.exception), "清单校验错误泄露密码")
        self.assertTrue(list(User.objects.order_by("pk").values()) == before, "超长密码改变了账号数据")

    @override_settings(LAB_BOOKING_DB_MODE="runtime")
    def test_seed_runtime_rejects_before_reading_or_writing(self):
        before = list(User.objects.values())
        with (
            patch("accounts.management.commands.seed_accounts.read_manifest") as read_manifest,
            patch("accounts.management.commands.seed_accounts.transaction.atomic") as atomic,
            self.assertRaisesMessage(CommandError, "预置账号需要迁移模式"),
        ):
            call_command("seed_accounts", manifest=Path("synthetic.json"))
        read_manifest.assert_not_called()
        atomic.assert_not_called()
        self.assertTrue(list(User.objects.values()) == before, "运行模式预置改变了账号数据")

    def test_seed_rejects_duplicate_raw_json_keys_without_writing(self):
        valid = seed_row("a_new", Role.STUDENT)
        marker = get_random_string(24)
        duplicate = f'{{"username":"b_new","role":"teacher","password":"{marker}","password":"{marker}"}}'
        before = list(User.objects.values())
        with self.assertRaisesMessage(CommandError, "不是有效的 UTF-8 JSON") as failure:
            seed_manifest(f"[{json.dumps(valid)},{duplicate}]")
        self.assertTrue(marker not in str(failure.exception), "重复键错误泄露输入")
        self.assertTrue(list(User.objects.values()) == before, "重复键清单产生写入")
        self.assertEqual(seed_accounts([valid]), "新增 1，跳过 0。")
