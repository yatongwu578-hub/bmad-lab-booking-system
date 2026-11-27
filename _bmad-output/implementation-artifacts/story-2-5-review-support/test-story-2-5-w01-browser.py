"""Real Chrome and actual W01 driver on a synthetic loopback HTTP fixture, never Django or production."""
import argparse
from datetime import datetime, timezone
import hashlib
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.parse import parse_qs, urlencode, urlsplit


ROUTE = "/reservations/manage/"
ROLES = {"admin": "业务管理员", "teacher": "教师", "student": "学生"}
PORT = 49173


def need(value, message):
    if not value:
        raise RuntimeError(message)


def validate_guard(support):
    spec = importlib.util.spec_from_file_location("w01_guard", support / "serve-story-2-5-w01-smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = (
        (("GET", ROUTE, 'SELECT * FROM "reservations_reservation"'), "business-read"),
        (("GET", ROUTE, 'SELECT "id" FROM "equipment_equipment" FOR UPDATE'), "business-lock"),
        (("GET", ROUTE, 'UPDATE "reservations_reservation" SET status=%s'), "blocked"),
        (("GET", ROUTE, "SELECT nextval('seq')"), "blocked"),
        (("POST", "/login/", 'INSERT INTO "django_session" ("session_key") VALUES (%s)'), "session"),
        (("POST", "/login/", 'UPDATE "accounts_user" SET "last_login" = %s WHERE "accounts_user"."id" = %s'), "last_login"),
        (("POST", "/login/", 'UPDATE "accounts_user" SET "password" = %s WHERE "accounts_user"."id" = %s'), "blocked"),
        (("POST", "/logout/", 'UPDATE "accounts_user" SET "last_login" = %s WHERE "accounts_user"."id" = %s'), "blocked"),
        (("POST", "/login/", 'INSERT INTO "audit_operationhistory" ("id") VALUES (%s)'), "blocked"),
        (("GET", ROUTE, 'SELECT 1; UPDATE "reservations_reservation" SET status=%s'), "blocked"),
        (("POST", "/login/", 'UPDATE "django_session" SET "session_key" = %s', True), "blocked"),
    )
    for args, expected in cases:
        need(module.sql_kind(*args) == expected, "W01 SQL guard classification differs")
    return len(cases)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "before", "chrome", "node"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--inject-browser-stop", action="store_true")
    args = p.parse_args()
    args.archive.mkdir()
    support = Path(__file__).resolve().parent
    checks = validate_guard(support)
    before = json.loads(args.before.read_text(encoding="utf-8-sig"))
    ident = before["identity"]
    need(ident["database"] == "test_lab_booking" and ident["host"] == "127.0.0.1" and ident["port"] == 55435
         and before["desired_port"] == PORT and before["acl_result"] == "EXACT_COLUMNS_PRESENT",
         "The Chrome fixture must use a qualified disposable PostgreSQL snapshot")
    sample = before["samples"]
    detail_path = f"{ROUTE}{sample['detail']['id']}/"
    filter_path = ROUTE + "?" + urlencode({"equipment": sample["filter"]["number"]})
    affected = f"{ROUTE}{sample['filter']['detail_id']}/?" + filter_path.split("?", 1)[1]
    token = "synthetic-csrf-only"
    csrf = f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">'
    access = args.archive / "server.jsonl"
    with TemporaryDirectory(prefix="story25-w01-synthetic-accounts-") as secret_dir, \
            access.open("x", encoding="utf-8", errors="strict", buffering=1) as logfile:
        fixture_secret = Path(secret_dir) / "synthetic-accounts.json"
        fixture_secret.write_text(json.dumps([{"role": role, "username": f"fixture-{role}", "password": "synthetic-only"}
                                              for role in ROLES]), encoding="utf-8", errors="strict")
        def log(event, **attrs):
            logfile.write(json.dumps(dict(event=event, at=datetime.now(timezone.utc).isoformat(), **attrs)) + "\n")

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def act(self):
                u = urlsplit(self.path)
                c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
                role = c["fixture_auth"].value if "fixture_auth" in c else None
                status, html, redirect, new_cookie = 200, "", None, None
                tech = []
                if u.path == "/login/" and self.command == "GET":
                    html = f'<form method="post">{csrf}<input name="username"><input name="password" type="password"><button>登录</button></form>'
                    new_cookie = "fixture_csrf=" + token + "; Path=/; SameSite=Lax"
                elif u.path in {"/login/", "/logout/"} and self.command == "POST":
                    data = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("ascii", "strict"),
                                    encoding="utf-8", errors="strict")
                    if data.get("csrfmiddlewaretoken") != [token] or "fixture_csrf" not in c or c["fixture_csrf"].value != token:
                        status = 403
                    elif u.path == "/logout/":
                        status, redirect, new_cookie = 302, "/login/", "fixture_auth=; Max-Age=0; Path=/"
                        tech = ["session"]
                    else:
                        selected = data.get("username", [""])[0].removeprefix("fixture-")
                        if selected not in ROLES or data.get("password") != ["synthetic-only"]:
                            status = 403
                        else:
                            status, redirect, new_cookie = 302, "/identity/", f"fixture_auth={selected}; Path=/; SameSite=Lax"
                            tech = ["session", "last_login"]
                elif u.path == "/identity/" and role in ROLES:
                    link = f'<a href="{ROUTE}">预约管理</a>' if role == "admin" else ""
                    html = f'<dl><dt>业务角色</dt><dd>{ROLES[role]}</dd></dl>{link}<form method="post" action="/logout/">{csrf}<button>退出</button></form>'
                elif u.path.startswith(ROUTE):
                    if args.inject_browser_stop:
                        status = 409
                    elif not role:
                        status, redirect = 302, "/login/?" + urlencode({"next": self.path})
                    elif role != "admin":
                        status, html = 403, "拒绝访问"
                    elif u.path == ROUTE:
                        html = '<a href="/identity/">返回我的身份</a><form method="get" action="' + ROUTE + '"><input name="equipment"><button>筛选</button></form>'
                        html += f'<a href="{ROUTE}">清除筛选</a>'
                        html += (f'<h2>受影响预约</h2><a href="{affected}">第二条</a>' if u.query else
                                 f'<h2>全部预约</h2><a href="{detail_path}">第一条</a>')
                    else:
                        back = filter_path if u.query else ROUTE
                        html = (f'<a href="{back}">返回预约管理</a><dl>' + "".join(f'<dt>{x}</dt><dd>合成</dd>'
                                for x in ("申请人", "设备", "预约状态", "设备当前状态", "时段", "处理原因")) +
                                '</dl><table><tbody><tr><td>合成历史</td></tr></tbody></table>')
                else:
                    status = 404
                if u.path != "/favicon.ico":
                    log("document", method=self.command, path=u.path, status=status, allowed_tech_writes=tech,
                        query_sha256=hashlib.sha256(("?" + u.query).encode()).hexdigest() if u.query else None,
                        guard_blocked=[], business_sql_categories=[])
                body = ('<!doctype html><meta charset="utf-8"><main>' + html + '</main>').encode()
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                if redirect:
                    self.send_header("Location", redirect)
                if new_cookie:
                    self.send_header("Set-Cookie", new_cookie)
                self.end_headers()
                self.wfile.write(body)

            do_GET = act
            do_POST = act

        with ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as server:
            log("ready", port=PORT, inspection_sha256=hashlib.sha256(args.before.read_bytes()).hexdigest())
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                roles = ("anonymous",) if args.inject_browser_stop else ("anonymous", "student", "teacher", "admin")
                for role in roles:
                    with TemporaryDirectory(prefix="story25-w01-chrome-", ignore_cleanup_errors=True) as profile:
                        with (args.archive / f"chrome-{role}.stderr").open("xb") as chrome_err, \
                                (args.archive / f"chrome-{role}.stdout").open("xb") as chrome_out:
                            process = subprocess.Popen([str(args.chrome), "--headless=new", "--no-first-run",
                                "--disable-background-networking", "--disable-extensions", "--no-default-browser-check",
                                f"--user-data-dir={profile}", "--remote-debugging-address=127.0.0.1",
                                "--remote-debugging-port=0", "about:blank"], stdout=chrome_out, stderr=chrome_err)
                            try:
                                active = Path(profile) / "DevToolsActivePort"
                                for _ in range(100):
                                    if active.exists() or process.poll() is not None:
                                        break
                                    time.sleep(.1)
                                need(process.poll() is None and active.exists(), "Chrome fixture did not start")
                                port = active.read_text(encoding="ascii", errors="strict").splitlines()[0]
                                need(port.isascii() and port.isdecimal() and 1024 <= int(port) <= 65535 and int(port) != PORT,
                                     "Unexpected dedicated Chrome debugging port")
                                if role == "anonymous" and not args.inject_browser_stop:
                                    with (args.archive / "node-probe.stdout").open("xb") as out, (args.archive / "node-probe.stderr").open("xb") as err:
                                        probe = subprocess.run([str(args.node), str(support / "capture-story-2-5-browser.mjs"),
                                            "--origin", f"http://127.0.0.1:{PORT}", "--debug", port, "--role", role,
                                            "--probe", "--out", str(args.archive / "probe.jsonl")], stdout=out, stderr=err, timeout=12)
                                    (args.archive / "node-probe.exit").write_text(str(probe.returncode), encoding="ascii")
                                    need(probe.returncode == 0, f"Renderer probe exited {probe.returncode}")
                                    markers = (args.archive / "node-probe.stdout").read_text(encoding="utf-8", errors="strict").splitlines()
                                    need(markers.count("STORY25_W01_CHROME_PROBE_OK") == 1,
                                         "Renderer probe failed before real document capture")
                                with (args.archive / f"node-{role}.stdout").open("xb") as out, (args.archive / f"node-{role}.stderr").open("xb") as err:
                                    driver = subprocess.run([str(args.node), str(support / "capture-story-2-5-browser.mjs"),
                                        "--origin", f"http://127.0.0.1:{PORT}", "--debug", port, "--role", role,
                                        "--inspection", str(args.before), "--accounts", str(fixture_secret),
                                        "--out", str(args.archive / f"{role}.jsonl")], stdout=out, stderr=err, timeout=55)
                                (args.archive / f"node-{role}.exit").write_text(str(driver.returncode), encoding="ascii")
                                if args.inject_browser_stop:
                                    need(driver.returncode == 1, f"Injected browser driver exited {driver.returncode}, expected 1")
                                    expected = (args.archive / f"node-{role}.stderr").read_text(encoding="utf-8", errors="strict").splitlines()
                                    need(expected.count("STORY25_W01_BROWSER_FAILED: Guard or server stopped the formal sequence.") == 1,
                                         "Injected browser failure did not fail at the real driver guard")
                                else:
                                    need(driver.returncode == 0, f"Chrome driver for {role} exited {driver.returncode}")
                                    terminal = (args.archive / f"node-{role}.stdout").read_text(encoding="utf-8", errors="strict").splitlines()
                                    need(terminal.count("STORY25_CHROME_CAPTURE_OK") == 1,
                                         f"Actual Chrome tooling failed for {role}; inspect archived native logs")
                            finally:
                                if process.poll() is None:
                                    process.terminate()
                                    process.wait(timeout=10)
                                (args.archive / f"chrome-{role}.exit").write_text(str(process.returncode), encoding="ascii")
            finally:
                server.shutdown()
                worker.join()
                log("stop")
    print(f"W01_SQL_GUARD_FIXTURE_CHECKS={checks}")
    print("W01_TOOL_BROWSER_STOP_CONFIRMED" if args.inject_browser_stop else "W01_TOOL_REAL_CHROME_OK")


if __name__ == "__main__":
    main()
