# Story 2.3 正式烟测的账号与 FR-018 前置核查

> 后续：负责人已批准有限真实写入，范围与执行命令见[当前执行单](story-2-3-authorized-demo.md)。原只读失败和限制保留为历史。

**本次失败不是账号或 SQL 错误。** 2026-11-27 15:08:18（北京时间），正式 PostgreSQL 17.12 的运行角色只读采集 `sample-before-catalog` 实际返回 1，stdout 空，stderr 为 `Unsafe FR-018 candidates or too little time before the next Beijing hour`。三类输入已通过存在、启用和角色校验，分别为学生 ID 2、教师 ID 3、管理员 ID 1。新的权限矩阵继续是 EXACT，未到期窗口足足 20 分钟。因此这次确切拦截原因是学生 #1：2026-11-27 10:00–11:00 已结束，但仍为待审核；点击该学生的「我的预约」将产生 FR-018 写入。教师无已有预约，亦无法在不变更数据的条件下证明教师详情。#2 未来预约不消除完整学生列表的 #1 风险。没有 `launch` 或浏览器回执，8003 未启动。 [阶段](smoke-20261127-145741-081-70fac945-formal-hold-original/stages.txt) · [原 stderr](smoke-20261127-145741-081-70fac945-formal-hold-original/sample-before-catalog.stderr.txt) · [原始前置快照](smoke-20261127-145741-081-70fac945-formal-hold-original/sample-before.json) · [散列](smoke-20261127-145741-081-70fac945-formal-hold-original/archive.sha256)

## 安全读取现有清单

预置命令的真实解析器要求受保护的 UTF-8 JSON **顶层数组**，每行仅有字符串 `username`、`role`、`password`，角色为 `student|teacher|admin`，用户名用项目登录表单规则规范化。默认文件为 `%LOCALAPPDATA%\LabBooking\Protected\accounts.json`。沙箱读取该受保护文件被拒，未看到其实际内容；下列普通 PowerShell 命令只输出角色、用户名。不要复制原始 JSON 或打开 PowerShell 转录后输出其内容。 [项目初始化口径](../../README.md) · [预置解析器](../../accounts/management/commands/seed_accounts.py)

```powershell
$manifest = Join-Path $env:LOCALAPPDATA 'LabBooking\Protected\accounts.json'
try {
    $raw = Get-Content -Raw -LiteralPath $manifest -Encoding UTF8 -ErrorAction Stop
    if (-not $raw.TrimStart().StartsWith('[')) { throw 'not an array' }
    $rows = ConvertFrom-Json -InputObject $raw -ErrorAction Stop
    $rows | Select-Object role, username
} catch {
    throw '无法读取受保护清单或清单格式不符。未输出任何原文或密码。'
} finally {
    Remove-Variable raw,rows -ErrorAction SilentlyContinue
}
```

## 最小工具修复及可复制命令

[正式 PowerShell 入口](run-story-2-3-formal.ps1) 的 `-AccountsManifest` 把路径交给 [只读采证助手](read-story-2-3-formal.py)，复用项目预置解析器，仅提取每角色唯一的规范化用户名，不运行预置命令，不传出或记录密码。三类账号仍经正式库只读核对；如清单某角色不唯一，不擅自选人，现有手填准确登录名入口仍可用。新增 `Inspect` 仅在新的目录落只读快照，区分有写风险、时间不足和缺少详情，并检查 8003 和本机 Chrome 是否可用；它不启动服务。 `Serve` 若运行会在另一个新目录**再次**核对当时 ACL、账号、完整候选与时间，绝不拿 Inspect 的快照冒充正式前置。新的日志按实际失败阶段引用 stderr，不再把普通样本失败指向授权恢复。

**当前三账号下，预计仍是 HOLD，不要直接重跑 Serve 或打开 Chrome。** 只读复核可以确认清单映射和数据是否已变化。只有发现已获准、真实安全且有两类现有详情的样本才继续。若清单仍是原样本，改用户名不会消除这两项数据阻塞，也不允许为演示执行额外写入。

普通 PowerShell 的**终端 A**：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$parent = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4'
$manifest = Join-Path $env:LOCALAPPDATA 'LabBooking\Protected\accounts.json'
$plan = @(& $tool -Phase Inspect -RunDirectory $parent -SmokeName 'smoke-20261127-151326-836-5861b5b2' -AccountsManifest $manifest)
$plan
if ($plan -ccontains 'STORY23_FORMAL_SMOKE_FULL_READY') {
    & $tool -Phase Serve -RunDirectory $parent -SmokeName 'smoke-20261127-151326-847-cc5d3f01' -AccountsManifest $manifest
} else {
    Write-Host 'HOLD: 未找到安全完整样本，不开 8003，不运行 Chrome 或 Finish。'
}
```

**仅当**终端 A 通过 Serve 的即时校验并启动了新的 8003，才在**终端 B**运行：

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$tool = '.\_bmad-output\implementation-artifacts\run-story-2-3-formal.ps1'
$smoke = 'F:\softwork\outputs\story-2-3-formal-20261127-120858-648-0dcaa5b4\smoke-20261127-151326-847-cc5d3f01'
& $tool -Phase Chrome -RunDirectory $smoke
```

Chrome 验实际 PID、命令标识及安全截止，为角色分别新建窗口配置，从同一 `http://127.0.0.1:8003` 获取该窗口的登录表单，不串用 Cookie、CSRF 或旧端口。只看已有安全预约，在本次 `$smoke\chrome-receipt.md` 记角色、预约/设备 ID、北京时间、URL、响应及实际页面；不新提交业务请求。完成后在终端 A 按 Ctrl+C 只停本次服务，再在同一个终端 B 运行：

```powershell
& $tool -Phase Finish -RunDirectory $smoke
```

Finish 仍用 Serve 的封存前置快照验证当前 ACL、相同应用输入及业务范围不变，和真实 Chrome 回执一起审阅。未启动服务则没有 Finish，不虚构状态。两种运行状态均不需重跑 Acl、Recover 或 GRANT。

## 核验与未完成事项

- 离线复算原始快照能分别识别学生 #1 的写风险、教师缺详情以及安全时间充足；对照测试区分可就绪和时间不足。读取清单路径、Inspect 的 HOLD/READY、不启动应用及不走手填分支通过 PowerShell 模拟。PowerShell 与 Python 语法通过，77 个业务运行输入匹配原独立复验清单。模拟没有访问正式库、浏览器或运行业务探针。
- 原失败的 12 份文件原样归档，不复制清单或密码。正式权限已精确核验，不能用隔离验证替代仍待处理的正式浏览器体验。保留 D-047、原延期台账、原 Sprint 8/5、实验 A。按课程指定第 25、26、27、33、34、36 页记录真实证据。Story 2.3 保持 review，不修改业务代码、不操作授权、不重跑 113/15/NFR-001，不开发 2.5，不标 done，不 commit/push。
