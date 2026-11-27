# Story 2.3 最终验收

**2026-11-27（北京时间），项目负责人正式批准「查询本人全部预约及处理结果」最终验收通过。** BMAD 6.12.4 Build Step 5 收尾。实施规格和 Sprint Story 2.3 均为 `done`。Epic 2 保持 `in-progress`，Story 2.5 保持 `backlog`。 [D-048](../../decision-log.md#d-048-2026-11-27-负责人最终验收-story-23) · [实施规格](spec-2-3-query-own-reservations.md) · [Sprint 状态](sprint-status.yaml)

## 正式运行、失败和负责人确认

- 原批次学生 #1 从本人列表触发 FR-018，原预约仅从 `pending` 变为 `expired`，恰好新增一条系统历史（ID 1）。后续两次列表读取均无重复写入。前置 #1 已不构成有效占用，后置仍不占用，不记作 `1 → 0`。原 Finish 因教师计划新增一条而实际零条失败，失败快照保留。后续首次教师 POST 因时段不符在写入前被守卫拒绝，未重放。 [原学生请求](story-2-3-formal-runtime-evidence/original-smoke/browser-http.jsonl) · [原 Finish 错误](story-2-3-formal-runtime-evidence/original-smoke/finish-failed/demo-after-catalog.stderr.txt) · [教师 403 前置拒绝证据](story-2-3-formal-runtime-evidence/teacher-readonly/source-review.json)
- 16:49:11–16:51:16 的只读补证共 16 条请求，5 项 Finish 机器断言通过。正式预约、历史、设备和非会话账号字段前后散列一致。无新增预约，无学生请求。匿名 302 沿用原证。负责人在本会话实际确认教师异主及不存在详情均为 404，管理员身份页无「我的预约」，直访预约列表为 403。两个 404 的机器响应体散列一致。以上是负责人对实际体验的确认，不推断各成员分别操作或发表意见。 [自动归档](story-2-3-formal-runtime-evidence/teacher-readonly/post-8a49872cb2be/chrome-receipt.md) · [Finish 明细](story-2-3-formal-runtime-evidence/teacher-readonly/post-8a49872cb2be/result.json)
- **正式 Chrome 未执行教师本人详情，教师预约未取得 201。** 正式库没有可复用教师预约，教师空列表实际返回 200。负责人明确接受这一现场样本局限，以已有隔离环境实测支持教师本人功能验收。本结论不将隔离结果或原 403 冒充正式 Chrome 成功。 [隔离 AC-1／AC-6／AC-7](story-2-3-independent-recheck.md#ac-1ac-8-本次逐项核对) · [正式库后置](story-2-3-formal-runtime-evidence/teacher-readonly/post-8a49872cb2be/current-db.json)

## 功能验收与 W1

正式 AC-1～AC-8 均以真实独立实测支持。AC-1／2 核对本人五态、列表／详情和设备当前状态。AC-3 核对本人授权原因的来源、转义及不泄露。AC-4／5 核对边界、一次历史、固定候选、锁序与一次时钟。AC-6／7 核对归属、空态、同形 404 和候选冻结。AC-8 核对实际 PostgreSQL 故障下的回滚及未知提交反馈。独立复验为 **113/113 Django、零跳过、15/15 PostgreSQL 探针**，保留四视角独立评审和已批准的处置。NFR-001 沿用 D-040 的历史标准竞争证据，不重跑、不计作本批新测。 [正式 AC](../planning-artifacts/epics.md#story-23-查询本人全部预约及处理结果) · [独立复验](story-2-3-independent-recheck.md) · [四视角评审](story-2-3-independent-review.md)

**W1 关闭。** 原正式批次仅增加获准的 `reservation_id`、`action`、`actor_type`、`reason` 四列 SELECT，保留原 `id` 读取权。最终正式前后独立核验均为精确矩阵，无表级 SELECT、无转授、无迁移漂移。授权成功、首次后置工具误报及随后精确读回均保留，不重复授权。中央延期台账仅关闭 W1，P01～P08 和 W2 保持开放，原九项驳回不变。 [授权及运行索引](story-2-3-formal-runtime-evidence/README.md) · [最终 ACL](story-2-3-formal-runtime-evidence/teacher-readonly/post-8a49872cb2be/app-acl.stdout.txt) · [中央延期台账](deferred-work.md)

第 25、26 页保留已定架构依赖、Story、FR-002／009／015／018 与 ADR／PC、AC、测试的可追溯链。第 27 页在独立评审和负责人实际验收后更新 `done`。第 33 页保留 Git 可追溯源码及证据，第 34 页不改实验 A 或 Sprint 8／5 的安排，第 36 页记录实际决定及后验依据。不重跑测试，不新增预约，不更改已核验业务源码，不推进 2.5。 [课程基线](../../docs/course-requirements.md)
