---
title: 'Story 2.4 本人取消预约'
type: 'feature'
created: '2026-11-27'
status: 'done'
route: 'dispatch'
baseline_commit: '33ff1eb86a1101db5033a4232a121a08d66a4c03'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-4-checkpoint-1.md'
---

<frozen-after-approval reason="人工批准后冻结">

## Intent

学生和教师从「我的预约」确认并取消本人尚未开始的预约，释放占用，保留原记录和历史。

## Boundaries & Constraints

以正式 2.4 AC-1～8 为准。只做本人取消，不做管理员操作、设备转换、原因采集或整体美化。沿用显式 Read Committed，只在 `127.0.0.1:5433/test_lab_booking` 测试，不碰正式库。

## I/O & Edge-Case Matrix

| 锁后最新状态 | `t_decision < start` | `t_decision >= start` |
| --- | --- | --- |
| 待审核 | 取消、释放、本人历史 | 拒绝取消，按 FR-018 失效并提交系统历史 |
| 已批准 | 取消、释放、本人历史 | 拒绝，不失效 |
| 已拒绝／已取消／已失效 | 拒绝，无转换 | 拒绝，无转换 |

设备维修或停用不阻止合法本人取消。到开始时刻已不是开始前。

</frozen-after-approval>

## Code Map

- `reservations/services.py` 复用 `require_applicant`、`_recheck_applicant`、`_decision_time`、`_expire`、`_durable_operation`。共享机制保持不变。
- `equipment/services.py::lock_equipment` 为唯一互斥点。复用 `audit/services.py` 的追加模式和既有模型，不改查询、占用或申请算法。

## Tasks & Acceptance

- [x] `reservations/services.py` 按本人范围查目标设备，短事务内锁设备、复核账号、重读本人目标，再取一次数据库时钟。仅对目标调用失效或更新状态并追加历史。确认 GET 单独只读。
- [x] `audit/services.py` 追加取消历史，记录真实申请账号、原状态、目标和两种时间，不改既有失效历史。
- [x] `reservations/{urls,views}.py` 和 `reservations/templates/reservations/{list,result,cancel}.html` 接入确认 GET 与 CSRF POST，提供返回、结果及两类数据库异常反馈。
- [x] `reservations/test_own_cancellation.py`、`reservations/management/commands/verify_own_cancellation.py`、`_bmad-output/implementation-artifacts/verify-story-2-4.ps1` 按检查点矩阵实现验证，复用隔离探针和归档。

- AC-1 给定开始前的本人待审或批准预约，提交后取消并释放占用，保留原记录身份及时段。
- AC-2 给定任一锁后状态，取时后严格执行上表，不以设备状态替代开始边界。
- AC-3 给定无权或非法请求，直访时拒绝且无泄露、无业务变化。
- AC-4 给定请求等锁或提交跨界，执行时仅锁后取时一次，持锁至提交。
- AC-5 给定合法取消，提交时状态与恰一条本人历史同事务可见。
- AC-6 给定到期待审，处理时业务拒绝仍提交失效与恰一条系统历史，重复零写。
- AC-7 给定申请、查询、取消或失效竞争同一设备，交错后符合锁序和实际先后，无重复转换或占用。
- AC-8 给定数据库异常，响应区分已确认回滚与结果待核查，均不报成功、不自动重试。

### Review Findings

2026-11-28，北京时间。BMAD 6.12.4 full 四视角初裁为 0 decision-needed、14 patch（1 阻塞，13 非阻塞）、1 defer、1 rejected。负责人按 D-055 选择「保留为行动项」，M01 开放并交回原 Build，P01～P13 条件延期，D01/R01 原裁决不变。Defer 的勾选表示已记录处置，不表示修复或关闭。尚未整改、独立实跑或验收。 [独立评审](story-2-4-independent-review.md) · [人工处置](story-2-4-review-disposition.md)

- [x] [Review][Patch] M01（原 High，AC-3 阻塞，D-056 已关闭）POST 表单解析失败或内容被丢弃时错误放行，可触发本人取消或目标到期失效。已收窄原生表单格式，验证解析不完整时先拒绝，V01-M01 零业务 SQL、写入或历史 [reservations/views.py:153] · [整改后独立复验](story-2-4-m01-independent-run-result.md)
- [x] [Review][Defer] P01（Medium，原 Patch）交付时把冻结规格、检查点及校验过的 125 项基线账本一并收录 [verify-story-2-4.ps1:38] — 延至交付包复现核对。
- [x] [Review][Defer] P02（Medium，原 Patch）前置只读 SQL 失败时避免声称取消事务已回滚，保留未知提交的独立反馈 [reservations/views.py:179] — 延至错误反馈维护。
- [x] [Review][Defer] P03（Low，原 Patch）管理员详情断言精确定位实际取消历史行 [reservations/management/commands/verify_own_cancellation.py:176] — 延至历史展示/回归维护。
- [x] [Review][Defer] P04（Low，原 Patch）A06 断言非目标预约全字段不变 [reservations/management/commands/verify_own_cancellation.py:189] — 延至失效探针维护。
- [x] [Review][Defer] P05（Low，原 Patch）V01 增补带有效 CSRF 的重复业务字段负例 [reservations/management/commands/verify_own_cancellation.py:278] — 延至输入矩阵维护，M01 必需的负例不延。
- [x] [Review][Defer] P06（Low，原 Patch）分别断言 I02 时段冲突及 I03 终态拒绝的业务原因 [reservations/management/commands/verify_own_cancellation.py:356] — 延至并发探针维护。
- [x] [Review][Defer] P07（Low，原 Patch）验证查询只按实际候选集合及顺序锁定设备 [reservations/management/commands/verify_own_cancellation.py:400] — 延至共用锁范围的下次验证。
- [x] [Review][Defer] P08（Low，原 Patch）Chrome 自动取证补请求方法并对照实际取消 POST 次数 [reservations/management/commands/verify_own_cancellation.py:571] — 延至浏览器取证维护。
- [x] [Review][Defer] P09（Low，原 Patch）用实际 SQL 绑定断言目标、归属、原状态及历史时点 [reservations/management/commands/verify_own_cancellation.py:109] — 延至 SQL 证据维护。
- [x] [Review][Defer] P10（Low，原 Patch）补有效 CSRF 的 POST 查询串和文件输入负例 [reservations/test_own_cancellation.py:146] — 延至输入矩阵维护，M01 直接相关的媒体类型覆盖不延。
- [x] [Review][Defer] P11（Low，原 Patch）补确认 GET 的前置读错误端到端断言 [reservations/services.py:232] — 延至读取故障测试维护。
- [x] [Review][Defer] P12（Low，原 Patch）锁定终态记录自己的详情及旧 201 中不显示取消链接 [reservations/templates/reservations/result.html:22] — 延至页面回归维护。
- [x] [Review][Defer] P13（Low，原 Patch）P08 自动化同时断言拒绝响应无受限字段或对象链接 [reservations/management/commands/verify_own_cancellation.py:308] — 延至权限回归维护。
- [x] [Review][Defer] D01（Medium）直接管理命令与历史验证器的共享隔离库串行 [reservations/management/commands/verify_own_cancellation.py:639] — deferred: 既有 2.5-D02 根因，普通 PowerShell 包装内串行有效，统一验证租约时一并解决。

#### Rejected

- R01（Low）真实跨界五秒夹具窗口在慢机器可能耗尽。当前四条都有成功原证，窗口耗尽会明确失败，新增自动重跑和参数控制的复杂度不值得。

## Implementation Notes

- 2026-11-28，按 D-055 仅落实 M01。本人取消入口校验原始 URL 编码确认表单与完整性，保留 Django CSRF 及业务权限／事务。已有验证器新增专项模式，真实回执待普通 PowerShell，规格和看板保持 `in-progress`。 [M01 开发专项交接](story-2-4-m01-development-handoff.md)

- 2026-11-28，团队普通 PowerShell 的 M01 实测经复算为 5/5 Django、V01-M01 和 Chrome 两组通过、8 阶段退出 0、91 项输入一致及隔离清理通过。按本轮有条件授权，规格 `in-review`、Sprint `review`，交回原独立评审会话。M01 不提前关闭，待针对性复审及一次新版完整隔离复验。 [真实专项与完整复验交接](story-2-4-m01-code-review-return.md)

- D-054 批准后实现本人取消。复用原 `lock_equipment`、`_recheck_applicant`、`_decision_time`、`_expire`、`_durable_operation` 和既有数据模型。确认 GET 不收尾，授权 POST 只写目标；未改申请竞争核心、迁移、角色或正式库。
- 团队普通 PowerShell 开发批次实际通过 125 个既有同名测试、8 个新增 Django、16 组 PostgreSQL／HTTP／Chrome 探针，8 阶段退出 0，91 项输入相等，隔离业务、ACL、迁移基线和夹具清理通过。测试运行时的规格独立封存。此批是开发实测，不是独立 Code Review。 [开发证据](story-2-4-development-evidence.md) · [原始回执](story-2-4-dev-run-20261127-234701/verified-receipt.json)

## Spec Change Log

## Review Triage Log

- 2026-11-28，D-055。正式 Step 4 处置已记录，规格和看板只退回 2.4 为 `in-progress`。M01 是唯一阻塞整改项，未修复。P01～P13 与原 D01 已在[中央台账](deferred-work.md)唯一跟踪，R01 保留原理由。保留整改前开发原证，待[原 Build 整改交接](story-2-4-remediation-handoff.md)完成后统一独立复验。
- 2026-11-28，原评审会话在 M01 开发回交后完成[针对性独立复审](story-2-4-m01-independent-recheck.md)。静态请求闸口与开发原证支持整改，未发现新阻塞，进入一次完整独立隔离复验。M01 保持开放，状态和延期不变。开发专项不算独立实跑，正式最小方案在独立复验通过后准备。
- 2026-11-28，D-056。整改后独立 PowerShell 批次的原证经复算支持 AC-1～AC-8，依负责人条件授权只关闭 M01。P01～P13、D01、R01 不变，规格 `in-review` 与 Sprint `review` 保留，待正式阶段。 [独立复验与处置](story-2-4-m01-independent-run-result.md) · [最小正式运行方案（未执行）](story-2-4-minimal-formal-run.md)

## Verification

按检查点执行既有 125 项同名回归与新增用例、真实 PostgreSQL 交错及 Chrome。没有迁移或授权增量。仅当核心机制不变且旧证据有效时复用 NFR-001 标准组。真实自测通过后才转 review，独立 Code Review 另开会话。

- **开发验证通过。** 精确等时由通过的受控 Django 测试验证，真实锁等待跨开始和判定先于开始而提交跨界分别由 I08/I09 验证。逐例状态、历史、权限分母、故障和浏览器证据见[开发矩阵](story-2-4-development-evidence.md)。无新标准竞争重跑，正式库发布前读回未执行。
- **整改后独立隔离验证通过。** 135/135 Django、零跳过，17/17 PostgreSQL／HTTP／Chrome 探针，8 个原生阶段退出 0、唯一成功标记、91 项输入、三份库基线和夹具清理均核对。Story 2.4 权限 16/16，M01 格式 20、补充 CSRF 4 单列；历史 NFR-001 不重跑。 [独立回执](story-2-4-independent-run-20261128-094455/verified-receipt.json)

- **正式最小运行与最终验收通过（D-057）。** 原外层 EXIT=1 源于两个合法归属查找 404 的汇总误报。27 个正式文档与 ACL、迁移及库前后读回均有实际原证；离线复核通过且未重跑，M01 维持关闭，其他延期不变。 [最终验收与恢复](story-2-4-final-acceptance.md)
