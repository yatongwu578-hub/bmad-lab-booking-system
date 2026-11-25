from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event
from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connections, transaction
from django.db.migrations.executor import MigrationExecutor

from accounts.models import Role

from equipment.models import Equipment
from equipment.services import EquipmentNumberConflict, create_equipment
from lab_booking.database_config import DATABASE_TARGETS, HOST, PORT


class Command(BaseCommand):
    help = "在预建 test_lab_booking 中验证设备编号的真实并发唯一约束。"

    def handle(self, *args, **options):
        if settings.LAB_BOOKING_DB_MODE != "test":
            raise CommandError("事务验证仅允许 test 模式。")
        database, role = DATABASE_TARGETS["test"]
        if connections["default"].settings_dict["TEST"]["NAME"] != database:
            raise CommandError("事务验证仅允许预建 test_lab_booking。")
        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()")
            if cursor.fetchone() != (database, role, HOST, int(PORT)):
                raise CommandError("实际测试连接与批准目标不符。")
            cursor.execute("SHOW transaction_isolation")
            if cursor.fetchone()[0] != "read committed":
                raise CommandError("实际事务隔离级别不是 read committed。")
        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        if executor.migration_plan(executor.loader.graph.leaf_nodes()):
            raise CommandError("测试库存在未应用迁移，先核对迁移计划。")

        number = "EQ-AC6-CONCURRENCY-CHECK"
        if Equipment.objects.filter(number=number).exists():
            raise CommandError("合成并发编号已存在，拒绝覆盖或删除。")
        start_second = Event()
        first_inserted = Event()
        admin = SimpleNamespace(is_authenticated=True, is_active=True, role=Role.ADMIN)
        values = {"number": number, "name": "并发验证", "category": "合成", "location": "测试", "description": ""}

        def first_request():
            close_old_connections()
            try:
                with transaction.atomic():
                    Equipment.objects.create(**values)
                    first_inserted.set()
                    if not start_second.wait(5):
                        raise TimeoutError
                    with connections["default"].cursor() as cursor:
                        cursor.execute("SELECT pg_sleep(0.25)")
                return "created"
            finally:
                connections.close_all()

        def second_request():
            close_old_connections()
            try:
                if not first_inserted.wait(5):
                    raise CommandError("首个连接未及时插入。")
                start_second.set()
                try:
                    create_equipment(admin, values)
                except EquipmentNumberConflict:
                    return "duplicate"
            finally:
                connections.close_all()
            return "unexpected-success"

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(first_request)
                second = pool.submit(second_request)
                results = (first.result(timeout=10), second.result(timeout=10))
            count = Equipment.objects.filter(number=number).count()
            if results != ("created", "duplicate") or count != 1:
                raise CommandError(f"并发唯一约束结果不符合预期：{results}，最终记录数 {count}。")
            self.stdout.write("通过：独立连接并发新增一成功、一明确重复，最终一条记录。")
        except TimeoutError as error:
            raise CommandError("并发请求等待超时。") from error
        finally:
            Equipment.objects.filter(number=number, name="并发验证", category="合成", location="测试").delete()
