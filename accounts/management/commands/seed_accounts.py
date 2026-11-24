import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from accounts.forms import AccountAuthenticationForm
from accounts.models import Role, User


def unique_json_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON keys")
    return result


def read_manifest(path):
    try:
        with path.open(encoding="utf-8-sig") as source:
            rows = json.load(source, object_pairs_hook=unique_json_object)
    except (OSError, ValueError, RecursionError):
        raise CommandError("无法读取预置清单，或清单不是有效的 UTF-8 JSON。") from None

    if not isinstance(rows, list):
        raise CommandError("预置清单必须是 JSON 数组。")

    login_username = AccountAuthenticationForm.base_fields["username"]
    login_password = AccountAuthenticationForm.base_fields["password"]
    accounts = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or row.keys() != {"username", "role", "password"}:
            raise CommandError(f"预置清单第 {index} 项字段无效。")
        username, role, password = row["username"], row["role"], row["password"]
        if not isinstance(username, str) or role not in Role.values or not isinstance(password, str) or not password:
            raise CommandError(f"预置清单第 {index} 项字段值无效。")
        try:
            username = login_username.clean(username)
            login_password.clean(password)
            if "\r" in password or "\n" in password:
                raise ValidationError("密码须可通过浏览器单行输入。")
            password.encode("utf-8")
        except (ValidationError, UnicodeError):
            raise CommandError(f"预置清单第 {index} 项用户名或密码无效。") from None
        if username in accounts:
            raise CommandError(f"预置清单第 {index} 项的规范化用户名重复。")
        accounts[username] = (role, password)
    return accounts


def encode_password(password):
    user = User()
    user.set_password(password)
    return user.password


class Command(BaseCommand):
    help = "从受保护的 JSON 清单补齐预置账号。"

    def add_arguments(self, parser):
        parser.add_argument("--manifest", type=Path, required=True, help="受保护的 UTF-8 JSON 清单路径")

    def handle(self, *args, **options):
        if settings.LAB_BOOKING_DB_MODE not in {"migration", "test"}:
            raise CommandError("预置账号需要迁移模式，或专用的隔离测试模式。")

        accounts = read_manifest(options["manifest"])
        created_count = 0
        try:
            with transaction.atomic():
                # Lock accounts in a stable order when seed runs overlap.
                for username, (role, password) in sorted(accounts.items()):
                    user, created = User.objects.select_for_update().get_or_create(
                        username=username,
                        defaults={
                            "role": role,
                            "password": lambda: encode_password(password),
                            "is_staff": False,
                            "is_superuser": False,
                        },
                    )
                    if user.role != role:
                        raise CommandError("已有同名账号的业务角色不同，本批未写入。")
                    created_count += created
        except DatabaseError:
            raise CommandError("数据库拒绝预置操作，未能完成本批写入。") from None

        self.stdout.write(f"新增 {created_count}，跳过 {len(accounts) - created_count}。")
