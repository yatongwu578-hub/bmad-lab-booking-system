# Story 2.4 · 独立 Code Review 交接

新会话使用安装版 BMAD 6.12.4 的 `$bmad-code-review`，只评审「本人取消预约」。原 Build 已核对真实开发自测，规格为 `in-review`、Sprint 为 `review`。即将开始的独立会话不等于已评审，不标 `done`。三位成员共同操作和审阅。

## 输入和范围

- 差异基线 `33ff1eb86a1101db5033a4232a121a08d66a4c03`。仅评审 Story 2.4 增量，包含未跟踪的新源码与测试，不暂存。排除以前已存在的日志、锁、118 个未跟踪条目及旧批次证据。审计文件与代码 diff 分读。
- 产品：`audit/services.py`、`reservations/{services,views,urls}.py`、`reservations/templates/reservations/{list,result,cancel}.html`。验证：`reservations/test_own_cancellation.py`、`reservations/management/commands/verify_own_cancellation.py`、`verify-story-2-4.ps1` 及字节受保护的既有 125 项名称记录。编译 Epic 2 上下文、规格和状态为流程资料，不改变正式需求。
- [正式 AC-1～8](../planning-artifacts/epics.md#story-24-取消本人尚未开始的预约) · [冻结的实施规格](spec-2-4-cancel-own-reservation.md) · [开发证据和验收映射](story-2-4-development-evidence.md) · [原始回执索引](./story-2-4-dev-run-20261127-234701/verified-receipt.json) · [原始运行时规格](./story-2-4-dev-run-20261127-234701/spec-at-run.md) · [归档散列](./story-2-4-dev-run-20261127-234701/archive.sha256)

## 评审核心

优先核对确认 GET 的无写、POST 防护和异主 404、短事务中锁后权限／归属重读与唯一数据库时刻、精确开始边界、已结束待审核和既有批准状态、占用与历史原子性、重复／并发及失败分类。用实际日志区分精确模拟时间、真实锁与数据库时间、真实回滚、真实断连和实际提交后模拟确认丢失。复用 133/133 和 16/16 的开发证据，不冒称独立测试。核心写入竞争机制未变，NFR-001 20×10 只引用有效历史原证。

如需独立实跑，仅用原 `.venv` 以及 `127.0.0.1:5433/test_lab_booking`，同库串行，新目录留证，只针对确有必要的分支。正式发布前实际核对权限和迁移状态另行授权；本阶段不接触正式库或新增授权。不改变 Sprint 8／5、实验 A，不提前开发 2.6／2.7，也不自动 commit/push。

新会话可直接发送：`$bmad-code-review 请按 _bmad-output/implementation-artifacts/story-2-4-code-review-handoff.md 独立评审 Story 2.4，保留 review，不标 done。`
