import re
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import Error, connections, transaction
from django.test import Client
from django.urls import reverse

from accounts.models import Role, User
from equipment.models import Equipment, EquipmentStatus
from equipment.services import EQUIPMENT_EDIT_FIELDS
from lab_booking.database_config import DATABASE_TARGETS, HOST, PORT, SERVER_VERSION_NUM
from lab_booking.test_runner import IsolatedPostgresRunner


def require(condition, message):
    if not condition:
        raise CommandError(message)


def query(connection, sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone() if cursor.description else None


def wait_for(check, label):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        result = check()
        if result:
            return result
        sleep(0.025)
    raise CommandError(f"等待超时：{label}")


def verify_target(connection):
    database, role = DATABASE_TARGETS["test"]
    actual = query(
        connection,
        "SELECT current_database(), session_user, current_user, host(inet_server_addr()), "
        "inet_server_port(), current_setting('server_version_num'), current_setting('transaction_isolation'), "
        "pg_backend_pid(), rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls, "
        "has_database_privilege(current_user, %s, 'CONNECT') FROM pg_roles WHERE rolname = current_user",
        [DATABASE_TARGETS["runtime"][0]],
    )
    require(actual is not None and actual[:7] == (
        database, role, role, HOST, int(PORT), str(SERVER_VERSION_NUM), "read committed",
    ) and actual[8:] == (False, False), "隔离连接实际目标、权限或隔离级别不符。")
    query(connection, "SET statement_timeout = '12s'")
    query(connection, "SET lock_timeout = '10s'")
    return actual[7]


def snapshot(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, number, name, category, location, description, status "
            "FROM equipment_equipment ORDER BY id"
        )
        columns = [column.name for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def expected_rows(before, pk, **updates):
    return [{**row, **updates} if row["id"] == pk else row for row in before]


def is_equipment_statement(sql):
    return '"equipment_equipment"' in sql


def check_edit_sql(queries):
    require(len(queries) == 3, f"设备 SQL 数量非 3：{queries!r}")
    lock, reread, update = queries
    require(lock.startswith('SELECT "equipment_equipment"."id"') and "FOR UPDATE" in lock,
            f"首条设备 SQL 未按主键取锁：{lock}")
    require(reread.startswith("SELECT") and '"equipment_equipment"."status"' in reread
            and "FOR UPDATE" not in reread, f"未独立锁后重读状态：{reread}")
    set_clause = update.split(" WHERE ")[0]
    require(update.startswith("UPDATE ") and set(re.findall(r'"(\w+)"\s*=', set_clause))
            == set(EQUIPMENT_EDIT_FIELDS), f"UPDATE 列超出四列边界：{update}")
    require(all('"equipment_equipment"."id" =' in sql for sql in queries), "设备 SQL 未按主键定向。")


class Command(BaseCommand):
    help = "使用预建隔离测试库验证设备编辑的真实锁等待、回滚和未知提交。"

    def handle(self, *args, **options):
        database = DATABASE_TARGETS["test"][0]
        require(settings.LAB_BOOKING_DB_MODE == "test" and list(connections) == ["default"],
                "此命令仅允许使用 test 模式的默认连接。")
        app = connections["default"]
        require(app.settings_dict["TEST"]["NAME"] == database, "未配置预建 test_lab_booking。")
        observer = app.copy(alias="story14-observer")
        try:
            observer_pid = verify_target(observer)
            verify_target(app)
            runner = IsolatedPostgresRunner(verbosity=0, parallel=1, keepdb=True)
            # Reuse the existing migration and fixture checks, not a migration or flush.
            db_before = runner.setup_databases(aliases={"default": True})
            rows_before = snapshot(observer)
            user_tag = f"story14-probe-{uuid4().hex}"
            prefix = f"E14-{uuid4().hex[:20]}-"
            require(not Equipment.objects.filter(number__startswith=prefix).exists()
                    and not User.objects.filter(username=user_tag).exists(), "隔离夹具标识已存在。")
            client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")
            self.stdout.write(f"隔离观察连接 PID {observer_pid}，{HOST}:{PORT}/{database}，Read Committed。")
            try:
                admin = User.objects.create_user(username=user_tag, role=Role.ADMIN)
                client.force_login(admin)
                self.make_equipment(prefix + "other")
                index = 0
                for status in (EquipmentStatus.MAINTENANCE, EquipmentStatus.DISABLED):
                    for blocking in (False, True):
                        equipment = self.make_equipment(prefix + str(index))
                        index += 1
                        self.interleave(observer, observer_pid, client, equipment, status, blocking)
                for fault in ("write-rollback", "commit-rejected", "commit-pre-disconnect", "commit-lost-ack"):
                    equipment = self.make_equipment(prefix + str(index))
                    index += 1
                    self.fault(observer, observer_pid, client, equipment, fault)
                for case, active, role in (
                    ("account-inactive", False, Role.ADMIN),
                    ("role-revoked", True, Role.STUDENT),
                ):
                    equipment = self.make_equipment(prefix + str(index))
                    index += 1
                    try:
                        self.interleave(observer, observer_pid, client, equipment, None, True,
                                        revoke=(case, admin.pk, active, role))
                    finally:
                        User.objects.filter(pk=admin.pk).update(is_active=True, role=Role.ADMIN)
            finally:
                app.close()  # Reconnect cleanly even if the actor's last connection was interrupted.
                session = client.cookies.get(settings.SESSION_COOKIE_NAME)
                if session is not None:
                    Session.objects.filter(session_key=session.value).delete()
                User.objects.filter(username=user_tag).delete()
                Equipment.objects.filter(number__startswith=prefix).delete()
                require(snapshot(observer) == rows_before, "清理后设备全字段或总数不一致。")
                require(runner.database_state(observer) == db_before, "清理后表、迁移、账号或会话不一致。")
                self.stdout.write("清理通过：设备全字段与总数、表、迁移、账号和会话恢复运行前状态。")
            self.stdout.write(self.style.SUCCESS("AC-6／T-01 4/4；AC-8 异常探针 4/4。"))
            self.stdout.write(self.style.SUCCESS("R1 2/2"))
        finally:
            app.close()
            observer.close()

    @staticmethod
    def make_equipment(number):
        return Equipment.objects.create(number=number, name="原名称", category="原类别",
                                        location="原位置", description="原说明")

    @staticmethod
    def open_form(client, equipment):
        url = reverse("equipment-edit", args=[equipment.pk])
        response = client.get(url)
        text = response.content.decode(response.charset)
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', text)
        require(response.status_code == 200 and equipment.number in text
                and "可用" in text and token is not None, "未成功取得旧设备表单及真实令牌。")
        values = {"name": "更新名称", "category": "更新类别", "location": "更新位置", "description": "更新说明"}
        return url, values, {**values, "csrfmiddlewaretoken": token[1]}

    def interleave(self, observer, observer_pid, client, equipment, status, blocking, *, revoke=None):
        url, values, data = self.open_form(client, equipment)
        before = snapshot(observer)
        locked = Event()
        release = Event()
        pids = {}
        edit_sql = []
        authorization_after = []

        def writer():
            try:
                pids["A"] = verify_target(connections["default"])
                with transaction.atomic():
                    Equipment.objects.select_for_update().values_list("pk", flat=True).get(pk=equipment.pk)
                    if revoke is None:
                        require(Equipment.objects.filter(pk=equipment.pk).update(status=status) == 1, "状态夹具更新失败。")
                    locked.set()
                    require(release.wait(8), "状态夹具事务等待放行超时。")
            finally:
                connections.close_all()

        def editor():
            app = connections["default"]
            try:
                pids["B"] = verify_target(app)

                def trace(execute, sql, params, many, context):
                    if is_equipment_statement(sql):
                        edit_sql.append(sql)
                    if revoke is not None:
                        projection, accounts_from, _ = sql.partition(' FROM "accounts_user"')
                        if (accounts_from and projection.count(",") == 1
                                and projection.startswith('SELECT "accounts_user"."is_active"')
                                and '"accounts_user"."role"' in projection):
                            require('"accounts_user"."id" =' in sql and tuple(params) == (revoke[1],),
                                    "锁后权限复核未按请求账号主键读取。")
                            authorization_after.append(len(edit_sql))
                    require("reservation" not in sql.lower() and "audit_" not in sql.lower(),
                            "编辑触及预约或历史。")
                    return execute(sql, params, many, context)

                with app.execute_wrapper(trace):
                    return client.post(url, data)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(writer)
            try:
                require(locked.wait(5), "状态夹具未及时取得行锁。")
                if blocking:
                    b = pool.submit(editor)
                    pid_b = wait_for(lambda: pids.get("B"), "编辑连接 PID")
                    blockers = wait_for(
                        lambda: [pid for pid in query(observer, "SELECT pg_blocking_pids(%s)", [pid_b])[0]
                                 if pid == pids["A"]],
                        "观察连接确认编辑受状态夹具行锁阻塞",
                    )
                    require(snapshot(observer) == before, "阻塞时观察连接不应看到未提交更新。")
                    if revoke is None:
                        self.stdout.write(f"T-01 绕不开同一行锁，状态={status}，B={pid_b}，阻塞者={blockers}。")
                    else:
                        _, admin_pk, active, role = revoke
                        require(observer.get_autocommit(), "撤权观察连接必须立即提交。")
                        require(query(observer, "UPDATE accounts_user SET is_active = %s, role = %s "
                                      "WHERE id = %s RETURNING id", [active, role, admin_pk]) == (admin_pk,),
                                "隔离账号夹具撤权失败。")
                else:
                    release.set()
                    a.result(timeout=12)
                    require(snapshot(observer) == expected_rows(before, equipment.pk, status=status),
                            "事务 A 提交后状态或其他设备不符。")
                    b = pool.submit(editor)
            finally:
                release.set()
            a.result(timeout=12)
            response = b.result(timeout=12)

        require(len({pids["A"], pids["B"], observer_pid}) == 3, "三个数据库后端必须互相独立。")
        if revoke is not None:
            case, admin_pk, active, role = revoke
            body = response.content.decode(response.charset)
            require(response.status_code == 403 and not response.has_header("Location"),
                    "设备锁等待期间撤权的请求未返回 403。")
            require(all(text not in body for text in (
                "<form", equipment.number, equipment.name, equipment.description, *values.values(),
            )), "撤权响应泄露了设备编辑内容。")
            require(
                len(edit_sql) == 1 and "FOR UPDATE" in edit_sql[0]
                and '"equipment_equipment"."id" =' in edit_sql[0] and authorization_after == [1],
                "撤权请求未按主键先锁设备、再读取账号，或尝试了额外设备 SQL。",
            )
            require(query(observer, "SELECT is_active, role FROM accounts_user WHERE id = %s", [admin_pk])
                    == (active, role), "观察连接未读到撤权后账号状态。")
            require(snapshot(observer) == before, "撤权后设备全字段或记录总数变化。")
            self.stdout.write(f"R1 {case} status=403 wait_verified=true blockers={blockers} pid={pids['B']} "
                              f"account_reread=1 updates=0 no_leak=true equipment_unchanged=true count={len(before)}")
            return
        require(response.status_code == 302
                and response["Location"] == reverse("equipment-detail", args=[equipment.pk]), "编辑未成功跳转原设备。")
        check_edit_sql(edit_sql)
        after = snapshot(observer)
        require(after == expected_rows(before, equipment.pk, status=status, **values),
                "锁后最终状态、基本字段、记录身份、无关设备或总数不符。")
        row = next(row for row in after if row["id"] == equipment.pk)
        self.stdout.write(f"T-01 状态={status}，真实等待={blocking}，PID={pids}，更新=1，末态={row!r}。")

    def fault(self, observer, observer_pid, client, equipment, fault):
        url, values, data = self.open_form(client, equipment)
        before = snapshot(observer)
        expected = expected_rows(before, equipment.pk, **values)
        app = connections["default"]
        actor_pid = verify_target(app)
        require(actor_pid != observer_pid, "应用与观察连接不能共用后端。")
        edit_sql = []
        commits = 0
        sqlstate = None
        real_commit = app._commit

        def trace(execute, sql, params, many, context):
            nonlocal sqlstate
            if is_equipment_statement(sql):
                edit_sql.append(sql)
            result = execute(sql, params, many, context)
            if fault == "write-rollback" and sql.startswith('UPDATE "equipment_equipment"'):
                try:
                    query(app, "DO $$ BEGIN RAISE EXCEPTION 'story14 probe' USING ERRCODE = '23514'; END $$")
                except Error as error:
                    sqlstate = error.__cause__.sqlstate
                    raise
            return result

        def interrupt_commit():
            nonlocal commits, sqlstate
            commits += 1
            raw = app.connection
            if fault == "commit-rejected":
                # This temporary table (never a business table) defers validation until the real COMMIT.
                query(app, "CREATE TEMP TABLE edit_commit_probe (n int UNIQUE DEFERRABLE INITIALLY DEFERRED) "
                           "ON COMMIT DROP")
                query(app, "INSERT INTO pg_temp.edit_commit_probe VALUES (1), (1)")
            elif fault == "commit-pre-disconnect":
                require(query(observer, "SELECT pg_terminate_backend(%s, 3000)", [actor_pid]) == (True,),
                        "未能关闭隔离应用后端。")
            elif fault == "commit-lost-ack":
                raw.pgconn.send_query(b"COMMIT")
                require(raw.pgconn.flush() == 0, "发送 COMMIT 尚未刷新。")
                wait_for(lambda: snapshot(observer) == expected, "独立观察连接读到真实 COMMIT")
                raw.close()  # Discard the confirmation before the application receives it.
            try:
                real_commit()
            except Error as error:
                sqlstate = getattr(error.__cause__, "sqlstate", None)
                raise

        try:
            with app.execute_wrapper(trace), patch.object(app, "_commit", side_effect=interrupt_commit):
                response = client.post(url, data)
        finally:
            app.close()
        check_edit_sql(edit_sql)
        require(commits == (0 if fault == "write-rollback" else 1), f"COMMIT 尝试次数不符：{commits}")
        body = response.content.decode(response.charset)
        unknown = fault in {"commit-pre-disconnect", "commit-lost-ack"}
        if unknown:
            require(sqlstate is None or sqlstate.startswith("08") or sqlstate in {"57P01", "57P02", "57P03"},
                    f"断连驱动返回非连接异常 SQLSTATE：{sqlstate}")
        else:
            require(sqlstate == {"write-rollback": "23514", "commit-rejected": "23505"}[fault],
                    f"实际数据库 SQLSTATE 不符：{sqlstate}")
        heading = "提交结果待核查" if unknown else "设备编辑失败"
        require(response.status_code == 503 and heading in body and "<form" not in body
                and "编号已存在" not in body and not response.has_header("Location"), "响应误报或提供了重试。")
        if unknown:
            require("请先核查设备记录" in body and "未保存" not in body, "未知结果不能断言回滚或未保存。")
        after = snapshot(observer)
        require(after == (expected if fault == "commit-lost-ack" else before), f"{fault} 的完整末态不符。")
        row = next(row for row in after if row["id"] == equipment.pk)
        self.stdout.write(f"AC-8 {fault} PID={actor_pid}，响应=503 {heading}，UPDATE=1，"
                          f"COMMIT 路径={commits}，SQLSTATE={sqlstate}，末态={row!r}。")
