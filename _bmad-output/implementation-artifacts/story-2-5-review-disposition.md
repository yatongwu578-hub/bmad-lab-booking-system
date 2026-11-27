# Story 2.5 · BMAD 6.12.4 Step 4 人工处置

2026-11-27（北京时间）。项目负责人在本会话明确选择 **2「保留为行动项」**，并批准下列集中处置。只记录这次实际负责人决定，不代签其他成员，不作最终验收。三位组员共同操作和审阅。 [D-050](../../decision-log.md#d-050-2026-11-27-负责人批准-story-25-独立评审处置) · [逐项裁决](story-2-5-review-triage.md) · [原始四视角](story-2-5-review-raw.md)

| 事项 | 严重程度及处置 |
| --- | --- |
| M01 | Medium，阻塞 AC-8。唯一必修，交回原 `bmad-build` 会话。保持开放，整改后一次集中独立复验。 |
| P01～P12 | 原 Patch 候选，确认当前不影响正式 AC、安全性或数据一致性，负责人批准条件延期。原编号、严重程度、理由、残余风险和后续节点均保留，未修复或关闭。出现影响上述范围的新事实时复判。 |
| D01～D05 | 原 Defer 保留。不重编号，不把与既有 RD01 等共用根因重复当作独立缺陷。按原节点跟踪，未关闭。 |
| 原始 01、04、12 | 三项驳回按原编号和证据保留。未重新裁决。 |
| W01 | High，正式发布门槛，不延期。整改后的独立复验通过后，再按正式运行角色当次有效／显式权限核对，另行批准历史表五列 SELECT 的实际缺量。独立评审和本处置不授予正式库访问或 GRANT。 |

依据正式工作流 Step 4，将实施规格从 `in-review`、Sprint Story 从 `review` 同步退回 `in-progress`，其他 Story、Epic 和 Sprint 8／5 不变。保留实验 A，未启动 Sprint 2。批准的 17 条延期已追加到中央台账，原前缀字节保留，逐项唯一，安全读回再次识别为已存在。中央台账不登记 M01 或 W01 为延期。 [实施规格](spec-2-5-admin-reservation-query.md#review-findings) · [Sprint 状态](sprint-status.yaml) · [中央台账](deferred-work.md) · [机器合并回执](story-2-5-review-support/deferred-merge-receipt.txt)

开发通过的 5/5 专项、125/125 Django、17/17 PostgreSQL 探针，以及首次 124/125 失败与导航整改证据原样保留。它们属于开发执行，已由评审离线复算，不计作整改后新测试。已独立核验有效的 NFR-001 标准竞争仍为 20 请求 × 10 轮，不重复。当前不跑整改前测试，也无整改后新回执。 [开发证据](story-2-5-dev-evidence.md) · [首次失败与整改](story-2-5-regression-remediation.md) · [NFR-001 历史复核](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

只更新处置、交接和台账。未修改业务代码、执行迁移、连接业务库、GRANT、标 `done`、暂存、提交或推送。PPT 第 25／26／27／33／34／36 页的对应依据沿用课程基线和已有团队核对，记录真实决定与后验依据，未声称直接取得 PPT 原件。 [课程基线](../../docs/course-requirements.md) · [M01 整改交接](story-2-5-remediation-handoff.md)
