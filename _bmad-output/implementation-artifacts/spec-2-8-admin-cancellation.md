---
title: 'Story 2.8 管理员取消预约并记录原因'
type: 'feature'
created: '2026-11-28'
status: 'done'
baseline_commit: '2c6380ac608b356df5f0be8251fa4882327e3eab'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/docs/course-requirements.md'
  - '{project-root}/_bmad-output/planning-artifacts/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

管理员须能从预约管理或详情确认取消单条预约，说明原因并返回原筛选视图。以[正式 AC-1～8](../planning-artifacts/epics.md#story-28-管理员取消预约并记录原因)为准，复用既有状态、占用和处理历史。

## Boundaries & Constraints

**始终：** 活跃业务管理员和目标授权先行，锁设备、复核权限、重读目标、一次数据库判时。仅对目标执行 FR-018，状态和历史同事务。

**不做：** 不改规则、模型、迁移、授权、共享锁协议或正式库。不做 3.1、批量取消、自动重试。不改 Sprint 8/5 或实验 A。

## I/O & Edge-Case Matrix

| 输入 | 结果 |
| --- | --- |
| 待审核且判时早于开始，或已批准且早于结束，原因非空 | 已取消，释放占用，保留原记录；维修、停用不改变规则 |
| 仍待审核且判时达到开始 | 仅提交系统失效及其历史，明确未执行取消；空白原因仍提示必填 |
| 合格预约但原因空白 | 必填且不写取消；合法失效不因业务拒绝回滚 |
| 已批准已到结束、终态、记录不存在 | 明确拒绝或不存在，不写；不把已批准改为失效 |
| 未授权、CSRF 不通过或畸形请求 | 不泄露、不改业务数据 |
| 已确认回滚／提交状态未知 | 分别报告失败／待核查；不重复提交 |

</frozen-after-approval>

## Code Map

- `reservations/services.py`：沿用 `require_reservation_admin`、`_recheck_reservation_admin`、`lock_equipment`、`_expire`、`_decision_time`、`_durable_operation`；参照 `get_cancellation_candidate` 的只读投影。
- `audit/services.py`：沿用写入字段与时间；已有管理员和本人原因投影支持 `admin/cancel`，无需改读路径或模型。
- `reservations/{forms,views,urls}.py`、`reservations/templates/reservations/`：沿用拒绝表单校验、CSRF、筛选和返回链接；新增取消入口及确认/结果渲染。

## Tasks & Acceptance

- [x] `audit/services.py`：新增管理员取消写入，使用现有字段、动作与账号。
- [x] `reservations/services.py`：新增单条取消及只读确认查询；在现有持久事务中按上表转态，业务拒绝正常返回，数据库错误沿用原分类。
- [x] `reservations/{forms,views,urls}.py`、`reservations/templates/reservations/`：新增受保护的 GET 确认与 POST 提交；显示结果和固定站内返回链接。列表、详情提示不作写入判据。
- [x] `reservations/test_admin_cancellation.py`、`reservations/management/commands/verify_admin_cancellation.py`：覆盖上表及真实交错，只新增专项用例，保留原 150 项。

**验收：** 给定可取消预约及合法管理员，确认提交后管理员可见完整历史，申请人仅可见本人准确原因。给定并发操作，后手按锁后真实状态处理，历史和占用与实际顺序一致。给定事务异常，按已确认回滚或未知分支返回。逐项断言见[验收矩阵](story-2-8-checkpoint-1.md)。

### Review Findings

2026-11-28 · BMAD 6.12.4 full · 四个独立视角。0 decision-needed，2 patch，9 defer，2 rejected。负责人已选择 2「保留为行动项」。P01/P02 在首评时保留开放，现按 D-063 经完整隔离独立复验正式关闭。D01～D09 保持原批准延期，两项不采纳原裁决不变。此处置不是最终验收。 [逐项裁决、AC 与原始证据](story-2-8-independent-code-review.md)

- [x] [Review][Patch] **2.8-P01（原 Medium 验收阻塞，已关闭）** 原始查询编码闸口与 28 个负例零业务副作用，经独立复验通过。 [D-063](../../decision-log.md#d-063-2026-11-28-负责人按完整独立复验关闭-story-28-p01p02)
- [x] [Review][Patch] **2.8-P02（原 Medium 证据缺口，已关闭）** 两个真实 POST 的双序锁等待、唯一历史及占用释放，经独立复验通过。 [原始探针](story-2-8-run-20261128-234855-694/probe.jsonl)
- [x] [Review][Defer] **2.8-D01** 未知结果导航 [reservations/views.py:477] — deferred: 原筛选可能隐藏已实际取消的记录；可清空筛选核查。后续改善直达详情且保持无重试表单。
- [x] [Review][Defer] **2.8-D02** 并发详情断言精度 [reservations/management/commands/verify_admin_cancellation.py:164] — deferred: 按主状态字段断言，不以历史表同词为依据；当前原始响应可核对。
- [x] [Review][Defer] **2.8-D03** 待审核取消与设备状态交叉测试 [reservations/test_admin_cancellation.py:145] — deferred: 补未开始待审核在维修／停用两种状态的正向组合；当前服务无设备状态闸口，已有已批准正例。
- [x] [Review][Defer] **2.8-D04** 隔离入口检出路径可移植性 [_bmad-output/implementation-artifacts/run-story-2-8-isolated.ps1:2] — deferred: 换检出时使用当前仓库定位，避免误测原 F:；本轮指定路径已核对一致。
- [x] [Review][Defer] **2.8-D05** 可选 Chrome 与预检依赖 [_bmad-output/implementation-artifacts/preflight-story-2-1.ps1:39] — deferred: 预检仍要求 Chrome 文件；当前原机文件存在，不阻塞，跨机改版时与可选回归一致。
- [x] [Review][Defer] **2.8-D06** 执行及复用依赖散列 [_bmad-output/implementation-artifacts/run-story-2-8-isolated.ps1:14] — deferred: 发布包补 runner、预检、W01 与共享探针输入；当前这些共享基线文件未改，已独立复核 13 项非文档输入。
- [x] [Review][Defer] **2.8-D07** 预期探针名与唯一性门禁 [_bmad-output/implementation-artifacts/run-story-2-8-isolated.ps1:74] — deferred: 当前 34 个唯一名称和 completed 一致，已独立复算；后续加固自动门禁。
- [x] [Review][Defer] **2.8-D08** 进行中已批准的页面入口回归 [reservations/test_admin_cancellation.py:75] — deferred: 当前服务和页面条件正确；后续补列表／详情的实际链接和筛选保留断言。
- [x] [Review][Defer] **2.8-D09** 判定与记录时间区分断言 [reservations/test_admin_cancellation.py:70] — deferred: 当前数据库独立取记录时钟，后续用受控判时和实际写入区间识别时间被复制。

#### Rejected

- 原始 03（low）。已有合法空白原因的受控边界和真实 PostgreSQL 等锁跨界支持同一分支，不增加重复交叉。
- 原始 04（low）。共享探针的区间占用候选不等同于页面历史分类；AC-3 依赖真实时间和状态／历史不变，不在本轮改共享投影。

## Implementation Notes

- 负责人在 Checkpoint 1 明确回复「批准继续」，已按正式顺序进入 `ready-for-dev`、`in-progress`，同步 Sprint 2.8，冻结区未改。
- 已实现入口、服务及历史，新增 9 项 Django 测试和 34 组 PostgreSQL 探针。静态语法和 Story 范围内的差异检查已做，不代表任何数据库行为通过。
- Windows 沙箱用 `Start-Process -Wait -PassThru` 启动原 `.venv` 的 `--version` 得到原生退出码 103，未开始 Django 或数据库验证。使用 [普通 PowerShell 验证命令](run-story-2-8-isolated.ps1) 执行单批并自动归档，回执核验前维持 `in-progress`。
- 首次普通 PowerShell 实测为 159 项中 157 通过、1 个新增方法失败（3 个子例）、既有可选 Chrome 项跳过。前后隔离快照一致，专项探针未开始。已纠正新增测试请求夹具和探针的路径前缀误判，未改任何业务代码或减弱断言。 [失败分析和单批复验](story-2-8-regression-remediation.md)
- 复验批次 `220430-872` 的 7 个阶段均退出 0。Django 158 通过／159（原有可选 Chrome 跳过 1），9 个新增测试和 34 组 PostgreSQL 探针全部通过。原生回执、散列、清理及 AC-1～8、T-01～04、Story 范围 NFR-002 已核验。按负责人指示进入独立评审待交接，不标 done。 [开发证据](story-2-8-dev-evidence.md) · [独立评审交接](story-2-8-code-review-handoff.md)
- D-062 的 P01 严格原始查询编码检查和 P02 本人／管理员两个 POST 双序探针已落盘。静态检查通过，现有脚本增加整改专项入口。没有运行真实专项，不勾选两项，不改 `in-progress`。 [专项命令、断言与候选散列](story-2-8-p01-p02-dev-evidence.md)
- 隔离批次 `233025-956` 的 1 个 Django 方法、2 组真实 POST 竞争探针均通过，5 个阶段原生退出 0，输入散列和数据库基线一致。按 BMAD 转 `in-review`，P01/P02 保持开放至独立复验。 [实测回执](story-2-8-p01-p02-dev-evidence.md#实测回执与交接) · [交回原独立评审](story-2-8-p01-p02-review-handoff.md)
- D-064 正式最小批次通过，只观察已失效终态，无安全正向样本。由已绑定的独立实测承接正向和边界，AC-1～8 证据完整。负责人条件授权生效，规格和 Sprint Story 进入 `done`。 [最终验收与追溯](story-2-8-final-acceptance.md)

## Spec Change Log

## Review Triage Log

- **2026-11-28 · Step 4 人工处置 D-062。** 项目负责人明确选择 2「保留为行动项」，批准原 Build 最小整改 P01、补 P02 真实双序且不改共享锁。D01～D09 在不影响正式 AC、安全性和一致性的条件下延期；原始 03、04 不采纳依据保留。规格与 Sprint 从评审回到 `in-progress`；冻结区不变，不把待整改项勾为完成。 [负责人决定](../../decision-log.md#d-062-2026-11-28-负责人批准-story-28-评审处置) · [原 Build 整改交接](story-2-8-remediation-handoff.md)
- **复验未运行。** 整改完成后用原隔离入口统一独立复验一次，不重跑整改前批次。原开发结果继续保留，标准 NFR-001 20×10 在机制不变时复用，不计作本次实跑。

- **2026-11-28 · 完整独立复验与 D-063。** 负责人在普通 PowerShell 实际运行默认批次 `234855-694`，本评审只读核对 35 个散列、15 个输入和前后隔离基线。全量 158/159（既有可选 Chrome 跳过 1），新增 9/9，36/36 探针，7 个原生阶段退出 0，总标记 `STORY28_ISOLATED_BATCH_OK`。正式 AC-1～8、T-01～04 及 Story 范围 NFR-002 证据满足。按负责人本次条件授权关闭 P01/P02，不等于正式运行验收。9 项延期、两项不采纳、D-062 及实验 A 保持。规格 `in-review`／Sprint `review`，3.1 不启动。 [本轮证据与关闭](story-2-8-independent-run-result.md) · [最小正式运行方案（未执行）](story-2-8-minimal-formal-run.md)

## Verification

以 `2c6380ac608b356df5f0be8251fa4882327e3eab` 为唯一基线。原 `.venv`、PostgreSQL 17.12，限 `127.0.0.1:5433/test_lab_booking`。运行 `check`、`makemigrations --check --dry-run`、`test --keepdb --parallel 1 -v 2` 和 Story 专项探针，自动归档。通过后移交新会话独立评审，不标 done。
