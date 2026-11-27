# Story 2.3 正式库授权后置回读故障与恢复

> 最新执行：已确认当前样本存在 FR-018 写入风险。先按[样本阻塞与只读检查](story-2-3-formal-sample-hold.md)执行，不直接重放以下历史命令。

> 后续更新：此批次的 ACL 已精确读回。Serve、Chrome 和 Finish 已改为独立目录，当前执行请使用[最新续跑命令](story-2-3-serve-recovery.md)。以下原命令仅保留历史依据，不要重跑授权。

**结论：四列 GRANT 已提交，停止原因是只读工具误报，不是迁移或权限漂移。禁止在本批重放 Acl 或 GRANT。** 批次 `story-2-3-formal-20261127-120858-648-0dcaa5b4`。Story 沿用 BMAD 6.12.4 独立评审处置、维持 `review`。W1 在原批次已观察到精确权限，生命周期仍待恢复后置回执与正式体验，不标已关闭。 [原始回执与散列](story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/archive.sha256) · [独立评审](story-2-3-independent-recheck.md)

## 实际原因与最小修复

- [原始阶段](story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/stages.txt) 显示 `grant` 退出 0，[原始 psql stdout](story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/grant.stdout.txt) 依次含 `GRANT`、`COMMIT`、唯一 `STORY23_HISTORY_SELECT_COMMITTED`，stderr 为空。随后 `acl-after-catalog` 退出 1，stdout 原样为空，[原始 stderr](story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/acl-after-catalog.stderr.txt) 为 `RuntimeError [n/a] Migration records changed`。PowerShell 第 22 行仅转报非零退出，并不是故障位置。
- 授权前后都是实际运行角色的新连接读回。[矩阵原证](story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/story23-acl-probe.jsonl) 各有 76 项，原 26 个有效正项悉数保留，新增有效和显式权限均恰为历史表的 `action`、`actor_type`、`reason`、`reservation_id` 的 SELECT。最终读列为这四列和 `id`，无转授权和额外权限。目录工具已通过表级拒绝及所有者断言后才到达报错指令。没有 SQL 字段歧义或 ACL 零维空数组错误；有效权限、输出匹配与退出码如实返回。
- 两次记录的迁移和值逐项一致，均为 `audit.0001_initial`、`reservations.0001_initial` 及对应关系。[对象证据](story-2-3-formal-20261127-120858-648-0dcaa5b4-acl-original/schema.jsonl) 的物理列、约束、索引、序列归属前后一致，所有者仍为 `lab_booking_migrator`。只读工具在内存中使用 `readiness()` 返回的外层 `tuple`，前置 JSON 读回则是 `list`。比较类型时即误判，即使每个值相同。
- [只读工具](read-story-2-3-formal.py) 仅在采集边界把外层结果转为 `list`，保留原值、顺序、所有者和权限的全部断言。用原始记录离线复现了旧误判、验证修复后相等，并对迁移记录和关系名分别注入差异，仍被拒。该验证不加载项目、不连接数据库，不是隔离回归重跑。已审授权 SQL 和 PowerShell 入口未改。应用源码仍匹配独立复验 77/77。原批次 17 个文件逐字节归档，没有覆盖失败证据。
- 已尝试用现有 `Recover`，沙箱的 PowerShell 执行策略在脚本加载时即拒绝，没有启动数据库客户端、没有产生新读回。普通 PowerShell 可按下文接续已有证据，不再申请已获批准的四列权限。

## 终端 A · 仅只读恢复，然后启动新服务

在正常 PowerShell 中完整复制。沿用原 passfile。当 `Recover` 打印 `STORY23_FORMAL_ACL_EXACT_READBACK`，才继续 `Serve`。这会在本批补建后置回执和就绪标记，不覆盖原失败日志。若相反报告缺列或出现漂移，停在读回并保留原始日志，不凭报错重放。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4'
$result = @(& $tool -Phase Recover -RunDirectory $run)
$result
if ($result -cnotcontains 'STORY23_FORMAL_ACL_EXACT_READBACK') { throw 'ACL 未精确读回，停止。' }
& $tool -Phase Serve -RunDirectory $run
```

只输入获准学生、教师、管理员的预置**用户名**，不是密码。脚本复核原源码、8003 和完整账号候选。任一师生账号在安全窗口内有可能失效的待审预约时不启动，不靠 GET 试探，也不更改预约。验证期间三人共同确认不从其他入口改动这些演示样本；只用预检列出的账号。测试地址 `http://127.0.0.1:8003`，尚未实际监听。

## 终端 B · 三个隔离 Chrome 窗口及后置核对

等待终端 A 的 8003 新进程启动，再在另一个普通 PowerShell 复制以下命令。脚本核验 8003 实际 PID、绑定、启动时间和命令行，验证安全截止，并为三个角色各启一个独立 Chrome profile。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4'
& $tool -Phase Chrome -RunDirectory $run
```

全程同一 `127.0.0.1:8003` origin，每个账号从该窗口重新 GET 登录表单再提交，不沿用 Cookie、CSRF 或 8000/8001 的窗口。建议启用 Network / Preserve log，逐请求写入本批 `chrome-receipt.md`。学生和教师各从身份页点击「我的预约」、现有本人详情、返回；分别记两种状态、设备和预约 ID、北京时间、URI/HTTP。再做管理员无入口且直访拒绝、异主与缺失同形拒绝的对照。缺少正式历史原因时引用隔离证据。不新提交预约，正式 201 分支如实注明此轮未执行。出现 403、503 或安全截止到达时，停止该操作，保留原日志，不盲重放。关闭本次三个独立 Chrome 窗口，用 Ctrl+C 只停终端 A 的 8003。然后终端 B 执行：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4'
& $tool -Phase Finish -RunDirectory $run
```

`STORY23_FORMAL_POSTCHECK_OK` 与填妥的浏览器回执需一起审阅，才决定 W1 与最终验收建议。未实跑 Recover、Serve、Chrome 或 Finish，不补造结果。保留 D-047、延期及原评审回执，课程六页沿用既有课程基线，保持 Sprint 8/5、实验 A 及三人共同操作。不重测 113/15/NFR-001，不改业务源码、不运行迁移、不开发 2.5、不标 done、不 commit/push。
