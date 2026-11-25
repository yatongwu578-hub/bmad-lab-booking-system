# Story 1.3 R1 一次性整改交接

**接收会话**为原 Story 1.3 `bmad-build` 开发会话。项目负责人已在独立评审会话选择保留行动项，仅批准后续整改 **R1**。本交接文件不启动开发、不代表整改完成，不另分派三位组员的个人任务。 [负责人处置](story-1-3-review-disposition.md) · [正式 Story AC-1～AC-6](../planning-artifacts/epics.md#story-13-查看设备目录与具体设备详情) · [实施规格](spec-1-3-view-equipment-catalog.md) · [首轮独立评审](story-1-3-independent-review.md)

## 原 Build 会话执行范围

1. 先读取 [AGENTS.md](../../AGENTS.md)、[课程要求](../../docs/course-requirements.md)、本交接、实施规格和首轮评审。核对前置 Sprint 状态和负责人批准。Step 4 的整改目标是 `in-progress`。若官方文档状态尚未写入，先读处置记录中的同步说明，不把目标状态当成事实。
2. 只修 R1（Medium，正式 AC-2）。在 `equipment/templates/equipment/detail.html` 中给设备说明的输出容器应用 CSS `white-space: pre-wrap`，完整保留合法多行说明的换行和连续空格，仍允许自然换行。保留现有空说明提示及 Django 自动转义，不使用 `safe`、`mark_safe` 或 `autoescape off`。
3. 为 R1 补最小回归。以合成多行夹具覆盖连续空白、换行及看起来像 HTML 的字面文本。对照数据库读取值、正确对象、页面说明容器的保留规则和实际转义。保留原有单行、其他设备资料不串读及不承诺时段预约的断言。若补浏览器显示证据，可对 Django 隔离测试渲染出的合成 HTML 快照做本地验证，不使用业务库。
4. 不实施 R2～R11。不得改角色、数据模型、迁移、设备写入、状态转换、预约、日期占用或 Story 1.4。不得访问业务库、执行任何 GRANT、启动业务运行验证、标 `done`、暂存、提交或推送。保留 Story 1.2 原有延期事项和实验 A 条件。

## 证据与返回条件

- 原 Build 如需运行针对性自测，只用原 `.venv` 的 Python 3.13.17 及 `lab_booking_test@127.0.0.1:5433/test_lab_booking`。显式使用项目设置及 `test` 模式，不重装解释器或重建虚拟环境。遇权限问题按具体命令申请，等待批准，不用其他解释器伪造正式结果。
- 本轮独立 Django 已执行 **0 项**，既有 54/54 只属于开发方。修复后单次集中进行独立复评与全量回归，由独立评审会话运行 `check`、`makemigrations --check --dry-run`、`test --keepdb --parallel 1 -v 2`。以实际发现计数为准，不强制补测后仍为 54。保存解释器、实际连接目标、用例数、退出码、前后状态、T-03 8 项拒绝与 12 项对照、Story 1.1／1.2 回归证据以及 R1 可见分行与自动转义断言。不要重复执行当前阶段的独立回归。
- 原 Build 完成修复并提交实际自测证据后，按 BMAD 工作流重新进入 `review` 交独立复评。未满足验证条件就保留未完成，最终验收由负责人另行决定。

## 2026-11-25 整改返回

R1 已在原 Build 会话完成最小修复并通过开发自测。原 Python 3.13.17、隔离 PostgreSQL 与无头 Chrome 的实测为 55/55，包含 R1 的真实渲染断言。Sprint 已回到 `review`，下一步由原独立 Code Review 会话执行 R1 针对性复审和完整独立回归。请使用开发证据中的 `LAB_BOOKING_R1_CHROME` 设置，以免跳过浏览器用例。R2～R11 仍延期，不执行正式库授权，不标 `done`。 [复现命令及自测](story-1-3-dev-evidence.md#2026-11-25-r1-整改与开发自测) · [处置更新](story-1-3-review-disposition.md#4-2026-11-25-原-build-会话-r1-整改交回)
