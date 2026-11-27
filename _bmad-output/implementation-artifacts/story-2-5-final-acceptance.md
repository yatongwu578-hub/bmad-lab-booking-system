# Story 2.5 最终验收 · D-052

**2026-11-27（北京时间），项目负责人有条件批准最终验收，归档核对确认条件满足。** Story 与实施规格为 done，W01 已关闭，M01 保持关闭。Epic 2 仍为 in-progress，未开始 Sprint 2。 [决定](../../decision-log.md#d-052-2026-11-27-负责人最终验收-story-25) · [规格](spec-2-5-admin-reservation-query.md)

## 正式运行与权限

- 22:31 正式库仅为 lab_booking_app 补上历史表实际缺少的 actor_id、before_status、after_status、decision_at、recorded_at 五列 SELECT，psql 退出 0，STORY25_W01_GRANT_COMMITTED，独立读回精确。首次排序误报未提交，编码和 Windows 活日志失败及整改均有原证。 [恢复记录](story-2-5-w01-recovery-evidence.md) · [编码整改](story-2-5-w01-log-encoding-evidence.md)
- 22:40:03～22:40:42 正式恢复跳过授权。前置、启动前及后置只读确认十列有效 SELECT，无整表 SELECT、无转授权。四组业务摘要及有效／显式 ACL 一致，预约 2、设备 2、历史 1、账号 3。登录／退出的会话技术写不算业务写入。没有新增预约或迁移。
- 37 条 Chrome／服务端文档逐项配对。匿名管理入口 3 次 302，师生各 3 次 403，均无受限信息或业务 SQL；管理员管理路径 7 次 200，涵盖全量、筛选、详情、历史和返回。用已有 #1、#2，不为取证新增样本。已验证路径为 http://127.0.0.1:8005/reservations/manage/，服务验后停止，非持续访问链接。现场只有待审核和已失效，其他终态与故障使用独立隔离证据。
- 17 个阶段退出 0，含四角色、正常停止、后置与最终比对。唯一 STORY25_W01_FORMAL_OK 和终态 complete exit=0 均实存。没有单独归档的外层控制台退出码，不代填。94 项输入前后及关账前实算一致。 [正式回执](story-2-5-w01-final-evidence/verified-receipt.json) · [阶段退出码](story-2-5-w01-final-evidence/stages.txt)

## 正式 AC 与证据

| AC | 验收依据 |
| --- | --- |
| 1 | 正式管理员入口、列表、详情、当前状态；隔离覆盖五种状态、申请人、北京时间。 |
| 2 | 正式 #2 设备筛选；隔离验证受影响范围、结束边界和无关设备不写。 |
| 3 | 隔离验证固定候选、必要设备升序锁、锁后复核和单一判定时刻。 |
| 4 | 隔离实测申请先／查询先两种交错，并发新增下次纳入。 |
| 5 | 正式全量、筛选及返回；隔离验证历史、终态、已结束记录不误隐藏。 |
| 6 | 正式列级权限和 #1 持久历史；隔离覆盖历史类型、双时点与幂等。 |
| 7 | 正式匿名 302、师生 403、管理员合法对照；隔离 20 次初始拒绝及 1 次等锁撤权。 |
| 8 | 隔离空结果、非法输入、404、M01 五个 400 无副作用，及真实事务失败、明确拒绝提交和未知提交结果。 |

独立 5/5 专项、125/125 Django、17/17 PostgreSQL 及 M01 原证保留，未重复运行。首次 124/125 的导航断言失败及整改保留。 [正式 Story](../planning-artifacts/epics.md) · [独立逐 AC](story-2-5-m01-independent-run-result.md) · [首次回归失败](story-2-5-regression-remediation.md) · [延期台账](deferred-work.md)
