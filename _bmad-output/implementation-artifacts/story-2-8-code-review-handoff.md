# Story 2.8 · 独立 Code Review 交接

在新会话用已安装 BMAD 6.12.4 的 `$bmad-code-review`，仅评审「管理员取消预约并记录原因」。当前规格 `in-review`，Sprint `review`。本 Build 会话只核验了开发自测，没有运行独立评审层或形成评审裁决。 [正式 AC](../planning-artifacts/epics.md#story-28-管理员取消预约并记录原因) · [实施规格](spec-2-8-admin-cancellation.md) · [开发证据](story-2-8-dev-evidence.md)

1. 先读 [课程基线](../../docs/course-requirements.md) 和规格。以 `2c6380ac608b356df5f0be8251fa4882327e3eab` 为唯一基线，构建含未跟踪 2.8 源码、模板及测试的限定差异。排除既有 1 条历史日志与 118 条旧记录，不暂存、提交或推送。对照通过批次 [输入清单](story-2-8-run-20261128-220430-872/source-before.sha256)，规格在验证后只做移交状态和证据更新，不是被测业务输入变更。
2. 重点核对未授权与锁后撤权无业务写或泄露、待审核开始/已批准结束的相等边界、空白原因不吞合法 FR-018、管理员与申请人原因可见性、批准先行的双历史，以及确认回滚和提交未知。使用 [原始探针](story-2-8-run-20261128-220430-872/probe.jsonl)、[全量回执](story-2-8-run-20261128-220430-872/regression.receipt.json) 和 [首次失败整改](story-2-8-regression-remediation.md)。如独立评审发现证据缺口，只安排必要的隔离验证；不得接触正式业务库或改实验 A。
3. 审查发现与人工处置留痕，不代签团队。Sprint 仍为 8/5，不开发 3.1，不把开发通过或进入 review 当作最终验收。非授权不标 done、不提交推送。
