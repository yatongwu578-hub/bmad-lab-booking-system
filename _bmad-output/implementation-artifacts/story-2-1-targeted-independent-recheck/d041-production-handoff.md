# D-041 · Story 2.1 正式运行单次接力

负责人已批准并关闭 P01/P02/P03、R02/R06/R07/R10。Story 2.1 保持 review，2.2 保持 backlog。团队首次正式运行已提交两条迁移，在授权前的 ACL 只读探针停止，尚未完成正式运行。**当前只使用下文的[定向恢复](#2026-11-26-实际故障与定向恢复)，不重跑首次入口。** 原延期和隔离测试证据不变。 [正式评审处置](d040-disposition-build-handoff.md) · [原独立复验](d040-independent-final-review.md)

## 首次运行入口（历史，不重复执行）

在仓库根目录执行一次正式运行入口。使用原 .venv/Python 3.13.17 和已存在的受保护 passfile、既有角色账号清单。默认沿用 Epic 1 的存放位置。已授权路径不同的情况下，通过 `-Passfile`、`-AccountsJson`、`-BackupRoot` 提供**路径**，不传明文凭据。无需重装或跑隔离回归。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\_bmad-output\implementation-artifacts\story-2-1-targeted-independent-recheck\run-story-2-1-production.ps1
```

1. 复核锁定提交、75 份运行输入、脚本、工具版本；核对受保护文件及 Windows ACL、8001。只认可 D-037 已归档的旧服务身份、启动窗口、解释器、命令行、父子关系与现场监听均吻合，否则不关进程。已有连接不强制停旧服务。旧监听读取受限不等于可重启。
2. 直接核对迁移及运行角色连接目标均为 `127.0.0.1:5433/lab_booking`、PostgreSQL 17.12、Read Committed。检查账号设备原权限和默认 ACL。用 migrator 在受保护目录生成并核对 custom 备份大小、散列、Windows ACL 和 `pg_restore --list`。只是验证可读备份目录，不冒充已恢复演练。备份留在 `%LOCALAPPDATA%\LabBooking\Protected\story21-d041-<批次>` 或获准的等价保护目录，绝不放入仓库。 [PostgreSQL 17 备份](https://www.postgresql.org/docs/17/app-pgdump.html)
3. 仅允许空目标应有的两项前向迁移，按 Django 依赖顺序完成预约后审计。完全符合预期的现存迁移跳过，半完成、额外、对象或所有者异常停止。按 R-04 核对预约／历史真实外键、CHECK、identity、索引和触发器。
4. 保持既有账号、设备、会话 ACL 不变。只在新表权限空白且无默认外放时执行批准的三条列级 GRANT。纯 SQL、字段别名限定、无 PL/pgSQL；用 psql 单事务和 ON_ERROR_STOP，前后有效权限及显式 ACL 不合即失败回滚。若已完全达到精确模型不重授。无序列、DELETE、DDL、后续功能授权。提交后用独立运行角色再次校验。 [静态审查 SQL](d041-authorization-reviewed.sql) · [psql 单事务](https://www.postgresql.org/docs/17/app-psql.html)
5. 核实后受控重启已知旧进程或在空闲 8001 启动本项目新版，仅 loopback。存在未知进程不停止，不另占端口。新进程用 runtime、原解释器、经审核源码，没有改变项目部署范围。重启采用新运行密钥，使用真实 Chrome 重新登录现有账号。
6. 仅用 `EQ-DEMO-S12-20261125`。从数据库当前北京时间动态挑选次日合法无冲突整点。临近开始或已到期的既有待审会让操作停止，避免本次按需触发额外历史。学生从目录和详情真实进入，唯一一次可保留的 POST 返回 201，确认待审占用及本人 200。教师从实际入口重叠申请应为明确 409，异主 404。管理员无入口，直达 GET/POST 应为 403。独立只读回查目标设备、唯一新增行、有效状态及历史不变。不会在正式库注入故障、压测、清理或重复纠错。
7. 以退出 0、`STORY21_D041_PRODUCTION_RUNTIME_OK`、后置散列、真实 Chrome、数据库最终回读、三类角色结果共同判断。控制台打印实际登录、申请与本人结果 URL，回执目录为 `story-2-1-targeted-independent-recheck/runtime-run-*`。保留目录，备份和凭据不随回执提交。原 91 项、导航、Chrome、权限、交错和历史三组全部复用，不重复运行。

## 失败后只读查证

运行会在任何迁移、授权或演示提交前固化 intent。留存失败目录及原始日志。已出现任何 intent 时，入口拒绝重放，一次运行失败不等于生产写入未提交。用显示的失败目录执行只读恢复并核对阶段，**不会**迁移、GRANT、启停服务或提交请求。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\_bmad-output\implementation-artifacts\story-2-1-targeted-independent-recheck\run-story-2-1-production.ps1 -ReadOnlyRecovery '<控制台显示的原失败目录>'
```

该模式回读登记、已存在正式对象、有效 ACL。若有预约 intent，再按原申请人、设备及时段查询已持久行。只有查清实际状态后才能决定定向恢复步骤，不能按空日志猜测并重做。

## 2026-11-26 实际故障与定向恢复

- 正式目标实测为 PostgreSQL 17.12、`127.0.0.1:5433/lab_booking`、`public`、Read Committed，分别校验了迁移角色与运行角色。受保护快照大小 34,479 字节、SHA-256 `C69A7E88C0940BB63B45498CFD846558D1A0562E8FF3AC982BEC3BF3F4816ED0`，备份、保护和 TOC 三项均退出 0。保护 stderr 是 PowerShell 的 CLIXML 进度记录，保护成功标记存在。备份目录不入库。 [版本、退出码](runtime-run-20261126-213638-448-312206ec440e/stages.txt) · [备份退出码](runtime-run-20261126-213638-448-312206ec440e/native-exits.jsonl) · [备份证明](runtime-run-20261126-213638-448-312206ec440e/backup-proof.jsonl)
- 原计划只有 `reservations.0001_initial` 和 `audit.0001_initial`；Django 两条均 `OK`，随后独立连接确认记录和表存在、Django 已无剩余计划。迁移已持久化，后续 ACL SELECT 的异常不可能回滚这些已提交迁移。原 schema 从新表目录核对 19 列、两条 identity、5 个有效且初始延迟的 FK、2 个 PK、3 个已验证 CHECK、7 个有效索引，所有者为 migrator，未启用 RLS、无用户触发器，运行角色没有 identity 序列权限。 [原始迁移回执](runtime-run-20261126-213638-448-312206ec440e/migration-result.jsonl) · [原始对象清单](runtime-run-20261126-213638-448-312206ec440e/schema.jsonl)
- `production-database` 退出 1 的根因是 `authorization → acl → RAW_ACL` 将新列的空 ACL 通过 `COALESCE` 换成零维 `'{}'::aclitem[]`，`aclexplode` 拒绝并报 `22023: ACL arrays must be one-dimensional`。原日志只保存类名和 SQLSTATE；完整错误文本由同版本独立 PostgreSQL 重现，不冒充生产 stderr。不是 PL/pgSQL 变量歧义、别名错误、42501 权限不足或成功行匹配误判。原批次没有 ACL 完整回执、没有 `grant-intent.json` 和 GRANT 子进程记录，也没有重启、Chrome 或 `reservation-intent.json`。原批次未发出 GRANT 或预约 POST；实时 ACL 是否仍是 pristine 以只读回读为准。 [原数据库日志](runtime-run-20261126-213638-448-312206ec440e/production-database.log) · [原 SQLSTATE](runtime-run-20261126-213638-448-312206ec440e/failure-diagnostics.jsonl)
- 只改两个部署工具，部署助手 SHA-256 `4AACBDF0AD62531F8852E00EA9703FFC3D6038E8188903C463810078576EDA31`。空／NULL ACL 不再送给 `aclexplode`，非空显式 ACL 和默认 ACL 保持核对；修复前后仍为 76 项矩阵／26 个批准列权限，不取消表级、转授、所有者、序列和未知 ACL 拦截。修复后生成的脚本 SHA-256 `B34A5E6F061211B594473FF3A8B0B0EF67C7802F980C1061D040F8DCBB274160`；旧审核 SQL 与原日志保留。独立临时 PostgreSQL 17.12 单用户进程无连接正式库，复现旧 SQL 的 22023，并以真实目录查询确认空白是 76/26/0、精确授权是 76/26/26，额外 DELETE 被拦截。PowerShell 语法及演示时段的合成边界另外核对，不计入正式实测。 [修正后的 SQL 审阅副本，不直接执行](d041-authorization-recovery-reviewed.sql)

由三位组员在普通 Windows PowerShell 共同执行。不要并行使用 8001 做其它操作。凭据或备份不在原默认位置时，把第一次成功使用的 `-Passfile`、`-AccountsJson`、`-BackupRoot` 或 `-Chrome` 原路径参数按需传给相应命令；不传明文。第一段只读，不启停服务、不写正式库。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$dir = '.\_bmad-output\implementation-artifacts\story-2-1-targeted-independent-recheck'
$runner = Join-Path $dir 'run-story-2-1-production.ps1'
$failed = Join-Path $dir 'runtime-run-20261126-213638-448-312206ec440e'
$out = @(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -ReadOnlyRecovery $failed)
$code = $LASTEXITCODE
$out | Write-Host
$ok = @($out | Where-Object { $_ -cmatch '^STORY21_D041_READ_ONLY_RECOVERY_OK .+$' })
if ($code -ne 0 -or $ok.Count -ne 1) { throw 'Read-only recovery did not pass. Preserve the new logs and stop.' }
$recovery = $ok[0] -replace '^STORY21_D041_READ_ONLY_RECOVERY_OK ', ''
$state = Get-Content -LiteralPath (Join-Path $recovery 'recovery-summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$state | ConvertTo-Json -Depth 6
```

同一窗口仅当 `both_migrated=true`、ACL 为 `pristine` 或 `ready` 且存在安全时段时继续。若是 `unapproved`（含部分或过宽授权）、迁移记录异常或无合法时段，停止，不手工补权限或迁移。

```powershell
if (-not $state.both_migrated -or $state.acl -cnotin @('pristine','ready') -or $state.demo_blocker -or @($state.slot_beijing).Count -ne 2) {
    throw 'Recovery did not certify the required state. Do not continue.'
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $runner -ResumeAfterRecovery $recovery
if ($LASTEXITCODE -ne 0) { throw 'Continuation stopped. Preserve the new evidence and run read-only recovery on that new run; never replay a write.' }
```

续跑不调用迁移、不生成第二份备份，只核对原受保护备份散列与 TOC。实时 ACL 与前一只读回执一致时，`pristine` 只在没有任何旧 GRANT intent 时执行 D-041 的三条原授权，`ready` 跳过授权，其他一律停。8001 首次记录为 D-037 旧服务 launcher 41208、listener 18648；沙箱目前仍只读看到监听 PID 18648，不能据此推定身份。普通 PowerShell 重核 PID、启动窗口、解释器、命令行、父子及活动连接，证据不符不停止进程。启动后核验实际监听、runtime 和代码散列。Chrome 可执行文件及 DevTools 先做无预约探活；只对批准设备按数据库北京时间选择次日合法无冲突整点，半开区间预查，已到期或五分钟内开始的旧待审使流程停止。正式 Chrome 依次验证学生 201／本人 200、教师明确 409／异主等同不存在的 404、管理员入口及直达 403；只允许一条保留预约。任何预约 intent 出现后不再自动发送 POST。正式发布仍待普通 PowerShell 回执。

本会话的受保护 passfile 存在性检查为 UnauthorizedAccessException，原项目解释器退出 103，未连接正式库或启停 8001。经核对 D-040 的 75 个认证输入未漂移，未重跑 91 项、20×10、故障或真整点。按课程第 25／26／27／33／34／36 页及 BMAD 6.12.4 保留正式 AC、证据链、状态和 D-041 事后实际结果；不改原 8/5、不填实验 A 或虚构人工判断。不修改业务代码、不碰 2.2、不标 done、不 commit/push。

## 独立合并延期台账

中央 `deferred-work.md` 的沙箱追加仍拒绝写入且散列未变。以下在普通 PowerShell 仅处理台账，以 `d040-approved-deferred-pending.md` 的三段为源，排除重复并保留原内容、编号和风险。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\_bmad-output\implementation-artifacts\story-2-1-targeted-independent-recheck\merge-story-2-1-deferred.ps1
```

成功以 `STORY21_DEFERRED_MERGE_OK` 为准。未收到实际回执前，不能记录已合并或达到最终验收。 [本轮写入拒绝](d041-deferred-merge-result.json) · [正式运行静态检查](d041-release-static-check.json)



## D-042 实际收尾，不重复执行

普通 PowerShell 只读恢复和续跑已实际完成，成功授权和 Chrome 及独立库回读全部保留。该文件上文仍按当时事实记录失败、恢复方案与权限拒绝。中央延期台账现在已经合并，三段内容与源逐段相同；无需再运行合并或数据库命令。 [实际运行索引](../story-2-1-runtime-evidence.md) · [负责人最终验收](../story-2-1-final-acceptance.md)
