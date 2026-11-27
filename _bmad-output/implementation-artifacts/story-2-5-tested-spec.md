---
title: 'Story 2.5 管理员查询预约详情并按设备筛选'
type: 'feature'
created: '2026-11-27'
status: 'in-progress'
route: 'dispatch'
baseline_commit: '1cedf9687208b20645b1acce3c7755e8525cd9fc'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-5-checkpoint-1.md'
---

<frozen-after-approval reason="人工确认的实施意图">

## Intent

让业务管理员从身份页进入「预约管理」，查询全部预约、查看单条详情及实际转换历史，或按具体设备编号筛选受影响预约。

## Boundaries & Constraints

以 `epics.md` 正式 AC-1～8 为准。先授权，固定候选，按需失效。仅开发 2.5，不加处理按钮、其他操作、审计模块或统一美化。只在隔离库开发和测试。正式授权和运行另批。Sprint 8／5、实验 A 不变。

## I/O & Edge-Case Matrix

| 输入 | 结果 |
| --- | --- |
| 有效条件无匹配 | 200 明确空态，不回退全量 |
| 筛选格式错误、合法编号不存在、详情不存在 | 分别 400、200 空态、404；无业务副作用 |
| 匿名、非业务管理员 | 登录跳转或 403，无受限信息 |
| 确认回滚、提交未知 | 不同 503 文案，均无成功结果，不自动重试 |

</frozen-after-approval>

## Code Map

- `reservations/services.py` 复用 `_durable_operation`、`_decision_time`、`_expire`、`RESULT_FIELDS`；参考 `_read_own_reservations` 与 `get_daily_occupancy`，不改旧路径或核心协议。
- `equipment/services.py` 复用 `lock_equipment`，原管理员谓词与 `accounts/policies.py` 共享；`audit/services.py` 保留旧原因投影和失效追加。

## Tasks & Acceptance

- [x] `accounts/{policies,views}.py`、`accounts/templates/accounts/identity.html` 落实角色策略及入口；`equipment/services.py` 保留原谓词接口和行为。
- [x] `audit/services.py` 为结果集合批量读取适用原因，为授权详情精确读取已有转换历史。
- [x] `reservations/services.py` 实现列表、设备筛选和详情。先查数据库有效角色再冻结，锁后复核并重读，单次取时后收尾、筛选和投影，提交后返回。
- [x] `reservations/{forms,views,urls}.py`、`reservations/templates/reservations/admin_{list,detail}.html` 接入 GET、表单、双状态、详情及返回路径。
- [ ] `reservations/test_admin_reservations.py`、`reservations/management/commands/verify_admin_reservations.py`、`_bmad-output/implementation-artifacts/verify-story-2-5.ps1` 覆盖下列 AC 和异常矩阵，复用现有验证器模式。

- AC-1／5 给定多设备、五态和多申请人，查全量或详情时保留终态及已结束记录，呈现申请人、设备、北京时间时段、双状态和适用原因；清楚区别筛选与全量。
- AC-2 给定目标设备，筛选时先检查含已结束待审的固定候选，仅返回未到开始的待审和 `end_at > t_decision` 的已批准，两类均须未结束。
- AC-3／4 给定固定候选或并发新增，仅锁待审候选涉及设备，去重升序，锁后按固定 ID 和原限定重读；无待审不锁，筛选仍取唯一时刻；新增留待下次。
- AC-6 给定持久转换，授权详情展示原预约、实际执行者、动作、前后状态、记录及判定两种时刻和适用原因；历史投影只读，系统与人工分离，无虚构记录。
- AC-7 给定非管理员或锁后撤权，请求不返回业务信息、不触发失效或写入；初始未授权不取业务锁。
- AC-8 给定边界输入或事务故障，按矩阵返回；确认失败整体回滚，未知不承诺持久性。

## Implementation Notes

- 2026-11-27，用户在当前会话回复「批准并继续」，规格从 `draft` 经 `ready-for-dev` 进入 `in-progress`，看板仅同步 2.5。上述勾选只表示代码已落盘，不表示 AC 实测通过。管理员导航、服务、投影、模板和验证入口已落盘。沙箱拒绝 `equipment/services.py` 写入，现有管理员谓词接入共享策略的单文件补丁可应用检查通过，尚未应用。
- 已准备 12 个 Django 测试及 17 个独立 PostgreSQL／实际 HTTP 探针。沙箱批次在原 `.venv` Python 预检停止，尚未连接测试库或运行用例。不进入 BMAD Step 4，不变更正式库。 [验证交接](story-2-5-verification-handoff.md)
- 2026-11-27，团队在普通 PowerShell 实际应用共享权限补丁，隔离预检通过。125 项 Django 中 124 项通过，12 项 2.5 用例和 40 项设备用例全通过。唯一失败为 Story 2.3 导航断言把管理员路由公共前缀当作本人入口。已校正同名测试并补充双方导航和直接访问断言。新验证入口一次串行完成针对性、全量和探针。本会话的原解释器仍报 `103`，整改后的实测回执待取得，规格／Sprint 维持 `in-progress`。 [故障证据和复验命令](story-2-5-regression-remediation.md)

## Spec Change Log

## Review Triage Log

## Design Notes

读取字段、精确列级授权、并发交错和开发／独立／正式取证分界见同目录检查点。正式 GRANT 不属于本次批准。

## Verification

运行 `verify-story-2-5.ps1`，以现有 113 项名称、新增断言和真实 PostgreSQL 探针为准。退出码、原始证据和清理全通过后才进 `review`，另开会话独立评审。
