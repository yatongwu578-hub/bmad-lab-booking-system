from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.base import DatabaseWrapper as PostgreSQLWrapper

from lab_booking.database_config import (
    DATABASE_TARGETS,
    HOST,
    PORT,
    SERVER_VERSION_NUM,
    reject_connection_overrides,
)


class DatabaseWrapper(PostgreSQLWrapper):
    def get_new_connection(self, conn_params):
        reject_connection_overrides()
        database, role = DATABASE_TARGETS[settings.LAB_BOOKING_DB_MODE]
        expected = {
            "dbname": database,
            "user": role,
            "host": HOST,
            "hostaddr": HOST,
            "port": PORT,
        }
        if (
            any(conn_params.get(key) != value for key, value in expected.items())
            or not conn_params.get("passfile")
            or {"password", "service", "options"} & conn_params.keys()
            or self.settings_dict["OPTIONS"].get("assume_role")
        ):
            raise ImproperlyConfigured("数据库连接参数与已批准的目标不符。")

        connection = super().get_new_connection(conn_params)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database(), session_user, current_user, "
                    "host(inet_server_addr()), inet_server_port()"
                )
                actual = cursor.fetchone()
            if actual != (database, role, role, HOST, int(PORT)) or (
                connection.info.server_version != SERVER_VERSION_NUM
            ):
                raise ImproperlyConfigured("数据库实际库、角色、地址、端口或版本与批准值不符。")
            # Django sets autocommit and initializes its session after this returns.
            connection.rollback()
        except Exception:
            connection.close()
            raise
        return connection
