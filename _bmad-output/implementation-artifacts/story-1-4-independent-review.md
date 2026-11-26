# Story 1.4 独立代码评审

2026-11-25。BMAD 6.12.4 `bmad-code-review`，`full`。Step 1、四视角和裁决已完成，Step 4 已写入发现，**停在负责人处置检查点**。当前结论为**不具备最终验收条件**。本文为 Codex 评审结论，不是团队最终验收决定。

## 基线与执行记录

- Story 1.3 的最终验收提交及本地 `main` HEAD 均为 `e200fee335536941e0705c112aefbf6751b244c3`。原工作树差异 19 文件（已跟踪 8、未跟踪 11），Git 文本统计新增 1,917、删除 12 行，另有一份按 Git 二进制补丁表示的 UTF-16 原始日志。其中业务及测试目录下 9 文件新增 721、删除 10 行，逐一比对补丁目标 Git 对象均相同。独立工作树快照 130,313 字节，SHA-256 `819EEC784495D5E9A5D9699A244A509733D2E5C75B4DABCF3BDE054FA0C9FE8D`。只读反向检查退出 0，未应用、反向应用或重建补丁。随后新建的评审记录和复验脚本不属于被评审补丁。
- 官方解析器成功，配置中文，四层启用。发出四个启动请求后，Acceptance Auditor 首次遇到 `agent thread limit reached`。三位独立代理实际返回；首个代理完成并释放槽位后，Acceptance Auditor 用同等能力、全新独立上下文和原冻结差异另行启动并返回。**四份独立报告实际收齐，不是四个同时运行**，没有把额度错误替换为主代理自评。 [补位时的独立输入](story-1-4-acceptance-auditor-handoff.md)
- 按 [AGENTS](../../AGENTS.md)、[课程基线](../../docs/course-requirements.md)、[正式 PRD](../planning-artifacts/PRD.md)、[Architecture](../planning-artifacts/architecture.md)、[项目规则](../planning-artifacts/project-context.md)、[正式 Story/AC](../planning-artifacts/epics.md#story-14-管理员维护设备基础信息并保护设备身份)、[Sprint 计划](../planning-artifacts/sprint-plan.md)、[决策 D-024、D-032](../../decision-log.md)、[实施规格](spec-1-4-edit-equipment-basics.md)、[Sprint 状态](sprint-status.yaml)、[延期台账](deferred-work.md)、[开发证据](story-1-4-dev-evidence.md)和原始日志核对。安装版 code-review 入口是 `SKILL.md` 加四个 step 文件，不依赖为 Build 重渲染 `workflow.md`。

## 正式 AC 的独立静态核对

下表的运行列是**团队开发自测**，不代表独立复跑。所有 AC 的本轮独立数据库运行仍待取得。

| 正式 AC | 独立静态与证据裁决 | 团队开发自测对应 |
| --- | --- | --- |
| AC-1 | 明确按原主键更新四列，成功后重定向原详情。通常值对照完整；合法多行说明的首尾空白可被静默丢弃，见 R2。 | 管理员 GET 200、有效 POST 302，四个常规值及完整设备行对比。 |
| AC-2 | 编号是只读展示，提交编号即报错且不进入写路径；沿用 PostgreSQL 具名唯一约束。 | HTTP 400、全字段不变；直接重复写入由 `equipment_number_unique` 拒绝。 |
| AC-3 | 状态不属于表单或更新列；伪造整笔拒绝，未新增预约、历史或状态转换逻辑。 | 三种起始状态各两种伪造对照，均无设备变更。 |
| AC-4／T-03 | Django CSRF 中间件、登录和业务角色先于设备读取/写入，否认 staff/superuser 豁免。当前代码缺 PC-008 锁后授权复核，T-03 留存缺口见 R7。 | 六项角色拒绝全通过；匿名两项 302、学生/教师四项 403。缺失、错配 CSRF 两项 403，合法 GET/POST 200/302，均另列。 |
| AC-5 | GET 和通过 CSRF 的 POST 缺目标均返回设备不存在，不创建或替换。 | GET、合法 POST、非法字段 POST 的 404 对照及全行不变。 |
| AC-6／T-01 | D-024 连接级 Read Committed。最外层短 atomic 先锁设备，独立语句重读，再按原 PK 仅更新四列。无旧对象回写状态。 | 维修和停用各测 A 先提交和 B 真实等待。维修 B 40892 等 A 7432，停用 B 17292 等 A 38936。观察连接 PID 35188，四例各写一次且状态保持最新。 |
| AC-7 | 无设备物理删除路由、表单动作、Django Admin 或删除后重建。仅测试命令含隔离夹具清理，不是业务入口。 | 两个 DELETE 方法 405，删除及 Admin 路径 404，设备全行和总数不变。 |
| AC-8 | 比对服务异常分类、503 模板、不重试路径和独立读回断言。四个已测场景一致，无编号冲突误报。其他明确拒绝路径的假设见 W2。 | UPDATE 后回滚 `23514` 和明确拒绝 COMMIT `23505`，均保持原值；送出 COMMIT 前断连仍为原值，实际提交后丢确认则为新值，两者均提示待核查。前者没有实际发出 COMMIT，日志“COMMIT 路径=1”是进入钩子一次。 |

AC-6 的通过证据来自 `pg_blocking_pids`、独立后端、锁中可见性、SQL 顺序和完整末态，不是测试名称或 HTML 文案。AC-8 的未知消息不宣称成功或回滚，页面指向原设备供核查，不返回表单、成功跳转或自动重试。隔离命令的 COMMIT 后丢确认通过 psycopg 底层发出真实 COMMIT、观察连接读到新值后才丢弃确认。

## 四视角原始条目的逐项裁决

ID 按收到的各层最终报告顺序规范化。严重度属于本层裁决，不来自子代理。Blind Hunter 按 130.313 kB 计算最低 10 项，返回 11 项；Edge Case Hunter 7 项，Verification Gap 4 项，Acceptance Auditor 2 项。下表先判每条，后按同根因归并。

| ID / 来源 | 原始条目与位置 | 裁决与证据 |
| --- | --- | --- |
| 01 Blind | 管理员看到入口但当前业务角色无保存授权，`detail.html:14`／`README.md:104` | **Medium → W1**。D-032 明确尚未授权，正式交付不能把隔离结果当作可用。属发布门槛，不建议拿未经批准的业务路径做核验。 |
| 02 Blind | 运行请求无明确行锁超时，`services.py:121` | **Low，驳回本轮整改**。代码不设应用端超时，探针超时不能代表运行时。正式协议没有给定超时目标，当前无超时事件证据，不引入新的事务参数。 |
| 03 Blind | 不在拒绝分类表中的服务器 COMMIT 错误可能被报未知，`services.py:102` | **Maybe-false → W2，未证实 Medium**。假设 P0001 或 COMMIT 锁超时需当前结构可达的实证，未见此类延期触发器或实际诊断。 |
| 04 Blind | GET/非法 POST 的设备查询异常可返回通用 500，`views.py:107` | **Low，驳回本轮整改**。只读分支不尝试保存，未违背 AC-8 的合法修改提交结果，不新增通用故障页面。 |
| 05 Blind | 直接调用服务可以送入表单会拒绝的值，`services.py:107` | **False（当前业务旁路）**。唯一业务调用传入通过校验的 `form.cleaned_data`；没有可访问的第二调用路径。服务依然强制键白名单。 |
| 06 Blind | 没有记录阶段/SQLSTATE 的脱敏细粒度诊断，`services.py:132` | **Low，驳回本轮整改**。运维可观测性可改进，当前 503 语义及探针诊断独立成立，未要求本 Story 架构新增日志功能。 |
| 07 Blind | 隔离测试角色不能证明实际业务角色四列授权，`story-1-4-checkpoint-1.md:18` | **Medium → W1**。当前角色不同，D-026/D-030 的有效权限是历史证据，需另批真实发布核查。 |
| 08 Blind | 隔离清理早期 DELETE 出错会中断其余清理，`verify_equipment_edit_transactions.py:129` | **Low，驳回本轮整改**。代码分三步，失败可能留专属夹具；正常运行实际清理成功，不引入复杂回滚/恢复分支。若清理实际失败，停止后核对隔离库，勿自动重复跑。 |
| 09 Blind | 原 PowerShell 驱动不自动依数量/skip/清理判失败，`verify-story-1-4.ps1:85` | **Low，驳回额外整改**。原脚本明示人工复核数量和清理，不声称只凭退出码通过；新增独立复验包装已核对这些门槛，不重复改原工具。 |
| 10 Blind | 无“显式空说明”的成功回归，`test_edit.py:75` | **Low → R6**。代码允许，现有正向只用非空，省略键的反例不能替代清空。 |
| 11 Blind | 打开表单后、下一个请求前改变账号权限未走真实会话回归，`test_edit.py:121` | **Low，驳回单列整改**。Django 在新请求重新取账号，当前代码未显示跨请求授权失效。优先修 R1 已识别的同一请求等待窗口，不另扩大矩阵。 |
| 12 Edge | 行锁长等超时边界，`services.py:121` | **Low，驳回本轮整改**。运行代码没有设置时间阈值；在现有需求下不把测试观察时限当作生产 SLO。 |
| 13 Edge | 授权后只读查询失败返回通用 500，`views.py:107` | **Low，驳回本轮整改**。设备不写、未报成功；不改 AC-8 范围。 |
| 14 Edge | 说明首尾有意义空白被静默裁剪，`forms.py:20` | **Medium → R2**。本地 Django `TextField.formfield` 最终使用默认 `CharField(strip=True)`，说明可被改短，甚至只编辑位置也可能改写原说明。正文详情本来保留文本空白。 |
| 15 Edge | 单行字段若已有内嵌换行，浏览器再编辑会改写，`forms.py:17` | **Low，驳回本轮整改**。普通表单输入是单行，需先有非普通方式保存的特殊值；另引入拒绝规则会改变既有输入策略，不夹带到 R2。 |
| 16 Edge | 旧表单状态断言会命中免责声明，`verify_equipment_edit_transactions.py:150` | **Low → R3**。`catalog_base.html:12` 固定含“可用”，不反证真实锁等待/最终状态，只使初始可见状态断言太宽。 |
| 17 Edge | 清理前一步异常留下后续夹具，`verify_equipment_edit_transactions.py:129` | **Low，驳回本轮整改**。局限在隔离工具，未发现夹具残留，已保留失败交接限制。 |
| 18 Edge | 建连发生在探针 statement/lock timeout 之前，`verify_equipment_edit_transactions.py:43` | **Low，驳回本轮整改**。等待事件不覆盖建连，实际 127.0.0.1 探针成功，未扩大守卫或引入新的连接参数。 |
| 19 Verification Gap | 通用词使错误状态标签仍可通过，`test_edit.py:79` | **Low → R3**。直接断言实际状态项可补足，当前模板字段正确。 |
| 20 Verification Gap | 表单的真实方法/目标未被测试，`test_edit.py:84` | **Low → R4**。删掉 POST 方法浏览器会 GET，测试却自行发 POST。当前模板正确。 |
| 21 Verification Gap | 未检查提交待核查页面原设备链接，`test_edit.py:205` | **Low → R5**。当前链接正确；若指向目录，现有 503、无表单和末态断言仍会通过。 |
| 22 Verification Gap | 不能发现把可空说明误改为必填，`test_edit.py:222` | **Low → R6**。现有省略键/文件用例与显式空文本不同，缺合法边界对照。 |
| 23 Acceptance | 缺设备行锁后的账号权限复核，`services.py:107`、`:125` | **High → R1**。PC-008 要求副作用前授权并锁后复核。Django 请求内已读的用户状态不随等待刷新，而锁后只回读设备。若等待中账号已被停用或撤权，服务可按旧授权更新四列。属静态安全与架构发现，未实测停用交错。 |
| 24 Acceptance | T-03 前后业务数据只在断言内比较，原日志不保留实际数据或指纹，`test_edit.py:121` | **Medium → R7**。PC-011 要求保存逐例输入、预期/响应及前后数据。原日志六条输出只有角色/方法/码/行数与结论，测试源码补充了预设，但不能替代逐例留存。不是发现泄露或实际写入。 |

**裁决结果。** 0 项需要需求决定，7 项待整改，2 项延期跟踪，12 条原始发现驳回。R1、R2 优先，R7 补齐可审计证据。R3～R6 仅为最小测试断言，建议随定向回归补齐，若团队选择延期，不把它们说成现行页面已失败。W1 是发布门槛而非四列之外的授权要求。没有修改业务代码、实际测试代码或原探针。发现已写入实施规格；既有延期台账写入被拒，原文件未修改，两个条目另存为可补入的 [延期附录](story-1-4-deferred-work-appendix.md)。

## 独立复验交接

- **历史实测**由团队普通 PowerShell 执行。按原始日志逐项比对 55 个历史测试 ID、12 个新增测试 ID、67 个通过且零跳过、五个记录的进程退出码均为 0。隔离探针 8/8，四个 T-01、两个可证数据库阻塞、四种 AC-8 结果及清理通过。历史日志 SHA-256 `26770FF8C36734614B7AFAC73990F05D7A33104E895329C4E2ACBD795A5D89A9`。 [原始输出](story-1-4-verification-20261125-221855-930.txt)
- **本轮独立实际执行** Django 0 项、PostgreSQL 探针 0 项。原解释器沙箱历史返回 103，未再次调用。未连接数据库，未访问业务库或执行任何授权。复验脚本通过 PowerShell 语法解析，输出判定规则已用现存原始日志做只读核对；沙箱拒绝运行外部 .ps1，未将脚本的读取、解析和日志核对记成运行测试。
- **复验方式**。三位组员在仓库根目录的普通 PowerShell 中共同操作，填写实际操作者，另注明真实共同审阅情况。脚本复用原 `.venv` Python 3.13.17；不应用补丁、不安装依赖、不改变执行策略。默认复用现有密码文件与 Chrome。需要时通过 `-Passfile` 和 `-Chrome` 指定已有绝对路径，不提交凭据。仅使用 `lab_booking_test@127.0.0.1:5433/test_lab_booking`，待前一进程退出后串行执行一次。

```powershell
& .\_bmad-output\implementation-artifacts\verify-story-1-4-independent.ps1 -ExecutedBy '填实际操作者姓名'
```

将脚本打印的证据目录中的 `raw.txt`、`run-summary.txt`、`before.sha256` 和 `after.sha256` 一并保留。复验包装保存实际执行者声明、原始输出、命令退出、整体判定和前后源码散列清单。审阅时比对 R1/R2 是否已修改及输入版本；复跑原候选的 67/8 即使全绿，也不消除静态发现。 [复验脚本](verify-story-1-4-independent.ps1)

## 正式业务库的最小授权与运行核查计划

1. D-026、D-030 留档表明 `lab_booking_app` 对 `public.equipment_equipment` 有七列 SELECT、六列 INSERT，未获设备 UPDATE。PostgreSQL 17 的 `SELECT ... FOR UPDATE` 要求该表至少一列 UPDATE，现有主键 SELECT 加候选四列 UPDATE 足以执行实际的取锁、读行和更新 SQL，不需要给主键或状态加 UPDATE。 [D-030 权限证据](story-1-3-runtime-evidence.md) · [PostgreSQL SELECT](https://www.postgresql.org/docs/17/sql-select.html) · [PostgreSQL UPDATE](https://www.postgresql.org/docs/17/sql-update.html)
2. **仅为另批候选，不执行。** 对象所有者在核对实际目标、角色、版本、所有权及有效权限后，以单一事务和失败即回滚处理，只授予 `UPDATE (name, category, location, description)`。事务内逐列验有效权限（含继承），断言只有四列新增 UPDATE；编号、状态、主键无 UPDATE，既有读/插入不变，无表级 UPDATE、DELETE、TRUNCATE、DDL 或转授权。有漂移即停止，不用扩大权限排错。 [原批准边界](story-1-4-checkpoint-1.md#正式库最小授权候选)
3. 只有独立复评和另行批准后，才在正式运行环境以实际应用角色核对连接及 Read Committed；通过明确许可的演示设备做正常管理员浏览器操作与三角色访问核查，记录实际操作者及原设备 ID、编号、状态、记录数和四项对照。若业务库运行仍未获准，保持待验证。故障注入、并发、伪造请求和数据库验证测试始终限于批准的隔离库，绝不把探针连到业务库。

## 课程证据与状态

- 第 26 页。FR-016/002 → ADR-002/003/006/008、PC-003/008/011/014 → 正式 AC 和测试映射记录在本报告。
- 第 27、33 页。留存开发自测、独立四视角、逐项裁决、复跑脚本和状态事实。Step 4 尚待实际负责人处置，规格继续 `in-review`、Sprint 继续 `review`；不标记 `done` 或推进 Story 2.1。
- 第 34 页。不改实验 A 条件、数据或分组，本轮不把 Story 1.4 记入该实验。
- 第 36 页。以 D-032 和本次会话的范围批准为实际事实，不预填整改、延期接受、最终验收或组员意见。收到真实人工处置后再记录结果。仓库未找到课程 PPT 原件，页码按课程基线及团队留档核对。不分派个人任务，不暂存、提交或推送。

## 2026-11-25 Step 4 人工处置补记

首轮评审与原始裁决保持为处置前快照。负责人随后实际选择「方案 2：保留为行动项」，批准 R1、R2、R7 待原 Build 修复并验证，R3～R6 条件性延期，W1/W2 继续跟踪，12 条原始驳回不变，0 项修复。规格与 Sprint 已转为 `in-progress`，本轮独立实际测试仍为 0 项，统一复验安排在整改后。既有延期台账写入仍受限，完整六项保留附录待合并。 [D-033](../../decision-log.md#d-033-2026-11-25-负责人批准-story-14-独立评审处置) · [逐项处置](story-1-4-review-disposition.md) · [原 Build 整改交接](story-1-4-remediation-handoff.md)
