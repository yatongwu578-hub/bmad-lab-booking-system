# Story 2.2 · BMAD 6.12.4 Step 4 人工处置

> 2026-11-27 事后结果：独立隔离复验与正式前后只读验收已经核验。D-044 的 2.2-P1～P6、2.2-D1 共七项已完整追加一次，中央原内容不变。0 Decision、6 项开放待办、原 Low 延期和 13 项不采纳均不改。下文保留当时过程。 [最终验收](story-2-2-final-acceptance.md) · [中央台账](deferred-work.md)

## 决定

2026-11-26（北京时间），项目负责人在当前评审会话明确选择 **2，保留为规格中的待办**，接受四视角和逐项裁决。在现有证据足以支持正式 AC-1～AC-8、安全性和数据一致性的前提下，批准 P1（Medium）、P2～P6（Low）延期为非阻塞测试及取证改进。D1 原 Low 延期保持，RD01 不关闭，13 条不采纳原理由不改。不是最终验收，不把决定写成已修复。三位组员共同操作和审阅，不代写成员个人决定。 [负责人决定 D-044](../../decision-log.md#d-044-2026-11-26-负责人处置-story-22-独立评审) · [逐条裁决](story-2-2-review-triage.md)

## Step 4 落盘与剩余事项

- 0 项需要决定，0 项修复，6 项规格待办保持未勾选并标注负责人批准延期。另有原 1 项延期和 13 项不采纳。规格与 Sprint 依 Step 4 的选项 2 同步为 `in-progress`，表示待取得独立运行回执，不要求为 P1～P6 返工，不是 `done`。
- P1 的 `history-second` 记录在故障注入前采样，原 `bind` 不是实际执行绑定。不能从原 JSONL 声称验证了替换后的绑定。开发原始证据的真实 SQLSTATE `23514`、两次写入尝试、零 COMMIT，以及独立观察的设备、预约、有效占用和历史前后相同，仍支持 AC-8 的原子回滚。P1～P6 及 D1 的理由、残余风险和重新处理节点见[中央台账待合并条目](story-2-2-d044-deferred-pending.md)。
- 中央 `deferred-work.md` 写入预检被沙箱拒绝（`UnauthorizedAccessException`），前后 SHA-256 同为 `100692B3AEFDFBB6404FE1AFB51D4FB6502F52A1B36C595E51D159CAEBA684FC`。合并入口在真实台账的临时副本上通过首次追加、原前缀保留、重跑不改字节、部分冲突拒绝四项核对。待三位组员在可写的普通 PowerShell 运行下方一次性命令，不把副本回执记成中央已合并。
- BMAD 正式解析器以指定解释器和独立临时目录解析 `workflow.on_complete`，其值为空。无后续代码、状态或 Git 钩子。本次处置结束，不再发起审批或启动下一故事。
- 课程按第 25／26／27／33／34／36 页保留可测试故事、FR-004／002／018／015 到 ADR 和 AC 再到证据的追踪、真实状态与文件链、实验 A 条件及人工决定五个证据维度。仅依据仓库课程基线及既有记录，不声称直接复核未找到的 PPT 原件。原 Sprint 8／5 不变。

## 普通 PowerShell 交接

从仓库根目录合并延期台账。命令只追加 D-044 七条，保留旧条目，完整合并后重跑只核对不重复写入。遇到部分或不一致条目会停，不覆盖或猜测。

```powershell
& '.\_bmad-output\implementation-artifacts\merge-story-2-2-deferred.ps1'
```

成功回执为 `STORY22_D044_DEFERRED_MERGE_OK`，另区分 `appended` 和 `already-present`。该脚本不运行测试、不访问任何数据库。

独立复验继续使用未修改的 [review-story-2-2-isolated.ps1](review-story-2-2-isolated.ps1)，无需整改补丁。已通过脚本语法核查，SHA-256 与原独立评审一致。三位组员串行执行，且运行期间不要继续编辑被测输入。仅连接 `127.0.0.1:5433/test_lab_booking`，以新目录、103/103 且零跳过、21/21、11 阶段及 `STORY22_INDEPENDENT_REVIEW_RUN_OK` 为准。故障绑定限制仍如实保留。

```powershell
& '.\_bmad-output\implementation-artifacts\review-story-2-2-isolated.ps1'
```

本处置未运行新 Django 或 PostgreSQL 探针，不把旧开发档案冒充独立实跑。Story 2.1 的核心事务未变，继续复用已独立核验的 NFR-001 20 请求 × 10 轮暨 200 个历史响应，不重跑、不等整点。未访问正式库、未迁移或 GRANT、未改业务代码、未启动 Story 2.3、未标记 done、未 commit/push。 [原独立评审](story-2-2-independent-review.md) · [D-040 历史复验](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

**后续实证。** 团队的新隔离独立批次已执行，评审会话只读核验通过，规格与 Sprint 分别回到 `in-review` 和 `review`。六项新批准延期、D1 和 13 项不采纳仍不变。没有中央延期台账新回执，也未执行正式运行。 [逐 AC 独立复验](story-2-2-independent-recheck.md) · [正式运行交接](story-2-2-runtime-handoff.md)
