import os
import runpy
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLWrapper
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.test.runner import DiscoverRunner

from .database_config import CONFLICTING_ENVIRONMENT
from .postgresql.base import DatabaseWrapper
from .test_runner import IsolatedPostgresRunner


class DatabaseBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.wrapper = DatabaseWrapper({"OPTIONS": {}})
        self.params = {
            "dbname": "test_lab_booking",
            "user": "lab_booking_test",
            "host": "127.0.0.1",
            "hostaddr": "127.0.0.1",
            "port": "5433",
            "passfile": "synthetic-passfile",
        }

    def test_libpq_conflicts_rejected_before_driver_connection(self):
        with patch.object(PostgreSQLWrapper, "get_new_connection") as connect:
            for name in CONFLICTING_ENVIRONMENT:
                with self.subTest(name=name), patch.dict(os.environ, {name: "synthetic-value"}):
                    with self.assertRaisesMessage(ImproperlyConfigured, name) as failure:
                        self.wrapper.get_new_connection(self.params)
                    self.assertTrue("synthetic-value" not in str(failure.exception))
            connect.assert_not_called()

    def test_unapproved_driver_parameters_rejected_before_connection(self):
        with patch.object(PostgreSQLWrapper, "get_new_connection") as connect:
            for changes in (
                {"dbname": "postgres"},
                {"dbname": "lab_booking"},
                {"user": "lab_booking_migrator"},
                {"host": "localhost"},
                {"hostaddr": "::1"},
                {"port": "5432"},
                {"passfile": ""},
                {"password": "synthetic-value"},
                {"service": "synthetic-value"},
            ):
                with self.subTest(fields=tuple(changes)):
                    with self.assertRaisesMessage(ImproperlyConfigured, "数据库连接参数"):
                        self.wrapper.get_new_connection({**self.params, **changes})
            connect.assert_not_called()

    def test_actual_identity_or_version_mismatch_closes_connection(self):
        approved = ("test_lab_booking", "lab_booking_test", "lab_booking_test", "127.0.0.1", 5433)
        mismatches = [
            ("other_db", "other_session_user", "other_user", "::1", 5432)[index]
            for index in range(len(approved))
        ]
        cases = [(approved[:i] + (value,) + approved[i + 1:], 170012) for i, value in enumerate(mismatches)]
        cases.append((approved, 170011))
        for actual, version in cases:
            with self.subTest(actual=actual, version=version):
                with patch.object(PostgreSQLWrapper, "get_new_connection") as connect:
                    raw = connect.return_value
                    raw.info.server_version = version
                    raw.cursor.return_value.__enter__.return_value.fetchone.return_value = actual
                    with self.assertRaisesMessage(ImproperlyConfigured, "数据库实际库、角色、地址、端口或版本"):
                        self.wrapper.get_new_connection(self.params)
                    raw.close.assert_called_once_with()
                    raw.rollback.assert_not_called()


class TestRunnerBoundaryTests(SimpleTestCase):
    def test_runner_rejects_non_test_modes_and_parallel_execution_before_discovery(self):
        with patch.object(DiscoverRunner, "build_suite") as discover:
            for mode, parallel in (("runtime", 1), ("migration", 1), ("test", 2)):
                with self.subTest(mode=mode, parallel=parallel), override_settings(LAB_BOOKING_DB_MODE=mode):
                    with self.assertRaisesMessage(CommandError, "test 模式和单进程"):
                        IsolatedPostgresRunner(parallel=parallel).build_suite([])
            discover.assert_not_called()

    def test_runner_rejects_flush_based_tests(self):
        with patch.object(DiscoverRunner, "build_suite", return_value=[TransactionTestCase()]):
            with self.assertRaisesMessage(CommandError, "禁止 flush"):
                IsolatedPostgresRunner(parallel=1).build_suite([])

    def test_runner_stops_if_prebuilt_database_is_unavailable(self):
        runner = IsolatedPostgresRunner(parallel=1)
        with patch("lab_booking.test_runner.connections") as database_connections:
            database_connections.__iter__.return_value = iter(["default"])
            connection = database_connections.__getitem__.return_value
            connection.settings_dict = {"TEST": {"NAME": "test_lab_booking"}}
            connection.cursor.side_effect = DatabaseError("synthetic-value")
            with self.assertRaisesMessage(CommandError, "无法核验预建隔离测试库") as failure:
                runner.setup_databases(aliases={"default": False})
            self.assertTrue("synthetic-value" not in str(failure.exception))
            connection.cursor.assert_called_once_with()


class WebEntryTests(SimpleTestCase):
    def test_web_entrypoints_gate_mode_before_initialization(self):
        for mode in ("migration", "test"):
            with self.subTest(mode=mode), override_settings(LAB_BOOKING_DB_MODE=mode):
                with patch("django.core.wsgi.get_wsgi_application") as wsgi:
                    with self.assertRaisesMessage(ImproperlyConfigured, "WSGI 仅允许"):
                        runpy.run_module("lab_booking.wsgi")
                    wsgi.assert_not_called()
                with patch("django.core.management.commands.runserver.Command.execute") as runserver:
                    with self.assertRaisesMessage(CommandError, "runserver 仅允许"):
                        call_command("runserver", use_reloader=False)
                    runserver.assert_not_called()
