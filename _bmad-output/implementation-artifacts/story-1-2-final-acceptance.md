# Story 1.2 最终验收记录

2026-11-25，项目负责人在最终验收会话正式批准「管理员新增具体设备基础档案」验收通过。实施规格与 Sprint 跟踪均为 `done`。Epic 1 继续 `in-progress`，Story 1.3 及其他未开始 Story 保持 `backlog`。 [负责人决定 D-027](../../decision-log.md#d-027-2026-11-25-story-12-负责人最终验收) · [实施规格](spec-1-2-create-equipment.md) · [Sprint 状态](sprint-status.yaml)

## 正式验收依据

FR-016／FR-002 → ADR-002／003／008 → Story 1.2 正式 AC → 隔离库独立验证与业务库运行证据。本入口覆盖 NFR-002 的设备新增权限场景。 [正式 PRD](../planning-artifacts/PRD.md) · [架构与 ADR](../planning-artifacts/architecture.md) · [正式 Story 与 AC](../planning-artifacts/epics.md#story-12-管理员新增具体设备基础档案)

| 正式 AC | 独立复审结果 |
| --- | --- |
| AC-1 | 通过。新增恰一条，独立回读与提交和成功页一致，初始「可用」只读且伪造状态无效。 |
| AC-2 | 通过。顺序重号明确报重，原行与数量保持原值。 |
| AC-3 | 通过。六类无效编号请求显示字段错误，逐次核对零新增。 |
| AC-4 | 通过。匿名、学生、教师的 GET／POST 共六例均被拦截，无新增页内容泄露及设备写入。管理员合法对照成功。 |
| AC-5 | 通过。缺失和错配 CSRF 均拒绝，逐次零新增。有效令牌对照成功。 |
| AC-6 | 通过。真实 PostgreSQL 独立连接确认同号竞争中 B 等待 A，最终 A 成功、B 明确报重，仅持久化赢家。 |
| AC-7 | 通过。真实约束回滚反馈明确失败，COMMIT 前断连与真实 COMMIT 后丢确认均提示待核查。独立读回依次为零、零、一条，各尝试写入一次，零自动重试。 |

独立 Django 回归 45/45，其中 Story 1.1 为 32/32。AC-6、AC-7 在隔离 PostgreSQL 实例取证，故障细节、独立读回及补验的首次管道编码失败均已留存。本轮依据已有证据完成验收。 [独立复审实测](story-1-2-independent-recheck.md#独立运行证据)

## 评审、运行与团队体验

- 开发自测后进入评审。首轮独立评审保留 AC-1、AC-3 和 AC-7 实测失败。D-025 批准原开发会话整改 R1～R5、延期 R6～R11。整改自测完成后回到评审，四视角独立复审通过后由 D-026 正式关闭 R1～R5。 [开发证据](story-1-2-dev-evidence.md) · [首轮独立评审](story-1-2-independent-review.md) · [整改交接](story-1-2-remediation-handoff.md) · [评审处置](story-1-2-review-disposition.md)
- D-026 授权后的实际运行证据包括迁移前受保护备份、仅应用 `equipment.0001_initial`、对运行角色授予六列 INSERT 和 `id` 列 SELECT、独立连接复核及本机 Chrome 三角色运行验证。获准保留一条课程演示档案，三角色退出后会话数归零。 [D-026](../../decision-log.md#d-026-2026-11-25-负责人关闭-r1r5-并批准-story-12-业务库验证) · [业务库证据](story-1-2-runtime-evidence.md)
- 团队体验记录到三位组员共同操作与审阅的粒度。具体角色结果以 Chrome 批次为准，现有记录未逐人对应操作步骤，也未记录额外的个人浏览器体验结果。第二台 Windows 机器仍待复现。 [团队参与与运行证据](story-1-2-runtime-evidence.md) · [延期台账](deferred-work.md)

## 课程证据与后续跟踪

| PPT 页 | 本 Story 的证据 |
| --- | --- |
| 26 | 正式 FR、ADR、Story／AC 与独立 Test 的追溯链，沿用已批准的需求和架构。 |
| 27 | 保留开发、自测、独立评审、失败、整改、复审及负责人验收证据。首轮评审后进入 `in-progress` 整改，随后回到 `review`，经本次批准推进至 `done`。 |
| 33 | 源码、迁移、回归测试、两版探针、报告、Sprint 跟踪及 README 启动说明纳入建议提交范围。 |
| 34 | Story 1.2 的回归、探针及实际运行均属于本 Story 验收证据，不计入实验 A。实验 A 延续批准的计划。 |
| 36 | 根目录决策日志以 D-024～D-027 记录实际建议、负责人判断、依据及结果，保留证据链接。 |

页码按课程基线和团队已记录的 PPT 口径核对，仓库内未找到 PPT 原件。R6～R11 按 D-025 延期，复审补充观察 F4、F5、F10 沿原节点跟踪。Git 的已提交基线为 Story 1.1 收尾，本次 Story 1.2 中间状态以开发及评审文档留证，最终提交和推送待负责人批准。 [课程要求](../../docs/course-requirements.md) · [团队 PPT 核对](../../docs/team/sprint-planning-review.md#l47) · [Sprint 计划](../planning-artifacts/sprint-plan.md) · [已提交基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/2333c0559a948da5cbf6e91f8a6bd2c630395204)
