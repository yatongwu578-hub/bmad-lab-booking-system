# Story 2.2 最终验收

**2026-11-27（北京时间），负责人按正式 AC-1～AC-8 批准最终验收。** 实施规格和 Sprint Story 2.2 为 `done`，Epic 2 保持 `in-progress`，2.3 及其他未开始 Story 保持 `backlog`。本次只做证据与状态收尾，不改业务代码，不重跑测试。 [D-045](../../decision-log.md#d-045-2026-11-27-负责人最终验收-story-22) · [实施规格](spec-2-2-query-equipment-occupancy.md) · [Sprint 状态](sprint-status.yaml)

## 正式运行与实际体验

团队在本机实际体验设备指定日期的占用查询并确认正常。负责人据此前服务日志补充的顺序为首次登录 POST **302**、身份页 **200**、重复登录 POST **CSRF 403**，之后恢复正常使用。这是负责人对日志和操作的补述，不是本次会话读取原始访问日志。实际体验角色、所选日期、占用结果细节、查询响应码及具体恢复步骤未留存，不补写为三角色浏览器测试、不认定查询一定用建议空日，也不推断 CSRF 根因。 [正式浏览器体验记录](story-2-2-runtime-experience.md)

前置和后置 READ ONLY 阶段分别于 00:09:18、00:17:46 退出 0，均有各自唯一成功标记。以 `lab_booking_app`、PostgreSQL 17.12、Read Committed 核验正式目标。设备 1 的设备摘要、两条预约摘要和历史 ID 集合前后一致。ACL 前后均为 ready，有效权限矩阵、显式 ACL 以及列、索引、约束和标识序列与 D-042 只读记录匹配。现有 `reservations.0001_initial`、`audit.0001_initial` 经正式读回核对，无迁移、GRANT 或正式业务写入由本验收会话执行。登录会话不计入预约业务快照。 [阶段退出码](story-2-2-runtime-20261127-000918-77eb9198/stages.txt) · [前置](story-2-2-runtime-20261127-000918-77eb9198/runtime-readonly-before.json) · [后置](story-2-2-runtime-20261127-000918-77eb9198/runtime-readonly-after.json) · [ACL](story-2-2-runtime-20261127-000918-77eb9198/acl.jsonl) · [模式证据](story-2-2-runtime-20261127-000918-77eb9198/schema.jsonl)

## 正式验收依据

| AC | 验收结论 |
| --- | --- |
| AC-1 | 北京时间日期和设备筛选正确。10:30 正在进行的已批准区间仍占用，恰到结束后保留历史、不再显示为当前占用。 |
| AC-2 | 包括已结束的到期待审按需失效，释放占用并追加系统历史；重复查询不重复追加，已批准不误改。 |
| AC-3 | 仅必要设备加锁，锁后复核权限并重读固定 ID，独立采样唯一 `t_decision`。无待审无额外写锁。 |
| AC-4 | 真实提交交错证明并发新增不进本次结果，下次纳入；过期夹具也不在首次越界收尾。 |
| AC-5 | 隔离环境三角色详情入口和查询通过，投影不泄露详情。匿名、停用和锁等待中撤权均无未授权业务副作用。 |
| AC-6 | 空日返回 200，缺失或无效日期 400，设备不存在 404；错误输入不扫描预约或写入业务数据。 |
| AC-7 | 设备状态、日期占用与最终可否预约分开。真实交错出现查空 200、他人提交 201、随后重叠提交 409。 |
| AC-8 | 真实历史写入失败与 COMMIT 拒绝共同回滚。断连与已提交后模拟丢确认均返回待核查，不臆断或重试。 |

开发原始批次和独立隔离复验各自保存 **103/103 Django、零跳过、21/21 PostgreSQL 探针、11 阶段均退出 0** 和清理前后等值基线。正式体验是烟测，不代替隔离完整矩阵。NFR-001 的 D-040 历史标准竞争仍是已经独立核验的 20 请求 × 10 轮，不做重跑，不把旧结果计作新增测试。 [开发实证](story-2-2-dev-evidence.md) · [独立复验与原始索引](story-2-2-independent-recheck.md) · [原 NFR-001 核验](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

## 评审处置与课程留证

D-044 四视角原裁决 0 Decision、6 Patch、1 Defer、13 Rejected。六项非阻塞待办保持开放，原 Low D1 和 RD01 不关闭，13 项不采纳不改。已核对中央延期台账和待合并原文，七项逐项一致且仅追加一次，历史前缀未改。独立复验的 P1 注入前绑定不冒充实际执行绑定。 [四视角独立评审](story-2-2-independent-review.md) · [逐项裁决](story-2-2-review-triage.md) · [原人工处置](story-2-2-review-disposition.md) · [中央延期台账](deferred-work.md)

第 25 页的 Story 验收字段、第 26 页的 FR→ADR／PC→AC→证据、第 27 页的实际 Sprint 状态流转及独立评审、第 33 页的可追溯产物、第 34 页的实验 A 隔离、第 36 页的真实人机决策均按仓库课程基线与已有团队记录收尾，不声称逐页复核 PPT 原件。保持 Sprint 8／5 和实验 A 候选安排，三人共同操作及审阅，不代填个人验收。 [课程基线](../../docs/course-requirements.md) · [Sprint 计划](../planning-artifacts/sprint-plan.md)
