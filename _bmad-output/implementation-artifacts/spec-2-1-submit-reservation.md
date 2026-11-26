---
title: 'Story 2.1 提交具体设备预约并获得可靠申请结果'
type: 'feature'
created: '2026-11-26'
status: 'done'
route: 'dispatch'
baseline_commit: 'e196aba098771a31eb203be4270b460d5e0aab42'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-1-checkpoint-1.md'
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-1-remediation-handoff.md'
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-1-review-disposition.md'
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-1-independent-verification/review-checkpoint.md'
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-1-dev-evidence.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/course-requirements.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 师生可看设备，但不能提交具体设备预约并得到可靠结果。

**Approach:** 详情页进入预约表单。成功提交即建立一条待审核占用并返回本人结果链接。按编号查询仅本人可用，并按需收尾。

## Boundaries & Constraints

**Always:** 正式 AC-1～AC-11 见 `epics.md` Story 2.1。先认证授权，设备行锁，独立重读和复核，再一次 `clock_timestamp()`。提交只收尾目标设备到期的待审，查询只收尾固定的本人目标。历史与状态同事务。全量回归和实测 20×10。

**Never:** 不信任请求申请人或时区，不预做列表、日期占用、审批、取消、状态转换；不重试未知结果，不碰未单独批准的正式库，不改 Sprint，不自动提交或推送。

## I/O & Edge-Case Matrix

| 场景 | 输入 / 状态 | 输出 | 错误口径 |
|---|---|---|---|
| 申请 | 师生、可用设备、北京时间合法且无冲突 | 201 确认及记录编号 | 时间 400，不可用或冲突 409，文案区分 |
| 越权 | 管理员、匿名、他人结果、伪造申请人、无效 CSRF | 拒绝或只认当前账号 | 无泄露和副作用 |
| 收尾 | 到期待审，或收尾后业务拒绝 | 已失效及恰一系统历史提交 | 数据库确认失败整体回滚，未知待核查 |

</frozen-after-approval>

## Code Map

- `accounts/models.py`、`equipment/services.py`：复用角色、账号锁后复核、单设备锁与事务错误分类。
- `lab_booking/settings.py`、`lab_booking/postgresql/base.py`：保留 D-024 和实际连接防护。
- `lab_booking/test_runner.py`、`equipment/management/commands/verify_equipment_edit_transactions.py`：保留回滚测试入口，独立连接另设隔离探针。

## Tasks & Acceptance

**Execution:**

- [x] `reservations/models.py`、`audit/models.py` 和各 `migrations/0001_initial.py` — 预约、审核状态与严格单对象 FK/CHECK。注册至 `lab_booking/settings.py`。
- [x] `reservations/services.py`、`audit/services.py` — 提交、最小本人读取、原子失效。仅抽取 `lab_booking/transactions.py` 共用错误分类，保留设备行为。
- [x] `reservations/forms.py`、`views.py`、`urls.py` 及模板 — 北京时间输入和清晰结果。接入 `lab_booking/urls.py`、`equipment/views.py` 及详情模板。
- [x] `reservations/tests.py`、`reservations/management/commands/verify_reservation_transactions.py` — 表内边界、授权成对、真实 HTTP 竞争及分组探针。
- [x] `_bmad-output/implementation-artifacts/verify-story-2-1.ps1` — 本机隔离验证、原始证据及 AC 对照。正式库迁移和最小权限仅提案，见检查点。

**Acceptance Criteria:**

- 给定锁等待，当跨开始后才判定则拒绝。给定判定在开始前，当提交跨界仍可成功。事务后由独立观察连接核对占用及历史（AC-4、AC-6～10）。
- 给定每轮无冲突的真实隔离夹具，当 20 独立授权请求同屏障竞争，十轮各 1 成功、19 明确冲突且只有 1 条有效待审核占用。逐轮保存连接和重叠证据（AC-11）。其余逐项判定以正式 AC 和检查点矩阵为准。

### Review Findings

BMAD 6.12.4 `full` Step 4。四层原始裁决为 0 Decision、18 Patch、1 Defer、3 Rejected。负责人依据 D-039 选择方案 2，P01～P03 为开放行动项，P04～P18 条件性延期，D01 仍待核实，驳回保留。0 项修复。 [原裁决与证据](story-2-1-independent-verification/review-checkpoint.md) · [人工处置](story-2-1-review-disposition.md) · [一次性交接](story-2-1-remediation-handoff.md)

- [x] [Review][Patch] P01 拒绝后整点纠正可能被原生表单拦截（Medium，必修实现） [reservations/forms.py:5–6] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Patch] P02 同角色本人范围缺少成对拒绝验证（Medium，必补正式证据） [reservations/management/commands/verify_reservation_transactions.py:670] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Patch] P03 I7 未用新增同一所有人的候选挑战固定范围（Medium，必补正式证据） [reservations/management/commands/verify_reservation_transactions.py:591–619] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Defer] P04 SQL 采样断言未完全冻结锁与业务语句顺序（Medium，非阻塞测试加固） [reservations/management/commands/verify_reservation_transactions.py:338–351] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P05 多条同设备到期预约与后续历史插入失败缺少组合验证（Medium，非阻塞测试加固） [reservations/tests.py:245–270] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P06 写失效历史的本人 GET 未覆盖确认失败／未知（Medium，非阻塞测试加固） [reservations/management/commands/verify_reservation_transactions.py:717–758] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P07 权限探针未断言拒绝响应的全部字段与实际跳转（Low，非阻塞测试加固） [reservations/management/commands/verify_reservation_transactions.py:676–688] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P08 成功页和本人页的全部可见字段未逐一冻结（Low，非阻塞测试加固） [reservations/tests.py:143–162] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P09 不可用与冲突的 409 断言复用生产常量（Low，非阻塞测试加固） [reservations/tests.py:199–219] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P10 偏移与秒级非法值的 POST 覆盖不足（Low，非阻塞测试加固） [reservations/tests.py:61–70] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P11 历史记录时间测试未区分业务判定时刻和实际写入时刻（Low，非阻塞测试加固） [audit/services.py:22–23] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P12 续跑白名单可跳过改动过的已复用断言（Medium，非阻塞证据工具） [_bmad-output/implementation-artifacts/verify-story-2-1.ps1:102–122] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P13 续跑门槛可仅凭成功标记接受不完整 JSONL（Medium，非阻塞证据工具） [_bmad-output/implementation-artifacts/verify-story-2-1.ps1:122–143] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P14 未知结果缺少可安全关联的服务端操作诊断（Low，非阻塞可运维性） [reservations/services.py:99–102] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P15 本人结果 GET 的待核查文案误称重复提交（Low，非阻塞文案） [reservations/views.py:69–70] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P16 截断 HTTP 响应没有被保留为单请求证据（Low，非阻塞证据工具） [reservations/management/commands/verify_reservation_transactions.py:264–270] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P17 迁移阶段退出零不能单独区分实际应用与 no-op（Low，非阻塞证据表述） [_bmad-output/implementation-artifacts/verify-story-2-1.ps1:196–215] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] P18 现有基线并非定义及权限的全量 schema 指纹（Low，非阻塞证据表述） [reservations/management/commands/verify_reservation_transactions.py:821–849] — deferred: D-039 条件性延期，未修复或关闭。理由、风险及节点见 [逐项处置](story-2-1-review-disposition.md#p04p18-条件性延期)。
- [x] [Review][Defer] D01 终态读取与同请求内账号撤权竞态（Medium，未核实） [reservations/services.py:135–146] — deferred: 先取认证完成、独立撤权、无设备写锁的终态读取和权限可见性的固定交错证据，再裁决。

#### Rejected

- #5 `maybe-false`。设备 FK 索引已存在，无有害负载或延迟证据，不引入优化需求。
- #14 `low`。初始表单 GET 在 DB 读取异常时通用 500，不是 AC-9 的事务结果。低频单独错误流程不作为本轮修补。
- #16 `low`。极少见且限隔离工具，基线守卫会探测和停止，不扩展清理扫描。



#### 2026-11-26 整改后针对性独立复审（BMAD 6.12.4 full）

四视角已回报，0 Decision、10 Patch、1 Defer、4 Rejected。均为测试／证据工具项目，无 High 或已观察到的正式业务回归。独立离线复核不等于独立运行，普通 PowerShell 收据及 Step 4 人工处置待回。P01～P03 不勾作独立验收通过。 [复审检查点](story-2-1-targeted-independent-recheck/review-checkpoint.md) · [原回报及逐条裁决](story-2-1-targeted-independent-recheck/review-triage.md)

- [x] [Review][Defer] R01 本人正例校验目标及各次快照（低） [reservations/management/commands/verify_reservation_transactions.py:849–855] — deferred: D-040 已延期、未关闭。已有独立比对与实际主体加固；首读中间快照待统一本人读取探针。
- [x] [Review][Patch] R02 I7 固定候选完整重读及绑定断言必须在锁后唯一取时前（中） [reservations/management/commands/verify_reservation_transactions.py:643–652] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Defer] R03 I7 冻结设备与未收尾候选字段（低） [reservations/management/commands/verify_reservation_transactions.py:653–665] — deferred: D-040 已延期、未关闭。保留候选关键字段比对；全字段冻结在下次维护 I7 夹具时补。
- [x] [Review][Defer] R04 归档批次版本与清理证据自动关联（中，本轮已独立离线核实，非重跑标准组要求） [_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:129–141] — deferred: D-040 已延期、未关闭。本次归档链已独立复核；自动归档来源绑定留验证工具维护。
- [x] [Review][Defer] R05 区分主测试与清理／最终校验失败（中） [_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:224–242] — deferred: D-040 已延期、未关闭。外层记录退出码与 stderr；双失败分别保存留工具维护。
- [x] [Review][Patch] R06 P02 的两条拒绝 trace 断言没有业务 DML（中） [reservations/management/commands/verify_reservation_transactions.py:838–846] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Patch] R07 P02 对应 404 应关联实际鉴权主体，并验证活跃学生请求同角色异主（中） [reservations/management/commands/verify_reservation_transactions.py:292,822–845] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Defer] R08 fresh 开关仅依赖实际沿用的历史批次（低） [_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:129,150,205,236] — deferred: D-040 已延期、未关闭。本次不使用可选重跑开关；归档再生耦合留相关维护。
- [x] [Review][Defer] R09 I7 明确冻结响应的单目标最小投影（低） [reservations/management/commands/verify_reservation_transactions.py:640–642] — deferred: D-040 已延期、未关闭。本轮独立审计已有单目标投影断言；下沉通用探针留工具统一。
- [x] [Review][Patch] R10 两条 P02 404 同时断言没有 Location（低） [reservations/management/commands/verify_reservation_transactions.py:268,836–846] — 已关闭（负责人 D-041，D-040 独立证据通过）。
- [x] [Review][Defer] RD01 不同验证入口共享隔离库 lease（低） [_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1:146] — deferred: 历史多入口协调问题，现有同入口锁及前后摘要拒绝混跑的结果。在统一验证入口前不并跑。非首轮 D01。

**Rejected**

- #04 `low`。现有五导航 400/201 特征 DOM、点击、快照交叉一致，不为未见的同 URL 关联误配扩展 CDP。
- #05 `false`。正式交接允许用可选开关重跑，未要求全量独立重复。当前用户授权有条件复用。
- #11 `maybe-false`，若为真影响低。未观察到 DevTools 端口先于 page target 的真实失败。保留复现条件，不扩展启动协议。
- #12 `maybe-false`，若为真影响低。未见网络事件不间断且命令无回复的实际路径。保留复现条件，不扩大变更。


### D-039 集中整改续接（本次唯一执行范围）

之前完成的 Story 2.1 主体与全部正式 AC 不重做。仅下面三项与必要验证工具。P04～P18、D01、Story 2.2 均不变。

- [x] **P01** 在 reservations/forms.py 最小调整步进（推荐两个 datetime-local 用 step="any"，以免回显的任意分秒成为整点提交的步进基准），保留页面现有说明及服务端全部校验。增加 Django 条件回归与真实 Chrome 验证。在动态的北京未来日期，对真实隔离 HTTP 先提交非整点、收到 400 回显，再在同一页面修正，用浏览器正常提交按钮获 201，并读回本人结果及独立数据库状态。只在第一次非法请求允许测试绕过原生校验，第二次不绕过。
- [x] **P02** 在 reservations/management/commands/verify_reservation_transactions.py 的 permissions 组补同角色乙访问甲的 404、不泄露、不写入及独立状态指纹，另留甲的 FR-018 正例。用真实活跃账号及鉴权链。保留已有 12 项、记新真实分母，不改权限业务逻辑。
- [x] **P03** 在同一命令的 interleavings/I7 组，实际等锁后以独立事务新增同一学生的到期待审，保留原异主与终态控制，报告候选身份、阻塞 PID、加入时序和独立末态；不改变真实查询业务逻辑。保证重复读取不追加，禁止 sleep 冒充真实等锁。
- [x] **仅本轮验证**。保持既有版本、守卫、隔离库及零夹具残留，保留真实原始输出和分母。不能连接正式 DB。原 .venv 已知在沙箱退出 103，不要重复失败，用经过核查的普通 PowerShell 单次入口。写不进源码时，按当前整改前工作树生成 P01～P03 增量补丁并进行只读适用预检；不重放 Story 全量补丁。NFR、故障、整点按改变的实际路径核对，不因单纯表单和隔离测试分支改动重等整点。旧原始证据只读。父执行者在获得实际运行证据前不得勾选或同步到 review。

## Implementation Notes

- 2026-11-26：负责人按 D-038 批准实施和集中验证设计。规格和 Sprint 已按实际进度进入 `in-progress`。
- 2026-11-26：首次实施时业务源码修改受限，改用[本 Story 增量补丁](story-2-1-implementation.patch)。补丁预检及基线副本应用成功，静态语法核对通过；当时原项目解释器在沙箱退出 103，未取得运行证据。
- 2026-11-26：团队随后在普通 PowerShell 应用补丁并取得隔离库实测。首次 I1 的 SQL 探针漏采 Django 带列别名的账号重读；仅修正探针和定向续跑工具。原失败、修复和成功复验均已留档。未变更业务实现和冻结矩阵。 [开发证据](story-2-1-dev-evidence.md)
- 2026-11-26：核对工作树差异（含未跟踪实现）、原始日志及正式 AC-1～AC-11 / R-04 / T-01～T-04 的本 Story 范围，确认冻结矩阵三行均有实际通过用例。根据本轮授权，规格进入 `in-review`、Sprint 进入 `review`。独立 `bmad-code-review` 尚未执行，本规格不标 `done`。 [复验矩阵与交接](story-2-1-dev-evidence.md#2026-11-26-复验核验与独立评审交接)

- 2026-11-26：已落盘 P01 原生时间控件步进修复，以及 P01 Chrome、P02 同角色拒绝、P03 同一申请人 I7 实际交错探针。原项目 .venv 沙箱已知 103，不重复尝试；静态核对完成，开发实际自测仍为 0，待普通 PowerShell 回执，保持规格与 Sprint in-progress。 [整改证据及运行入口](story-2-1-remediation-evidence.md)

- 2026-11-26 20:08 整改实跑收据经离线核验，P01～P03 通过开发自测。新运行 Django 91/91（0 跳过）、师生导航 1/1、Chrome 纠错 1/1、未授权 13/13、交错 15/15（含扩展 I7）。历史 NFR-001 200 响应、故障 5/5、真实北京 18:00 同路径证据复用，不计新测试。Step 3 实际取证门槛满足，实施规格 in-review／Sprint review，交原独立 Code Review。 [整改回执](story-2-1-remediation-evidence.md) · [针对性复审交接](story-2-1-remediation-review-handoff.md)

## Spec Change Log

## Review Triage Log

- 2026-11-26：负责人 D-039 实际选择「保留为行动项」。P01～P03 开放并交原 Build 集中整改，P04～P18 条件性延期，D01 仍未核实。保留原拒绝与开发证据，独立运行 0 项，整改后另开独立复验。不改冻结标准。 [人工处置](story-2-1-review-disposition.md) · [一次性交接](story-2-1-remediation-handoff.md)

- 2026-11-26 · D-040。负责人明确选「2 保留为行动项」并限定最小证据闭环。R02/R06/R07/R10 继续开放，仅补 I7 的固定范围绑定及取时顺序、P02 同一 404 实际认证主体与无业务 DML/Location。R01/R03/R04/R05/R08/R09 批准延期，均未关闭。P01 既有代码不改，独立实跑验收后再关闭。首轮延期与驳回保持。Step 4 按行动项推进回 `in-progress`，本轮独立实跑未取得，不虚填通过。 [负责人处置及 Build 交接](story-2-1-targeted-independent-recheck/d040-disposition-build-handoff.md)


- 2026-11-26 · D-040 事后复审。团队于 20:52～20:53 在普通 PowerShell 一次实跑，独立评审在当前会话读取原始回执并只读复算，全阶段 0。Django 91/91 零跳过、师生导航 1/1、真实 Chrome 1/1、权限 13/13、交错 15/15。P02 同一请求的实际主体、无 DML／Location 及本人对照齐全，I7 固定目标锁后重读、唯一时钟与绑定闭环。P01～P03、R02/R06/R07/R10 的技术复验通过，**建议关闭**，不代表负责人最终验收。旧历史 NFR-001、故障及 18:00 复用不计新运行，首轮与 D-040 延期仍保持，台账写入受限未冒充合并。按当前条件授权规格 in-review／Sprint review，无新增阻塞，不标 done。 [独立复审收尾](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)


## Design Notes

采用预约和设备两个可空真实外键，加非空类型及精确匹配约束。仅写入预约系统失效历史，不增加设备状态服务。使用半开区间，不另建占用表。

## Verification

**Commands:**

- `manage.py check`、`makemigrations --check --dry-run` — 检查通过且无漂移。
- `manage.py test --keepdb --parallel 1 -v 2` 及专项探针 — 只连隔离库，逐阶段原始输出、退出码、明确分母、前后数据及输入散列齐全。

**Actual results:** 原两条迁移、Django 90/90（零跳过）、R-04 和未授权 12/12 有效；复验交错 15/15、故障 5/5、标准竞争 10/10（200 条真请求）、真实 B3/B4 及 B4 回读全部达标。样本仅覆盖当前入口，不提前关闭未来 Story 或全项目 NFR-002。 [原阶段日志](story-2-1-run-20261126-171347-146-27af94f2/stages.txt) · [交错](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173530-191-df47c547/interleavings.jsonl) · [余项退出码](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/stages.txt)


**D-042 最终验收。** 条件已获真实证据验证，负责人验收通过。P01～P03 与 R02/R06/R07/R10 的 D-041 关闭不变。中央延期已合并且逐段复核。正式库只迁移、授权与受控验证已批准范围，不启动后续 Story。 [最终验收](story-2-1-final-acceptance.md) · [运行记录](story-2-1-runtime-evidence.md)
