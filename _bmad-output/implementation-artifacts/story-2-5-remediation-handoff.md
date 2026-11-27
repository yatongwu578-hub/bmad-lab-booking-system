# Story 2.5 · M01 整改交接（原 Build 会话）

负责人已按 BMAD 6.12.4 full Step 4 选择「保留为行动项」。本交接授权范围仅为 M01（Medium，阻塞正式 AC-8）。请在原 `bmad-build` 会话续办本 Story，不新开下一 Story。规格与看板均为 `in-progress`，三位组员共同操作、审阅，不分派个人任务。 [D-050](../../decision-log.md#d-050-2026-11-27-负责人批准-story-25-独立评审处置) · [人工处置](story-2-5-review-disposition.md) · [正式 AC-8](../planning-artifacts/epics.md#story-25-管理员查询预约详情并按设备筛选)

## 只修 M01

现在管理员详情在 `reservations/views.py` 中把无效 `equipment` 当作没有导航上下文，继续调用预约详情服务。对到期待审，这个请求可能执行 FR-018、提交失效状态和系统历史并返回 200。现有导航用例接受重复参数回退，但夹具为取消终态，未触及这一副作用。本组合为独立静态发现，未声称已新跑复现。

- 管理员服务端授权检查先于输入错误响应。对明确提供但格式非法的 `equipment` 在读取预约前返回 400，显示设备编号错误，不降级成成功详情。保留未提供及合法返回导航、合法详情原授权范围、预约不存在的 404、匿名跳转与师生 403。不得让有效的返回筛选参数改变详情对象范围。
- 保留原用例名称与合法返回、权限、缺失、历史断言。替换原「非法参数回到全量」断言。在到期待审夹具上核对重复、空白、超长等非法设备参数，真实 HTTP 明确 400；无候选读取、无设备锁、无 `t_decision`、无预约状态变化、无有效占用变化、无历史写入。认证所需技术查询不记为业务读取。
- 对同一预约使用无参或有效导航的合法详情，核对 200、状态转为失效且恰好新增一条系统历史；重复合法读取不重复写。合法筛选列表、无匹配与正常详情返回保留。可扩展现有专项及 `edge-input` 探针，实际测试新增须更新清单，不删用例凑原数字。
- 不修改 FR、AC、ADR 或冻结意图，不改共享权限、预约核心事务、其他 Story 或 Sprint 计划。不重应用共享补丁，不并跑同隔离库，不开展非阻塞延期项。P01～P12、D01～D05 和三项驳回按已批准记录保留。

## 整改后一次独立复验

**当前续接。** M01 开发专项已由团队在普通 PowerShell 实跑，3/3 Django、1/1 真实探针及 `STORY25_M01_DEV_OK` 已核对。Story 已回 `review`，由原评审会话针对性复审，并执行下方的一次独立全量复验。以下开发命令仅保留为历史输入，不需要再运行。已应用的共享补丁不再应用。 [M01 开发实测与原始证据](story-2-5-m01-dev-evidence.md)

```powershell
Set-Location -LiteralPath 'F:\softwork\SE-Management\bmad-lab-booking-system'
& 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\verify-story-2-5.ps1' -M01Only
```

`-M01Only` 检查三个已命名的 Django 用例，再执行一个真实 HTTP/PostgreSQL 专项探针。用同一条已到期待审预约串行检查五种非法参数 `400`、合法筛选导航 `200` 和缺省参数重复读取 `200`。新的目录保留实际响应、SQL、观察连接前后快照、隔离库基线、输入散列及 `STORY25_M01_DEV_OK`。不以 400 前已无逻辑占用冒充“释放一次占用”，以状态和实际唯一系统历史判定。成功和失败均只需提供实际目录。

提交实际最小差异、测试清单变化与授权分支核对供此独立评审会话复核。不要重跑整改前全量，或把当前开发回执写成新测试。独立复验统一安排在 M01 整改之后，使用原 `.venv`、Python 3.13.17、Django 5.2.19、PostgreSQL 17.12，并且只连接 `127.0.0.1:5433/test_lab_booking`。检查原先的 5 专项、113 旧 + 12 新 Django 用例、17 探针及 M01 新断言，明确记录实际分母、退出码、散列、前后基线和清理。如有清单变化，先核对再如实调整入口。沙箱已有解释器 103 证据，不重试旧命令。无必要不重跑已独立核验的 NFR-001 20×10 标准组。

```powershell
Set-Location -LiteralPath 'F:\softwork\SE-Management\bmad-lab-booking-system'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\_bmad-output\implementation-artifacts\story-2-5-review-support\run-story-2-5-independent.ps1'
```

脚本原生退出 0 且唯一整行 `STORY25_REVIEW_RUN_OK` 才记本批通过，以新输出目录和原始回执交接，不填额外表格。独立包装仍运行原 5 专项、125 项全量及 17 项探针；M01 放入已有同名用例和 `edge-input.m01`，离线审计拒绝缺失专项或不一致的请求、SQL、状态／占用／历史和终行回执。保留旧版 5/5、125/125、17/17，以及最初 124/125 和导航整改原证，旧批不冒充 M01 复测。 [开发证据](story-2-5-dev-evidence.md) · [首次失败整改](story-2-5-regression-remediation.md)

W01 暂不执行。独立复验通过后，另行处理历史表 `actor_id`、`before_status`、`after_status`、`decision_at`、`recorded_at` 五列 SELECT 实测缺量。不得访问正式库、提前授权、迁移、标 `done` 或自动 commit/push。 [最小正式运行方案](story-2-5-review-support/story-2-5-minimal-formal-run.md)
