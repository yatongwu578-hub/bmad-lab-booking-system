// Route/DOM adapter for the verified W01 CDP recorder. Never submit a reservation form.
async function drive() {
    const plan = readJson(opts.inspection);
    const sample = plan.samples.detail;
    const pk = String(sample?.id ?? "");
    const terminal = ["rejected", "cancelled", "expired"].includes(sample?.status);
    const status = {approved:"已批准", pending:"待审核", rejected:"已拒绝", cancelled:"已取消", expired:"已失效"}[sample?.status];
    if (!/^[1-9][0-9]*$/.test(pk) || !status || plan.desired_port !== Number(origin.port) ||
        plan.acl_result !== "EXACT_COLUMNS_PRESENT" || Date.now() >= Date.parse(plan.samples.safe_until)) {
        throw Error("No current qualified formal route.");
    }
    const detail = "/reservations/manage/" + pk + "/";
    const confirm = detail + "cancel/";
    if (opts.role === "anonymous") {
        await action(() => nav(confirm), confirm, 302, "GET", "/login/");
        const redirects = documentReceipts.filter(x => x.method === "GET" && x.path === confirm && x.status === 302);
        if (redirects.length !== 1 || redirects[0].redirect?.path !== "/login/" ||
            redirects[0].redirect.query_sha256 !== digest("?next=" + confirm)) throw Error("Wrong anonymous login target.");
        record({event:"dom-assertion",label:"exact anonymous next path",passed:true});
        return;
    }
    const matches = readJson(opts.accounts).filter(r => r.role === opts.role);
    if (matches.length !== 1 || typeof matches[0].username !== "string" || typeof matches[0].password !== "string") {
        throw Error("Protected account input does not match the required business role.");
    }
    const account = matches[0];
    await action(() => nav("/login/"), "/login/", 200);
    await action(async () => {
        if (!await evaluate(`(() => {
            const f=document.querySelector('form[method=post]');
            if(!f?.elements.username||!f.elements.password||!f.elements.csrfmiddlewaretoken?.value)return false;
            f.elements.username.value=${JSON.stringify(account.username)};
            f.elements.password.value=${JSON.stringify(account.password)};
            setTimeout(()=>f.requestSubmit(),0);return true;
        })()`)) throw Error("Login form unavailable.");
    }, "/login/", 302, "POST", "/identity/");
    await verifyPage("authenticated business role", `[...document.querySelectorAll('dt')].find(x=>x.textContent.trim()==='业务角色')
        ?.nextElementSibling?.textContent.trim()===${JSON.stringify(opts.role === "admin" ? "业务管理员" : "学生")}`);
    if (opts.role === "admin") {
        const check = `(() => { const find=k=>[...document.querySelectorAll('main dl dt')].find(x=>x.textContent.trim()===k)
            ?.nextElementSibling?.textContent.trim(); return find('预约编号')===${JSON.stringify(pk)}
            && find('预约状态')===${JSON.stringify(status)} && !!find('设备') && !!find('时段（北京时间）'); })()`;
        await action(() => nav(detail), detail, 200);
        await verifyPage("existing detail and status", check);
        if (terminal) {
            await verifyPage("terminal detail has no cancellation link", `![...document.links].some(a=>a.pathname===${JSON.stringify(confirm)})`);
            await action(() => nav(confirm), confirm, 409, "GET", confirm, null);
            await verifyPage("terminal confirmation is unavailable", "!document.querySelector('main form[method=post]')");
        } else {
            await action(() => click(confirm), confirm, 200);
            await verifyPage("confirmation fields, reason input and abandon links", `(() => {
                const f=document.querySelector('main form[method=post]');
                const reason=f?.elements.reason;
                const link=(p,t)=>[...document.links].some(a=>a.pathname===p&&!a.search&&a.textContent.trim()===t);
                if(!(${check})||!f||new URL(f.action).origin!==location.origin||new URL(f.action).pathname!==${JSON.stringify(confirm)}||
                    new URL(f.action).search||!f.elements.csrfmiddlewaretoken?.value||!reason||reason.disabled||reason.readOnly||
                    f.querySelector('button[type=submit]')?.textContent.trim()!=='确认取消'||
                    !link(${JSON.stringify(detail)},'返回预约详情')||!link('/reservations/manage/','返回预约管理'))return false;
                reason.value='smoke-draft-only';return reason.value==='smoke-draft-only';
            })()`);
            await action(() => click(detail), detail, 200);
            await verifyPage("abandon returned to unchanged detail", check);
        }
    } else {
        await action(() => nav(confirm), confirm, 403, "GET", confirm, null);
        await verifyPage("role denial is generic", "!document.querySelector('main dl, main table, main form') && !document.body.innerText.includes('操作历史')");
    }
    await action(() => nav("/identity/"), "/identity/", 200);
    await signOut();
}
