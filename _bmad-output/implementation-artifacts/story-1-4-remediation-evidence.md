# Story 1.4 R1／R2／R7 Build 整改证据

2026-11-25，按 D-033 续接 BMAD 6.12.4 Build 的 Patch 路线。R1、R2、R7 整改后开发自测已核验，Story 1.4 回到 `review`，由独立 Code Review 会话复审及独立复验。三位组员共同操作及审阅，不分派个人任务。 [正式 AC](../planning-artifacts/epics.md#story-14-管理员维护设备基础信息并保护设备身份) · [D-033](../../decision-log.md#d-033-2026-11-25-负责人批准-story-14-独立评审处置) · [独立评审](story-1-4-independent-review.md) · [整改交接](story-1-4-remediation-handoff.md)

## 团队实测与汇总误判复核

负责人回交 23:06:32～23:06:57（+08:00）普通 PowerShell 执行的原始记录。该轮只在 `lab_booking_test@127.0.0.1:5433/test_lab_booking` 执行，原 `.venv` 为 Python 3.13.17，PostgreSQL 17.12，探针为 Read Committed。个人操作者字段仍是占位文字，保留原样，不代填。Codex 仅做只读代码及日志复核，没有重复应用增量、执行 Django 测试、访问数据库或修改被测代码。 [原始日志](story-1-4-remediation-run-20261125-230632-931/raw.txt) · [原汇总与真实报错](story-1-4-remediation-run-20261125-230632-931/run-summary.txt) · [运行前散列](story-1-4-remediation-run-20261125-230632-931/before.sha256) · [运行后散列](story-1-4-remediation-run-20261125-230632-931/after.sha256)

原脚本第 155 行是汇总失败出口，并非子命令失败。只读重放原判定得到同一错误 `Expected exact R2 whitespace evidence.`。原正则 `^R2 whitespace preserved(?:\s|$)` 在 `preserved` 后只接受空白或行尾，但实测输出的下一字符是冒号，导致匹配数为 0。原汇总的 `verification exit=1`、`INCOMPLETE OR FAILED` 与错误文字均原样保留。只将 [验证包装](verify-story-1-4-remediation.ps1) 改为精确匹配唯一完整 R2 成功行，不改业务代码、验收口径、其它断言或退出分支。

在同一日志上离线重算修正后全部断言，实际通过。五个原生命令退出码均 **0**；两条裸 `System.Management.Automation.RemoteException` 是日志合流记录，不匹配测试失败、错误或跳过判定。Django 总结为 `OK`，原 **67/67**、新增 R2 **1/1**，共 **68/68**、零跳过，含 Chrome R1。系统检查无问题，迁移一致性无变更，常规测试前后均为 10 张表、17 条迁移、0 个账号、0 条会话。用同一判定器在内存中移除或重复 R2 标记、改为非零退出、移除 R1 成功行或清理标记，五种反例均按预期被拒绝。未修改原文件或运行任何数据库测试来制造这些反例。

| 核验项 | 真实开发自测与复核结果 |
| --- | --- |
| R1／AC-4、AC-6 | 停用和撤权 **2/2**，均证实真实锁等待、锁后读账号一次、返回 403、设备 UPDATE 0 次、无泄露且设备全行不变。停用 B 35732 等 A 19592，撤权 B 8260 等 A 38048。 |
| R2／AC-1 | 唯一新增用例通过。新说明精确持久化，详情保留多行、空白及自动转义；以 CRLF 回交未改说明时，修改名称不改变原说明。 |
| R7／AC-4、T-03 | 判定器逐项读回 **6/6** 结构化记录，角色／方法、响应、脱敏请求、无泄露、前后行数与指纹一致。匿名两项 302，学生和教师四项 403。管理员合法 GET／POST 与缺失／错配 CSRF 各两项单列。 |
| 既有 AC／隔离清理 | 原 67 项覆盖编号、状态、权限、不存在、不可删除等 AC。T-01 **4/4** 含两次真实设备锁等待，旧表单保留最新维修或停用状态；AC-8 **4/4** 区分确认回滚、明确拒绝、提交前断连和提交后丢确认。合计 **10/10** 真实探针，隔离清理断言通过。 |

增量补丁只读反向检查为 0，四路径已应用，不重放。原汇总记录的补丁、原始日志与两份清单散列均匹配实际文件；运行前后清单的 **47 个文件**逐项匹配当前工作区。原始日志 SHA-256 为 `61B4B4306C3B1072812B8E56E68BB5761A45949329C3D12FCCE089FE122D188F`，前后清单均为 `81FE2E7497A5816135F18121B0D121EF262BD72BE2DB9151CD1B194B3DB5A15E`，原失败汇总为 `D6F25D2133E8E34A2A083C154B1DB30E8B91A3AA31507D478EFA440BDE111104`。

## 整改与取证范围

| 批准项 | 整改目标与验证 |
| --- | --- |
| R1（AC-4／AC-6，PC-008） | 先授权、锁设备、按操作者主键重读账号当前启用状态和角色，仍获准才独立重读设备、原位写四列。失权返回 403，不写设备。读取沿用现有账号 SELECT，不引入账号业务写操作或额外授权。复用隔离观察、夹具和 HTTP 入口，分别构造真实行锁等待期间停用与撤权，两例另计。原成功管理员、四例 T-01 和四类 AC-8 保留。 |
| R2（AC-1） | 仅说明设置 `strip=False`，保留多行及首尾／连续空格、原输入边界和 Django 自动转义。锁后比较时，若表单仅有浏览器换行编码差异，保留原始说明。针对用例核对新提交文本和独立读回、详情原样转义，以及只改其它字段时以 CRLF 回交也不改原说明。 |
| R7（AC-4，PC-011／T-03） | 每例保存匿名／学生／教师两种方法的实际路由、合成目标、脱敏请求、预期和实测响应、拒绝与无泄露，以及按主键排序的设备全行前后指纹及行数。不记录密码、密钥、会话标识或 CSRF 值。六项拒绝原分母不变；管理员 GET／POST 合法对照、两个 CSRF 拒绝及锁后撤权独立列示。 |

## 先前环境受阻留档

- BMAD 官方渲染使用已验证的 `D:/ttAPP/python.exe`（只作渲染）和独立临时目录，退出 0。工件仍使用原正式快照 `13340bf8aef33bedeff3`，未改工作流文件。
- 原项目 `.venv` 的 `--version` 在本沙箱仍退出 103。此命令的具体额外授权请求被 `sandbox_approval: false` 自动拒绝，未实际提权执行。原解释器没有替换、重装或重建。对实际 `equipment/services.py` 的写句柄及延期台账写句柄均被拒绝。
- 增量补丁仅四个 `equipment/` 路径，SHA-256 `1ABA031F506CD5901A2A245E6516B4C3AA62F277CC099AFC3610DC7281464488`。`git apply --check --whitespace=error-all` 退出 0；仅在临时副本应用并逐个校验目标文件散列，实际工作树的四个原文件未改。原完整补丁的只读反向检查仍为 0，未重放。验证包装及文档命令通过 PowerShell 语法检查。
- 静态检查发现探针起草版的 SQL 前缀会漏掉 Django 5.2 为投影添加的列别名。已按本机安装源码修正为检测来源、两列投影及原主键参数，并保留设备锁 SQL 先于账号 SELECT 的断言。此为静态修正，不是数据库探针失败或复测通过记录。
- 整改阶段本会话实际执行 **0 项 Django 测试、0 项 PostgreSQL 探针**，没有数据库连接。上一轮团队普通 PowerShell 的 **67/67、8/8** 仅为整改前有效基线，不转记成本轮结果。 [整改前原始日志](story-1-4-verification-20261125-221855-930.txt)

## 原普通 PowerShell 交接（历史留档）

以下是本轮已实际执行的交接步骤，增量已应用，**不要重复应用或重跑本轮通过的测试**。独立复验仅在后续独立会话按其流程执行。 [R1／R2／R7 增量补丁](story-1-4-r1-r2-r7.patch)

```powershell
$increment = '.\_bmad-output\implementation-artifacts\story-1-4-r1-r2-r7.patch'
git -c core.autocrlf=false apply --check --whitespace=error-all -- $increment
if ($LASTEXITCODE -ne 0) { throw '增量补丁预检查失败，停止。' }
git -c core.autocrlf=false apply --whitespace=error-all -- $increment
if ($LASTEXITCODE -ne 0) { throw '增量补丁应用失败，停止。' }
& .\_bmad-output\implementation-artifacts\verify-story-1-4-remediation.ps1 -ExecutedBy '填写实际操作者'
```

验证包装复用原有安全脚本，以实际增量文件散列和前后待测文件清单绑定测试版本，只连接 `lab_booking_test@127.0.0.1:5433/test_lab_booking`。原 Python 3.13.17、Chrome R1、`check`、迁移差异 dry-run、全量 Django 与 PostgreSQL 探针分别留存。当前计划为 **68 项 Django（67 项原回归＋1 项 R2）和 10 项 PostgreSQL 探针（8 项原探针＋2 项 R1）**，R7 增补原 6 个用例的逐例证据，不增加其分母。请保留输出目录的 `raw.txt`、`run-summary.txt`、`before.sha256` 和 `after.sha256`。若失败先提供原始错误与退出码，不凭预期填入结果。仅实际自测全部通过后回到 `review`，交独立 Code Review 会话针对性复审和独立复验。

延期 R3～R6、W1、W2 的处置不变。原台账当前仍不可写，其 [已决六项附录](story-1-4-deferred-work-appendix.md) 保留为未合并记录。具备原台账写权限时可单独将该节追加一次，不能覆盖历史。如已存在同标题，不重复追加。

```powershell
$artifactDir = '.\_bmad-output\implementation-artifacts'
$ledger = (Resolve-Path (Join-Path $artifactDir 'deferred-work.md')).Path
$appendix = Get-Content -LiteralPath (Join-Path $artifactDir 'story-1-4-deferred-work-appendix.md') -Raw -Encoding UTF8
$heading = ($appendix -split '\r?\n', 2)[0]
if ($heading -notlike '## Deferred from: code review of spec-1-4-*') { throw '延期附录标题不符。' }
if (-not (Select-String -LiteralPath $ledger -Pattern $heading -SimpleMatch -Quiet -Encoding UTF8)) {
    [IO.File]::AppendAllText($ledger, [Environment]::NewLine * 2 + $appendix, [Text.UTF8Encoding]::new($false))
}
```

## 课程和授权边界

第 26 页按 FR-016／002、ADR-002／003／006／008、PC-003／008／011／014、AC、整改测试保留追溯。第 27 页如实记录团队实测及汇总纠正后 `in-progress → review`。第 33 页保存增量差异、真实失败汇总、实际通过日志与清单。第 34 页实验 A 不变。第 36 页在 D-033 追加事后验证，不新增人工决定。页码按课程基线与团队留档核对。未访问正式库、未执行 GRANT 或正式迁移，未改正式需求及架构，Story 2.1 不启动，未标 done 或暂存、提交、推送。

独立会话复审输入为本页、D-033、正式 AC、完整当前差异（含未跟踪源码和测试）及原始运行目录。若在团队本机进行独立复验，使用修正后的整改验证包装，不使用旧的 67／8 固定分母；开发自测 68／10 不记作独立结果。不关闭延期项、正式库权限或最终验收。
