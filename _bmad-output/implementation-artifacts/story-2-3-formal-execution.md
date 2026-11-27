# Story 2.3 正式运行执行单

> 最新执行：已确认当前样本存在 FR-018 写入风险。先按[样本阻塞与只读检查](story-2-3-formal-sample-hold.md)执行，不直接重放以下历史命令。

> 后续更新：此批次的 ACL 已精确读回。Serve、Chrome 和 Finish 已改为独立目录，当前执行请使用[最新续跑命令](story-2-3-serve-recovery.md)。以下原命令仅保留历史依据，不要重跑授权。

**现状：待本机普通 PowerShell 执行。** 负责人已批准仅在 `127.0.0.1:5433/lab_booking` 条件性补四列读权和预约业务只读烟测。沙箱读权限被拒，原 `.venv` 版本探针实际退出 `103`。未连接正式库、未执行 GRANT、未启动 8003 或 Chrome。最新探测中 8003 无监听，8000/8001 原进程仍在。W1 不能关闭，Story 保持 `review`。

[已审核正式交接](story-2-3-formal-runtime-handoff.md) · [最小授权 SQL](story-2-3-history-select-reviewed.sql) · [普通 PowerShell 入口](run-story-2-3-formal.ps1) · [只读采证助手](read-story-2-3-formal.py) · [Chrome 原始空表](story-2-3-chrome-receipt-template.md)

## 1. 开窗前置及条件授权

在普通 Windows PowerShell 完整复制执行。读到 `STORY23_FORMAL_ACL_READY` 才进入下一步。保存该命令输出的 `Evidence:` 目录。不在各阶段打印受保护的 PostgreSQL 密码、Django 密钥或预置账号密码。若已配置非默认的绝对 `PGPASSFILE`，入口会复用它。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$story23 = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
& $story23 -Phase Acl
```

入口核查 77 个运行相关输入仍匹配独立复验，固定目标、17.12、授权角色、两表所有者、既有两项预约／审计迁移及有效／显式 ACL。仅历史表四列读权同时被两组只读核对确认为缺失时，执行已审核 SQL；已齐全不执行 GRANT；任何部分授予、其余权限漂移、整表 SELECT 或转授权即停。前后确认 76 项矩阵中原 26 个正项不变，只允许四个新增正项。没有迁移或业务数据写入。脚本在实测前不宣称授权成功。

如授权或回读中断，**仅做只读恢复**，不重放写操作。进入普通 PowerShell 后复制：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$story23 = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = Read-Host '粘贴这一批 Evidence: 后的完整目录'
& $story23 -Phase Recover -RunDirectory $run
```

`STORY23_FORMAL_ACL_EXACT_READBACK` 证明实际状态已齐，不推断未知写命令是否收到提交响应；`STORY23_FORMAL_ACL_STILL_NEEDS_FOUR` 表示仍缺四列，保留回执交回核查。不要切换数据库、角色或用旧部署脚本修复。

## 2. 新服务和三角色 Chrome

只在团队确认同一验证窗口内不会通过旧服务或其他渠道改动这些样本时，从终端 A 复制执行。只输入获准预置学生、教师、管理员的**用户名**供数据库检查，不输入密码。脚本核对对方角色与账号状态、角色完整本人预约候选范围、查询前快照及 HTTP 使用的实际安全截止时间；若任何学生或教师的待审可能在截止前失效，直接停，不启动服务。不用该样本访问本人列表或详情，也不新增业务记录。若临近整点不足 3 分钟，只保留记录，重新安排安全窗口。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$story23 = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = Read-Host '粘贴已就绪的 Evidence 目录'
& $story23 -Phase Serve -RunDirectory $run
```

终端 B，在同一个安全窗口内复制执行。检查实际监听地址、PID 和启动命令；为三个角色分别打开全新 Chrome profile。不复用 8000/8001、旧窗口、Cookie 或登录表单。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$story23 = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = Read-Host '粘贴与终端 A 相同的 Evidence 目录'
& $story23 -Phase Chrome -RunDirectory $run
```

以脚本打印的北京时间为截止。可在终端 B 查看 `Get-Content -Raw -LiteralPath (Join-Path $run 'sample-before.json')` 确认账号 ID、设备、现有预约及不存在对照。所有浏览业务 URL 固定为 `http://127.0.0.1:8003`。用每个隔离窗口取该站当前表单，三位组员共同操作与审阅。

- 浏览器 Network 选择文档请求、启用 Preserve log，仅记 URL、方法、状态及页面文字，不保存敏感 HAR。每个窗口仅使用和对应预检角色一致的获准账号。学生、教师各点击身份页 → 我的预约 → 一条本人现有详情 → 返回，记录两种状态、日期、时段、实际设备和预约 ID。若某角色没有安全既有详情，如实记缺样本，不展示数据库中未授权资料。管理员核对无入口、直访列表与师生详情被拒。
- 师生用已验证的对方预约 URL 与 `sample-before.json` 提供的不存在 ID 核对两个 404，不从页面错误中推断实际不存在或归属信息。若没有预先批准的同角色第二账号，只做现有跨角色对照，同角色证据沿用隔离复验。
- 只复用已有预约。不能用当前批准范围提交新预约；本轮正式 201 分支记未执行且引用隔离证据。若双状态有相同词义仍分栏记录。没有相应真实原因样本时 AC-3 功能证据用隔离复验，不造拒绝历史。登录的技术性会话与预约业务分开。
- 实际结果填写批次内 `chrome-receipt.md`，不要事后补造。出现 403 CSRF、503、旧页或意外响应，保留原日志；不盲目重试，不在安全截止后继续访问。

## 3. 仅停止本次服务并只读后查

结束 Chrome 操作后，用 **Ctrl+C 仅停止终端 A 中本次 8003 前台服务**。终端 B 复制执行：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$story23 = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$run = Read-Host '粘贴本次 Evidence 目录'
& $story23 -Phase Finish -RunDirectory $run
```

`STORY23_FORMAL_POSTCHECK_OK` 只证明：ACL exact、运行输入未漂移、所核验范围的预约/设备/有效占用/对应历史前后不变。不等于 Chrome 体验已验收。请回传确切批次目录及填好的脱敏 Chrome 回执，失败也保留原始输出。正式结论、W1 处置及仓库内归档须基于实际输出，不靠此执行单推断。不得带入密码、Cookie、CSRF、完整私密 HAR 或 Chrome profile。暂不标 done，不开发 2.5，不提交或推送。

本次静态准备已核对授权稿和 D-042 只读助手指纹、运行输入 77/77、PowerShell 语法和监听输出解析。新入口尚无正式库实跑回执。PPT 指定页按既有课程基线与团队记录执行；保持 Sprint 8/5、实验 A 与 D-047 的非阻塞待办，不分派个人任务。
