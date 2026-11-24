from django.conf import settings
from django.core.management.base import CommandError
from django.db import DatabaseError, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.test.runner import DiscoverRunner, iter_test_cases

from .database_config import DATABASE_TARGETS, HOST, PORT


class IsolatedPostgresRunner(DiscoverRunner):
    """Run rollback-based tests on the already migrated Story 1.1 database."""

    def build_suite(self, *args, **kwargs):
        if settings.LAB_BOOKING_DB_MODE != "test" or self.parallel not in (0, 1):
            raise CommandError("隔离测试必须使用 test 模式和单进程。")
        suite = super().build_suite(*args, **kwargs)
        if any(
            isinstance(test, TransactionTestCase) and not isinstance(test, TestCase)
            for test in iter_test_cases(suite)
        ):
            raise CommandError("此测试入口只接受回滚式数据库测试，禁止 flush。")
        return suite

    def setup_databases(self, **kwargs):
        database, role = DATABASE_TARGETS["test"]
        if list(connections) != ["default"] or set(kwargs["aliases"]) - {"default"}:
            raise CommandError("隔离测试仅允许 default 数据库连接。")
        connection = connections["default"]
        if connection.settings_dict["TEST"]["NAME"] != database:
            raise CommandError("隔离测试配置必须指向预建的 test_lab_booking。")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication "
                    "OR rolbypassrls, has_database_privilege(current_user, %s, 'CONNECT') "
                    "FROM pg_roles WHERE rolname = current_user",
                    [DATABASE_TARGETS["runtime"][0]],
                )
                if cursor.fetchone() != (False, False):
                    raise CommandError("测试角色权限越界，已停止测试。")

            executor = MigrationExecutor(connection)
            executor.loader.check_consistent_history(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                raise CommandError("隔离库存在待迁移项，请核对预建隔离库。")
            before = self.database_state(connection)
            if before[2:] != (0, 0):
                raise CommandError("隔离测试库包含账号或会话，已停止测试。")
        except DatabaseError:
            raise CommandError("无法核验预建隔离测试库，请检查数据库与 PGPASSFILE。") from None
        self.log(f"已核验并保留 {HOST}:{PORT}/{database}，角色 {role}，PostgreSQL 17.12。")
        self.log(f"测试前：{len(before[0])} 张表、{len(before[1])} 条迁移、0 个账号、0 条会话。")
        return before

    def teardown_databases(self, before, **kwargs):
        connection = connections["default"]
        try:
            after = self.database_state(connection)
            if after != before:
                raise CommandError("隔离测试库前后状态不一致，请核对隔离库。")
            self.log(f"测试后：{len(after[0])} 张表、{len(after[1])} 条迁移、0 个账号、0 条会话。")
        finally:
            connection.close()

    @staticmethod
    def database_state(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            tables = cursor.fetchall()
            cursor.execute("SELECT app, name FROM public.django_migrations ORDER BY app, name")
            migrations = cursor.fetchall()
            cursor.execute("SELECT (SELECT count(*) FROM public.accounts_user), (SELECT count(*) FROM public.django_session)")
            accounts, sessions = cursor.fetchone()
        return tables, migrations, accounts, sessions
