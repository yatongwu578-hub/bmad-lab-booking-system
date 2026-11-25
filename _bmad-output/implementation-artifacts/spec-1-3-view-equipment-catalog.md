---
title: 'Story 1.3 查看设备目录与具体设备详情'
type: 'feature'
created: '2026-11-25'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '09085cbc0b03dc5a3e03f54ba8604f15579b2533'
context: ['{project-root}/docs/course-requirements.md', '{project-root}/_bmad-output/planning-artifacts/project-context.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

让已登录的学生、教师和业务管理员识别具体设备及当前状态。FR-003／002 → ADR-001／002／003 → [正式 Story 1.3 AC-1～6](../planning-artifacts/epics.md#story-13-查看设备目录与具体设备详情) → 隔离库验证。NFR-002 仅取证目录和详情权限。

## Boundaries & Constraints

沿用现有设备模型、认证和连接守卫，不新增迁移。普通查询不写设备、预约或历史，不取设备写锁，不触发 FR-018。「可用」不表示某时段可预约。维修、停用仅用测试夹具覆盖。不做编辑、预约、占用查询或状态转换。正式库授权另批。

</frozen-after-approval>

## Code Map

- `equipment/models.py` 的 `Equipment` 提供主键与唯一编号，`EquipmentStatus` 提供三种状态标签。
- `accounts/views.py:identity` 示范会话、有效角色与不缓存。`lab_booking/urls.py` 已接入 `equipment/urls.py`。保留新增端点及管理员检查不变。
- `lab_booking/database_config.py`、`postgresql/base.py`、`test_runner.py`（均在 `lab_booking/`）提供目标、连接及回滚测试守卫。

## Tasks & Acceptance

- [x] `equipment/services.py` 分别实现列表与单对象读取，统一校验启用账号及 `Role.values` 后才读取。列表按编号排序、仅加载主键和五个展示字段，详情按主键读六字段；渲染前求值，不查预约或历史。
- [x] `equipment/urls.py`、`equipment/views.py` 接入 GET／HEAD `/equipment/` 与 `/equipment/<int:pk>/`。复用登录跳转和不缓存；不存在返回明确 404。
- [x] `equipment/templates/equipment/` 增加列表、详情及缺失反馈，用现有状态标签，显示当前身份并说明时段边界。`accounts/templates/accounts/identity.html` 增加目录链接。
- [x] `equipment/tests.py` 追加回滚式 `TestCase`。三状态夹具逐行、逐对象断言，逐请求比对设备完整快照。T-03 配对两端点的匿名与三角色访问；未授权逐例断言正确拒绝、无资料泄露、无设备查询或业务变化，合法对照单列。捕获重复读取 SQL，仅普通查询，排除写入及行锁。预约／历史模型尚不存在，记录无调用与 SQL，不造表。
- [x] `README.md` 说明入口及部署所需权限；`story-1-3-dev-evidence.md` 保存实际命令、输出、AC 和 T-03 结果。开发自测后 Sprint 停在 `review`，交新会话独立评审。不提交或推送。

1. AC-1 给定三状态设备，三角色分别登录查询列表，逐行正确显示编号、名称、类别、位置、当前状态。
2. AC-2 给定目标设备，三角色从列表进入及直达详情，所见上述五项和说明均匹配目标，不串对象或暗示预约成功。
3. AC-3 给定无设备，登录查询列表，返回 200 并提示暂无设备，不造数据。
4. AC-4 给定标识不存在，登录直达详情，明确返回 404，不替换对象、不写设备。
5. AC-5 给定无有效会话且有设备，直达列表或已有详情，引导登录，不泄露且无业务变化；三角色分别作合法对照。
6. AC-6 给定三状态和初始快照，登录重复读取列表及详情，数量和数据不变，无状态历史、预约处理或设备写锁。

### Review Findings

2026-11-25，BMAD 6.12.4 `full` Step 4。负责人选择保留行动项。1 项 Patch 待原 Build 会话整改，10 项 Defer 未关闭，3 条原始发现驳回，0 项修复，0 项 Decision。[独立处置](story-1-3-review-disposition.md) · [R1 整改交接](story-1-3-remediation-handoff.md) · [首轮独立评审](story-1-3-independent-review.md)

- [x] [Review][Patch] R1（Medium，AC-2 阻塞）保留设备说明的换行及连续空白 [equipment/templates/equipment/detail.html:11]。应用 `white-space: pre-wrap` 并保留 Django 自动转义。独立复审通过，负责人依据 D-030 正式关闭。
  - 2026-11-25，开发自测、独立复审与负责人关闭证据分别保留。 [R1 开发证据](story-1-3-dev-evidence.md#2026-11-25-r1-整改与开发自测) · [独立复审](story-1-3-independent-recheck.md) · [D-030](../../decision-log.md#d-030-2026-11-25-负责人关闭-r1-并批准-story-13-业务库验证)
- [x] [Review][Defer] R2（Medium，正式库运行门槛）另批业务库六列 SELECT 与浏览器验证 [README.md:95] — 已延期跟踪，未修复。D-026 现有授权仅有 SELECT(id) 支持主键读取，新投影还需六列规则。本轮无批准，不执行。风险：以现有业务角色运行目录／详情可能因授权不足失败，不能用隔离测试代替运行证据。节点：R1 整改及独立复评后，按负责人另批的最小权限和浏览器计划验证。
- [x] [Review][Defer] R3（Low，非阻塞覆盖改进）真实会话停用回归 [equipment/tests.py:421] — 已延期跟踪，未修复。已核对认证后仍检查有效账号，注入用例覆盖服务守卫，正式 AC-5 的无有效会话矩阵仍单列。风险：真实账号停用与既有会话的集成退化可能漏检。节点：下一次认证生命周期或 T-03 会话权限矩阵维护时补测。
- [x] [Review][Defer] R4（Low，非阻塞覆盖改进）目录锚点的端到端点击 [equipment/tests.py:338] — 已延期跟踪，未修复。现有用例分别断言渲染锚点、正确目标直达和字段，当前链接与路由吻合。风险：独立生成 URL 不直接证明点击行为，未来导航变化可能漏检。节点：下次目录导航回归整理时由渲染 href 驱动测试。正式运行验证也应实际点击，不借此关闭自动化延期。
- [x] [Review][Defer] R5（Low，非阻塞覆盖改进）只读 SQL 的表名识别 [equipment/tests.py:275] — 已延期跟踪，未修复。已沿设备读链路核对仅有普通 ORM SELECT，无写入、写锁或 FR-018 调用，现有测试另有快照对比。风险：未来无引号或 schema 限定 SQL 可能漏报非预期表读取或误判。节点：新增其他 SQL 形态或预约／历史查询前加强捕获断言。
- [x] [Review][Defer] R6（Low，非阻塞覆盖改进）POST 的 CSRF 中间件对照 [equipment/tests.py:436] — 已延期跟踪，未修复。GET／HEAD 是正式读取边界，视图拒绝 POST，既有 CSRF 中间件仍启用。此项不计入 T-03 的 8／12。风险：真实 CSRF 校验失败与带有效令牌的 405 路径未在本 Story 成对冻结。节点：下次权限与 CSRF 回归维护时补两类真实中间件用例。
- [x] [Review][Defer] R7（Low，非阻塞覆盖改进）空说明的可见占位提示 [equipment/templates/equipment/detail.html:11] — 已延期跟踪，未修复。现有模板已保留合法空值的「暂无说明」分支，未见错误对象或字段串读。风险：将来移除占位处理，现有单行／多行非空夹具可能漏报。节点：下次维护详情边界测试时补空值断言。本次 R1 不得破坏现有空值行为。
- [x] [Review][Defer] R8（Low，既有测试工具缺口）隔离库设备残留预检 [lab_booking/test_runner.py:32] — 已延期跟踪，未修复。现有 runner 检查表／迁移／账号／会话，设备残留会由目录空数据或精确夹具断言报失败，未发现虚假通过。风险：他人遗留的数据可能使隔离测试不易诊断。节点：项目级隔离测试工具加固节点补设备基线，不改变当前连接守卫。
- [x] [Review][Defer] R9（Low，非阻塞覆盖改进）断言目录表格真实行序 [equipment/tests.py:322] — 已延期跟踪，未修复。当前服务按编号排序，模板原序遍历，正式 AC-1 要求行与记录对应，未单列排序为验收条件。风险：只检查 context 和每行是否存在，模板重排可能漏检。节点：下次目录排序、展示布局或测试维护时核对实际行序。
- [x] [Review][Defer] R10（Low，非阻塞覆盖改进）固定文档中的直达路由 [equipment/tests.py:338] — 已延期跟踪，未修复。当前 URLconf 与 README 一致，生成链接核对与直接请求覆盖现有路径。风险：未来能同步改变 URLconf、反向链接和测试而未发现历史字面 URL 失效。节点：下次 URL 或导航契约调整前，以字面 URL 固定直达对照。
- [x] [Review][Defer] R11（Low，非阻塞覆盖改进）T-03 拒绝响应中的状态无泄露断言 [equipment/tests.py:268] — 已延期跟踪，未修复。匿名／未知会话先登录跳转，无设备查询与设备模板渲染，静态未发现状态泄露。保留无业务变化与其他五字段断言。风险：未来拒绝响应若只泄露状态码或标签，当前正文断言可能漏报。节点：下次 T-03 权限回归加固时补状态断言，或明确断言拒绝跳转无正文。新证据如显示实际泄露，立即重评阻塞性。

**Rejected**

- 原始 #2 `blind-hunter`，`false`。现行 `Role.values` 与正式规格和数据库约束一致，仅三类角色。无当前误授，不重开批准方案。
- 原始 #7 `blind-hunter`，`maybe-false`。全集求值存在，但无当前规模退化证据或对应正式阈值。仅在有代表性规模及响应目标时复评，不增加分页。
- 原始 #10 `edge-case-hunter`，`false`。负数转换器限制成立，但批准路径使用正向 identity，运行角色不能指定 id，没有合规写入路径可达。

#### 2026-11-25 R1 独立复审

- R1 独立实测通过，结论为**建议关闭**。AC-1～AC-6 在隔离环境均满足，未发现新增验收阻塞。R1 勾选留给负责人确认，Sprint 仍为 `review`，R2 正式库验证未执行。 [复审报告](story-1-3-independent-recheck.md) · [独立回归原始输出](story-1-3-independent-recheck-output.txt)
- [x] [Review][Defer] 常规回归未启用 R1 浏览器布局验证 [equipment/tests.py:386] — 仅记验证维护观察，未修复。R1 的专项命令已经显式启用 Chrome，本轮 55/55 无跳过。后续修改 README 测试入口或 CI 时再区分两种验证，不扩大本次整改。 [延期台账](deferred-work.md)

**Rejected**

- #2 `low`。单行详情断言耦合当前样式属性，当前无错，拆分需要调整现有回归结构，不作为本次修补。
- #3 `low`。复杂空白组合未被单列，但真实渲染已覆盖三行、连续空格及换行，未发现 AC-2 实际退化，不扩展测试矩阵。
- #4 `maybe-false`。未证明窄屏超长无断点串是 R1 新增回归，也无相应正式布局约束。保留判定依据，不增加新 CSS。

## Implementation Notes

- 2026-11-25，负责人回复「批准并继续」，规格进入 `ready-for-dev`，按 Step 3 开始实施后转为 `in-progress`。正式业务库授权未获批。
- 代码修改前已由本会话运行原 45 项并全部通过，保留在[开发证据](story-1-3-dev-evidence.md)。开发完成后仍须全量回归。当前会话在隔离限制外获准执行过原 `.venv` 的基线命令，未更改解释器。
- 2026-11-25，完成实现及开发自测。首轮修正排序断言后，原 45 项与新增 9 项全量复跑通过，6 条正式 AC 均有自测证据。按负责人要求停在评审，等待独立会话。 [开发证据](story-1-3-dev-evidence.md)

## Spec Change Log

## Review Triage Log

2026-11-25，负责人选择保留行动项，仅 R1 待整改。R2/R8 保持原跟踪，R3–R7、R9–R11 条件性延期。首轮独立 Django 为 0 项，开发 54/54 不转记为独立。R1 整改后统一独立运行，再判断正式 AC 和回归。[独立处置](story-1-3-review-disposition.md) · [R1 整改交接](story-1-3-remediation-handoff.md) · [首轮独立评审](story-1-3-independent-review.md)

2026-11-25，原 Build 会话完成 R1 及全量自测（55/55），规格回到 `in-review`、Sprint 回到 `review`。十项延期和三项驳回不变，R1 待原独立会话针对性复审。 [开发证据](story-1-3-dev-evidence.md#2026-11-25-r1-整改与开发自测)

2026-11-25，独立复审四视角均返回结果，0 项新 Decision、0 项新 Patch，1 项非阻塞验证观察延期，另 3 项观察驳回。独立 55/55，R1 技术复审通过并建议关闭。未代签人工接受，也未将故事置为 `done`。 [复审报告](story-1-3-independent-recheck.md)

2026-11-25，负责人依据 [D-030](../../decision-log.md#d-030-2026-11-25-负责人关闭-r1-并批准-story-13-业务库验证) 正式关闭 R1。经单独批准，已补齐 R2 对应的正式库六列 SELECT 与三角色真实 Chrome 运行证据。原延期台账和裁决保留，不把运行验证记作最终验收。规格仍为 `in-review`，Sprint 仍为 `review`。 [实际运行证据](story-1-3-runtime-evidence.md)

## Design Notes

D-026 已授予 `SELECT(id)` 和六列 `INSERT`。保留两者，正式库只提议以下增量，不授予表级 SELECT、写权限、序列权限或转授权。另获负责人批准后才由 `lab_booking_migrator` 核实目标 `127.0.0.1:5433/lab_booking`、表归属及现有权限，再事务内授权并验证。

```sql
GRANT SELECT (number, name, category, location, description, status)
ON TABLE public.equipment_equipment TO lab_booking_app;
```

## Verification

原 `.venv`（Python 3.13.17），仅 `test` 模式和 `lab_booking_test@127.0.0.1:5433/test_lab_booking`。新增前运行原 45 项，新增后全量重跑。以 `.\.venv\Scripts\python.exe -B manage.py` 运行 `check`、`makemigrations --check --dry-run`、`test --keepdb --parallel 1 -v 2`。记录真实通过数与六条 AC、权限案例分母，三者不混计。隔离库通过不证明正式库权限生效。实验 A 不变。

2026-11-25，负责人按 D-031 正式接受 AC-1～AC-6、独立 55/55、R1 关闭和正式库三角色运行证据。规格与 Sprint 转为 `done`，原延期项及第二台 Windows 复现继续保留。未重新测试或改变数据库。 [最终验收](story-1-3-final-acceptance.md)
