async function drive() {
    const plan = readJson(opts.inspection);
    if (plan.port !== Number(origin.port) || Date.now() >= Date.parse(plan.deadline)) {
        throw Error("2.4 receipt window is closed.");
    }
    const list = "/reservations/";
    const target = plan.existing_target ?? plan.absent;
    const cancel = "/reservations/" + target + "/cancel/";
    const detail = "/reservations/" + target + "/result/";
    const absent = "/reservations/" + plan.absent + "/cancel/";
    if (opts.role === "anonymous") {
        await action(() => nav(cancel), cancel, 302, "GET", "/login/");
        return;
    }
    const rows = readJson(opts.accounts);
    const account = rows.find(row => row.role === opts.role);
    if (!account) throw Error("Protected input role is missing.");
    await action(() => nav("/login/"), "/login/", 200);
    await action(async () => {
        if (!await evaluate("(() => {const f=document.querySelector('form[method=post]');"
            + "if(!f?.elements.csrfmiddlewaretoken?.value)return false;"
            + "f.elements.username.value=" + JSON.stringify(account.username) + ";"
            + "f.elements.password.value=" + JSON.stringify(account.password) + ";"
            + "setTimeout(()=>f.requestSubmit(),0);return true;})()")) throw Error("Native login form unavailable.");
    }, "/login/", 302, "POST", "/identity/");
    await verifyPage("signed-in role", "document.body.innerText.includes(" +
        JSON.stringify({student:"学生",teacher:"教师",admin:"业务管理员"}[opts.role]) + ")");
    if (opts.role === plan.owner_role) {
        if (plan.list_safe) {
            await action(() => click(list), list, 200);
            await action(() => click(cancel), cancel, 200);
        } else {
            await action(() => nav(detail), detail, 200);
            await action(() => click(cancel), cancel, 200);
        }
        await verifyPage("owner confirmation uses a native form", "(() => {const f=document.querySelector('main form');"
            + "return document.querySelector('h1')?.textContent.includes('确认取消')&&f?.method==='post'&&"
            + "f.enctype==='application/x-www-form-urlencoded'&&!!f.elements.csrfmiddlewaretoken?.value;})()");
        await evaluate("(() => {for(const e of document.querySelectorAll('main dd')) e.textContent='[redacted]'; return true;})()");
        const png = await command("Page.captureScreenshot", {format:"png"});
        writeFileSync(opts.out + ".redacted.png", Buffer.from(png.data,"base64"), {flag:"wx"});
        const back = plan.list_safe ? list : detail;
        await action(() => click(back), back, 200);
        await verifyPage("abandon returns to the same selectable target", "Array.from(document.links).some(a=>a.pathname===" + JSON.stringify(cancel) + ")");
    } else {
        const status = opts.role === "admin" ? 403 : 404;
        for (const p of new Set([cancel, absent])) {
            await action(() => nav(p), p, status, "GET", p, null);
            await verifyPage("denied response does not project reservation fields",
                "!document.querySelector('main dl,main table,main form')&&!(" +
                JSON.stringify(cancel) + "!==location.pathname&&Array.from(document.links).some(a=>a.pathname===" + JSON.stringify(cancel) + "))");
        }
        if (status === 404 && cancel !== absent) {
            const hashes = documentReceipts.filter(r => [cancel,absent].includes(r.path) && r.status === 404).map(r=>r.body_sha256);
            if (hashes.length !== 2 || !hashes[0] || hashes[0] !== hashes[1]) throw Error("Foreign and missing responses differ.");
            record({event:"dom-assertion",label:"foreign and missing equal",passed:true});
        }
    }
    await action(() => nav("/identity/"), "/identity/", 200);
    await signOut();
}
