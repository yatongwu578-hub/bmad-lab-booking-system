"""Small local Chrome DevTools client for the isolated reservation browser probe."""

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

from django.core.management.base import CommandError


def check(condition, message):
    if not condition:
        raise CommandError(message)


def poll(operation, label, seconds=20):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        result = operation()
        if result:
            return result
        sleep(.05)
    raise CommandError(f"Chrome did not reach {label}")


class DevTools:
    def __init__(self, connection, endpoint):
        self.connection = connection
        self.incoming = connection.makefile("rb")
        self.sequence = 0
        self.documents = []
        key = base64.b64encode(os.urandom(16)).decode()
        self.connection.sendall((
            f"GET {endpoint.path} HTTP/1.1\r\nHost: {endpoint.netloc}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        check(b" 101 " in self.incoming.readline(), "Chrome DevTools websocket upgrade failed")
        headers = {}
        for line in iter(self.incoming.readline, b"\r\n"):
            check(line and b":" in line, "Invalid Chrome DevTools upgrade headers")
            name, value = line.split(b":", 1)
            headers[name.lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        check(headers.get(b"sec-websocket-accept") == expected, "Invalid Chrome DevTools websocket key")

    def close(self):
        self.incoming.close()

    def send(self, payload, opcode=1):
        length = len(payload)
        size = bytes((128 | length,)) if length < 126 else b"\xfe" + struct.pack("!H", length)
        mask = os.urandom(4)
        self.connection.sendall(bytes((128 | opcode,)) + size + mask
                                + bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload)))

    def read(self):
        fragments = []
        while True:
            header = self.incoming.read(2)
            check(len(header) == 2, "Chrome closed the DevTools connection")
            flags, length = header
            check(not (length & 128), "Chrome sent an invalid masked DevTools frame")
            if length in (126, 127):
                width = 2 if length == 126 else 8
                length = int.from_bytes(self.incoming.read(width), "big")
            check(length <= 2_000_000, "Unexpectedly large Chrome DevTools frame")
            payload = self.incoming.read(length)
            check(len(payload) == length, "Truncated Chrome DevTools frame")
            opcode = flags & 15
            if opcode == 9:
                self.send(payload, opcode=10)
            elif opcode in (0, 1):
                fragments.append(payload)
                if flags & 128:
                    return json.loads(b"".join(fragments))
            else:
                raise CommandError(f"Unexpected Chrome DevTools frame type {opcode}")

    def call(self, method, **params):
        self.sequence += 1
        self.send(json.dumps(dict(id=self.sequence, method=method, params=params)).encode())
        while True:
            event = self.read()
            if event.get("id") == self.sequence:
                # Do not echo the request parameters, which can include the fixture session cookie.
                check("error" not in event, f"Chrome DevTools rejected {method}")
                return event["result"]
            if event.get("method") == "Network.responseReceived":
                data = event["params"]
                if data["type"] == "Document":
                    self.documents.append({key: data["response"][key] for key in ("status", "url")})

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        if "exceptionDetails" in result:
            return None  # The previous document may still be loading.
        return result["result"].get("value")

    def document(self, url, status, expression):
        def ready():
            data = self.evaluate(
                f"location.href === {json.dumps(url)} && document.readyState === 'complete' && ({expression})"
            )
            if {"url": url, "status": status} in self.documents and data:
                return data

        return poll(ready, f"HTTP {status} page at {urlsplit(url).path}")

    def click(self, selector):
        coordinates = self.evaluate(f"""(() => {{
            const element = document.querySelector({json.dumps(selector)});
            if (!element) return null;
            element.scrollIntoView({{block: "center"}});
            const rect = element.getBoundingClientRect();
            return {{x: rect.x + rect.width / 2, y: rect.y + rect.height / 2}};
        }})()""")
        check(coordinates, "Chrome could not find the rendered control")
        for action in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=action, button="left", clickCount=1, **coordinates)


@contextmanager
def chrome():
    binary = os.environ.get("LAB_BOOKING_R1_CHROME")
    check(binary and Path(binary).is_file(), "The existing LAB_BOOKING_R1_CHROME executable is required")
    with TemporaryDirectory(prefix="story21-chrome-") as folder:
        profile = Path(folder)
        with subprocess.Popen(
            [binary, "--headless", "--no-first-run", "--disable-background-networking", "--no-proxy-server",
             "--window-size=1024,768", "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ) as process:
            try:
                def active_port():
                    check(process.poll() is None, "Chrome exited before opening its local DevTools endpoint")
                    try:
                        return int((profile / "DevToolsActivePort").read_text(encoding="ascii").splitlines()[0])
                    except (OSError, ValueError, IndexError):
                        return None

                port = poll(active_port, "the local DevTools endpoint")
                with build_opener(ProxyHandler({})).open(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                    tab, = [item for item in json.load(response) if item["type"] == "page"]
                endpoint = urlsplit(tab["webSocketDebuggerUrl"])
                check(endpoint.scheme == "ws" and endpoint.hostname == "127.0.0.1" and endpoint.port == port,
                      "Refusing non-local Chrome DevTools endpoint")
                with socket.create_connection(("127.0.0.1", port), timeout=8) as connection:
                    browser = DevTools(connection, endpoint)
                    try:
                        browser.call("Network.enable")
                        browser.call("Page.enable")
                        yield browser
                    finally:
                        try:
                            browser.call("Browser.close")
                        except (CommandError, OSError):
                            pass
                        browser.close()
            finally:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()


def fill(browser, values, *, bypass=False):
    return browser.evaluate(f"""(() => {{
        const form = document.querySelector('form[aria-describedby="time-rules"]');
        const button = form.querySelector('button[type=submit]');
        if ({json.dumps(bypass)}) button.formNoValidate = true;
        const inputs = Object.entries({json.dumps(values)}).map(([name, value]) => {{
            const input = form.elements.namedItem(name);
            input.value = value;
            return {{value: input.value, step: input.step, stepMismatch: input.validity.stepMismatch,
                     valid: input.validity.valid}};
        }});
        return {{formNoValidate: form.noValidate, buttonNoValidate: button.formNoValidate,
                 valid: form.checkValidity(), inputs}};
    }})()""")
