"""Summarize retained guarded-smoke evidence. Never runs Django, Chrome, SQL or Finish."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGIN = "http://127.0.0.1:8003"
BEGIN = "<!-- MACHINE-EVIDENCE:BEGIN -->"
END = "<!-- MACHINE-EVIDENCE:END -->"
ATTEMPT = r"\d{8}-\d{6}-\d{3}-[0-9a-f]{8}"
BEIJING = timezone(timedelta(hours=8))
ROLES = {None: "未认证", "student": "学生", "teacher": "教师", "admin": "管理员"}
ACL_INPUTS = {"acl-before.json", "acl-after.json", "acl-ready.txt", "runtime-source.sha256"}
DEMO_TOOLS = {"run-story-2-3-demo-server.py", "story23_formal_demo.py", "read-story-2-3-formal.py"}
FINISH_INPUTS = {"acl-before.json", "acl-after.json", "runtime-source.sha256", "sample-before.json",
                 "sample-before.sha256", "browser-http.jsonl", "guard-start.txt", "demo-tools.sha256"}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    data = path.read_bytes()
    return data.decode("utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")


def digest(path):
    return sha256(path.read_bytes()).hexdigest().upper()


def manifest(path):
    rows = {}
    for line in read(path).splitlines():
        hash_, name = line.split("  ", 1)
        require(re.fullmatch(r"[0-9A-F]{64}", hash_) and name not in rows
                and all(re.fullmatch(r"[a-zA-Z0-9_.-]+", part) and part not in {".", ".."}
                        for part in name.split("/")), f"Invalid manifest: {path.name}")
        rows[name] = hash_
    return rows


def check_files(entries, directory):
    for name, hash_ in entries.items():
        require(digest(directory / name) == hash_, f"Fingerprint differs: {name}")


def timestamp(value):
    # PowerShell's round-trip format carries seven fractional digits.
    at = datetime.fromisoformat(re.sub(r"(\.\d{6})\d+(?=[+-])", r"\1", value))
    require(at.utcoffset() is not None, "Missing timestamp offset")
    return at.astimezone(BEIJING)


def link(scope, path, label=None):
    return f"[{label or path.name}]({Path(os.path.relpath(path, scope)).as_posix()})"


def finish_evidence(scope):
    candidates = sorted(p for p in scope.iterdir() if p.is_dir() and re.fullmatch("finish-" + ATTEMPT, p.name))
    complete = []
    other = []
    for folder in candidates:
        try:
            entries = manifest(folder / "sample-origin.sha256")
            require(set(entries) == FINISH_INPUTS, "Finish source inventory differs")
            check_files(entries, scope)
            check_files(entries, folder)
            require(read(folder / "postcheck.txt").strip() == "STORY23_FORMAL_POSTCHECK_OK", "No success marker")
            require(read(folder / "demo-after-catalog.stdout.txt").strip() == "STORY23_READ_EXACT_OK"
                    and "ACL_RESULT=EXACT_COLUMNS_PRESENT" in read(folder / "browser-after-app.stdout.txt").splitlines(),
                    "No bound exact post-run ACL readback")
            path = folder / "sample-after.json"
            after = json.loads(read(path))
            require(after["state"] == "EXACT" and after["outcome"]["outside_approved_delta_unchanged"] is True,
                    "No verified database delta")
            complete.append((path, after["outcome"]))
        except (OSError, KeyError, ValueError):
            other.append(folder)
    return complete, other


def archived_failure(scope, folder):
    """Read the retained negative result, without changing its formal verdict."""
    entries = manifest(folder / "sample-origin.sha256")
    require(folder.parent == scope and set(entries) == FINISH_INPUTS, "Unbound Finish inputs")
    check_files(entries, scope)
    check_files(entries, folder)
    sample = json.loads(read(scope / "sample-before.json"))
    after = json.loads(read(folder / "sample-after-unverified.json"))
    plan = sample["sample"]["demo"]
    prior, later = plan["hashes"], after["after_hashes"]
    require(plan["teacher"]["mode"] == "submit_once" and plan["expiry_mode"] == "expire_once",
            "Not the original guarded demo pattern")
    require(after["not_verified"] == "Teacher demo count or unapproved write differs"
            and read(folder / "demo-after-catalog.stderr.txt").strip() ==
            "Story 2.3 read-only stopped: RuntimeError [n/a] Teacher demo count or unapproved write differs"
            and not (folder / "postcheck.txt").exists(), "Different Finish failure")
    reason = after["not_verified"]
    require(after["state"] == "EXACT" and all(after[key] == sample[key] for key in (
        "effective_matrix", "explicit_acl", "identity", "migrations", "prior_acl_sha256", "independent_identity")),
        "After ACL, schema or identity differs from before")
    require(all(later[table] == prior[table] for table in ("equipment", "accounts")), "Equipment or account drift")
    added = set(later["reservations"]) - set(prior["reservations"])
    require(not added and set(later["reservations"]) == set(prior["reservations"])
            and all(later["reservations"][rid] == digest_ for rid, digest_ in prior["reservations"].items() if rid != "1"),
            "Reservation delta is not the missing-teacher case")
    expired = {**plan["student_reservation"], "status": "expired"}
    student_hash = sha256(json.dumps(expired, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(student_hash == later["reservations"]["1"], "Student #1 is not a status-only expiry")
    new_history = set(later["history"]) - set(prior["history"])
    require(len(new_history) == 1 and all(later["history"].get(hid) == hash_ for hid, hash_ in prior["history"].items()),
            "History delta is not one append")
    history_id = int(next(iter(new_history)))
    events = [json.loads(line) for line in read(scope / "browser-http.jsonl").splitlines() if line.strip()]
    student = [e for e in events if e["role"] == "student" and e["method"] == "GET"
               and e["path"] == "/reservations/" and e["status"] == 200]
    require(len(student) >= 2 and all(e.get("student_snapshot") == {"status": "expired", "history_ids": [history_id]} for e in student)
            and student[0]["writes"] == ["expire-1", "expire-history-1"]
            and all(not e["writes"] for e in student[1:]), "Student reads did not prove idempotence")
    require(not any(e["method"] == "POST" and e["path"].endswith("/reserve/") for e in events), "A reservation POST was retained")
    return {"reason": reason, "history_id": history_id, "student_reads": len(student),
            "reservation_added": len(added), "after_hashes": later}


def render(scope):
    require(re.fullmatch("smoke-" + ATTEMPT, scope.name)
            and re.fullmatch("story-2-3-formal-" + ATTEMPT, scope.parent.name)
            and not any("offline" in p.lower() for p in scope.parts), "Not a formal guarded smoke directory")
    logs = scope / "browser-http.jsonl"
    stderr = scope / "server.stderr.txt"
    acl_link = manifest(scope / "acl-origin.sha256")
    require(set(acl_link) == ACL_INPUTS, "Wrong ACL link inventory")
    check_files(acl_link, scope)
    check_files(acl_link, scope.parent)
    require(read(scope / "acl-ready.txt").strip() == "STORY23_FORMAL_ACL_READY_BY_READBACK", "No linked ACL readback")
    runtime = scope / "runtime-source.sha256"
    runtime_rows = manifest(runtime)
    approved = HERE / "story-2-3-independent-run-20261127-114813-950-de7b7f2c" / "before.sha256"
    require(digest(approved) == "F12EB1C9C5947E37BE7AC3E4E760F846A480AD4557FD7B92DE99C6193B892E06",
            "Independent source manifest changed")
    actual_paths = {"manage.py", "requirements.txt"}
    for directory in ("accounts", "audit", "equipment", "lab_booking", "reservations"):
        actual_paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob("*")
                            if p.is_file() and p.suffix in {".py", ".html"})
    approved_rows = manifest(approved)
    require(set(runtime_rows) == actual_paths and all(approved_rows.get(p) == h for p, h in runtime_rows.items()),
            "Runtime inventory differs from independent review")
    check_files(runtime_rows, ROOT)
    demo_tools = manifest(scope / "demo-tools.sha256")
    require(set(demo_tools) == DEMO_TOOLS, "Wrong demo-tool manifest")
    check_files(demo_tools, HERE)

    before_path = scope / "sample-before.json"
    require(digest(before_path) == read(scope / "sample-before.sha256").strip(), "Before sample hash differs")
    before = json.loads(read(before_path))
    sample = before["sample"]
    demo = sample["demo"]
    require(before["state"] == "EXACT" and demo["ready"] is True
            and read(scope / "guard-start.txt").strip() == "STORY23_VERIFICATION_GUARD_CONFIGURED", "Guarded launch unverified")
    matrix = before["effective_matrix"]
    acl_before = json.loads(read(scope / "acl-before.json"))
    acl_after = json.loads(read(scope / "acl-after.json"))
    require(acl_after["state"] == "EXACT"
            and all(acl_after[key] == before[key] for key in ("effective_matrix", "explicit_acl", "identity", "migrations", "prior_acl_sha256"))
            and acl_before["prior_acl_sha256"] == acl_after["prior_acl_sha256"], "Before-smoke ACL differs from original readback")
    columns = sorted(r["column_name"] for r in matrix if r["relation_name"] == "audit_operationhistory"
                     and r["operation"] == "SELECT" and r["effective"])
    require(columns == ["action", "actor_type", "id", "reason", "reservation_id"]
            and not any(r["can_delegate"] for r in matrix), "ACL matrix differs")
    started, origin, mode, attempt = read(scope / "launch.txt").splitlines()
    require(origin == ORIGIN and attempt == scope.name and mode == "original .venv; runtime; --noreload",
            "Launch origin or attempt differs")
    launches = []
    for folder in sorted(scope.glob("chrome-*")):
        if not (folder / "opened.txt").is_file():
            continue
        require(read(folder / "opened.txt").strip() == "STORY23_CHROME_LAUNCHES_REQUESTED", "Wrong Chrome marker")
        path = folder / "listener.txt"
        listener = dict(line.split("=", 1) for line in read(path).splitlines())
        require(listener["attempt"] == attempt and listener["origin"] == origin
                and listener["pid"].isdigit() and re.fullmatch(r"\d+(\.\d+){3}", listener["chrome"])
                and timestamp(listener["start"]) >= timestamp(started), "Chrome listener differs")
        launches.append((path, listener))
    require(launches and all(item[1] == launches[0][1] for item in launches), "No consistent Chrome listener receipt")

    events = [json.loads(line) for line in read(logs).splitlines() if line.strip()]
    django = Counter((date, method, path.partition("?")[0], int(status)) for date, method, path, status in
                     re.findall(r'^(?:python\.exe : )?\[(\d{2}/[A-Za-z]{3}/\d{4} \d{2}:\d{2}:\d{2})\] "([A-Z]+) (\S+) HTTP/[^ ]+" (\d{3}) \d+\s*$',
                                read(stderr), re.M))
    require(events and timestamp(events[0]["at"]) >= timestamp(started), "Missing or unbound HTTP receipts")
    require(django == Counter((timestamp(e["at"]).strftime("%d/%b/%Y %H:%M:%S"), e["method"], e["path"], e["status"])
                              for e in events), "Structured HTTP and Django access log disagree")
    pid = launches[0][1]["pid"]
    chrome = launches[0][1]["chrome"]
    roles = sample["accounts"]
    teacher = demo["teacher"]
    posts = [e for e in events if e["method"] == "POST" and re.fullmatch(r"/equipment/\d+/reserve/", e["path"])]
    teacher_posts = [e for e in posts if e["role"] == "teacher"]
    lines = ["## 机器证据（自动整理）", "",
             f"- 批次 `{attempt}`。启动 `{started}`，监听 `{origin}`，PID `{pid}`。",
             f"- Chrome `{chrome}`。学生／教师／管理员隔离配置的启动请求已留存，"
             f"不代表三位组员各自操作。{link(scope, launches[0][0])} · {link(scope, launches[0][0].parent / 'stages.txt')} · {link(scope, scope / 'server.stdout.txt')}",
             f"- {len(runtime_rows)}/{len(runtime_rows)} 项运行输入逐项核对独立复验及本地文件，"
             f"清单 SHA-256 `{digest(runtime)}`。验证工具 {len(demo_tools)}/{len(demo_tools)} 项匹配。"
             f"{link(scope, runtime)} · {link(scope, approved, '独立复验输入')} · {link(scope, scope / 'demo-tools.sha256')}",
             f"- ACL 为已授权批次回读及本轮启动前同源核验，运行角色 `{before['identity']['role']}`，"
             f"{len(matrix)} 项矩阵中有效项 {sum(r['effective'] for r in acl_before['effective_matrix'])} → "
             f"{sum(r['effective'] for r in matrix)}（原授权前 → 原授权后及本轮启动前）。"
             f"历史表仅 `{'`, `'.join(columns)}` 可读，无转授。"
             f"{link(scope, scope / 'acl-origin.sha256')} · {link(scope, scope / 'acl-before.json', '原授权前 ACL')} · "
             f"{link(scope, scope / 'acl-after.json', '原授权后 ACL（非本轮结束后）')}",
             f"- 前置快照 `{sample['observed_beijing']}`，SHA-256 `{digest(before_path)}`。"
             f"开放窗口截至 `{sample['deadline_beijing']}`。{link(scope, before_path)}", "",
             "### 预约、占用及写入", "",
             "| 角色 / 预约 | 设备 / 北京时间段 | 前置状态 |", "| --- | --- | --- |"]
    for role, account in roles.items():
        for r in account["reservations"]:
            lines.append(f"| {ROLES[role]} #{r['id']} | `{r['device_number']}`（ID {r['device_id']}），"
                         f"{r['start_beijing']} → {r['end_beijing']} | `{r['reservation_status']}`，设备 `{r['device_status']}`，有效占用 {str(r['effective']).lower()} |")
        if not account["reservations"]:
            lines.append(f"| {ROLES[role]} | — | 无本人预约 |")
    lines.extend(["", f"- 学生前置历史 {roles['student']['history_count']} 条。"
                  f"获批范围仅含现有 #1 的 FR-018 收尾或已失效复用。学生新增 POST **不适用（未批准）**，"
                  f"留存预约路由中学生 POST {sum(e['role'] == 'student' for e in posts)} 次。"])
    if teacher["mode"] == "reuse":
        lines.append(f"- 教师前置计划为复用 #{teacher['reservation_id']}，实际是否打开本人详情见下表。")
    else:
        lines.append(f"- 教师前置计划为单次提交，`{origin}{teacher['path']}`，设备 `{teacher['device_number']}`"
                     f"（ID {teacher['device_id']}），拟用 `{teacher['start']}` → `{teacher['end']}`。以上为计划，非实际请求。")
    lines.append(f"- 教师预约 POST 实际留存 **{len(teacher_posts)} 次**。"
                 + ("状态见逐请求表。是否新增及其预约 ID 仅取独立后置回执。" if teacher_posts else "没有已留存的提交或 201。"))
    complete, other = finish_evidence(scope)
    if len(complete) == 1:
        path, outcome = complete[0]
        row = outcome["teacher_new_row"]
        history = outcome["student_history"]
        lines.append(f"- 独立后置核验留存。学生 #{outcome['student_id']} `{outcome['student_status']}`，"
                     f"有效占用 `{str(outcome['student_effective_before']).lower()}` → `{str(outcome['student_effective_after']).lower()}`，"
                     f"历史 ID `{history['id']}`。教师 #{outcome['teacher_reservation_id']}，"
                     f"模式 `{outcome['teacher_mode']}`，新增 `{int(row is not None)}` 条。批准增量外未变。{link(scope, path)}")
        if row:
            lines.append(f"- 新增预约设备 ID `{row['equipment_id']}`，`{row['status']}`，"
                         f"北京时间 `{timestamp(row['start_at']).isoformat()}` → `{timestamp(row['end_at']).isoformat()}`。")
    elif not complete:
        lines.append("- **没有正式 `Finish` 通过回执**。不完整或失败的独立快照作为单独证据列在下方。")
    else:
        lines.append("- 有多份绑定的后置回执，未自动选定验收依据。")
    for folder in other:
        try:
            archived = archived_failure(scope, folder)
        except (KeyError, OSError, ValueError):
            lines.append(f"- 后置尝试未形成完整可绑定回执。{link(scope, folder / 'stages.txt', folder.name)}")
        else:
            lines.append(f"- 失败批次 `{folder.name}` 的真实后置快照绑定原请求及前置证据。"
                         f"验收错误为 `{archived['reason']}`。计划新增教师预约 1 条，实际新增 {archived['reservation_added']} 条。"
                         f"学生 #1 仅状态变为 `expired`，有效占用前置已为 `false`、后置仍不占用，唯一新增系统历史 ID "
                         f"`{archived['history_id']}`，{archived['student_reads']} 次列表读回中仅首次有写入。"
                         f"其他预约、设备、既有历史及非会话账号字段散列一致。后置权限目录核验为 `EXACT`，"
                         f"但未走到独立的 `browser-after-app` 阶段，也没有正式成功标记。"
                         f"{link(scope, folder / 'demo-after-catalog.stderr.txt')} · {link(scope, folder / 'sample-after-unverified.json')}")

    lines.extend(["", "### 实际请求（北京时间，UTC+08:00）", "",
                  f"{len(events)} 条与 Django 访问日志逐条交叉核对。写入栏是验证中间件的 SQL 标签，"
                  f"有独立请求内读回时单独列出。URL 只列留存路径，不转录查询参数。"
                  f"HTTP 不能证明页面文字、点击来源或 `Location` 响应头。"
                  f"{link(scope, logs)} · {link(scope, stderr)}", "",
                  "| 行 | 北京时间 | 角色 / 脱敏账号 | 方法和 URL | HTTP | 预约 ID / 记录 |",
                  "| --- | --- | --- | --- | --- | --- |"])
    for i, e in enumerate(events, 1):
        require(e["method"] in {"GET", "POST"} and re.fullmatch(r"/[A-Za-z0-9_/.-]*", e["path"]), "Unsafe request evidence")
        role = e["role"]
        account_id = e["account_id"]
        require((role is None and account_id is None) or (role in roles and account_id == roles[role]["account_id"]),
                "HTTP account differs from approved sample")
        target = re.fullmatch(r"/reservations/(\d+)/result/", e["path"])
        details = [f"#{target[1]}"] if target else []
        if e["writes"]:
            details.append("`" + ", ".join(e["writes"]) + "`")
        if "student_snapshot" in e:
            state = e["student_snapshot"]
            details.append(f"#1 独立读回 `{state['status']}`，历史 ID `{state['history_ids']}`")
        lines.append(f"| {i} | {timestamp(e['at']).replace(tzinfo=None).isoformat(sep=' ', timespec='microseconds')} | "
                     f"{ROLES[role]}{f' / #{account_id}' if role else ''} | `{e['method']} {origin}{e['path']}` | "
                     f"{e['status']} | {' · '.join(details) or '—'} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("smoke_directory", type=Path)
    parser.add_argument("--check", action="store_true", help="Compare current receipt without writing")
    options = parser.parse_args()
    try:
        scope = options.smoke_directory.resolve(strict=True)
        receipt = scope / "chrome-receipt.md"
        require(receipt.is_file() and not receipt.is_symlink(), "Missing receipt")
        old = read(receipt)
        require(old.count(BEGIN) == old.count(END) == 1 and old.index(BEGIN) < old.index(END),
                "Missing machine section markers; existing human notes left untouched")
        start, _, rest = old.partition(BEGIN)
        _, _, end = rest.partition(END)
        new = start + BEGIN + "\n\n" + render(scope) + "\n" + END + end
        if options.check:
            require(new == old, "Machine evidence differs from existing receipt")
        elif new != old:
            receipt.write_text(new, encoding="utf-8", newline="\n")
        print("STORY23_CHROME_MACHINE_EVIDENCE_CHECKED")
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.exit(1, f"Evidence summary stopped: {error}\n")


if __name__ == "__main__":
    main()
