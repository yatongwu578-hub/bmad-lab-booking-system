# Story 2.8 · P01／P02 回交原独立评审

2026-11-28，原 Build 已核验开发专项 1/1 Django、2/2 PostgreSQL，规格 `in-review`、Sprint `review`。回到**发出 D-062 整改交接的原独立 Code Review 会话**续办针对性复审。不是重新开首评，不表示 P01/P02 已作独立关闭。 [首评与裁决](story-2-8-independent-code-review.md) · [D-062](../../decision-log.md#d-062-2026-11-28-负责人批准-story-28-评审处置) · [整改专项回执](story-2-8-p01-p02-dev-evidence.md)

1. 以 `2c6380ac608b356df5f0be8251fa4882327e3eab` 为唯一主线基线，纳入未跟踪的 2.8 候选源码、测试与验收工具，不暂存。对照候选散列和 [开发专项归档](story-2-8-run-20261128-233025-956/archive.sha256)；规格在批次后仅追加结果与更新状态。保留原历史日志、首评及 9 项延期、两项不采纳，不扩大本轮范围。
2. 对 P01 核对原始查询字节、400 拒绝与零业务副作用，合法编码导航及 FR-018 例外不变。对 P02 核对两组真实 POST、独立后端和等锁、实际后手 409、先手历史主体和原因、释放占用及清理，不改共享锁。
3. 对整改候选只用同一脚本默认模式做**一次完整独立复验**。源码已核对默认分支不附带专项标签，覆盖 159 项 Django 测试（含原 150 项）和 36 组探针（原 34＋两序），实跑再核对实际分母。无需重跑旧开发批、整改专项或 NFR-001 的历史标准组。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\run-story-2-8-isolated.ps1"
```

只连接 `127.0.0.1:5433/test_lab_booking`。按课程基线使用独立工作流和真实人机证据，不代签三位成员。Sprint 8/5、实验 A 原始证据、五项口径及观察截止均保持不变。不访问正式库、不新增迁移或授权、不开发 3.1、不标 done、不提交推送。 [实施规格](spec-2-8-admin-cancellation.md) · [Sprint 状态](sprint-status.yaml) · [课程基线](../../docs/course-requirements.md)
