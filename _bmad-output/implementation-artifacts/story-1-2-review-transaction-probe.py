"""Independent Story 1.2 acceptance probe for the pre-existing isolated test database."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
if os.environ.get("LAB_BOOKING_DB_MODE") != "test":
    raise SystemExit("Refusing to run outside test mode")
os.environ["DJANGO_SETTINGS_MODULE"] = "lab_booking.settings"

import django

django.setup()

from django.conf import settings
from django.db import connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, RequestFactory

from accounts.models import Role, User
from equipment.models import Equipment
from equipment.views import create_equipment_view


def query(connection, sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def wait_for(condition):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        if result := condition():
            return result
        sleep(0.02)
    raise AssertionError("Timed out waiting for PostgreSQL evidence")


def verify_target(connection):
    actual = query(
        connection,
        "SELECT current_database(), session_user, current_user, host(inet_server_addr()),"
        " inet_server_port(), current_setting('server_version_num'),"
        " current_setting('transaction_isolation'), pg_backend_pid()",
    )
    assert actual[:-1] == (
        "test_lab_booking", "lab_booking_test", "lab_booking_test",
        "127.0.0.1", 5433, "170012", "read committed",
    ), actual
    return actual


def submit(number, marker):
    request = RequestFactory().post("/equipment/new/", {
        "number": number, "name": marker, "category": "review",
        "location": "isolated", "description": marker,
    })
    request.user = User(username=marker, role=Role.ADMIN, is_active=True)
    response = create_equipment_view(request)
    body = response.content.decode(response.charset)
    heading = body.split("<h1>")[1].split("</h1>")[0]
    return response.status_code, "该设备编号已存在。" if "该设备编号已存在。" in body else heading


def check_http():
    url = "/equipment/new/"
    tag = uuid4().hex[:20]
    values = {
        "number": "H-" + tag, "name": "审查设备名称", "category": "光学验证",
        "location": "审查位置", "description": "审查保存说明",
    }
    findings = []
    with transaction.atomic():
        users = {
            role: User.objects.create_user(username=f"review-{role}-{tag}", role=role)
            for role in (Role.ADMIN, Role.STUDENT, Role.TEACHER)
        }
        baseline = list(Equipment.objects.order_by("pk").values())
        for role in (None, Role.STUDENT, Role.TEACHER):
            client = Client(HTTP_HOST="localhost")
            if role is not None:
                client.force_login(users[role])
            for method in ("get", "post"):
                response = client.get(url) if method == "get" else client.post(url, values)
                body = response.content.decode(response.charset)
                assert response.status_code == (302 if role is None else 403)
                if role is None:
                    assert response["Location"] == "/login/?next=/equipment/new/"
                assert "新增具体设备档案" not in body and 'name="number"' not in body
                assert list(Equipment.objects.order_by("pk").values()) == baseline
                print("AC4", role, method.upper(), response.status_code, "no content or equipment changes")

        client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")
        client.force_login(users[Role.ADMIN])
        form = client.get(url)
        assert form.status_code == 200
        form_text = form.content.decode(form.charset)
        assert 'name="status"' not in form_text
        if "可用" not in form_text:
            findings.append("AC1 GET form omits read-only available status")
        token = client.cookies["csrftoken"].value
        wrong = ("a" if token[0] != "a" else "b") + token[1:]
        for headers in ({}, {"HTTP_X_CSRFTOKEN": wrong}):
            denied = client.post(url, values, **headers)
            assert denied.status_code == 403
            assert list(Equipment.objects.order_by("pk").values()) == baseline
            print("AC5", "invalid" if headers else "missing", denied.status_code, "no equipment changes")

        good_header = {"HTTP_X_CSRFTOKEN": token}
        for data in ({key: value for key, value in values.items() if key != "number"},
                     {**values, "number": ""}):
            invalid = client.post(url, data, **good_header)
            assert invalid.status_code == 200 and 'errorlist' in invalid.content.decode(invalid.charset)
            assert list(Equipment.objects.order_by("pk").values()) == baseline
        empty = client.post(url, "", content_type="application/x-www-form-urlencoded", **good_header)
        assert empty.status_code == 200 and list(Equipment.objects.order_by("pk").values()) == baseline
        if "errorlist" not in empty.content.decode(empty.charset):
            findings.append("AC3 CSRF-valid empty POST omits number validation error")

        accepted = client.post(url, {**values, "status": "disabled"}, **good_header)
        assert accepted.status_code == 201
        record = Equipment.objects.get(number=values["number"])
        assert record.status == "available"
        body = accepted.content.decode(accepted.charset)
        assert "可用" in body
        for key, value in values.items():
            assert getattr(record, key) == value and value in body
        original = list(Equipment.objects.order_by("pk").values())
        assert len(original) == len(baseline) + 1
        repeated = client.post(url, {**values, "name": "重复记录不得覆盖"}, **good_header)
        assert repeated.status_code == 200 and "已存在" in repeated.content.decode(repeated.charset)
        assert list(Equipment.objects.order_by("pk").values()) == original
        transaction.set_rollback(True)
    assert not Equipment.objects.filter(number=values["number"]).exists()
    assert not User.objects.filter(username__endswith=tag).exists()
    print("AC1/2/3/5 HTTP field, count, duplicate and valid CSRF controls passed; rollback cleanup verified")
    for finding in findings:
        print(finding)
    return findings


def main():
    assert settings.LAB_BOOKING_DB_MODE == "test"
    observer = connections["default"]
    print("observer", verify_target(observer), "Django", django.get_version())
    executor = MigrationExecutor(observer)
    executor.loader.check_consistent_history(observer)
    assert not executor.migration_plan(executor.loader.graph.leaf_nodes())
    marker = "story12-review-" + uuid4().hex
    numbers = {case: "R12-" + uuid4().hex[:20] for case in ("race", "rollback", "pre", "post")}
    assert not Equipment.objects.filter(number__in=numbers.values()).exists()
    sim_insert = Equipment.save
    http_findings = check_http()
    failures = []

    def persisted(case):
        return list(Equipment.objects.filter(number=numbers[case]).values_list(
            "number", "name", "category", "location", "description", "status",
        ))

    try:
        inserted = Event()
        release = Event()
        pids = {}

        def race_save(obj, *args, **kwargs):
            sim_insert(obj, *args, **kwargs)
            if obj.name == marker + "-A":
                inserted.set()
                assert release.wait(8)

        def contender(label):
            try:
                pids[label] = verify_target(connections["default"])[-1]
                return submit(numbers["race"], marker + "-" + label)
            finally:
                connections.close_all()

        with patch.object(Equipment, "save", race_save), ThreadPoolExecutor(2) as pool:
            attempt_a = pool.submit(contender, "A")
            try:
                assert inserted.wait(5)
                attempt_b = pool.submit(contender, "B")
                pid_b = wait_for(lambda: pids.get("B"))
                blockers = wait_for(
                    lambda: [pid for pid in query(observer, "SELECT pg_blocking_pids(%s)", (pid_b,))[0]
                             if pid == pids["A"]]
                )
                assert pids["A"] != pids["B"] != verify_target(observer)[-1]
                assert persisted("race") == []
                print("AC6 actual blocking", pids, blockers)
            finally:
                release.set()
            race_a, race_b = attempt_a.result(8), attempt_b.result(8)
        race_rows = persisted("race")
        print("AC6", race_a, race_b, race_rows)
        assert race_a == (201, "设备已新增") and race_b == (200, "该设备编号已存在。")
        assert len(race_rows) == 1 and race_rows[0][1] == marker + "-A"

        for case in ("rollback", "pre", "post"):
            app = observer.copy(alias="review-actor")
            with patch.object(connections._connections, "default", app):
                actor_pid = verify_target(app)[-1]
                original_commit = app._commit
                calls = {"insert": 0, "commit": 0}

                def measured_save(obj, *args, **kwargs):
                    calls["insert"] += 1
                    sim_insert(obj, *args, **kwargs)
                    if case == "rollback":
                        try:
                            with app.cursor() as cursor:
                                cursor.execute(
                                    "UPDATE equipment_equipment SET status = 'invalid' WHERE number = %s",
                                    (numbers[case],),
                                )
                        except Exception as exc:
                            diagnostic = exc.__cause__
                            print("AC7 rollback", diagnostic.sqlstate, diagnostic.diag.constraint_name)
                            raise

                def interrupt_commit():
                    calls["commit"] += 1
                    raw = app.connection
                    if case == "pre":
                        assert query(observer, "SELECT pg_terminate_backend(%s, 3000)", (actor_pid,)) == (True,)
                    else:
                        raw.pgconn.send_query(b"COMMIT")
                        assert raw.pgconn.flush() == 0
                        wait_for(read_observer)
                        raw.close()
                    try:
                        original_commit()
                    except Exception as exc:
                        cause = exc.__cause__
                        print("AC7 driver", case, type(exc).__name__,
                              type(cause).__name__, getattr(cause, "sqlstate", None))
                        raise

                # Observer checks must use its own connection while the view uses the actor.
                def read_observer():
                    return query(
                        observer, "SELECT count(*) FROM equipment_equipment WHERE number = %s",
                        (numbers[case],),
                    )[0]

                try:
                    with patch.object(Equipment, "save", measured_save):
                        if case == "rollback":
                            result = submit(numbers[case], marker)
                        else:
                            with patch.object(app, "_commit", interrupt_commit):
                                result = submit(numbers[case], marker)
                finally:
                    app.close()
            rows = persisted(case)
            print("AC7", case, "actor", actor_pid, "response", result, "attempts", calls, "rows", rows)
            assert len(rows) == int(case == "post") and calls["insert"] == 1
            assert calls["commit"] == int(case != "rollback")
            expected = "设备新增失败" if case == "rollback" else "提交结果待核查"
            if result != (503, expected):
                failures.append((case, result, expected))
    finally:
        deleted, _ = Equipment.objects.filter(
            number__in=numbers.values(), description__startswith=marker,
        ).delete()
        print("cleanup rows deleted", deleted, "remaining",
              Equipment.objects.filter(number__in=numbers.values()).count())
        assert not Equipment.objects.filter(number__in=numbers.values()).exists()
    if failures:
        print("AC7 mismatches", failures)
    if http_findings or failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
