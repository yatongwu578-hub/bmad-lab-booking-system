# Story 1.3 正式业务库授权与运行验证

2026-11-25，项目负责人接受 BMAD 6.12.4 独立复审结论，正式关闭 R1，并批准本机正式库六列读取授权及真实运行验证。**授权和三角色浏览器批次均实际成功。** Story 1.3 保持 `review`，等待最终验收。保留已批准延期项及其历史文字。 [D-030](../../decision-log.md#d-030-2026-11-25-负责人关闭-r1-并批准-story-13-业务库验证) · [独立复审](story-1-3-independent-recheck.md) · [实际命令输出](story-1-3-runtime-output.txt)

## 授权边界与结果

沿用 6.12.4 独立复审的收尾步骤，使用 `uv run --no-cache --python D:/ttAPP/python.exe` 重新核对 `workflow.on_complete` 为空。未启动新的规划、评审或开发流程，未重复渲染 Build。原 `.venv` 在受限环境探测解释器未能启动，具体命令获准后报告 Python 3.13.17，无需重装或重建。Python 3.14 只用于 BMAD 解析。

通过已批准的受保护 `PGPASSFILE`，在仓库根目录把带前后验证的 SQL 送入同一 `psql`。 [已执行 SQL 的留档副本](#附录实际执行内容留档)

```powershell
$env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf'
# $aclBatch 为包含前后约束断言和下列唯一 GRANT 的 SQL 批次。
$aclBatch | & 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -X -w -h 127.0.0.1 -p 5433 -U lab_booking_migrator -d lab_booking -v ON_ERROR_STOP=1 --single-transaction -f -
```

```sql
GRANT SELECT (number, name, category, location, description, status)
ON TABLE public.equipment_equipment TO lab_booking_app;
```

- 事务前守卫核对实际 `lab_booking`、`session_user=current_user=lab_booking_migrator`、`127.0.0.1:5433`、17.12（170012）、表所有者和七列定义。有效权限为仅 `id` 可读、仅原六列可插入。未发现权限漂移。
- 事务后有效权限为七列 SELECT、原六列 INSERT。七列均无 UPDATE、REFERENCES 或读／写转授权，表级 SELECT、INSERT、UPDATE、DELETE、TRUNCATE、REFERENCES、TRIGGER、MAINTAIN 均未授予。无新增序列权限、库／模式 CREATE 或角色级管理能力。输出前后断言均通过、`GRANT`、退出 0。若任何断言失败，`ON_ERROR_STOP` 与单事务会回滚。
- 仅此一条 ACL 变更。不调用迁移、预置或设备写操作，未访问旧 PostgreSQL 11.17。

## 系统启动与验证命令

实际在工作目录以 `runtime`、`DJANGO_SETTINGS_MODULE=lab_booking.settings` 和受保护的 `PGPASSFILE` 启动。先检查 8000 无监听，启动后核实确属本次项目进程（启动器 PID 23444，监听 PID 1964），未停止任何已有进程。已保留运行服务，验证批次结束后再次核实端口仍监听且登录页返回 200。以下为需要重新启动时的同等前台命令。当前仍运行时无需重复启动。

```powershell
$env:LAB_BOOKING_DB_MODE = 'runtime'
$env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
$env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf'
if (-not $env:LAB_BOOKING_SECRET_KEY) {
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
}
& '.\.venv\Scripts\python.exe' -B -u manage.py runserver 127.0.0.1:8000 --noreload
```

三类账号均从既有受保护账号清单读取。Node 24.22.1 调用实际 Chrome 159.0.8154.34，以隔离临时配置经环回 DevTools 操作登录、点击及退出表单，未输出账号凭据或会话值。命令为 `node _bmad-output/implementation-artifacts/story-1-3-runtime-chrome.mjs`，`STORY13_RUNTIME_ORIGIN=http://127.0.0.1:8000`，`STORY13_RUNTIME_DEMO` 由下方真实数据库前快照提供。浏览器退出 0。 [浏览器核验脚本](#附录实际执行内容留档)

| 身份 | 目录／详情及权限结果 |
| --- | --- |
| 未登录 | 目录和已有详情直接访问均 302 至对应登录页，验证 `next`，未展示设备区域。 |
| 学生 | 登录后显示本人及学生身份。实际点击身份页目录及设备，目录、点击详情、直达详情均 200，数据与数据库一致；不存在设备 404。正常退出后直达两入口均 302。 |
| 教师 | 同样通过，身份标签为教师，目录和详情字段正确，404 与退出后 302 均通过。 |
| 业务管理员 | 同样通过，身份标签为业务管理员，目录和详情字段正确，404 与退出后 302 均通过。 |

详情还验证了说明容器计算样式 `pre-wrap` 和“可用不等于指定时段可预约”的提示。真实演示设备为 `EQ-DEMO-S12-20261125`（主键 1），目录五个字段与详情六个字段通过实际 DOM 对照。空目录、维修、停用及多行说明沿用已复审的隔离证据，未为演示改动业务数据。应用只读链路另有既有隔离 SQL 捕获证据，本轮业务库用前后独立只读快照核查，没有声称启用了运行时 SQL 追踪。

## 独立数据库前后核对

使用运行角色 `lab_booking_app` 的两个独立只读事务，执行了以下调用及快照 SQL。只输出已批准的演示档案和全设备摘要。

```powershell
$snapshotSql | & 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -qAtXw -h 127.0.0.1 -p 5433 -U lab_booking_app -d lab_booking -v ON_ERROR_STOP=1 -c 'BEGIN READ ONLY' -f - -c 'COMMIT'
```

```sql
DO $scope$
BEGIN
  IF current_database() <> 'lab_booking' OR session_user <> 'lab_booking_app'
     OR current_user <> 'lab_booking_app' OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
     OR inet_server_port() IS DISTINCT FROM 5433 OR current_setting('server_version_num') <> '170012'
     OR current_setting('transaction_read_only') <> 'on'
  THEN RAISE EXCEPTION 'incorrect snapshot target'; END IF;
END
$scope$;
WITH snapshot AS (
    SELECT count(*) AS device_count, (coalesce(max(id), 0) + 1)::text AS missing_id,
           encode(sha256(convert_to(coalesce(jsonb_agg(
               jsonb_build_array(id, number, name, category, location, description, status) ORDER BY id
           )::text, '[]'), 'UTF8')), 'hex') AS device_digest
    FROM public.equipment_equipment
)
SELECT jsonb_build_object('database', current_database(), 'database_role', current_user,
    'address', host(inet_server_addr()), 'port', inet_server_port(),
    'server_version', current_setting('server_version_num'), 'read_only', current_setting('transaction_read_only'),
    'id', e.id::text, 'number', e.number, 'name', e.name, 'category', e.category,
    'location', e.location, 'description', e.description, 'status', e.status,
    'device_count', s.device_count, 'missing_id', s.missing_id, 'device_digest', s.device_digest,
    'session_count', (SELECT count(*) FROM public.django_session),
    'migration_count', (SELECT count(*) FROM public.django_migrations))
FROM public.equipment_equipment e CROSS JOIN snapshot s WHERE e.number = 'EQ-DEMO-S12-20261125';
```

前后均为 1 台设备、17 条迁移记录、1 条既有会话。全设备按主键排序、七列拼成 JSON 后计算的 SHA-256 前后均为 `212caa4aa4a4d6039bb0509c76b4a20219c87e243dbd580f4e9a88767337e264`。三类验证账号均经实际表单退出，业务会话计数恢复原值，不清理既有会话。登录带来的 `last_login` 和临时会话属于正常认证副作用，不是业务设备变更。 [原始快照与浏览器输出](story-1-3-runtime-output.txt)

## 查看地址和课程追溯

- [登录](http://127.0.0.1:8000/login/)
- [设备目录](http://127.0.0.1:8000/equipment/)
- [演示设备详情](http://127.0.0.1:8000/equipment/1/)
- [不存在的设备对照](http://127.0.0.1:8000/equipment/2/)（需先登录，返回 404）

第 26 页以 FR-003／FR-002 → ADR-001／002／003 → 正式 AC → 独立隔离和运行证据追溯。第 27 页实录 R1 的独立复审、负责人关闭和业务验证，仍等待最终验收。第 33 页保存授权、运行、Git 基线和 Sprint 证据。第 34 页条件不变，不计入实验 A。第 36 页记录本次负责人真实决定 D-030。页码按课程基线及团队记录核对。三位组员共同查看和审阅，不在记录中臆造逐人操作。复用已有效的 55 项独立回归，未重跑，未开始 Story 1.4，未改 PRD／Architecture，未暂存、提交或推送。 [课程基线](../../docs/course-requirements.md) · [Sprint 状态](sprint-status.yaml) · [Git 基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/09085cbc0b03dc5a3e03f54ba8604f15579b2533)

## 附录：实际执行内容留档

下列内容是 D-030 实际执行的 SQL 与 Chrome 验证源码。以 Markdown 证据留档，不将临时运行脚本纳入提交。SQL 前置断言针对授予前状态，不应在已授权的本机重复执行。

<details>
<summary>授权批次 SQL</summary>

```sql
-- D-030 业务库授权实录。前置断言要求 D-026 的历史权限状态。
-- 证据副本，不是启动脚本。不能在已完成授权的业务库重复执行。
DO $verify$
DECLARE
    field text;
    p text;
    table_id oid := to_regclass('public.equipment_equipment');
    role_id name := 'lab_booking_app';
    sequence_name text;
    fields text[] := ARRAY['id','number','name','category','location','description','status'];
BEGIN
    IF current_database() <> 'lab_booking' OR current_user <> 'lab_booking_migrator'
        OR session_user <> 'lab_booking_migrator'
        OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
        OR inet_server_port() IS DISTINCT FROM 5433
        OR current_setting('server_version_num') <> '170012' THEN
        RAISE EXCEPTION 'wrong database, role, address, port or version';
    END IF;
    IF (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = table_id AND relkind = 'r')
        IS DISTINCT FROM 'lab_booking_migrator' THEN RAISE EXCEPTION 'wrong equipment owner or object'; END IF;
    IF (SELECT array_agg(attname::text ORDER BY attnum) FROM pg_attribute
        WHERE attrelid = table_id AND attnum > 0 AND NOT attisdropped) IS DISTINCT FROM fields
        THEN RAISE EXCEPTION 'equipment columns drifted'; END IF;
    FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
        IF has_table_privilege(role_id, table_id, p) THEN RAISE EXCEPTION 'unexpected table privilege: %', p; END IF;
    END LOOP;
    FOREACH field IN ARRAY fields LOOP
        IF has_column_privilege(role_id, table_id, field, 'SELECT') IS DISTINCT FROM (field = 'id')
          OR has_column_privilege(role_id, table_id, field, 'INSERT') IS DISTINCT FROM (field <> 'id')
          OR has_column_privilege(role_id, table_id, field, 'SELECT WITH GRANT OPTION')
          OR has_column_privilege(role_id, table_id, field, 'INSERT WITH GRANT OPTION')
          OR has_column_privilege(role_id, table_id, field, 'UPDATE')
          OR has_column_privilege(role_id, table_id, field, 'REFERENCES') THEN
            RAISE EXCEPTION 'unexpected before column privileges: %', field;
        END IF;
    END LOOP;
    sequence_name := pg_get_serial_sequence('public.equipment_equipment','id');
    IF sequence_name IS NULL OR has_sequence_privilege(role_id, sequence_name, 'USAGE,SELECT,UPDATE')
        OR has_schema_privilege(role_id, 'public', 'CREATE')
        OR has_database_privilege(role_id, 'lab_booking', 'CREATE')
        OR NOT has_schema_privilege(role_id, 'public', 'USAGE')
        OR (SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname = role_id) IS DISTINCT FROM false
        THEN RAISE EXCEPTION 'unexpected role, schema or sequence privilege'; END IF;
    RAISE NOTICE 'before ACL assertions passed';
END
$verify$;
SELECT current_database(), session_user, current_user, host(inet_server_addr()), inet_server_port(),
       current_setting('server_version'), pg_get_userbyid(relowner) AS table_owner
FROM pg_class WHERE oid = 'public.equipment_equipment'::regclass;
SELECT attname AS column_name,
       has_column_privilege('lab_booking_app', attrelid, attname, 'SELECT') AS can_select,
       has_column_privilege('lab_booking_app', attrelid, attname, 'INSERT') AS can_insert,
       has_column_privilege('lab_booking_app', attrelid, attname, 'UPDATE') AS can_update
FROM pg_attribute
WHERE attrelid='public.equipment_equipment'::regclass AND attnum>0 AND NOT attisdropped
ORDER BY attnum;
GRANT SELECT (number, name, category, location, description, status)
ON TABLE public.equipment_equipment TO lab_booking_app;
DO $verify$
DECLARE
    field text;
    p text;
    table_id oid := to_regclass('public.equipment_equipment');
    role_id name := 'lab_booking_app';
    sequence_name text;
    fields text[] := ARRAY['id','number','name','category','location','description','status'];
BEGIN
    IF current_database() <> 'lab_booking' OR current_user <> 'lab_booking_migrator'
        OR session_user <> 'lab_booking_migrator'
        OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
        OR inet_server_port() IS DISTINCT FROM 5433
        OR current_setting('server_version_num') <> '170012' THEN
        RAISE EXCEPTION 'wrong database, role, address, port or version';
    END IF;
    IF (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = table_id AND relkind = 'r')
        IS DISTINCT FROM 'lab_booking_migrator' THEN RAISE EXCEPTION 'wrong equipment owner or object'; END IF;
    IF (SELECT array_agg(attname::text ORDER BY attnum) FROM pg_attribute
        WHERE attrelid = table_id AND attnum > 0 AND NOT attisdropped) IS DISTINCT FROM fields
        THEN RAISE EXCEPTION 'equipment columns drifted'; END IF;
    FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
        IF has_table_privilege(role_id, table_id, p) THEN RAISE EXCEPTION 'unexpected table privilege: %', p; END IF;
    END LOOP;
    FOREACH field IN ARRAY fields LOOP
        IF has_column_privilege(role_id, table_id, field, 'SELECT') IS DISTINCT FROM (true)
          OR has_column_privilege(role_id, table_id, field, 'INSERT') IS DISTINCT FROM (field <> 'id')
          OR has_column_privilege(role_id, table_id, field, 'SELECT WITH GRANT OPTION')
          OR has_column_privilege(role_id, table_id, field, 'INSERT WITH GRANT OPTION')
          OR has_column_privilege(role_id, table_id, field, 'UPDATE')
          OR has_column_privilege(role_id, table_id, field, 'REFERENCES') THEN
            RAISE EXCEPTION 'unexpected after column privileges: %', field;
        END IF;
    END LOOP;
    sequence_name := pg_get_serial_sequence('public.equipment_equipment','id');
    IF sequence_name IS NULL OR has_sequence_privilege(role_id, sequence_name, 'USAGE,SELECT,UPDATE')
        OR has_schema_privilege(role_id, 'public', 'CREATE')
        OR has_database_privilege(role_id, 'lab_booking', 'CREATE')
        OR NOT has_schema_privilege(role_id, 'public', 'USAGE')
        OR (SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls FROM pg_roles WHERE rolname = role_id) IS DISTINCT FROM false
        THEN RAISE EXCEPTION 'unexpected role, schema or sequence privilege'; END IF;
    RAISE NOTICE 'after ACL assertions passed';
END
$verify$;
SELECT attname AS column_name,
       has_column_privilege('lab_booking_app', attrelid, attname, 'SELECT') AS can_select,
       has_column_privilege('lab_booking_app', attrelid, attname, 'INSERT') AS can_insert,
       has_column_privilege('lab_booking_app', attrelid, attname, 'UPDATE') AS can_update
FROM pg_attribute
WHERE attrelid='public.equipment_equipment'::regclass AND attnum>0 AND NOT attisdropped
ORDER BY attnum;
```

</details>

<details>
<summary>Chrome 验证源码</summary>

```javascript
import { spawn } from "node:child_process";
import { mkdtemp, readFile, realpath, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, relative, isAbsolute } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const origin = process.env.STORY13_RUNTIME_ORIGIN || "http://127.0.0.1:8000";
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(origin)) throw Error("Only local HTTP is permitted.");
const expected = JSON.parse(process.env.STORY13_RUNTIME_DEMO);
if (expected.number !== "EQ-DEMO-S12-20261125" ||
    !/^\d+$/.test(expected.id) || !/^\d+$/.test(expected.missing_id) ||
    !Number.isSafeInteger(expected.device_count)) throw Error("Invalid demo snapshot.");
const roleLabels = { student: "学生", teacher: "教师", admin: "业务管理员" };
const statusLabel = { available: "可用", maintenance: "维修", disabled: "停用" }[expected.status];
const detail = "/equipment/" + expected.id + "/";
const missing = "/equipment/" + expected.missing_id + "/";
const protectedPath = join(process.env.LOCALAPPDATA, "LabBooking", "Protected", "accounts.json");
const manifest = JSON.parse((await readFile(protectedPath, "utf8")).replace(/^\uFEFF/, ""));
for (const role of Object.keys(roleLabels)) {
    if (manifest.filter(account => account.role === role && typeof account.username === "string" &&
        account.username.length && typeof account.password === "string" && account.password.length).length !== 1) {
        throw Error("Expected one approved account for role " + role);
    }
}
const profileRoot = await realpath(tmpdir());
const profile = await mkdtemp(join(profileRoot, "story13-chrome-"));
const chrome = spawn("C:/Program Files/Google/Chrome/Application/chrome.exe", [
    "--headless", "--no-first-run", "--disable-background-networking", "--no-proxy-server",
    "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0",
    "--user-data-dir=" + profile, "about:blank"
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
    ensure(await evaluate(expression(() => !document.querySelector("tbody, #equipment-description"))),
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
async function inspectDetail(account) {
    const sample = await evaluate(expression(() => ({
        values: [...document.querySelectorAll("main dl dd")].map(el => el.innerText),
        identity: document.querySelector("main p")?.innerText,
        whiteSpace: getComputedStyle(document.getElementById("equipment-description")).whiteSpace,
        boundary: document.querySelector("main").innerText.includes("不代表指定时段可预约")
    })));
    ensure(JSON.stringify(sample.values) === JSON.stringify([
        expected.number, expected.name, expected.category, expected.location, expected.description, statusLabel
    ]) && sample.identity === "当前身份：" + account.username + "（" + roleLabels[account.role] + "）" &&
        sample.whiteSpace === "pre-wrap" && sample.boundary, "Detail fields or identity mismatch for " + account.role);
}
let phase = "Chrome startup";
try {
    const port = await until(async () => {
        const s = (await readFile(join(profile, "DevToolsActivePort"), "utf8")).split(/\r?\n/)[0];
        return /^\d+$/.test(s) ? s : false;
    }, phase);
    const targets = await (await fetch("http://127.0.0.1:" + port + "/json/list")).json();
    const target = targets.find(t => t.type === "page");
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
    phase = "anonymous";
    await denied("/equipment/");
    await denied(detail);
    console.log(JSON.stringify({ case: phase, catalog: 302, detail: 302, restricted_markup: false }));
    for (const role of Object.keys(roleLabels)) {
        const account = manifest.find(account => account.role === role);
        let cleanup = false;
        try {
            phase = role + " login";
            await navigate("/login/");
            const beforeLogin = (await locationInfo()).time;
            ensure(await evaluate(expression((username, password) => {
                const form = document.querySelector('form[method="post"]');
                if (!form || form.querySelector("[name=next]") || !form.querySelector("[name=csrfmiddlewaretoken]")) return false;
                form.querySelector("[name=username]").value = username;
                form.querySelector("[name=password]").value = password;
                setTimeout(() => form.requestSubmit(), 0);
                return true;
            }, account.username, account.password)), "Login form missing.");
            cleanup = true;
            await after(beforeLogin, "/identity/", 200);
            ensure(await evaluate(expression((username, label) => {
                const values = [...document.querySelectorAll("main dl dd")].map(el => el.innerText);
                return values[0] === username && values[1] === label;
            }, account.username, roleLabels[role])), "Identity values mismatch.");
            phase = role + " catalog";
            await clickLink("main a", "查看设备目录", "/equipment/");
            const row = await evaluate(expression(number => {
                const rows = [...document.querySelectorAll("main tbody tr")];
                const row = rows.find(tr => tr.querySelector("th a")?.innerText === number);
                return row && { count: rows.length, values: [...row.children].map(td => td.innerText),
                    href: row.querySelector("th a").getAttribute("href") };
            }, expected.number));
            ensure(row?.count === expected.device_count && row.href === detail &&
                JSON.stringify(row.values) === JSON.stringify([
                    expected.number, expected.name, expected.category, expected.location, statusLabel
                ]), "Catalog row does not match the database.");
            phase = role + " clicked and direct detail";
            await clickLink("main tbody th a", expected.number, detail);
            await inspectDetail(account);
            await navigate(detail);
            await inspectDetail(account);
            phase = role + " missing";
            await navigate(missing, missing, 404);
            ensure(await evaluate(expression(() => document.querySelector("main h1")?.innerText === "设备不存在" &&
                !document.querySelector("#equipment-description"))), "Missing page did not hide equipment fields.");
            phase = role + " logout";
            await navigate("/identity/");
            const beforeLogout = (await locationInfo()).time;
            ensure(await evaluate(expression(() => {
                const button = document.querySelector('form[action="/logout/"] button[type="submit"]');
                if (!button) return false;
                setTimeout(() => button.click(), 0); return true;
            })), "Logout form missing.");
            await after(beforeLogout, "/login/", 200);
            cleanup = false;
            await denied("/equipment/");
            await denied(detail);
            console.log(JSON.stringify({ case: role, identity: 200, catalog: 200, detail_click: 200,
                detail_direct: 200, absent: 404, logout_verified: true, post_logout: [302, 302], fields_match: true }));
        } finally {
            if (cleanup) {
                try {
                    const current = (await locationInfo())?.time;
                    await command("Page.navigate", { url: origin + "/identity/" });
                    await after(current, "/identity/", 200);
                    const prior = (await locationInfo()).time;
                    await evaluate(expression(() => setTimeout(() => document.querySelector('form[action="/logout/"]')?.requestSubmit(), 0)));
                    await after(prior, "/login/", 200);
                } catch {}
            }
        }
    }
    console.log(JSON.stringify({ result: "passed", detail_url: origin + detail, missing_url: origin + missing }));
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
    if (/^story13-chrome-[^\\/]+$/.test(delta) && !isAbsolute(delta)) {
        try { await rm(resolved, { recursive: true, maxRetries: 4, retryDelay: 200 }); }
        catch { console.error("Temporary Chrome profile could not be removed."); process.exitCode = 1; }
    }
}
```

</details>
