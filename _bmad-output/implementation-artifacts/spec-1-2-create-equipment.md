---
title: 'Story 1.2 管理员新增具体设备基础档案'
type: 'feature'
created: '2026-11-25'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '2333c0559a948da5cbf6e91f8a6bd2c630395204'
context: ['{project-root}/docs/course-requirements.md', '{project-root}/_bmad-output/planning-artifacts/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

管理员通过专用表单为具体实物建立唯一编号档案。[正式 AC-1～7](../planning-artifacts/epics.md#story-12-管理员新增具体设备基础档案)是验收基线。追溯 FR-016／002 → ADR-001／002／003／008 → AC → PostgreSQL 与权限测试。NFR-002仅取证本入口。

## Boundaries & Constraints

沿用 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12 及 D-015／016 的三角色分离。编号去首尾空白后判空，保留大小写。仅提供新增与本次成功确认。业务库迁移、授权或数据写入另行审批。测试仅使用 `test_lab_booking`。

**D-024** 负责人批准 Django PostgreSQL `OPTIONS["isolation_level"] = IsolationLevel.READ_COMMITTED`，runtime、migration、test 共用。PostgreSQL 服务器级、数据库级及角色级设置保持原样。

</frozen-after-approval>

## Code Map

- `accounts/models.py` 的 `User.role`、`Role.ADMIN` 和现有启用状态是授权来源。复用 `lab_booking/settings.py` 的认证、会话、CSRF 和 `lab_booking/urls.py` 的登录入口。业务管理员可无 staff 标志。
- `lab_booking/database_config.py` 和 `lab_booking/postgresql/base.py` 已限制连接目标。现有 `lab_booking/test_runner.py` 拒绝 flush，且因已迁移前提与回滚事务，无法单独验证并发提交。
- 三模式变更前的只读实测见 [D-024](../../decision-log.md#d-024-2026-11-25-负责人批准显式-read-committed)。

## Tasks & Acceptance

- [x] `equipment/models.py`、`equipment/migrations/0001_initial.py` 建立档案和具名编号唯一约束。保留独立主键，仅开放新增。业务角色运行权限仍需独立批准。
- [x] `equipment/forms.py`、`equipment/services.py` 校验输入，复查有效业务角色，在最外层短事务插入。事务退出后分类。SQLSTATE 23505 加匹配设备表及编号约束才报重复。提交阶段失联且结果未证实时提示待核查。
- [x] `equipment/views.py`、`equipment/urls.py`、`equipment/templates/equipment/` 和项目设置、路由接入 `/equipment/new/` 的 GET/POST。同次成功响应展示已保存档案。
- [x] `lab_booking/settings.py` 应用 D-024，在三模式核对实际库、角色和事务隔离。
- [x] `equipment/tests.py` 覆盖表单、权限、CSRF 与约束。独立命令 `equipment/management/commands/verify_equipment_transactions.py` 仅接受已迁移 test 模式，核对实际库及角色、独立连接和隔离级别，夹具冲突即停止，执行后精确清理合成数据。保留现有回滚套件。

### D-025 集中整改

- [x] R1、R5 在 `equipment/services.py` 区分写入和提交阶段，可靠确认的约束拒绝或回滚方可报告失败。进入提交路径且无足够结果证据时（含无 SQLSTATE 的数据库连接异常）报告待核查，既不声称失败或成功，也不提示或自动重试。只有已确认对应 PostgreSQL 设备编号唯一约束冲突才报重。保证正常应用调用在最外层事务提交前不返回成功，拒绝普通嵌套和已有手动事务；真实提交以隔离探针取证。必要时同步 `equipment/templates/equipment/create_result.html`。
- [x] R2 在 `equipment/templates/equipment/create_form.html` 显示只读可用状态，保持服务端默认值并忽略伪造状态。
- [x] R3、R4 在 `equipment/views.py` 绑定所有 POST，在 `equipment/forms.py` 保留既有字段约束、首尾去空白和大小写语义。空请求体、缺失、空字符串、空白、超长及非法空字符给出编号字段错误且无新增。移除表单层的查库预判或纳入受控异常边界，保留顺序及并发重号效果。不得新增编号字符规则。
- [x] 针对 R1～R5 在 `equipment/tests.py` 补必需用例，并在原 Python 3.13.17、test 模式和实际 `127.0.0.1:5433/test_lab_booking` 上执行系统检查、迁移差异只读检查和全量回归。复用原评审探针验证 AC-1～AC-7，必要时在实施产物中另存适配入口，保留首轮探针及其失败证据。记录实际响应、PostgreSQL 连接／锁等待、独立读回及一次写入尝试。将结果交开发证据及处置记录，留独立复评。

本次只实现 R1～R5。R6～R11 延期，不改原并发管理命令、正式 AC、数据库配置或业务功能范围。不连接业务库，不执行迁移、授权、commit/push 或 Story 1.3。整改自测完成后 Sprint 停在 `review`，由独立 Code Review 复评。 [D-025](../../decision-log.md#d-025-2026-11-25-负责人批准-story-12-独立评审处置) · [整改交接](story-1-2-remediation-handoff.md) · [首轮独立评审](story-1-2-independent-review.md)

**验收**

1. AC-1 已登录管理员用不存在的 EQ-001 提交有效编号、名称、类别、位置和说明，恰新增一条。重读五项字段、默认可用状态与成功页一致。表单及成功页状态只读，伪造状态输入无效。
2. AC-2 已有 EQ-001，再提交不同资料，明确报重且原记录全部字段不变。
3. AC-3 缺失或空编号，提交时显示字段错误，且无新增或成功页。
4. AC-4 匿名、学生、教师以合法资料直接 GET／POST，各自被拒绝或引导登录，无受限内容，无设备、预约或处理历史写入。管理员合法对照成功。
5. AC-5 已登录管理员提交缺失或无效 CSRF，被拒且无新增。有效令牌对照成功。
6. AC-6 EQ-002 不存在时，两名管理员使用独立连接提交同号。A 已插入未提交时 B 尝试插入，确认有竞争后放行 A 提交，最终一成功、一明确重复，仅赢家记录持久化。
7. AC-7 合法提交遇到已确认事务失败或回滚时，反馈失败且无部分档案。提交前后失联且结果无法确认时，仅反馈待核查，零自动重试。其他数据库错误不得误报编号重复。

### Review Findings

- [x] [Review][Patch] R1（High，阻塞 AC-7）提交断连被报告为明确失败，已提交记录也会触发重试提示。按事务阶段与连接结果分类并复跑真实断连。 [equipment/services.py:33]
- [x] [Review][Patch] R2（Medium，阻塞 AC-1）新增表单缺少只读初始状态。 [equipment/templates/equipment/create_form.html:7]
- [x] [Review][Patch] R3（Medium，阻塞 AC-3）有效 CSRF 下空 POST 不显示编号字段错误。 [equipment/views.py:28]
- [x] [Review][Patch] R4（Medium，批准随 AC-7 整改）表单唯一预查在已处理的事务异常边界之外。 [equipment/views.py:29]
- [x] [Review][Patch] R5（Medium，批准随 AC-7 整改）普通原子块允许嵌套，未保证服务在最外层提交后返回。 [equipment/services.py:33]

负责人依据独立复审于 2026-11-25 正式关闭上述 R1～R5。该决定与 Story 最终验收分别记录。 [D-026](../../decision-log.md#d-026-2026-11-25-负责人关闭-r1r5-并批准-story-12-业务库验证)
- [x] [Review][Defer] R6（Medium，测试工具）原命令未观察真实阻塞。独立探针已补齐 AC-6，延至下一次整理并发测试入口。 [equipment/management/commands/verify_equipment_transactions.py:50]
- [x] [Review][Defer] R7（Medium，测试工具）原命令固定夹具可能跨运行清理，清理后未核验零残留。原命令并行或自动化前处理。 [equipment/management/commands/verify_equipment_transactions.py:39]
- [x] [Review][Defer] R8（Medium，回归测试）原权限用例未检查两个方法的拒绝正文。独立探针已逐例验证，延至 T-03 权限回归整理。 [equipment/tests.py:64]
- [x] [Review][Defer] R9（Medium，测试工具）Future 超时后 executor 仍可等待数据库 worker。原命令进入无人值守流程前处理。 [equipment/management/commands/verify_equipment_transactions.py:74]
- [x] [Review][Defer] R10（Medium，回归测试）原 CSRF 用例缺错配令牌及拒绝后即时验库。独立探针已验证，延至 CSRF 回归整理。 [equipment/tests.py:79]
- [x] [Review][Defer] R11（Medium，回归测试）原成功测试未逐项比较数据库值与提交值。独立探针已验证，延至设备档案回归用例整理。 [equipment/tests.py:33]

延期项的勾选表示负责人已记录处置，技术状态仍为延期未修复。见[首轮独立评审证据](story-1-2-independent-review.md)、[负责人处置](story-1-2-review-disposition.md)及[延期台账](deferred-work.md)。

#### Rejected

无。

### 整改后独立复审发现

- [x] [Review][Defer] F4 原探针打印回滚约束诊断，自动断言尚未核对诊断值。独立复审已人工核对本次 `23514 equipment_status_valid`，延至探针断言整理。 [story-1-2-remediation-transaction-probe.py:272]
- [x] [Review][Defer] F5 原探针在丢确认场景自动断言持久化行数并输出完整行。独立复审已对照本次行内容，延至探针断言整理。 [story-1-2-remediation-transaction-probe.py:311]
- [x] [Review][Defer] F10 提交阶段其他明确拒绝的分类尚未证实存在当前可达偏差。若新增延期约束、提交回调或复现新的明确 COMMIT 拒绝，按真实响应补查。 [equipment/services.py:54]

F8 沿用已批准的 R9，F3、F9 已通过额外独立运行补证。无新增验收阻塞。R1～R5 建议关闭，保留负责人处置及验收确认。 [逐项裁决、独立测试与业务库计划](story-1-2-independent-recheck.md)

#### 整改后复审 Rejected

- F1，当前入口无 pipeline 或提交回调，已确认成功后的连接处于 IDLE，恢复 autocommit 不发额外 SQL。
- F2，当前 INSERT 后无吞掉 SQL 错误的回调，提出的静默回滚路径不成立。
- F6，专用隔离库串行运行，保留全表比较以捕捉无关记录上的业务副作用。
- F7，实际复测使用普通解释器并观察到真实故障结果，优化模式加固不属于本轮执行条件。

## Implementation Notes

- 2026-11-25，按 D-025 完成 R1～R5 开发整改。使用无数据库预查的表单、Django 最外层原子事务和提交阶段异常分类。已完成 45 项 Django 回归及真实 PostgreSQL 探针。 [开发证据](story-1-2-dev-evidence.md#整改后实测)

## Spec Change Log

## Review Triage Log

- 2026-11-25，负责人选择 BMAD Step 4 方案 2。R1～R5 交原开发会话一次性整改，R6～R11 批准延期。Step 4 将规格和 Sprint 跟踪同步为 `in-progress`。5 项待整改、6 项延期、0 项修复、0 项驳回。 [D-025](../../decision-log.md#d-025-2026-11-25-负责人批准-story-12-独立评审处置) · [一次性整改任务](story-1-2-remediation-handoff.md)
- 2026-11-25，R1～R5 已实现并通过开发自测，待独立复评。R6～R11 的延期决定沿用原记录，首轮评审发现的勾选状态留给独立复评处理。规格进入 `in-review`，Sprint 进入 `review`。 [开发整改交回](story-1-2-review-disposition.md#2026-11-25-开发整改交回)
- 2026-11-25，整改后四视角独立复审和 45/45 全量回归已完成，正式 AC-1～AC-7 在隔离环境通过。R1～R5 建议关闭，业务库迁移、实际运行及最终验收仍待批准。按本轮授权保留评审状态。 [复审证据](story-1-2-independent-recheck.md)
- 2026-11-25，负责人接受独立复审并正式关闭 R1～R5。已按批准范围完成单项迁移、设备列级授权与三角色 Chrome 运行验证，保留一条获准课程演示档案。规格保持 `in-review`，Sprint 保持 `review`，等待负责人最终批准。 [业务库证据](story-1-2-runtime-evidence.md)

- 2026-11-25，负责人依据已有独立验证和业务库运行证据批准最终验收。规格及 Sprint 中 Story 1.2 更新为 `done`。R6～R11 继续延期，第二台 Windows 待复现。 [最终验收](story-1-2-final-acceptance.md)

## Verification

- 在 test 模式运行 `check`、`makemigrations --check --dry-run` 和 `test --keepdb --parallel 1`，另运行事务验证命令。先核对测试库迁移、角色与前后业务数据。测试库迁移单独核对目标及计划。
- 按 T-01 保留 AC-6 交错证据，按 T-03 登记实际路由，未授权六例逐一断言拒绝、无泄露、无业务变化，合法及 CSRF 对照分别计数。AC-7 区分真实回滚和提交前后故障注入，并用独立连接核对持久化。
- 将实际结果记录到 `story-1-2-dev-evidence.md`。R-04、T-02、T-04 按后续既定节点，实验 A 条件沿用 Sprint 计划。开发自测后进入 `review`，交新会话独立评审。

首次开发自测交接时，AC-7 尚缺真实断连证据。首轮独立评审已补取证并复现失败。D-025 整改后的开发自测与独立复审均已通过真实故障探针。首轮失败、开发通过及独立复审通过证据分开保留。 [首次独立 PostgreSQL 证据](story-1-2-independent-review.md#postgresql-时序记录) · [整改后实测](story-1-2-dev-evidence.md#整改后实测) · [整改复审](story-1-2-independent-recheck.md)
