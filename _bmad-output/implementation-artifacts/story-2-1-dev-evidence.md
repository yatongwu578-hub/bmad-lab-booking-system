# Story 2.1 · 开发证据与普通 PowerShell 交接

2026-11-26（北京时间）。BMAD 6.12.4 Build Step 3。负责人已按 [D-038](../../decision-log.md#d-038-2026-11-26-负责人批准-story-21-checkpoint-1) 批准规格及实施。**正式开发自测已全部满足，Story 2.1 已进入 Sprint `review`，待新会话独立代码评审。** 下列首次实施和探针整改记录保留为历史。以[真实复验及交接](#2026-11-26-复验核验与独立评审交接)为当前结论，不重复应用完整补丁或重跑已有有效证据。

## 实施及静态证据

- 基线 `e196aba098771a31eb203be4270b460d5e0aab42`。沙箱允许写产物，但对现有业务源码 `equipment/services.py` 的补丁和直写均返回拒绝。按批准方案在可写副本完成实现，真实仓库只保留本 Story 的增量补丁，未提前应用、未暂存。旧 `server-stderr.txt` 保留且不在补丁中。
- [增量补丁](story-2-1-implementation.patch)含 28 个路径。SHA-256 是 `44339655D023D71E6579E17A46FD255A89CB0FAA0C733B59DAD7B05B84AD0775`。实际仓库 `git apply --check --whitespace=error` 退出 0，从基线源码导出临时副本并实际应用同一补丁也退出 0。开发工作流读取了业务及验证差异，纠正了跨模块依赖方向、共用设备锁、确认业务拒绝后的额外读取、提交超时的分类和隔离库迁移前检查。没有将本轮内部核对写成独立 Code Review。
- 工具解释器仅做 Python 3.13 语法 AST 检查，23 个变更 Python 文件均通过。两个 PowerShell 脚本语法解析通过。静态测试方法数为既有 72 项、新增 18 项，预计发现 90 项，非执行数。代码补丁没有夹带 Sprint、决策日志、旧运行日志或 Story 2.2。
- 沙箱内项目原 `.venv` 版本探测退出 103。该结果不表示普通 PowerShell 中的虚拟环境损坏。未重装、未替换项目运行解释器或改用 Docker／SQLite。Django check、迁移、全量回归、锁探针、整点、故障和 20×10 真并发均无本轮实测结果。未连接或修改正式库，未运行隔离库 SQL，未 commit 或 push。

## 首次实施交接（历史，不重复执行）

在普通 Windows PowerShell 中进入项目根目录。仅当预检和补丁散列与上方一致时应用。命令不接触正式库，测试仅允许 `127.0.0.1:5433/test_lab_booking`。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$story21Patch = '.\_bmad-output\implementation-artifacts\story-2-1-implementation.patch'
if ((Get-FileHash -LiteralPath $story21Patch -Algorithm SHA256).Hash -cne '44339655D023D71E6579E17A46FD255A89CB0FAA0C733B59DAD7B05B84AD0775') { throw 'Story 2.1 patch SHA-256 mismatch' }
git apply --check --whitespace=error -- $story21Patch
if ($LASTEXITCODE -ne 0) { throw 'Story 2.1 patch check failed' }
git apply --whitespace=error -- $story21Patch
if ($LASTEXITCODE -ne 0) { throw 'Story 2.1 patch application failed' }
powershell -NoProfile -ExecutionPolicy Bypass -File .\_bmad-output\implementation-artifacts\verify-story-2-1.ps1
if ($LASTEXITCODE -ne 0) { throw 'Story 2.1 verification did not pass; preserve the run directory' }
```

原凭据或 Chrome 不在默认位置时，在验证命令加 `-Passfile` 或 `-Chrome`。不要贴出凭据。脚本分离保存回归、权限、交错、故障、标准竞争、时间边界及迁移前后基线。最后一组等待下一个合法北京时间整点，等待期间不持设备锁。测试运行时不要再使用同一隔离库运行别的探针。

把脚本输出的 `story-2-1-run-…` 目录路径发回本会话即可，失败也请保留原目录。核验各阶段退出码、输入散列、90 项实际回归、11 条正式 AC 和连续 10 轮的全部 HTTP／数据库记录后，才完成 Build Step 3 的矩阵审计并推进到 `review`。不以文件存在、静态检查或末尾标记代替运行原始证据。独立 `bmad-code-review` 仍由新会话执行。

## 2026-11-26 原始失败取证与定向复验

### 实际结果

原始目录未改写。实际连接为 `lab_booking_test@127.0.0.1:5433/test_lab_booking`，PostgreSQL 17.12、Read Committed，角色无超额权限且没有正式库 CONNECT。预检记录 Python 3.13.17、Django 5.2.19。原运行输入散列前后相同，原回归前后数据库快照文件 SHA-256 相同。 [阶段退出码](story-2-1-run-20261126-171347-146-27af94f2/stages.txt) · [运行输入](story-2-1-run-20261126-171347-146-27af94f2/after.sha256)

| 阶段 | 原始证据 |
| --- | --- |
| 迁移与检查 | 只执行 `reservations.0001_initial`、`audit.0001_initial`，两个均为 OK。原有表行摘要未改变。12 张表、19 条迁移，系统检查通过、无迁移漂移。 |
| Django 回归 | 发现 90，执行 90，逐项成功 90，零跳过，20.645 秒，`OK`，退出 0。含 Chrome R1、R-04 数据库约束、B1/B2 及提交错误分类单测。 |
| permissions | 退出 0。12/12 拒绝且无泄露、无业务变化。另有不存在 404、非法方法 405、两项师生提交 201 各自回读 200，篡改是其中一项的输入对照。本人已结束查询及重复查询均为 200，只有一次收尾。不外推为全项目 NFR-002。 |
| interleavings | 只到 I1，退出 1。四项实际 HTTP 结果符合预期，但探针漏采 SQL，运行未走到 I1 末尾的数据断言或 I2–I7。 |
| 后续 | `faults`、`nfr001-standard`、`time-boundaries` 无原始运行结果。 |

### 失败根因与原始时间线

实际 stderr 只有 `CommandError: No separate reread of target and account after locking`，Django 未输出 Python 完整堆栈，没有数据库异常或 SQLSTATE。按命令源码还原调用链为 `Command.handle → Experiment.interleavings → Experiment.i1 → check_order(a) → require → CommandError`。不是 PowerShell 报错行造成故障。 [原始 stderr](story-2-1-run-20261126-171347-146-27af94f2/interleavings.stderr.txt) · [逐请求取证](story-2-1-run-20261126-171347-146-27af94f2/interleavings.jsonl)

- 设备 358 起初可用且无预约。学生 PID 27080 取得设备行锁后独立重读，服务采样 `09:14:32.504908 UTC`，插入记录 42，到 COMMIT 前等待测试闩锁。教师 PID 35144 申请同一合法未来时段；`pg_blocking_pids(35144)` 实际为 `[27080]`，锁调用约 26.788 ms。学生 COMMIT 返回后教师取锁再采样 `09:14:32.615671 UTC`，返回明确的 409 占用冲突，未插入。学生 201。
- 独立观察者 PID 39816 在正对照之前读到一条仍有效的待审核记录 42，零历史。后做同设备相邻与不同设备同区间，两项均 201（记录 43、44）。原始日志没有后续独立快照称这两条为最终存量。权限阶段与 I1 的授权师生结果均未显示拒权。实际时间为锁后采样且申请是次日，北京时间整点尚未跨界。没有证据把本次失败归因于业务代码、数据库权限、死锁、时间边界或夹具数据冲突。
- 探针原先只识别未加别名的连续账号列。实际服务调用 `_recheck_applicant`，它用 `values_list("is_active", "role")` 按当前账号主键独立查询。用本机已安装 Django 5.2.19 的编译器对项目账号模型做无连接 SQL 编译，得到 `SELECT "accounts_user"."is_active" AS "is_active", "accounts_user"."role" AS "role" FROM "accounts_user" WHERE "accounts_user"."id" = %s ORDER BY "accounts_user"."id" ASC LIMIT 1`。原匹配为假，新匹配为真。原日志没有保留这句 SQL，不能把离线编译结果写成原运行实测；需复验亲自看到锁后、取时前的 SQL 序列。
- `cleanup=true`，五张业务/会话测试表计数均为零，完整行摘要和 schema/迁移前后相同，包括上述两个已登记迁移。使编号前进的序列未重置。该快照证明失败退出时已清理，不代表替代本次复验前的只读复查。

### 变更与复验

仅原地修改两个验证文件。探针识别明确的账号表、账号主键谓词、活跃标志和角色投影，接受 Django 列别名，仍要求在设备锁后、唯一业务时钟前有独立账号和目标重读。PowerShell 新增从原始证据定向续跑的入口，检查历史阶段成功标记、基线和输入散列，数据库现状若与原基线不符即停止，完全跳过迁移、重置和清库。相对于历史清单的 75 个输入，另 73 个输入散列保持原值。

静态核验实际通过 PowerShell 语法解析、Django SQL 编译和匹配正反例，含排除全字段账号查询、缺少账号查询、锁前或取时后查询必须失败。用无数据库替身核对续跑组选择及业务文件散列不匹配会阻断。沙箱启动原 `.venv` 返回 103，两次续跑尝试均止于预检，未连接数据库，不能据此填报任何整点、故障、交错或 NFR 通过。 [初次沙箱预检](story-2-1-run-20261126-172209-204-8be77a0f/preflight.txt) · [最终修改后沙箱预检](story-2-1-run-20261126-172509-616-cb608334/preflight.txt)

由三位组员在普通 Windows PowerShell 共同执行和审阅。第一段只跑失败组，并在组前后只读对照隔离快照。

```powershell
Set-Location 'F:\softwork\SE-Management\bmad-lab-booking-system'
$art = '.\_bmad-output\implementation-artifacts'
$verify = Join-Path $art 'verify-story-2-1.ps1'
$original = Join-Path $art 'story-2-1-run-20261126-171347-146-27af94f2'
$retryRoot = Join-Path $art "story-2-1-recheck-$([guid]::NewGuid().ToString('N'))"
$null = New-Item -ItemType Directory -Path $retryRoot -ErrorAction Stop
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -ResumeFrom $original -OutputRoot $retryRoot
if ($LASTEXITCODE -ne 0) { throw 'Interleavings failed. Preserve the new evidence and stop.' }
$passed = (Get-ChildItem -LiteralPath $retryRoot -Directory).FullName
```

第一段通过后在同一窗口运行余项。若凭据或 Chrome 不在默认位置，两条命令都传原先成功的 `-Passfile` 或 `-Chrome` 参数。余项会先核验交错通过日志、实时数据库基线及两次输入散列，才执行故障、NFR 和实时时间边界。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -ResumeFrom $original -ResumePhase remaining -InterleavingsEvidence $passed -OutputRoot $retryRoot
if ($LASTEXITCODE -ne 0) { throw 'Remaining verification failed. Preserve the new evidence and stop.' }
```

NFR-001 仍为每轮 20 个独立授权 HTTP 请求与独立数据库 PID，连续 10 轮，每轮恰好 1 个 201、19 个明确 409 占用冲突，以及唯一有效待审占用，必须有实际竞争证据。B3/B4 等真实下一个合法北京时间整点，等待期间不持设备锁，不用模拟取代。余项前遇基线不同或任一阶段失败时，不使用全量入口绕行，不执行迁移或清空数据库。

第 25 页按已归档 Story 字段及可测 AC 口径，第 26 页保持 FR-018→ADR-003/004/005/006/008 与对应 PC→AC→R-04/T-01～T-04→运行证据，第 27 页仅保留真实状态变化、待自测全部完成后进入 review，第 33 页保存原始证据和最小修改，第 34 页不改实验 A 条件或填造数据，第 36 页保留 D-038 与本次事后验证事实，不代填三位成员判断。仓库未找到 PPT 原件，依据课程基线和既有团队条目。没有改正式 AC、规格、Sprint 或决策口径，没有开发 Story 2.2，没有 commit/push。 [正式证据对照](story-2-1-verification-map.md) · [课程基线](../../docs/course-requirements.md) · [Sprint](sprint-status.yaml)

## 2026-11-26 复验核验与独立评审交接

团队报告在普通 PowerShell 完成定向复验，本会话只读核对原始文件和实现差异，没有重跑服务、测试或连接数据库。两次复验的预检、各分组、前后快照及 `resume-complete` 均退出 0，分组 stdout 各有唯一精确成功标记、stderr 为空。交错于北京时间 17:35:50 结束，剩余批次在真实 18:00 整点后完成，于 18:00:02 收尾。首次 I1 漏采 SQL 的失败、探针修复和沙箱预检失败均保留原样。 [首次退出码](story-2-1-run-20261126-171347-146-27af94f2/stages.txt) · [首次 I1 失败](story-2-1-run-20261126-171347-146-27af94f2/interleavings.stderr.txt) · [交错退出码](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173530-191-df47c547/stages.txt) · [余项退出码](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/stages.txt)

**证据版本与清理。** Git HEAD 和规格基线均为 `e196aba098771a31eb203be4270b460d5e0aab42`。两次复验前后四份输入清单字节相同，SHA-256 为 `B0DA21E2B06806981243A0BA4FA3B0DCEF5C7702E115F07E18D62E0048B815D6`。与原始 75 项清单逐条对照，仅 `verify_reservation_transactions.py` 与 `verify-story-2-1.ps1` 改变，另 73 项不变。核验时工作区 75 项全部匹配复验输入。下文规格状态与勾选等是**测后文档更新**，不会改写旧清单或改变被测代码。原回归前后与两次复验前后共六份基线文件 SHA-256 同为 `5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272`。各组 `cleanup=true`，完整行摘要、表所有者及迁移记录前后一致，五张业务/会话测试表均为零行、12 张表、19 条迁移。唯一目标为 `127.0.0.1:5433/test_lab_booking`，PostgreSQL 17.12，Read Committed，测试角色无正式库 CONNECT。无重复迁移或序列重置。 [原输入清单](story-2-1-run-20261126-171347-146-27af94f2/after.sha256) · [复验输入清单](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/after.sha256) · [末次基线](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/resume-after.jsonl)

### 并发交错与事务

15 个实例覆盖 I1～I7。记录到的申请 SQL 为设备主键 `FOR UPDATE`（无 `SKIP LOCKED`）→独立设备重读→按账号 ID 读 `is_active AS "is_active"`、`role AS "role"`→唯一 `clock_timestamp() AS decision_at`→失效、校验/冲突、写入和提交。锁内修改结果的本人读取先固定候选，再锁设备、复核账号并重读固定候选后唯一取时。撤权和重读已是终态时不取样，终态首次读取不额外加锁。 [交错原始 SQL、阻塞与快照](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173530-191-df47c547/interleavings.jsonl)

| 场景 | 实际证据 |
| --- | --- |
| I1 | 学生 PID 43464 写入 45 并先提交。教师 PID 37072 实际等待，阻塞方为 43464，锁调用约 19.032 ms。取得锁后教师收到明确冲突 409，两项相邻／跨设备控制为 201。竞争快照恰一有效待审、零历史。 |
| I2×2 | 维修／停用写事务先提交。申请取得锁并重读后均 409 不可用，对旧到期待审各执行一次合法失效及历史，零新申请。 |
| I3×2 | 申请先提交 201，独立维修／停用写事务实际等待，之后才落库。待审占用仍有效，零设备或失效历史。 |
| I4×2 | 本人读取先锁和申请先锁两种方向均实测阻塞。旧预约各仅失效一次，系统历史一条，重叠未来申请成功，已批准和无关设备保持原状。写先时，后到读者锁后重读到终态而未重复取时或失效。 |
| I5×3 | 不可用 409、时间非法 400、仍有冲突 409。每次均零新申请，相关失效及历史仍提交，其他有效占用不变。 |
| I6×4 | 停用账号／改成管理员分别覆盖申请和本人查询。实际等锁后复核均 403，零取时、零业务写入、无数据或历史变化。 |
| I7 | 设备锁被占用时终态读取直接 200；待审读取实际等待，只将原固定候选 69 失效并写一条历史，期间新增的他人记录 70 保持待审。另由回归验证同一归属的其他记录也不被收尾。 |

### 逐轮复算 NFR-001

直接重算 200 条响应及 200 条服务端轨迹。每轮同一设备、空初始占用和同一合法未来时段，两个合法账号各 10 个请求，登录和 CSRF 在统一屏障前准备。逐请求核验屏障后启动、路由和输入、数据库身份、服务端活动、唯一取时、实际响应及胜者与数据库记录的一致性。实际竞争对定义为一个事务已取得设备锁、尚未进入提交时，另一个独立后端尝试取锁。各轮 20 个不同 PID，均与观察连接不同；无其他错误、无无响应、无历史写入，不据此报告延时达标。 [200 条原始响应和连接证据](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/nfr001-standard.jsonl)

| 轮 | 设备 / 胜者预约 | 201 / 明确 409 | 有效待审 | 独立 PID | 实际持锁重叠对数（示例 PID 对） | 屏障后启动分布 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 383 / 80 | 1 / 19 | 1 | 20 | 10（2324→24400） | 0.237–4.473 |
| 2 | 384 / 81 | 1 / 19 | 1 | 20 | 9（43132→41408） | 0.168–4.957 |
| 3 | 385 / 82 | 1 / 19 | 1 | 20 | 8（40592→39300） | 0.146–4.546 |
| 4 | 386 / 83 | 1 / 19 | 1 | 20 | 7（24624→20684） | 0.197–4.169 |
| 5 | 387 / 84 | 1 / 19 | 1 | 20 | 7（42988→34620） | 0.160–3.882 |
| 6 | 388 / 85 | 1 / 19 | 1 | 20 | 9（4200→14052） | 0.178–4.507 |
| 7 | 389 / 86 | 1 / 19 | 1 | 20 | 4（41780→37048） | 0.161–4.239 |
| 8 | 390 / 87 | 1 / 19 | 1 | 20 | 10（8764→33552） | 0.154–3.662 |
| 9 | 391 / 88 | 1 / 19 | 1 | 20 | 8（27540→17088） | 0.191–3.791 |
| 10 | 392 / 89 | 1 / 19 | 1 | 20 | 8（41312→40132） | 0.201–3.857 |

**结果为 10/10 轮，10 个成功、190 个明确时段冲突。** 200 条请求不是 200 个不同账号，符合 Q3 已批准的测试条件。

### 故障和真实时间边界

| 验证 | 实际结果 |
| --- | --- |
| F1 历史／预约插入 | 两次实际 PostgreSQL `23514`，均 503 明确回滚，零 COMMIT 尝试，预约、失效、历史不留部分结果。 |
| F2 | 延迟约束在一次 COMMIT 时给出 `23505`，503 明确回滚，无部分结果。 |
| F3 | 独立连接实际终止目标后端，一次 COMMIT 尝试，无 SQLSTATE；界面 503 待核查且不重试。独立观察确认未持久化，界面未提前断言。 |
| F4 | PostgreSQL 实际提交，测试仅模拟驱动确认丢失，一次 COMMIT 尝试，无 SQLSTATE。界面同为 503 待核查且不重试；独立观察确认旧记录 78 已失效、预约 79 仍有效、唯一系统历史同时落库。 |
| B1/B2 | 复用 Django 实测的开始前／等／后 1µs、北京时间输入与 UTC 往返矩阵，含 22:00–23:00、合法午夜、非整点和跨日等。 |
| B3 | 北京时间 17:59:48.100164 已实际等锁，18:00:00.003698 之后放行，锁后唯一判定 18:00:00.011708。新申请 400，旧记录 90 失效并产生一条一致的系统历史。 |
| B4 | 北京时间 17:59:48.085528 锁内判定，越过 18:00 才放行 COMMIT，响应 201。独立观察读到 91 仍为待审但不再计有效占用、尚无历史。本人 GET 于 18:00:00.238186 取时，响应 200 已失效并仅追加一次历史。 |

[故障注入原始记录](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/faults.jsonl) · [真实时间原始记录](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/time-boundaries.jsonl)

### 正式开发自测矩阵

| 条款 | 本 Story 实证结论 |
| --- | --- |
| AC-1 | 通过。师生 201、有编号及本人回读，字段与当前主体、设备及时段匹配，I1/NFR 确证提交即占用。 |
| AC-2 | 通过。权限 12/12，伪造身份、设备、时区不能改变可信输入；I6 证实锁后撤权不产生副作用。 |
| AC-3 | 通过。B1/B2 精确边界及真实 B3，合法时段、北京时间解释及严格未来规则成立。 |
| AC-4 | 通过。I2/I3；维修或停用顺序改变实际结果，不自动取消或失效已成功的未来申请。 |
| AC-5 | 通过。两种有效状态的重叠矩阵、双向相邻、同人跨设备、三种终态及 I1，无他人详情泄露。 |
| AC-6 | 通过。I2/I4/I5 和回归确认按需收尾相关待审、原区间释放、历史完整唯一、批准不误失效，R-04 保证对象关联。 |
| AC-7 | 通过。I1 与 200 条申请轨迹证明锁后重读、权限复核、唯一 DB 时钟及提交顺序；B3/B4 证明等锁跨界拒绝和判定后跨界提交成功。 |
| AC-8 | 通过。I5 三种业务拒绝无新增，合法失效及历史同时提交；回归验证拒绝渲染不额外重读设备。 |
| AC-9 | 通过。F1～F4 共 5 实例，区分确定回滚与未知、不重试、不伪装成冲突；原回归补充服务器取消及其他提交错误分类。 |
| AC-10 | 通过。合法本人、已结束待审、重复读取、他人／不存在等价、合法 CSRF 下非法方法 405，I4/I6/I7 确认权限范围、固定候选与无待审不加设备写锁。 |
| AC-11 | 通过。标准真实并发 10/10 轮，与时间边界独立取证。 |
| R-04 | 本 Story 通过。原迁移 SQL 和 `test_r04_database_checks_both_fk_and_protects_referenced_rows` 覆盖零/双对象、错配、未知类型、NULL、两种悬空 FK、两种合法引用及删除保护。I4 与 F1～F4 验证唯一历史和原子持久化。 |
| T-01 | 本 Story 通过。I1～I7 全部 15 个实例，与标准 20×10 分开。后续真实审批/取消及设备状态入口交错仍由对应 Story 执行。 |
| T-02 | 本 Story 通过。B1～B4 与 I4/I5、F1～F4 对应 B5。原 IR-05 的历史设计交接节点未按时闭环，保留原记录，不追溯关闭；真实管理员结束边界留给对应 Story。 |
| T-03 | 本 Story 通过。合规及越权对照与 I6，非全项目 NFR-002。后续权限入口仍须单独验证。 |
| T-04 | 本 Story 通过。NFR-001 逐轮重算、两账号映射、屏障、真实重叠、独立连接、逐响应与最终状态全量保留。 |

[正式 AC](../planning-artifacts/epics.md#story-21-提交具体设备预约并获得可靠申请结果) · [原回归输出](story-2-1-run-20261126-171347-146-27af94f2/regression.stderr.txt) · [原权限输出](story-2-1-run-20261126-171347-146-27af94f2/permissions.jsonl) · [AC/实现追溯](story-2-1-verification-map.md)

### 独立评审交接

按本次授权记录 Build Step 3 的任务与冻结矩阵自测证据。规格 `in-review`、Sprint Story 2.1 `review`，只表示可交评审，不表示通过独立评审或最终验收。未执行 Build Step 5 的 done、提交或推送步骤，未将本会话记为独立评审。Epic 2 保持 `in-progress`，2.2 及之后未开始。三位组员共同操作与审阅，不造个人意见。第 25 页保持 Story 结构和验收不变，第 26 页保存 FR/NFR→ADR/PC→AC→原始证据链，第 27/33 页记录状态与真实产物，第 34 页不修改实验 A 条件或填报数据，第 36 页仅补 D-038 的事后实证。页码以仓库课程基线与已有团队记录核对，未声称直接核验 PPT 原页。

在**新会话**调用已安装 BMAD 6.12.4 的 `bmad-code-review`（菜单 CR，full 模式），传入 `_bmad-output/implementation-artifacts/spec-2-1-submit-reservation.md`。以规格 `baseline_commit` 对工作树构造 Story 2.1 范围 diff，明确纳入未暂存和未跟踪的预约、审核历史、账户策略、设备接入、事务与验证工具；旧 Story 1.4 日志不属于评审 diff，原始 JSONL 作为证据读取，不混入业务差异。请独立检查锁与错误分类、FR-018/GET 候选范围、R-04、最小授权提案、测试取证与断言。按工作流先出目标和范围核对，再由小组三人共同审阅和处置，不为人代填裁决。后续 Story 的审批、拒绝、取消、列表/日期占用、设备状态真实入口、全项目 NFR-002 与正式库迁移/授权都未关闭，且不在本次评审中擅自实施。 [规格](spec-2-1-submit-reservation.md) · [Sprint](sprint-status.yaml)
