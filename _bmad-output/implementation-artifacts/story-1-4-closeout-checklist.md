# Story 1.4、Epic 1 与 GitHub 收尾清单

2026-11-26 由准备清单续接收尾。正式 AC-1～AC-8 及 W1 已取得证据，负责人按 D-036 批准最终验收及有条件的 Epic 收尾、指定 Git 提交和推送。Story 1.1～1.4 均已验收，Story 2.1 保持 `backlog`。 [AC 核对与原始输出](story-1-4-runtime-evidence.md) · [Sprint 状态](sprint-status.yaml)

## 1. Story 1.4 最终验收

- [x] 对照正式 AC、独立复审裁决、隔离复验及 D-035 正式运行。保留 10:56 SQL 歧义、11:20 已授权但浏览器前中止、11:46 只读恢复成功的三段历史。W1 已取证。Q-1／Q-2、R3～R6、W2 与第二台 Windows 复现等既有延期不改。
- [x] 负责人确认接受正式八条 AC、W1、剩余风险和延期的跟踪方式。只登记实际决定和理由，不代填三位组员的确认或投票。
- [x] 按 BMAD 6.12.4 Build Step 5 收尾并同步规格与 Sprint，更新最终验收及 README。本轮不重授权、重提同一设备修改或重复执行回归。

## 2. Epic 1 收尾

- [x] 范围核对为登录和身份、管理员新增、目录和详情、管理员基础编辑。四条对应[1.1 验收](../../docs/team/story-1-1-review-disposition.md#负责人最终验收与状态推进2026-11-24-d-023)、[1.2 验收](story-1-2-final-acceptance.md)、[1.3 验收](story-1-3-final-acceptance.md)、[1.4 验收](story-1-4-final-acceptance.md)。
- [x] 四条 Story 都已完成，Epic 1 完成依据及跨 Story 检查单独留档。设备维修／停用／恢复仍属 Epic 3，预约关联集成回归随 Epic 2 执行。Epic 1 完成不等于 Sprint 1、NFR-001 或全项目 NFR-002 已验收。
- [x] 完成 [Epic 1 证据回顾](epic-1-retro-2026-11-26.md)，裁决 `accepted-with-open-items`。不代填三人意见。课程根目录回顾已有 Epic 1 索引，但真实实验 A 和两轮 Sprint 回顾仍按原计划。

## 3. GitHub 提交清单

D-036 明确授权检查通过后提交及推送。操作前，本地 HEAD 与远端 main 已核对同为 `e200fee335536941e0705c112aefbf6751b244c3`，暂存区为空。最终提交及同步实际结果以 Git 历史和远程查询为准。 [Git 基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/e200fee335536941e0705c112aefbf6751b244c3)

| 候选组 | 纳入范围 |
| --- | --- |
| 业务、模板与测试 | `equipment/forms.py`、`services.py`、`urls.py`、`views.py`；`equipment/templates/equipment/{detail,edit_form,edit_result}.html`；`equipment/test_edit.py`、`equipment/management/commands/verify_equipment_edit_transactions.py`。无新增迁移。 |
| 需求落实与人工记录 | `README.md`、`decision-log.md`、Sprint 跟踪、Story 1.4 规格、Checkpoint 1、开发／独立评审／处置／整改／复验证据、延期附录、运行证据及本清单。最后验收记录只在确认后纳入。无正式 PRD 或 Architecture 改动。 |
| 可复现入口与历史 | 保留 Q-3 专项、隔离和运行包装、ACL／快照 SQL 与 Chrome 工具。被文档引用的补丁属历史，不重放。原始证据含首次及后续开发自测、独立复验两目录、D-035 两个只读 ACL 目录及三个正式库运行目录，连同原退出码和散列核对。 |

- [x] 用明确路径白名单审查候选和暂存差异，不用 `git add .`。逐项筛查含 UTF-16 的原始证据，不纳入 `.venv`、密码文件、账号清单、密码／会话／CSRF 值、数据库备份、浏览器配置或渲染缓存。冻结复审交接、两份历史补丁与分阶段日志各有来源或复现用途，保留原件，不重放。证据目录和冻结文本禁止 Git 转换行尾，避免清单散列改变。
- [ ] 核对 `git status --short --branch`、`git diff --check`、`git diff --cached --check` 与暂存文件清单。按实际授权使用 `feat(story-1.4): deliver equipment editing and close epic 1`，推送 main 后核对远程 SHA，不预填不存在的提交。

## 课程追溯

第 26 页核对正式 FR、ADR、Story、AC 和实证链。第 27 页保留独立开发、独立评审、处置、复验及负责人最终验收的节点。第 33 页同仓保留真实状态、源码、验证和交付证据。第 34 页实验 A 不加入本轮数据。第 36 页保留 D-035 实测结果和 D-036 新发生的负责人批准。页码依据[课程基线](../../docs/course-requirements.md)和[第 27 页团队记录](../../docs/team/sprint-planning-review.md)，未声称重新直接查看原 PPT。
