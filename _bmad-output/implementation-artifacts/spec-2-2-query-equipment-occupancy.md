---
title: 'Story 2.2 查询具体设备在指定日期的占用时段'
type: 'feature'
created: '2026-11-26'
status: 'done'
route: 'dispatch'
baseline_commit: '930d3cb1c6ce02a934a93295b850c9109165dcf1'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-2-checkpoint-1.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 设备详情无法查询指定日期占用。
**Approach:** 三类业务用户从详情选择北京时间日期，查看占用、历史区间和未被占用时段。

## Boundaries & Constraints

**Always:** 以 `epics.md` Story 2.2 AC-1～AC-8 为准。先授权，再以设备和北京时间自然日交集固定候选 ID。不漏未到点或已结束待审。有待审才锁目标设备，复核账号、独立重读固定 ID 和设备，再独立取一次数据库时钟。失效与历史原子提交后再渲染。
**Never:** 不扩入并发新增、不泄露身份或详情、不保证可预约、不新增状态、迁移、授权、定时任务或后续故事。不访问正式库，不自动提交 Git。

## I/O & Edge-Case Matrix

| 场景 | 输入 | 结果 |
|---|---|---|
| 查询 | 登录三角色、设备、日期 | GET 200。区分已占用、无有效占用、设备状态 |
| 拒绝 | 匿名、无效日期、设备不存在 | 登录跳转、400、404。无业务副作用 |
| 异常 | 确认失败或提交未知 | 503。分别提示未成功或待核查，无成功占用结果 |

</frozen-after-approval>

## Code Map

- `reservations/services.py` 复用 `BEIJING`、`_decision_time`、`_expire`、`_durable_operation`。不改提交或本人结果行为。
- `equipment/services.py` 复用 `lock_equipment` 与目录读取口径。账号复核读 `is_active`、`role`，允许三业务角色，不复用师生专用申请判定。
- `audit/services.py` 继承系统历史。保持 D-024、模型、连接守卫及最小列权限。

## Tasks & Acceptance

- [x] `reservations/services.py` 加定日查询。锁后和无锁分支均限固定 ID，仅返回区间和展示类别。
- [x] `reservations/forms.py`、`views.py`、`urls.py`、`templates/reservations/occupancy.html` 接入严格日期校验与查询结果。
- [x] `equipment/views.py`、`templates/equipment/detail.html` 给三角色提供日期表单，并保留原导航。
- [x] `reservations/test_occupancy.py` 覆盖正式八条 AC。独立验证命令与 PowerShell 入口按检查点实施真实交错、故障及回归。

**Acceptance Criteria:** 正式八条 AC 不改。给定 10～11 点已批准预约，当查询采样为 10:30，显示进行中，11:00 起仍保留历史区间但不再算当前或未来占用。给定同区间仍待审，当取时达到 10:00，仅失效一次并留系统历史。给定固定候选后插入，当查询返回，本次排除，下次纳入，后续提交仍查冲突。逐项矩阵见检查点。

### Review Findings

BMAD 6.12.4 full，四视角均返回。原裁决为 0 Decision，6 Patch，1 Defer，13 Rejected。未发现正式 AC 的产品阻塞。负责人在 D-044 选择 2，批准以下 P1～P6 保留为未勾选的非阻塞延期行动项，原 D1 及不采纳依据不变。新独立隔离运行待执行，不是最终验收。 [处理记录](story-2-2-review-disposition.md) · [完整复核](story-2-2-independent-review.md) · [逐条裁决](story-2-2-review-triage.md)

- [ ] [Review][Patch] P1（Medium，取证）第二次审计插入的日志区分注入前与实际执行绑定 [reservations/management/commands/verify_equipment_occupancy.py:75]。实际 SQLSTATE 23514、两个写入尝试与独立前后快照支持整体回滚，原绑定不作为实际执行值。
- [ ] [Review][Patch] P2（Low，取证）通过前后状态比较后再写清理成功记录 [reservations/management/commands/verify_equipment_occupancy.py:569]。本次清理已独立复算，未受此问题影响。
- [ ] [Review][Patch] P3（Low，工具）前后清单独立枚举输入路径 [verify-story-2-2.ps1:42]。本轮外层入口对新批次额外核对当前文件集合，不重写开发脚本。
- [ ] [Review][Patch] P4（Low，覆盖）验证由实际详情日期表单产生的 GET 请求与结果 [reservations/test_occupancy.py:173]。现有产品行为一致，真实 Chrome 操作留正式烟测落证。
- [ ] [Review][Patch] P5（Low，覆盖）同一天历史区间和当前占用的精确补集 [reservations/test_occupancy.py:53]。
- [ ] [Review][Patch] P6（Low，覆盖）在历史及未占用区间的实际 HTML 中断言时段 [reservations/test_occupancy.py:84]。
- [x] [Review][Defer] D1（Low）旧入口与本入口无全覆盖共享租约 [verify-story-2-2.ps1:109] — deferred: 已登记 RD01，统一工具时再处理，同一隔离库不并跑。

#### Rejected

- #1 low。获批 GET 的预取残余仅能使已到期待审合法收尾，未见未登录访问或提前释放，不扩大协议。
- #2 low。重复参数取末项确实存在，正式 AC 没有新增参数基数规则，原生表单不生成歧义。
- #3 false。当前 Role 只含明确的三种角色，无额外角色获权。
- #4 false。正式预约规则拒绝非整点及非零秒和微秒，合法申请不会形成亚秒占用。
- #5 low。只在认证后的并发撤权边缘产生不存在与复核拒绝的差异，不返回占用或触发写入，不新增强一致撤权协议。
- #6 low。纯投影计算持锁，但模板渲染不持锁，未触犯正确性或正式时限约束。
- #7 low。缺少脱敏诊断关联号是运维增强，已保留既有 P14，不改本入口异常语义。
- #13 low。重复日期按单一有效末项处理，不改变正式输入约定。
- #14 low。既有短事务设备锁协议无此路由专用等待上限，没有相应 SLA，不新增异常分支。
- #15 false。亚秒间隔不是有效正式预约所能产生的数据。
- #20 low。重复值的请求形态不属于已定义的非法日期用例，不扩范围。
- #21 low。D-043 已批准 GET，保留受控的授权按需失效；不宣称防跨站触发全覆盖，也未发现跨站读取或越权写。
- #24 low。投影不在响应前绕过提交，当前无需拆分事务。

## Implementation Notes

- 2026-11-26，负责人批准并开始实施，见 [D-043](../../decision-log.md#d-043-2026-11-26-负责人批准-story-22-checkpoint-1)。
- 查询、结果和测试代码已写入。设备详情存在源码写入限制，补丁已在副本验证。在原普通 PowerShell 应用补丁并实跑 [验证交接](story-2-2-verification-handoff.md) 后，按证据关闭对应任务。现阶段不进入 review。
- 2026-11-26，团队已完整应用补丁并实际完成验证。本会话核验 103/103 Django（原 91 加新 12，零跳过）、21/21 真实隔离探针、清理和 AC-1～AC-8，冻结矩阵三行均有实际通过的用例。规格进入 `in-review`，Sprint 进入 `review`。本阶段不等同独立评审或最终验收。 [开发证据与评审交接](story-2-2-dev-evidence.md)

## Spec Change Log

## Review Triage Log

- 2026-11-26 D-044，负责人选择 2，接受四视角和裁决。P1～P6 未修复，保留待办并批准延期，D1 和 13 条不采纳不变。P1 的第二次 INSERT 注入前绑定不代表实际执行值。实际 SQLSTATE 23514 和独立前后读回支持 AC-8 的原子回滚，不以原采样冒充执行取证。按 Step 4 同步为 `in-progress`，待一次隔离独立复验。无需先整改或重跑 NFR-001。 [理由、风险、后续节点及验证交接](story-2-2-review-disposition.md)
- 2026-11-26，负责人报告团队已在普通 PowerShell 执行现有独立入口，评审会话只读核验新批。103/103、零跳过、21/21 探针、11 个退出 0 阶段、79 份输入与清理均通过。正式 AC-1～AC-8 通过，未发现新增阻塞。规格与 Sprint 重新进入 `in-review`／`review`，仍未最终验收。D-044 原延期保留，NFR-001 历史 20×10 原证据复用。 [独立复验收尾](story-2-2-independent-recheck.md) · [正式运行交接](story-2-2-runtime-handoff.md)

- 2026-11-27，D-045 最终验收。正式前后只读回执通过，负责人确认实际体验及 CSRF 403 后恢复。中央台账与原七项延期逐项一致。P1～P6 仍开放，D1、RD01 和 13 项不采纳不改。 [最终验收](story-2-2-final-acceptance.md) · [中央延期台账](deferred-work.md)

## Design Notes

北京自然日用 `[日首, 次日日首)`。无占用区间取当日已占用及历史区间的补集。历史与仍有效结果分标，区间不可推导可预约。无待审无写锁，仍以一次数据库时钟区分批准区间。

## Verification

只用 `127.0.0.1:5433/test_lab_booking`。原 .venv 全量 91 项及新增用例零跳过，真实隔离交错、权限和异常按检查点验收。若 2.1 核心不变，复用其已独立核实的 20×10 标准竞争，不计作本轮新结果。

实际批次、逐 AC 测试与证据入口见 [开发验证](story-2-2-dev-evidence.md#补丁与实际运行)。
