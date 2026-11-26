import { spawn, execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdtemp, readFile, realpath, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, isAbsolute } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const origin = "http://127.0.0.1:8001";
const roles = { student: "学生", teacher: "教师", admin: "业务管理员" };
const statusLabels = { available: "可用", maintenance: "维修", disabled: "停用" };
const fields = ["name", "category", "location", "description"];
const runPsql = promisify(execFile);
const expectedNumber = "EQ-DEMO-S12-20261125";
const revised = {
    name: "课程演示设备 · Story 1.4",
    category: "课程设备 · Story 1.4",
    location: "实验室演示区",
    description: "Story 1.4 基础资料编辑验证，仅用于课程演示",
};
const maxLengths = { name: 120, category: 80, location: 120 };
function sameRow(actual, expected) {
    return actual && expected && Object.entries(expected).every(([key, value]) => actual[key] === value)
        && Object.keys(actual).length === Object.keys(expected).length;
}
async function readback(stage) {
    let result;
    try {
        result = await runPsql(process.env.STORY14_PSQL, [
            "-X", "-qAtw", "-h", "127.0.0.1", "-p", "5433", "-U", "lab_booking_app",
            "-d", "lab_booking", "-v", "ON_ERROR_STOP=1", "-c", "BEGIN READ ONLY",
            "-f", process.env.STORY14_SNAPSHOT_SQL, "-c", "COMMIT",
        ], { timeout: 10000, windowsHide: true, encoding: "utf8" });
    } catch {
        throw Error("Read-only runtime SQL failed: " + stage);
    }
    let parsed;
    try { parsed = JSON.parse(result.stdout.trim()); } catch { throw Error("Unexpected runtime snapshot: " + stage); }
    if (parsed?.row?.number !== expectedNumber || !Number.isSafeInteger(parsed.row.id) ||
        parsed.row.id <= 0 || !statusLabels[parsed.row.status] ||
        parsed.database !== "lab_booking" || parsed.role !== "lab_booking_app" ||
        parsed.port !== 5433 || parsed.version !== "17.12" || parsed.isolation !== "read committed" ||
        !fields.every(key => typeof parsed.row[key] === "string") ||
        !Number.isSafeInteger(parsed.device_count) || !/^[0-9a-f]{64}$/.test(parsed.other_devices_sha256)) {
        throw Error("Wrong runtime database or demonstration record: " + stage);
    }
    console.log(JSON.stringify({ stage, ...parsed }));
    return parsed;
}
const before = await readback("before");
if (process.env.STORY14_RECOVERY_BASELINE) {
    const saved = (await readFile(process.env.STORY14_RECOVERY_BASELINE, "utf8")).trim().split(/\r?\n/);
    const baseline = saved.length === 2 && saved[1] === "Exit 0" && JSON.parse(saved[0]);
    if (!baseline || !sameRow(before.row, baseline.row) || before.device_count !== baseline.device_count ||
        before.migrations !== baseline.migrations || before.other_devices_sha256 !== baseline.other_devices_sha256) {
        throw Error("Demonstration data changed since the pre-Chrome stop. Do not submit a recovery edit.");
    }
}
if (Object.keys(revised).length !== fields.length || fields.some(key =>
    typeof revised[key] !== "string" || !revised[key] || revised[key] !== revised[key].trim() ||
    (maxLengths[key] && [...revised[key]].length > maxLengths[key]))) {
    throw Error("Invalid planned demonstration data.");
}
const unchangedFields = fields.filter(key => before.row[key] === revised[key]);
if (unchangedFields.length) {
    throw Error("One or more planned fields already equal the new values (" + unchangedFields.join(", ") +
        "); stop rather than repeat a write.");
}
const detail = "/equipment/" + before.row.id + "/";
const edit = detail + "edit/";
let manifest;
try {
    manifest = JSON.parse((await readFile(process.env.STORY14_ACCOUNTS_JSON, "utf8")).replace(/^\uFEFF/, ""));
} catch {
    throw Error("Protected account manifest could not be read or parsed.");
}
if (!Array.isArray(manifest) || Object.keys(roles).some(role =>
    manifest.filter(a => a.role === role && typeof a.username === "string" && a.username &&
        typeof a.password === "string" && a.password).length !== 1)) {
    throw Error("Expected exactly one existing protected account per approved role.");
}
const expectedAfter = { ...before.row, ...revised };
const attempted = { ...revised, name: "Should not be saved", description: "Should not be saved" };
const profileRoot = await realpath(tmpdir());
const profile = await mkdtemp(join(profileRoot, "story14-chrome-"));
const chrome = spawn(process.env.STORY14_CHROME, [
    "--headless", "--no-first-run", "--disable-background-networking", "--no-proxy-server",
    "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank",
], { windowsHide: true, stdio: "ignore" });
let chromeFailed = false;
chrome.once("error", () => { chromeFailed = true; });
let ws, seq = 0;
const pending = new Map();
const redirects = [];
const ensure = (condition, note) => { if (!condition) throw Error(note); };
async function until(check, label) {
    const end = Date.now() + 10000;
    while (Date.now() < end && !chromeFailed) {
        try { const result = await check(); if (result) return result; } catch {}
        await delay(100);
    }
    throw Error("Timed out: " + label);
}
async function command(method, params = {}) {
    const id = ++seq;
    const p = Promise.withResolvers();
    const timer = setTimeout(() => { pending.delete(id); p.reject(Error("CDP timeout: " + method)); }, 5000);
    pending.set(id, { ...p, timer, method });
    ws.send(JSON.stringify({ id, method, params }));
    return p.promise;
}
async function evaluate(expression) {
    const result = await command("Runtime.evaluate", { expression, returnByValue: true });
    if (result.exceptionDetails) throw Error("Page expression failed.");
    return result.result.value;
}
const expression = (fn, ...values) => "(" + fn.toString() + ")(" + values.map(v => JSON.stringify(v)).join(",") + ")";
const locationInfo = () => evaluate(expression(() => ({
    origin: location.origin, path: location.pathname, next: new URL(location.href).searchParams.get("next"),
    time: performance.timeOrigin, status: performance.getEntriesByType("navigation")[0]?.responseStatus,
    ready: document.readyState,
})));
async function after(previous, path, status) {
    return until(async () => {
        const v = await locationInfo();
        return v?.origin === origin && v.path === path && v.time !== previous &&
            v.ready === "complete" && v.status === status ? v : false;
    }, path + " " + status);
}
async function navigate(path, expectedPath = path, status = 200) {
    const previous = (await locationInfo())?.time;
    const nav = await command("Page.navigate", { url: origin + path });
    ensure(!nav.errorText, "Navigation failed: " + path);
    return after(previous, expectedPath, status);
}
async function denied(path) {
    const start = redirects.length;
    const location = await navigate(path, "/login/");
    ensure(location.next === path &&
        redirects.slice(start).some(response => response.url === origin + path && response.status === 302),
        "Anonymous request did not produce the correct redirect: " + path);
    ensure(await evaluate(expression(() => !document.querySelector("tbody, #equipment-description, [name=description]"))),
        "Restricted markup unexpectedly present on login page.");
}
async function clickLink(selector, value, path) {
    const previous = (await locationInfo()).time;
    ensure(await evaluate(expression((selector, value) => {
        const link = [...document.querySelectorAll(selector)].find(el => el.textContent.trim() === value);
        if (!link) return false;
        setTimeout(() => link.click(), 0); return true;
    }, selector, value)), "Missing rendered link: " + path);
    await after(previous, path, 200);
}


async function snapshotMatches(stage, row = before.row) {
    const value = await readback(stage);
    ensure(sameRow(value.row, row) &&
        value.device_count === before.device_count && value.migrations === before.migrations &&
        value.other_devices_sha256 === before.other_devices_sha256, "Independent database readback mismatch: " + stage);
    return value;
}
async function doLogin(account) {
    await navigate("/login/");
    const prior = (await locationInfo()).time;
    ensure(await evaluate(expression((u, p) => {
        const form = document.querySelector('form[method="post"]');
        if (!form?.querySelector("[name=csrfmiddlewaretoken]")) return false;
        form.querySelector("[name=username]").value = u;
        form.querySelector("[name=password]").value = p;
        setTimeout(() => form.requestSubmit(), 0);
        return true;
    }, account.username, account.password)), "Protected login form absent.");
    await after(prior, "/identity/", 200);
    ensure(await evaluate(expression((username, label) => {
        const values = [...document.querySelectorAll("main dl dd")].map(el => el.innerText);
        return values[0] === username && values[1] === label;
    }, account.username, roles[account.role])), "Incorrect role identity.");
}
async function doLogout() {
    await navigate("/identity/");
    const prior = (await locationInfo()).time;
    ensure(await evaluate(expression(() => {
        const form = document.querySelector('form[action="/logout/"]');
        if (!form?.querySelector("[name=csrfmiddlewaretoken]")) return false;
        setTimeout(() => form.requestSubmit(), 0);
        return true;
    })), "Logout form absent.");
    await after(prior, "/login/", 200);
}
async function ensureNoEditPage() {
    ensure(await evaluate(expression(number => {
        const text = document.querySelector("main")?.innerText ?? document.body?.innerText ?? "";
        return !document.querySelector('[name=description], #equipment-description') &&
               !text.includes(number) && !text.includes("编辑设备基础信息");
    }, before.row.number)), "Restricted edit content returned.");
}
async function doPost(values, replacementForm, expectedPath, status) {
    const prior = (await locationInfo()).time;
    const start = redirects.length;
    ensure(await evaluate(expression((data, target, replace) => {
        if (location.origin !== "http://127.0.0.1:8001") return false;
        const token = document.querySelector('input[name=csrfmiddlewaretoken]')?.value;
        if (!token) return false;
        const form = replace ? document.createElement("form") : document.querySelector('form[method="post"]');
        if (!form) return false;
        if (!replace && (location.pathname !== target || new URL(form.action).pathname !== target || form.method !== "post")) return false;
        if (replace) {
            form.action = target;
            form.method = "post";
            document.body.append(form);
            data = { ...data, csrfmiddlewaretoken: token };
        }
        for (const [key, value] of Object.entries(data)) {
            let item = form.elements.namedItem(key);
            if (!item) {
                item = document.createElement("input");
                item.type = "hidden";
                item.name = key;
                form.append(item);
            }
            item.value = value;
        }
        setTimeout(() => form.requestSubmit(), 0);
        return true;
    }, values, edit, replacementForm)), "Could not use the confirmed form and CSRF token.");
    const result = await after(prior, expectedPath, status);
    if (expectedPath !== edit) {
        ensure(redirects.slice(start).some(r => r.url === origin + edit && r.status === 302), "Expected edit redirect missing.");
    }
    return result;
}
async function inspectForm() {
    const form = await evaluate(expression(() => {
        const f = document.querySelector('form[method="post"]');
        return f && { names: [...f.elements].map(x => x.name).filter(n => n && n !== "csrfmiddlewaretoken").sort(),
            values: Object.fromEntries(["name", "category", "location", "description"].map(n => [n, f.elements[n]?.value])),
            readOnlyValues: [...document.querySelectorAll("main dl dd")].map(el => el.innerText),
        };
    }));
    ensure(form && JSON.stringify(form.names) === JSON.stringify([...fields].sort()) &&
        fields.every(key => form.values[key] === before.row[key].replace(/\r\n?/g, "\n")) &&
        form.readOnlyValues[0] === before.row.number && form.readOnlyValues[1] === statusLabels[before.row.status],
        "Admin form has incorrect contents or exposes protected fields.");
}

let phase = "Chrome startup";
try {
    const port = await until(async () => {
        const s = (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split(/\r?\n/)[0];
        return /^\d+$/.test(s) ? s : false;
    }, phase);
    const target = await until(async () => {
        const response = await fetch("http://127.0.0.1:" + port + "/json/list", { signal: AbortSignal.timeout(2000) });
        if (!response.ok) return false;
        const targets = await response.json();
        return targets.find(t => t.type === "page" && typeof t.webSocketDebuggerUrl === "string");
    }, "Chrome page target");
    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(Error("DevTools WebSocket open timeout.")), 5000);
        ws.addEventListener("open", () => { clearTimeout(timer); resolve(); }, { once: true });
        ws.addEventListener("error", () => { clearTimeout(timer); reject(Error("DevTools WebSocket open failed.")); }, { once: true });
    });
    ws.addEventListener("message", event => {
        const data = JSON.parse(event.data);
        if (data.method === "Network.requestWillBeSent" && data.params.type === "Document" && data.params.redirectResponse)
            redirects.push({ url: data.params.redirectResponse.url, status: data.params.redirectResponse.status });
        const task = pending.get(data.id);
        if (task) {
            clearTimeout(task.timer); pending.delete(data.id);
            if (data.error) task.reject(Error("CDP failed: " + task.method)); else task.resolve(data.result);
        }
    });
    await command("Page.enable");
    await command("Network.enable");
    await command("Network.setCacheDisabled", { cacheDisabled: true });


    console.log(JSON.stringify({ chrome: (await command("Browser.getVersion")).product, origin }));
    phase = "anonymous GET and POST";
    await denied(edit);
    await ensureNoEditPage();
    await snapshotMatches("anonymous-get");
    await navigate("/login/");
    const anon = await doPost(attempted, true, "/login/", 200);
    ensure(anon.next === edit, "Anonymous POST lost its edit destination.");
    await ensureNoEditPage();
    await snapshotMatches("anonymous-post");
    console.log(JSON.stringify({ case: "anonymous", get: 302, post: 302, no_leak: true, unchanged: true }));

    for (const role of ["student", "teacher", "admin"]) {
        const account = manifest.find(a => a.role === role);
        let cleanup = true;
        try {
            phase = role + " login";
            await doLogin(account);
            phase = role + " detail";
            await navigate(detail);
            const hasEditLink = await evaluate(expression(path => [...document.querySelectorAll("main a")]
                .some(a => a.getAttribute("href") === path), edit));
            ensure(hasEditLink === (role === "admin"), "Edit navigation does not match role.");
            if (role !== "admin") {
                phase = role + " GET";
                await navigate(edit, edit, 403);
                await ensureNoEditPage();
                await snapshotMatches(role + "-get");
                phase = role + " POST";
                await navigate("/identity/");
                await doPost(attempted, true, edit, 403);
                await ensureNoEditPage();
                await snapshotMatches(role + "-post");
                console.log(JSON.stringify({ case: role, get: 403, post: 403, no_leak: true, unchanged: true }));
            } else {
                phase = "admin rendered edit link";
                await clickLink("main a", "编辑设备基础信息", edit);
                await inspectForm();
                for (const [key, value, error] of [
                    ["number", "EQ-DEMO-S14-FORGED", "设备编号不可修改"],
                    ["status", before.row.status === "disabled" ? "available" : "disabled", "设备状态不可在此修改"],
                ]) {
                    phase = "admin rejects " + key;
                    await navigate(edit);
                    await doPost({ ...attempted, [key]: value }, false, edit, 400);
                    ensure(await evaluate(expression(s => document.querySelector(".errorlist.nonfield")?.innerText.includes(s), error)),
                        "Expected protected-field validation error missing.");
                    await snapshotMatches("admin-forged-" + key);
                    console.log(JSON.stringify({ case: "admin-forged-" + key, response: 400, unchanged: true }));
                }
                phase = "admin one permitted update";
                await navigate(edit);
                await inspectForm();
                await snapshotMatches("admin-before-single-update");
                // Attempt once. A failed or unknown response must be independently read back, not retried.
                try {
                    await doPost(revised, false, detail, 200);
                } catch {
                    await snapshotMatches("admin-failed-or-unknown-readback", expectedAfter).catch(() => {});
                    throw Error("No confirmed successful edit. Consult database readback before any further action.");
                }
                const shown = await evaluate(expression(() => [...document.querySelectorAll("main dl dd")].map(el => el.innerText)));
                ensure(JSON.stringify(shown) === JSON.stringify([
                    expectedNumber, revised.name, revised.category, revised.location, revised.description, statusLabels[before.row.status],
                ]), "Detail does not show all four saved values and original identity.");
                await snapshotMatches("admin-committed-readback", expectedAfter);
                console.log(JSON.stringify({ case: "admin", get: 200, post: 302, detail: 200, original_identity: true, four_fields: true }));
            }
            phase = role + " logout";
            await doLogout();
            cleanup = false;
        } finally {
            if (cleanup) { try { await doLogout(); } catch {} }
        }
    }
    phase = "final committed readback after logout";
    const afterState = await snapshotMatches("after", expectedAfter);
    ensure(afterState.sessions === before.sessions, "Session count did not return to baseline.");
    console.log(JSON.stringify({ result: "passed", detail_url: origin + detail, edit_url: origin + edit }));

} catch (error) {
    console.error("Chrome verification failed at " + phase + ": " + error.message);
    process.exitCode = 1;
} finally {
    if (ws?.readyState === WebSocket.OPEN) {
        try { await command("Browser.close"); } catch {}
        ws.close();
    }
    if (chrome.exitCode === null) await delay(400);
    if (chrome.exitCode === null) chrome.kill();
    const resolved = await realpath(profile);
    const delta = relative(profileRoot, resolved);
    if (/^story14-chrome-[^\\/]+$/.test(delta) && !isAbsolute(delta)) {
        try { await rm(resolved, { recursive: true, maxRetries: 4, retryDelay: 200 }); }
        catch { console.error("Temporary Chrome profile could not be removed."); process.exitCode = 1; }
    }
}
