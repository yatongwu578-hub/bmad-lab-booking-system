---
title: 'Story 2.4 本人取消预约'
type: 'feature'
created: '2026-11-27'
status: 'in-progress'
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

- [ ] `reservations/services.py` 按本人范围查目标设备，短事务内锁设备、复核账号、重读本人目标，再取一次数据库时钟。仅对目标调用失效或更新状态并追加历史。确认 GET 单独只读。
- [ ] `audit/services.py` 追加取消历史，记录真实申请账号、原状态、目标和两种时间，不改既有失效历史。
- [ ] `reservations/{urls,views}.py` 和 `reservations/templates/reservations/{list,result,cancel}.html` 接入确认 GET 与 CSRF POST，提供返回、结果及两类数据库异常反馈。
- [ ] `reservations/test_own_cancellation.py`、`reservations/management/commands/verify_own_cancellation.py`、`_bmad-output/implementation-artifacts/verify-story-2-4.ps1` 按检查点矩阵实现验证，复用隔离探针和归档。

- AC-1 给定开始前的本人待审或批准预约，提交后取消并释放占用，保留原记录身份及时段。
- AC-2 给定任一锁后状态，取时后严格执行上表，不以设备状态替代开始边界。
- AC-3 给定无权或非法请求，直访时拒绝且无泄露、无业务变化。
- AC-4 给定请求等锁或提交跨界，执行时仅锁后取时一次，持锁至提交。
- AC-5 给定合法取消，提交时状态与恰一条本人历史同事务可见。
- AC-6 给定到期待审，处理时业务拒绝仍提交失效与恰一条系统历史，重复零写。
- AC-7 给定申请、查询、取消或失效竞争同一设备，交错后符合锁序和实际先后，无重复转换或占用。
- AC-8 给定数据库异常，响应区分已确认回滚与结果待核查，均不报成功、不自动重试。

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

按检查点执行既有 125 项同名回归与新增用例、真实 PostgreSQL 交错及 Chrome。没有迁移或授权增量。仅当核心机制不变且旧证据有效时复用 NFR-001 标准组。真实自测通过后才转 review，独立 Code Review 另开会话。
