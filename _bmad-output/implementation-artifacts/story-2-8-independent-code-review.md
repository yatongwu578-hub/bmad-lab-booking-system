# Story 2.8 · BMAD 6.12.4 full 独立代码评审

2026-11-28（北京时间）。**首评建议有变更请求。** 1 项实现问题、1 项必需实证缺口；集中整改后一次隔离复验。未修改业务代码、未访问正式库、未执行独立数据库测试、未标 done、未暂存、提交或推送。负责人已确认评审范围，尚未选择发现处置；不代替三位成员签审。

## 范围与依据

- 以 [2c6380ac608b356df5f0be8251fa4882327e3eab](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/2c6380ac608b356df5f0be8251fa4882327e3eab) 比对当前实际工作树，11 个文件（其中 4 个未跟踪）、新增 1,126 行、删除 10 行。统一 diff SHA-256 `55EA37BE6BB9C9F7992F9BA41843C7CFDB0CA059B309552947AEE22C3CBBD482`。排除历史日志及锁文件。跟踪的业务差异集中在 `audit/services.py`、预约服务、表单、路由、视图与模板；新确认模板、测试、探针、隔离脚本均纳入。设备、冻结规划和实验目录无业务差异，3.1 仍为 backlog。
- 以 [正式 AC-1～AC-8](../planning-artifacts/epics.md#story-28-管理员取消预约并记录原因) 为唯一正式 AC，对照 [PRD](../planning-artifacts/PRD.md)、[Architecture／ADR-001～008](../planning-artifacts/architecture.md)、[Project Context](../planning-artifacts/project-context.md)、[实施规格](spec-2-8-admin-cancellation.md)、[开发证据](story-2-8-dev-evidence.md)、[交接](story-2-8-code-review-handoff.md)、[首测整改](story-2-8-regression-remediation.md)、[Sprint 计划](../planning-artifacts/sprint-plan.md)、[Sprint 状态](sprint-status.yaml)、[决定日志](../../decision-log.md) 及 [延期台账](deferred-work.md)。
- 同一评审会话中独立启用 Blind Hunter、Edge Case Hunter、Verification Gap Reviewer、Acceptance Auditor，无失败层。宿主同时可运行三个子评审，第四个在槽位释放后启动。盲评差异大小为 79.318 kB，最低发现数 `min(floor(sqrt(79.318)+1),10) = 9`。4 层共 18 个原始发现，独立裁决后归并。

## 必须整改

| ID | 严重程度 | 证据与最小关闭条件 |
| --- | --- | --- |
| 2.8-P01 | Medium，阻塞，实施偏差 | `reservations/views.py:417–433,445–470` 仅严格检查 POST 正文的转义及 UTF-8，`equipment` 查询值直接取 Django 容错解码后的 `request.GET`。`reservations/forms.py:38–54` 只校验允许字段、单值、非空及模型字段长度。畸形转义或非法 UTF-8 可被保留或替换为可接受的短文本，已授权提交仍会到达取消事务，可能写取消或 FR-018。该缺陷不绕过角色或 CSRF。仅对新入口修好原始查询串的格式闸口，保留正常的已编码设备编号和固定返回。以合法 CSRF 配对验证畸形查询在目标读取／锁／判时前返回通用 400，且未到期的合法取消与到期待审的 FR-018 均未被该畸形请求触发。合法查询和合法缺省原因作为对照。 |
| 2.8-P02 | Medium，阻塞本轮证据关闭，不是已发现的实现错误 | `reservations/management/commands/verify_admin_cancellation.py:112–132,449–454` 的 `cancel` 为另一个管理员，`own-detail` 是本人 GET。34 组均无本人取消 POST 与管理员取消 POST 的竞争。本轮明确要求实证。用既有探针／设备锁同步点补双序，保持同一未开始的待审核预约，后手真实等锁，独立回读恰一条历史、正确主体与原因、原记录已取消、无有效占用；一次主管理员成功，一次本人成功。隔离归档中检查两个 POST 的真实路由、独立后端 PID 和实际阻塞关系。一并同步现有批次的探针分母和成功标记，不另造框架。 |

## 正式 AC 独立核对结果

以下是独立读码与复算**开发实测**的结果，不是本会话独立复验通过。

| AC | 核对结果 |
| --- | --- |
| AC-1 | 静态实现与开发实证支持。正常列表／详情到确认页可保留筛选，GET 不写，合法 POST 取消并保留原预约。真实取消先行后同窗口合法申请 201，恰一条新有效占用。 |
| AC-2 | 正常请求路径符合。等锁跨开始按 `>= start` 仅写目标失效及一条系统历史，邻项不动，重复无额外转换。P01 影响非法输入能否进入这条合法失效路径。 |
| AC-3 | 支持。已批准在开始后尚未结束仍可取消。精确相等/之后不取消、不误失效，真实等锁跨结束仍已批准。 |
| AC-4 | 支持结构合法的缺省、空串、全空白分支。未到期零写且必填，到期待审仍提交一条系统失效、提示必填及未取消。首批实际失败是同一新增方法的 3 个缺省原因子例；补用确认页签发的 CSRF 使请求成为合法表单，仍不传 `reason`，未弱化 400、必填、失效/历史及表单断言。P01 另涉查询部分非法输入。 |
| AC-5 | 支持。终态、缺失与重复提交均拒绝，双管理员实际 200/409，仅一条取消历史。 |
| AC-6 | 正向锁序与角色、启用、CSRF 整体支持。两起真实等锁后降权或停用均 403，锁后不读取目标、不判时和不提交。合法路径按账号复核、目标定位、设备锁、锁后复核、重读及一次 PostgreSQL `clock_timestamp()` 顺序运行。非法输入闸口有 P01，暂不关闭。 |
| AC-7 | 支持。管理员可看完整历史，申请人只看本人原因，异主和占用投影不泄露。取消保存真实 actor/前后状态/原因/判时，`Now()` 在此 PostgreSQL 后端独立编译为 `STATEMENT_TIMESTAMP()`。历史和状态同事务提交。 |
| AC-8 | 现有交错和故障证据可信，P02 尚未闭合请求指定的本人取消双序。批准先且未到结束为批准→取消两条历史，取消先批准拒绝，拒绝与取消仅先手转换。F1/F2 实证确认回滚，F3 真实断连未持久化，F4 真实提交后模拟确认丢失且独立可回读。未知均只提示待核查，无自动重试。 |

## 原始回执复算与运行准备

- 首批 `215250-720` 全部 27 个归档散列一致，6 个阶段的原生回执均与分流文件的长度和 SHA-256 一致。回归原生退出 1，原始 unittest 汇总为 `failures=3`（同一个新增方法的三个子例）、1 可选 Chrome 跳过，8 个其他新增方法通过，尚未启动探针。保留首次失败，未改称通过。
- 复验 `220430-872` 全部 35 个归档散列一致，7 阶段原生退出皆 0，stdout/stderr 长度及散列一致。Django 159 项，158 通过、原有可选 Chrome 1 跳过，新增 9 项全通过，既有 150 项中 149 通过，无观察到业务回归。34 个唯一探针名称与末条 `completed` 完全同序。NFR-002 角色拒绝 20 个静态场景加 2 个等锁撤权，22/22；CSRF／非法 14/14 另计，快照和零 SQL 均独立复算。该 14 项没有覆盖 P01，不能据此声称所有非法输入已拦截。
- 两批前后基线 SHA-256 `6EDF380E544390AC1B975BE960C34049EBB73494111DDA3DED12086C259AC7F8`，测试目标 `127.0.0.1:5433/test_lab_booking`、角色 `lab_booking_test`、PG 17.12 Read Committed。结构、19 项迁移、ACL 及被测业务行无差异，夹具和会话清理成功。通过批次的 14 项输入前后一致，其 13 项非文档输入现仍同散列，规格仅有移交更新（本评审记录另行追加）。两开发批的变更只有新测试、探针和规格，不是业务源码。 [失败原件](story-2-8-run-20261128-215250-720/archive.sha256) · [通过原件](story-2-8-run-20261128-220430-872/archive.sha256) · [探针原件](story-2-8-run-20261128-220430-872/probe.jsonl)
- NFR-001 的申请入口、冲突谓词、设备锁、判时机制没变。历史 JSONL 复算 `3364EDF809D5F11C2E865C6608636C6A80FA16736D16C74CA4E1C759D9A7AEC1`，10 轮各 20 个响应、1 成功、19 明确冲突、零异常结果，最终 1 条有效占用且清理成功。复用，不计入本次新增实跑。 [原始历史标准组](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/nfr001-standard.jsonl)
- 运行前静态核对短前缀 17 字符加序号小于设备编号上限 32，SQL 参数化且快照 JOIN 别名限定，原生 `Start-Process -Wait -PassThru` 分写 stdout/stderr，原始重定向在退出后读取、JSONL UTF-8、独占文件 lease。旧取消路径共享详情前缀并不等同详情跳转，已复算匿名/停用 `next` 为原请求路径。此次只读 OS 检查时端口 5433 的监听进程为 postgres PID 6292；不是批次端口证明，实跑由守卫重核库身份和独立后端 PID。新沙箱实测仅 `python.exe --version` 原生退出 103，stdout SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`、stderr `903CED2C52453CEC236FBF288D2377DB2DF46A1A3098D28EEE1219C3A8B619C8`，未连接数据库。普通 PowerShell 执行现有入口，整改后只跑一次，不替换解释器。

```powershell
$runner = 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\run-story-2-8-isolated.ps1'
$out = (New-Item -ItemType Directory -Path (Join-Path (Split-Path -Parent $runner) ('story-2-8-independent-recheck-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')))).FullName
$proc = Start-Process -FilePath "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"{0}"' -f $runner)) -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $out 'batch.stdout.txt') -RedirectStandardError (Join-Path $out 'batch.stderr.txt')
$proc.ExitCode | Set-Content -LiteralPath (Join-Path $out 'batch.exit.txt') -Encoding UTF8
Get-Content -LiteralPath (Join-Path $out 'batch.stdout.txt') -Encoding UTF8
if ($proc.ExitCode -ne 0) { throw "Exit $($proc.ExitCode) — $out" }
```

命令只在整改候选就绪时执行。确认新目录、外层退出 0、`STORY28_ISOLATED_BATCH_OK`、最终明确登记分母、两项新增必要验证、7 个阶段退出、前后快照与散列。不能把此次版本预检或旧归档冒充独立实跑。不复用旧批次目录。

## 正式库迁移、ACL 和最小运行验证（未执行）

**预计无需 migrate、GRANT 或新增数据库对象。** 新代码使用已有 `reservations_reservation.status` 更新权限、设备锁用既有设备列权限、同列历史 INSERT（含主键回读）及已有历史读取。按 Story 2.6/2.7 [已核验的正式基线](story-2-6-2-7-final-acceptance.md) 和 [已有 ACL 清单](story-2-1-targeted-independent-recheck/d041-authorization-reviewed.sql) 判定，不把隔离库无漂移当作正式当前状态。未来获准时只读回读 19 项迁移、准确列权限、业务前置计数和散列；漂移则停止，不自动迁移／授权。

隔离通过并获准后，选**已存在且有足够结束余量的已批准记录**，优先从单条管理员详情进入确认、检查原因字段及返回目标、只放弃返回，不发取消 POST。若需点击筛选列表，先按同一查询范围清点 `pending` 至安全截止；有到期风险即不打开列表。无安全正例时只用已验证终态样本看无取消入口，记录正式正例未覆盖，由隔离证据承接。可配匿名 302、非管理员 403，不以守卫拒绝冒充应用拒绝。复用既有 W01 SQL 防写／HTTP 守卫，阻断业务 DML、迁移和所有业务 POST，允许必要会话技术写；使用空闲 loopback 端口，核对 HTTP 就绪 PID、守卫日志和 Windows 启动器父子关系，活日志共享读。前后独立比对预约、设备、历史和 ACL，保留脱敏汇总、退出码和输入散列，不新增、取消或触发 FR-018 写入；不采集真实账号凭证或原表单正文。 [已验证守卫方案参考](story-2-4-minimal-formal-run.md)

## 独立层逐项裁决（先裁决，再归并）

| 原始 ID／视角 | Verdict | 裁决证据与归并 |
| --- | --- | --- |
| 01 Blind | medium | 原始查询未严验，Django 容错值可通过字段校验并到达事务。P01。 |
| 02 Blind | low | 未知结果只有原筛选返回，已取消行可能被筛掉；清除筛选仍可查，不违反 AC-8。D01。 |
| 03 Blind | low | 空白分支的精确规则有 9 个子例，真实等锁跨界已单独覆盖。拒绝为本次再加一个交叉组合，用现有双层证据。 |
| 04 Blind | low | 历史 approved 会进入既有 `snapshot().effective`，该字段是用于时段重叠的候选，不能替代历史／当前占用页面。AC-3 证据依赖锁后判时、无 DML、原状态与历史不变，不依赖该页面；占用展示已有 Story 2.2 回归，拒绝在本轮重做共享投影和探针。 |
| 05 Blind | low | 详情全文可由历史行满足命中，实际主状态仍可在原件核对，尚非产品故障。D02。 |
| 06 Blind | low | 未到期待审核未与维修/停用做全交叉，代码确实不读取设备状态取舍取消。既有已批准正例及待审核边界保留。D03。 |
| 07 Blind | medium | 运行入口写死原检出位置，另一检出可能测到错误工作树；当前运行位置与硬编码一致。D04。 |
| 08 Blind | low | 预检强制 Chrome 二进制存在，尽管单项测试可跳过；当前指定机器已找到安装。D05。 |
| 09 Blind | medium | 输入散列未列脚本及几个复用辅助文件，跨环境封装证据可能遗漏差异。当前辅助文件无相对基线变更。D06。 |
| 10 Blind | low | 外层脚本只检查 JSONL 行数等，唯一性和清单未设自动门禁。当前原件已独立复算 34 个唯一场景并与清单一致。D07。 |
| 11 Edge | medium | 原始查询未严格校验，同触发同影响。P01。 |
| 12 Edge | low | 详情历史可代替当前状态全文命中。D02。 |
| 13 Edge | medium | 多工作树可能执行原 F: 检出。D04。 |
| 14 Edge | medium | 运行器及复用探针依赖未进入源清单。D06。 |
| 15 Verification | low | 已批准进行中直接 POST 有证据，列表及详情的取消链接缺专项正例；当前链接条件正确。D08。 |
| 16 Verification | low | 现有断言允许同值，未来把判时复制到记录时间会逃逸；本版确实由数据库另取记录时间。D09。 |
| 17 Acceptance | medium | 畸形查询绕过预期输入闸口；不是角色或 CSRF 绕过。P01。 |
| 18 Acceptance | medium | 缺本人实际取消 POST 的两种锁序。未观察到共用锁被破坏，是必要证据缺口。P02。 |

汇总 **0 decision-needed，2 patch，9 defer，2 rejected**。延期项均属本次 AI 处置建议，未代记人为决定。P01/P02 不延期。未改变 FR、NFR、ADR、Sprint 8/5 或实验 A 原始材料、五项口径和观察截止 C。PPT 第 20～39 页依仓库 [课程基线](../../docs/course-requirements.md) 的可追溯规则核对，原 PPT 未取得；落实独立评审、FR→ADR/PC→AC→测试、真实决策与验收证据、三人审阅，不声称逐页检查原件。后续不提前开发 3.1。
