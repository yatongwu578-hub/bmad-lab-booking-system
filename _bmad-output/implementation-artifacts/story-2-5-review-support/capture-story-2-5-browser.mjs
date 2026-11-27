// Passive Chrome CDP document recorder. Run only in the approved local smoke window.
// Does not log headers other than Cache-Control, credentials, cookies, bodies, or CDP frames.
import { createHash } from "node:crypto";
import { closeSync, openSync, readFileSync, writeSync } from "node:fs";
import { parseArgs } from "node:util";

const { values: opts } = parseArgs({ options: {
    origin: { type: "string" }, debug: { type: "string" }, out: { type: "string" },
    role: { type: "string" }, seconds: { type: "string", default: "180" },
    inspection: { type: "string" }, accounts: { type: "string" }, probe: { type: "boolean" },
} });
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(opts.origin ?? "") ||
    !/^\d+$/.test(opts.debug ?? "") || !opts.out ||
    !["anonymous", "student", "teacher", "admin"].includes(opts.role) ||
    !/^\d+$/.test(opts.seconds) || Number(opts.seconds) < 10 || Number(opts.seconds) > 1200 ||
    (opts.probe && (opts.inspection || opts.accounts || opts.role !== "anonymous"))) {
    throw Error("Specify --origin http://127.0.0.1:PORT --debug PORT --out NEW.jsonl --role ROLE [--seconds 10-1200].");
}
const origin = new URL(opts.origin);
if (Number(origin.port) < 1024 || Number(opts.debug) < 1024 || Number(opts.debug) > 65535 ||
    Number(opts.debug) === Number(origin.port) || typeof WebSocket === "undefined") {
    throw Error("Use separate loopback ports and a Node runtime with native WebSocket.");
}
const digest = value => createHash("sha256").update(value).digest("hex");
function scopedUrl(value) {
    try {
        const u = new URL(value, origin);
        if (u.origin !== origin.origin ||
            !/^(?:\/login\/|\/logout\/|\/identity\/|\/reservations\/manage\/(?:\d+\/)?)$/.test(u.pathname)) return null;
        return { path: u.pathname, query_sha256: u.search ? digest(u.search) : null };
    } catch { return null; }
}
const targets = await fetch(`http://127.0.0.1:${opts.debug}/json/list`, {
    redirect: "error", signal: AbortSignal.timeout(3000)
}).then(r => {
    if (!r.ok) throw Error("Cannot list dedicated Chrome tabs.");
    return r.json();
});
const available = targets.filter(t => t.type === "page" &&
    (t.url === "about:blank" || scopedUrl(t.url)) && t.webSocketDebuggerUrl);
if (available.length !== 1) throw Error("Use a dedicated Chrome profile with exactly one eligible tab.");
const endpoint = new URL(available[0].webSocketDebuggerUrl);
if (endpoint.protocol !== "ws:" || endpoint.hostname !== "127.0.0.1" ||
    endpoint.port !== String(Number(opts.debug)) || !endpoint.pathname.startsWith("/devtools/page/")) {
    throw Error("Chrome CDP endpoint is not the dedicated loopback target.");
}
const fd = openSync(opts.out, "wx");
const documentReceipts = [];
const record = x => {
    if (x.event === "document") documentReceipts.push(x);
    writeSync(fd, JSON.stringify({ at: new Date().toISOString(), role: opts.role, ...x }) + "\n");
};
const ws = new WebSocket(endpoint);
const commands = new Map(), active = new Map(), finishing = new Set();
let seq = 0, documents = 0, bodyErrors = 0, aborted = 0, closing = false;
const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq;
    const timer = setTimeout(() => { commands.delete(id); reject(Error("CDP receipt timed out for " + method + ".")); }, 4000);
    commands.set(id, { resolve, reject, timer });
    ws.send(JSON.stringify({ id, method, params }));
});
const header = (h, name) => Object.entries(h ?? {}).find(([key]) => key.toLowerCase() === name)?.[1] ?? null;
const responseMeta = response => ({
    status: response.status, cache_control: header(response.headers, "cache-control"),
    redirect: header(response.headers, "location") ? scopedUrl(header(response.headers, "location")) : null,
    served_from_cache: Boolean(response.fromDiskCache || response.fromServiceWorker),
});
ws.addEventListener("message", e => {
    const packet = JSON.parse(e.data);
    const p = packet.params;
    if (packet.id) {
        const pending = commands.get(packet.id);
        if (!pending) return;
        commands.delete(packet.id);
        clearTimeout(pending.timer);
        if (packet.error) pending.reject(Error("Chrome did not return the requested receipt."));
        else pending.resolve(packet.result);
        return;
    }
    if (closing || !p) return;
    const key = p.requestId;
    if (packet.method === "Network.requestWillBeSent" && p.type === "Document") {
        const prev = active.get(key);
        if (prev && p.redirectResponse) {
            const meta = responseMeta(p.redirectResponse);
            record({ event: "document", ...prev.request, ...meta, redirect: meta.redirect ?? scopedUrl(p.request.url), body_sha256: null });
            documents++;
        }
        active.delete(key);
        const url = scopedUrl(p.request.url);
        if (url) active.set(key, {request: { request_id: key, method: p.request.method, ...url }});
    } else if (packet.method === "Network.responseReceived" && p.type === "Document") {
        const req = active.get(key);
        if (req) req.response = responseMeta(p.response);
    } else if (packet.method === "Network.loadingFinished") {
        const req = active.get(key);
        active.delete(key);
        if (!req?.response) return;
        const task = command("Network.getResponseBody", {requestId: key}).then(body => {
            const bytes = Buffer.from(body.body, body.base64Encoded ? "base64" : "utf8");
            record({event: "document", ...req.request, ...req.response, body_sha256: digest(bytes), body_bytes: bytes.length});
            documents++;
        }).catch(() => {
            bodyErrors++;
            record({event: "document", ...req.request, ...req.response, body_sha256: null, body_receipt_unavailable: true});
        });
        finishing.add(task);
        task.finally(() => finishing.delete(task));
    } else if (packet.method === "Network.loadingFailed" && active.has(key)) {
        aborted++;
        record({event: "document-failed", ...active.get(key).request});
        active.delete(key);
    }
});

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(test, failure) {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
        if (bodyErrors || aborted) throw Error("Chrome document evidence is incomplete.");
        if (await test()) return;
        await sleep(80);
    }
    throw Error(failure);
}
const readJson = path => JSON.parse(new TextDecoder("utf-8", {fatal:true}).decode(readFileSync(path)));
const nav = path => command("Page.navigate", { url: new URL(path, origin).href });
async function evaluate(expression) {
    const answer = await command("Runtime.evaluate", {expression, returnByValue:true});
    if (answer.exceptionDetails) throw Error("Chrome DOM action failed.");
    return answer.result?.value;
}
async function verifyPage(label, predicate) {
    if (!await evaluate(predicate)) throw Error(`${label} DOM check failed.`);
    record({event:"dom-assertion",label,passed:true});
}
async function action(run, path, status, method="GET", finalPath=path, finalStatus=200) {
    const begin = documentReceipts.length;
    const wanted = scopedUrl(path), final = scopedUrl(finalPath);
    await run();
    await waitFor(() => {
        const all = documentReceipts.slice(begin);
        if (all.some(x => x.status >= 500 || x.status === 409)) throw Error("Guard or server stopped the formal sequence.");
        return !active.size && !finishing.size && all.some(x => x.method === method && x.path === wanted.path &&
            x.query_sha256 === wanted.query_sha256 && x.status === status) &&
            (finalStatus === null || all.some(x => x.path === final.path && x.status === finalStatus));
    }, "Expected navigation was not captured.");
}
async function click(path) {
    const url = new URL(path, origin).href;
    const clicked = await evaluate(`(() => { const a=[...document.links].find(a=>a.href===${JSON.stringify(url)}); if(!a)return false; setTimeout(()=>a.click(),0); return true; })()`);
    if (!clicked) throw Error("Expected same-origin navigation link is absent.");
}
async function signOut() {
    await action(async () => {
        if (!await evaluate(`(() => { const f=[...document.forms].find(x=>x.method==='post'&&new URL(x.action).pathname==='/logout/');
            if(!f?.elements.csrfmiddlewaretoken?.value)return false;setTimeout(()=>f.requestSubmit(),0);return true; })()`)) {
            throw Error("Native logout form or CSRF input unavailable.");
        }
    },"/logout/",302,"POST","/login/");
}
async function drive() {
    const plan = readJson(opts.inspection);
    const {samples: sample} = plan;
    const route = "/reservations/manage/";
    if (plan.desired_port !== Number(origin.port) || plan.acl_result !== "EXACT_COLUMNS_PRESENT" ||
        sample.full_unsafe_pending !== 0 || !sample.filter || !sample.detail || Date.now() >= Date.parse(sample.safe_until)) {
        throw Error("Browser plan is not in the approved complete safe scope.");
    }
    const filterQuery = "?" + new URLSearchParams({equipment: sample.filter.number}).toString();
    const filter = route + filterQuery;
    const detail = route + sample.detail.id + "/";
    if (opts.role === "anonymous") {
        for (const path of [route,filter,detail]) await action(() => nav(path),path,302,"GET","/login/");
        return;
    }
    const rows = readJson(opts.accounts);
    const matches = rows.filter(r=>r.role===opts.role);
    if (matches.length!==1 || typeof matches[0].username!=="string" || typeof matches[0].password!=="string") {
        throw Error("Protected native login inputs do not match the approved role.");
    }
    const account = matches[0];
    await action(() => nav("/login/"),"/login/",200);
    await action(async () => {
        const valid = await evaluate(`(() => {const f=document.querySelector('form[method=post]');
            if(!f||!f.elements.username||!f.elements.password||!f.elements.csrfmiddlewaretoken?.value)return false;
            f.elements.username.value=${JSON.stringify(account.username)};f.elements.password.value=${JSON.stringify(account.password)};
            setTimeout(()=>f.requestSubmit(),0);return true;})()`);
        if (!valid) throw Error("Native login form or CSRF input unavailable.");
    },"/login/",302,"POST","/identity/");
    await verifyPage("authenticated identity and role-specific management link", `(() => {
        const roleLabel=${JSON.stringify({admin:"业务管理员",student:"学生",teacher:"教师"}[opts.role])};
        const role=[...document.querySelectorAll('dt')].find(x=>x.textContent.trim()==='业务角色')?.nextElementSibling;
        return location.pathname==='/identity/'&&role?.textContent.trim()===roleLabel&&
            [...document.links].some(a=>a.pathname==='/reservations/manage/')===${opts.role === "admin"};})()`);
    if (opts.role !== "admin") {
        for (const p of [route,filter,detail]) {
            await action(() => nav(p),p,403,"GET",p,null);
            await verifyPage("denial page contains no reservation projection",
                `!document.querySelector('main table, main dl')&&!document.body.innerText.includes('操作历史')`);
        }
        await action(() => nav("/identity/"),"/identity/",200);
        await signOut();
        return;
    }
    await action(() => click(route),route,200);
    await verifyPage("complete list, search and no future mutation controls", `document.querySelector('form[method=get] [name=equipment]')!==null&&
        document.body.innerText.includes('全部预约')&&![...document.querySelectorAll('main button')].some(b=>/批准|拒绝|取消/.test(b.textContent))`);
    await action(() => click(detail),detail,200);
    await verifyPage("detail summary and persisted history", `(() => {const f=[...document.querySelectorAll('main dl dt')].map(x=>x.textContent.trim());
        return ['申请人','设备','预约状态','设备当前状态'].every(x=>f.includes(x))&&f.some(x=>x.startsWith('时段'))&&
            f.some(x=>x==='处理原因')&&${sample.detail.has_history ? "!!document.querySelector('main table tbody tr')" : "true"};})()`);
    await action(() => click(route),route,200);
    await action(async () => {
        if (!await evaluate(`(() => {const field=document.querySelector('form[method=get] [name=equipment]');if(!field?.form)return false;
            field.value=${JSON.stringify(sample.filter.number)};setTimeout(()=>field.form.requestSubmit(),0);return true;})()`)) {
            throw Error("Expected native equipment form is absent.");
        }
    },filter,200);
    await verifyPage("affected scope or existing-device empty result", `document.body.innerText.includes(${JSON.stringify(sample.filter.affected ? "受影响预约" : "未找到符合筛选条件的预约")})`);
    if (sample.filter.detail_id !== null) {
        const selected = route + sample.filter.detail_id + "/" + filterQuery;
        await action(() => click(selected),selected,200);
        await verifyPage("filtered detail summary", `!!document.querySelector('main dl')`);
        await action(() => click(filter),filter,200);
    }
    await action(() => click(route),route,200);
    await action(() => click("/identity/"),"/identity/",200);
    await signOut();
}

try {
    await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(Error("Chrome WebSocket timeout.")), 4000);
        ws.addEventListener("open", () => {clearTimeout(timer); resolve();}, {once:true});
        ws.addEventListener("error", () => {clearTimeout(timer); reject(Error("Chrome WebSocket failed."));}, {once:true});
    });
    if (opts.probe) {
        if (await evaluate("location.href === 'about:blank' && 1 + 2 === 3") !== true) {
            throw Error("The dedicated Chrome renderer probe did not respond.");
        }
        record({event:"renderer-probe",passed:true});
        console.log("STORY25_W01_CHROME_PROBE_OK");
    } else {
    await command("Network.enable");
    await command("Page.enable");
    await command("Network.setCacheDisabled", {cacheDisabled:true});
    record({event:"capture-ready", origin:origin.origin});
    console.log("STORY25_CHROME_CAPTURE_READY");
    if (opts.inspection) await drive();
    else await new Promise(resolve => {
        const stop=() => {clearTimeout(timer); process.removeListener("SIGINT",stop); resolve();};
        const timer=setTimeout(stop,Number(opts.seconds)*1000);
        process.once("SIGINT",stop);
        ws.addEventListener("close",stop,{once:true});
    });
    closing=true;
    await Promise.all([...finishing]);
    record({event:"capture-stop", complete_documents:documents, body_errors:bodyErrors, aborted, pending:active.size});
    if (!documents || bodyErrors || aborted || active.size) throw Error("Incomplete Chrome evidence. Retain the first archive.");
    console.log("STORY25_CHROME_CAPTURE_OK");
    }
} catch (error) {
    if (opts.inspection || opts.probe) {
        // Archive progress but never print the private CDP expression or payload.
        record({event:"capture-error",failure:"formal browser action did not finish"});
        console.error("STORY25_W01_BROWSER_FAILED: " + (error instanceof SyntaxError ? "protected input format" : error.message));
        process.exitCode = 1;
    } else throw error;
} finally {
    if (ws.readyState < WebSocket.CLOSING) ws.close();
    closeSync(fd);
}
