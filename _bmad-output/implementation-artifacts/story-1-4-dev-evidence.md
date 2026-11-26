# Story 1.4 开发证据与本机交接

> 此页保留整改前开发自测。D-033 独立评审处置后的当前状态及实际验证见 [R1／R2／R7 整改证据](story-1-4-remediation-evidence.md)。

2026-11-25 · **review**。三位组员共同操作与审阅，团队在普通 PowerShell 应用补丁并实际执行隔离自测。Codex 只核对当前差异、原始日志及断言，没有在沙箱执行测试或重复应用补丁。下文保留先前沙箱受阻的历史记录。 [实施规格](spec-1-4-edit-equipment-basics.md) · [Checkpoint 1](story-1-4-checkpoint-1.md) · [课程要求](../../docs/course-requirements.md)

## 实际补丁与运行结果

[Git 补丁](story-1-4-edit-equipment-basics.patch) 基于 `e200fee335536941e0705c112aefbf6751b244c3`。只读 `git apply --reverse --check` 退出 0，当前 9 个 `equipment/` 文件逐个以 `git hash-object --no-filters` 与补丁目标 Git 对象核对，全部相符。未重新应用或反向应用补丁，未修代码或重跑已有效的测试。没有模型或迁移、测试 runner、预约／历史、删除路径或状态转换改动。补丁 SHA-256 为 `7555350E0921677272A65A84517833638EA7DC4FDFD855251DBEFA7BF120AA5C`。

团队日志记录 2026-11-25 22:18:55 +08:00 开始，使用原 `.venv` 的 Python **3.13.17**，校验通过的实际目标为 `lab_booking_test@127.0.0.1:5433/test_lab_booking`、PostgreSQL 17.12，事务探针确认 Read Committed。版本、系统检查、迁移差异检查、Django 全量及真实探针五条命令均退出 0。系统检查无问题，迁移差异为 `No changes detected`。Django **67/67**，18.671 秒、零跳过，包含 Chrome R1。按测试方法全名与 Story 1.3 的有效独立基线比较，原 **55/55** 无增减，新增 **12/12**。Django 前后均为 10 张表、17 条迁移、0 个账号、0 条会话。日志中的两行 `System.Management.Automation.RemoteException` 是 PowerShell 合流输出中夹在 unittest 分隔线与总结旁的记录，未见失败／错误／跳过条目，实际总结为 `OK`，进程退出 0。原始日志不改写。 [本轮原始日志](story-1-4-verification-20261125-221855-930.txt) · [55 项历史基线](story-1-3-independent-recheck-output.txt)

原始日志 SHA-256 为 `26770FF8C36734614B7AFAC73990F05D7A33104E895329C4E2ACBD795A5D89A9`。

## 正式 AC 逐项开发自测

| 正式 AC | 团队实际验证结果 |
| --- | --- |
| AC-1 | 通过。管理员 GET 200、有效 CSRF POST 302 到原详情。详情与重读的四字段均匹配提交，主键、编号、状态、总数及无关设备保持不变。 |
| AC-2 | 通过。编号只展示；伪造编号返回 400「设备编号不可修改」，整笔不写。直接写入重复编号由 PostgreSQL 的 `equipment_number_unique` 约束拒绝。 |
| AC-3 | 通过。可用、维修、停用各以两种不同状态伪造，共六种组合均拒绝。设备前后全字段相同，设备 SQL 无写入或加锁，无预约／历史调用。 |
| AC-4／T-03 | 通过。匿名 GET、有效 CSRF POST 均 302 到登录，学生、教师各两种请求均 403。六项均无设备读取、受限内容泄露或业务变化（6/6）。管理员缺失和错配 CSRF 均 403 且不写（2/2）；合法 GET 200 与 POST 302（2/2）另计。教师的 Django staff/superuser 不授予编辑权。 |
| AC-5 | 通过。不存在的目标 GET、有效 CSRF 的合法 POST 与非法字段 POST 均明确 404，不新增或修改设备。 |
| AC-6／T-01 | 通过。短事务按主键 `FOR UPDATE`、独立 SELECT 重读，再按主键更新四列。四组交错均保留另一个事务提交的维修或停用状态，旧表单只更新四字段。两组真实等待由 `pg_blocking_pids` 证实。 |
| AC-7 | 通过。编辑及详情的 DELETE 返回 405，删除路由及 Django Admin 不可达。正常编辑原位更新，主键与编号不变，无删除重建。 |
| AC-8 | 通过。四种异常的响应、提交尝试数、SQLSTATE 和独立末态均匹配，未知不自动重试，无成功、回滚承诺或重号误报。 |

额外的表单边界、服务角色／白名单、拒绝普通外层事务也通过。相关断言可在 [12 项 Django 测试](../../equipment/test_edit.py) 与 [隔离事务探针](../../equipment/management/commands/verify_equipment_edit_transactions.py) 核对。

## 独立事务实测细节

T-01 四组均以旧表单显示可用为初态，覆盖维修及停用分别在编辑提交前已生效，以及编辑先阻塞再放行。两组实际阻塞为维修 B=40892 等 A=7432、停用 B=17292 等 A=38936。观察连接 PID 35188 与各事务独立。四组均保持原记录身份和数量，独立读回四个字段的新值及夹具提交的最新状态。

| AC-8 实测探针 | 应用响应 | UPDATE／COMMIT 路径次数 | 诊断与独立回读 |
| --- | --- | --- | --- |
| UPDATE 后回滚 | 503 设备编辑失败 | 1／0 | `23514`，仍为原四字段 |
| 明确拒绝 COMMIT | 503 设备编辑失败 | 1／1 | `23505`，仍为原四字段，未冒报设备编号冲突 |
| COMMIT 前断连 | 503 提交结果待核查 | 1／1 | 无 SQLSTATE，仍为原四字段 |
| 真实 COMMIT 后丢确认 | 503 提交结果待核查 | 1／1 | 无 SQLSTATE，四字段已提交 |

探针合计 **8/8**（T-01 四项、AC-8 四项，独立于 Django 67 项）。清理断言通过，设备全字段及总数、表、迁移、账号、会话均恢复运行前状态。

## 先前沙箱受阻记录

| 命令或检查 | 实际结果 |
| --- | --- |
| `git rev-parse HEAD` | 基线与实施规格相同。 |
| `git -c core.autocrlf=false apply --check <patch>` | 退出 0。应用到同一工作区的临时独立副本后，比较所有设备文件 SHA-256，和候选逐文件相同。没有在原 `equipment/` 应用。 |
| `git apply --numstat <patch>`、`git diff --check` | 补丁 9 文件；使用仓库默认 Git 换行配置检查差异未报告空白错误。 |
| `System.Management.Automation.Language.Parser.ParseFile` | PowerShell 脚本无语法错误。 |
| `apply_patch` 写 `equipment/services.py`、`Set-Content` 探测 `equipment/` 及模板／命令子目录 | 写入被拒绝。README 和实施证据目录可写，未更改任何权限。 |
| 单次申请仅应用 Story 1.4 补丁的 `git apply` 执行授权 | `sandbox_approval: false` 自动拒绝，未弹出确认或执行该命令。 |
| `.\.venv\Scripts\python.exe --version` | 原 venv 启动器退出 103，不能访问其基础解释器，不能据此判断 Python 未安装。 |
| `Test-Path` 检查默认受保护密码路径；直接调用验证脚本 | 文件元数据访问被拒；受限会话禁止执行外部 PowerShell 脚本。没有读取密码内容。 [实际输出](story-1-4-sandbox-verification.txt) |

该阶段沙箱实际运行 0 项，未连接数据库或创建夹具。与随后团队在普通 PowerShell 的实际运行结果分开留档。

## 原普通 PowerShell 交接命令（历史留档）

补丁已实际应用，以下应用命令只记录原交接步骤，**不要重复执行**。脚本会拒绝冲突连接环境变量、非原解释器版本或缺失 Chrome，命令与输出写入带时间戳的日志。不公开凭据内容，也无需重跑已取得有效证据的测试。

```powershell
$storyPatch = '.\_bmad-output\implementation-artifacts\story-1-4-edit-equipment-basics.patch'
git -c core.autocrlf=false apply --check $storyPatch
if ($LASTEXITCODE -ne 0) { throw '补丁预检查失败。' }
git -c core.autocrlf=false apply $storyPatch
if ($LASTEXITCODE -ne 0) { throw '补丁应用失败。' }
& .\_bmad-output\implementation-artifacts\verify-story-1-4.ps1
```

脚本可选 `-Passfile`、`-Chrome`、`-LogPath`。如果本机不运行外部 `.ps1`，可以逐段粘贴以下同等隔离命令，无需改变执行策略。先完成上面的补丁应用，并把已有密码文件和 Chrome 的路径按需改为实际绝对路径。

```powershell
$pgConflicts = @('PGHOST', 'PGHOSTADDR', 'PGPORT', 'PGDATABASE', 'PGUSER',
    'PGPASSWORD', 'PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS') |
    Where-Object { Test-Path "Env:$_" }
if ($pgConflicts) { throw "先移除冲突变量：$($pgConflicts -join ', ')" }
$venvPython = '.\.venv\Scripts\python.exe'
$env:LAB_BOOKING_DB_MODE = 'test'
$env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
if (-not $env:PGPASSFILE) {
    $env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf'
}
if (-not $env:LAB_BOOKING_R1_CHROME) {
    $env:LAB_BOOKING_R1_CHROME = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe'
}
foreach ($path in @($env:PGPASSFILE, $env:LAB_BOOKING_R1_CHROME)) {
    if (-not [IO.Path]::IsPathRooted($path) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw '指定已有密码文件和 Chrome 的绝对路径。'
    }
}
$storyStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$storyLog = ".\_bmad-output\implementation-artifacts\story-1-4-verification-$storyStamp.txt"
$storyVersion = & $venvPython --version
$storyExit = $LASTEXITCODE
'> .\.venv\Scripts\python.exe --version', $storyVersion, "Exit $storyExit" |
    Tee-Object -FilePath $storyLog
if ($storyExit -ne 0 -or $storyVersion -cne 'Python 3.13.17') { throw '原 .venv 解释器未通过检查。' }
$env:LAB_BOOKING_SECRET_KEY = & $venvPython -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
if ($LASTEXITCODE -ne 0 -or -not $env:LAB_BOOKING_SECRET_KEY) { throw '临时密钥生成失败。' }
function Invoke-StoryCheck([string[]]$StoryArgs) {
    ('> .\.venv\Scripts\python.exe ' + ($StoryArgs -join ' ')) | Tee-Object -FilePath $storyLog -Append
    & $venvPython @StoryArgs 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $storyLog -Append
    $storyExitCode = $LASTEXITCODE
    "Exit $storyExitCode" | Tee-Object -FilePath $storyLog -Append
    if ($storyExitCode -ne 0) { throw "验证失败，见 $storyLog" }
}
Invoke-StoryCheck -StoryArgs @('manage.py', 'check')
Invoke-StoryCheck -StoryArgs @('manage.py', 'makemigrations', '--check', '--dry-run')
Invoke-StoryCheck -StoryArgs @('manage.py', 'test', '--keepdb', '--parallel', '1', '-v', '2')
Invoke-StoryCheck -StoryArgs @('manage.py', 'verify_equipment_edit_transactions')
```

## Review 交接与课程核对

开发自测 AC-1～AC-8 均通过，按 BMAD 6.12.4 Build 结清实施检查项，规格转为 `in-review`，Sprint 仅 Story 1.4 转为 `review`。新会话使用 `bmad-code-review`，以 Git 基线、当前完整差异（含新增文件）、正式 AC、本规格及团队原始日志为输入。重点独立核查授权与 CSRF 的拒绝无副作用、锁后重读与四列写入、事务分类及探针夹具隔离。本次不是独立代码评审或最终验收。

第 26 页保留 FR-016／FR-002 → ADR-002／003／006／008 → AC → 测试与运行证据链；第 27 页保留真实状态节点；第 33 页保存源码、差异、测试、Sprint 状态与证据；第 34 页实验 A 条件及数据保持原样；第 36 页在 D-032 增补事后验证，不新增或推断人工决定。PPT 依据为仓库课程基线及团队留档。未访问正式业务库、未执行 GRANT 或业务库迁移，正式四列权限等待独立评审后另批。Story 2.1 仍是 backlog，未暂存、提交或推送，未标记 done。
