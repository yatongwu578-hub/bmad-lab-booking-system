---
title: 'Story 2.3 查询本人全部预约及处理结果'
type: 'feature'
created: '2026-11-27'
status: 'in-progress'
route: 'dispatch'
baseline_commit: 'c4912cb911ffeccbd4a8cfefa0b7eaaf26dab64d'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-3-checkpoint-1.md'
---

<frozen-after-approval reason="human-owned intent">

## Intent

师生目前只能按编号查看单条结果。补齐「我的预约」列表及详情，保留全部本人历史，显示当前设备状态与经授权的处理原因。

## Boundaries & Constraints

以 epics.md 正式 AC-1～8 为准。登录账号限定本人，不接受外部归属。遵守 FR-018、D-024；复用现有模型、权限和事务。仅隔离 PostgreSQL 测试；正式库新增授权另批。不做取消、管理、审批、拒绝、设备状态维护或统一美化。

## I/O & Edge-Case Matrix

| 场景 | 条件 | 结果 |
| --- | --- | --- |
| 导航 | 师生身份页、预约成功页 | 进入「我的预约」，列表可往返详情；管理员无师生入口 |
| 空与拒绝 | 无本人记录、他人或不存在、匿名或管理员 | 空列表 200；他人同不存在 404；匿名登录跳转、管理员 403 |
| 事务异常 | 确认回滚或提交未知 | 各自 503 文案；不显示旧列表，不重试，不把未知说成回滚 |

</frozen-after-approval>

## Code Map

- `reservations/services.py`：沿用 `require_applicant`、`_recheck_applicant`、`_durable_operation`、`_decision_time`、`_expire` 和 `equipment/services.py::lock_equipment`；参考 `get_daily_occupancy` 冻结候选。不改申请和设备占用路径。
- `audit/services.py`：保留 `append_reservation_expiry`；增加受限原因投影，不查整行。现有历史读权仅 `id`，精确列投影与待审授权详见检查点。
- `reservations/urls.py`、`reservations/views.py`：新增 `reservation-list`，保留 `reservation-result` 原 URL 和成功页 201 契约。

## Tasks & Acceptance

- [x] `reservations/services.py`、`audit/services.py`：统一本人列表和详情的候选限制、排序锁、锁后复核与重读、判定和投影；返回提交后的状态。
- [x] `reservations/views.py`、`reservations/urls.py`、`reservations/templates/reservations/{list,result}.html`：GET 无缓存，展示北京时间和分离的双状态，处理导航、空态与异常。
- [x] `accounts/views.py`、`accounts/templates/accounts/identity.html`：用现有师生角色策略控制入口。
- [ ] `reservations/test_own_reservations.py`、`reservations/management/commands/verify_own_reservations.py`、`_bmad-output/implementation-artifacts/verify-story-2-3.ps1`：执行正式八条 AC、边界矩阵、权限和真实独立连接探针，保留 103 项原回归。

- AC-1 给定本人五态及他人记录，查询列表和详情时，显示本次本人全部记录及完整设备、日期和时段，保留已结束及终态。
- AC-2 给定已批准预约和变动设备，查询时显示设备最新可用／维修／停用状态，预约仍为已批准。
- AC-3 给定关联的拒绝或管理员取消历史，查询时仅显示匹配原因，不显示其他操作历史。
- AC-4 给定待审，查询时早于开始保持；等于或晚于开始（含已结束）持久失效、释放占用并仅追加一次系统历史，其他状态不变。
- AC-5 给定固定本人候选，查询时仅按主键升序锁相关待审设备，锁后复核、重读、取一次数据库时钟并同事务收尾；无待审不加设备写锁。
- AC-6 给定匿名、管理员或其他账号，直访或篡改参数时拒绝或不扩大范围，不泄露、不写；合法本人访问单测。
- AC-7 给定冻结后新增或无匹配，查询时新记录下次才见，空列表或统一 404 按矩阵返回。
- AC-8 给定跨设备收尾发生确认失败或提交未知，返回区分的 503；前者状态及历史一起回滚，后者不推断持久性。

## Implementation Notes

- 主代理复读了 Story 2.3 范围内的新旧差异，前三项为实现交付，最后一项真实测试仍待执行。提交、设备占用、失效写入、判定时钟和事务实现保持原代码。
- 沙箱使用项目原解释器测得退出 `103`。本轮不把静态检查当测试通过，保持 `in-progress`，尚未进入 BMAD Step 4。 [验证交接](story-2-3-verification-handoff.md)

## Spec Change Log

## Review Triage Log

## Verification

普通 PowerShell 先用原 .venv 执行只读预检，批准开发后在 `127.0.0.1:5433/test_lab_booking` 运行独立单批脚本。以检查点的逐例证据、退出码及精确标记为准。完成自测后进入 review，另开会话独立评审。
