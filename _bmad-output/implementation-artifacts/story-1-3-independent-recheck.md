# Story 1.3 R1 针对性独立复审

2026-11-25 · BMAD 6.12.4 `bmad-code-review` · `full`。**建议关闭 R1。AC-1～AC-6 在隔离验证范围内均满足，未发现新增验收阻塞。** 正式库授权和浏览器运行验证仍是 R2 的既有门槛。Sprint 保持 `review`，R1 是否正式关闭待负责人确认，不作最终验收。 [最新规格](spec-1-3-view-equipment-catalog.md) · [首轮独立评审](story-1-3-independent-review.md) · [处置与整改](story-1-3-review-disposition.md) · [整改交接](story-1-3-remediation-handoff.md)

## 1. 复审输入与真实执行

- 安装清单为 6.12.4。通过既有 `uv run --no-cache --python D:/ttAPP/python.exe` 方式解析 `workflow` 和项目配置，均退出 0。Python 3.14 仅用于 BMAD 工具，未用于项目测试。
- Step 1 确认 R1 增量为 2 文件、+67／−2、106 行、5729 字节。以 Build 整改前保存的差异在临时目录重建两个文件，与当前工作区比较。逆向补丁检查退出 0。SHA-256 `79EC19A1AAEA639F6D509901B50FE697923BFA6FA5751643D6F121A3F54E73D9`。负责人实际回复「确认继续」。Git 祖先基线为 [Story 1.2 收尾提交](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/09085cbc0b03dc5a3e03f54ba8604f15579b2533)，本次 R1 仍是工作区差异。
- 四个视角均返回结果。前三个先并行启动，Acceptance Auditor 首次因席位上限未启动，在席位释放后成功独立执行。Edge Case Hunter 返回明确空列表，Acceptance Auditor 未认定正式 AC 或约束有偏差。不把四个视角记成四人表决，也未给三位组员分派个人任务。
- 沙箱原解释器探测返回 103。一次具体命令获准后，本轮独立执行以下命令，原 `.venv` 实际为 Python 3.13.17，Chrome 为 159.0.8154.34。不安装或重建环境。连接守卫、隔离运行器先核对实际数据库、角色及版本，再开始测试。

```powershell
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
$env:LAB_BOOKING_DB_MODE = 'test'
if (-not $env:PGPASSFILE) { $env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf' }
$env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
if (-not $env:LAB_BOOKING_R1_CHROME) { $env:LAB_BOOKING_R1_CHROME = 'C:\Program Files\Google\Chrome\Application\chrome.exe' }
if (-not (Test-Path -LiteralPath $env:LAB_BOOKING_R1_CHROME -PathType Leaf)) { throw '缺少本机 Chrome，停止复审以免跳过 R1。' }
$reviewPython = '.\.venv\Scripts\python.exe'
$reviewVersion = & $reviewPython --version
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$reviewVersion
if ($reviewVersion -ne 'Python 3.13.17') { throw '解释器不是 Python 3.13.17，未执行测试。' }
& $reviewPython -B manage.py check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $reviewPython -B manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $reviewPython -B manage.py test --keepdb --parallel 1 -v 2
exit $LASTEXITCODE
```

独立执行 **55/55**，无跳过，耗时 **18.555s**，退出 **0**。系统检查无问题，迁移差异检查 `No changes detected`。按实际通过的测试方法计，Story 1.1 **32/32**、1.2 **13/13**、1.3 **10/10**。实际连接 `lab_booking_test@127.0.0.1:5433/test_lab_booking`、PostgreSQL 17.12。测试前后均为 10 张表、17 条迁移、0 个账号、0 条会话。该前后检查与每次请求的设备全字段快照是两类证据。首轮独立评审原记录仍为 0 项，整改时的 55/55 仍为开发自测，均未替代本轮独立实测。Story 1.2 的历史并发和事务外置探针不包含在这 55 项内。 [本轮原始输出](story-1-3-independent-recheck-output.txt) · [开发证据](story-1-3-dev-evidence.md)

## 2. 正式 AC 和 T-03

追溯 FR-003／002 → ADR-001／002／003 → PC-003／008／011 → 正式 AC → `EquipmentCatalogTests`。不以测试方法数代替 AC 数。 [PRD](../planning-artifacts/PRD.md) · [Architecture](../planning-artifacts/architecture.md) · [正式 AC](../planning-artifacts/epics.md#story-13-查看设备目录与具体设备详情) · [实测用例](../../equipment/tests.py)

| 正式 AC | 独立复审 |
| --- | --- |
| AC-1 | **满足。** 三角色经实际 Django 登录端点进入身份页，目录逐行核对三种设备状态及五个字段。 |
| AC-2 | **满足，R1 可关闭。** 三角色、三个设备合计 18 次详情响应与目标六字段一致，确认目录给出的链接目标、详情直达及“不承诺时段可预约”提示。R1 的独立 Chrome 用例通过，详见下文。既有 R4 关于从浏览器实际点击链接的延期仍保留。 |
| AC-3 | **满足。** 登录访问空目录返回 200，看到「暂无设备」，无虚构记录或占位数据行。 |
| AC-4 | **满足。** 已有设备时访问不存在的主键返回 404 和「设备不存在」，不替换成其他档案，设备快照不变。 |
| AC-5 | **满足。** 8 个未授权请求均为登录跳转，目标正确，无设备资料或设备 SQL，业务数据不变。12 个合法对照单列并全部成功。 |
| AC-6 | **满足。** 三轮共 12 次目录或详情读取，每次只有普通设备 SELECT，字段投影与主键条件正确，前后设备数量及全字段快照相等，无设备行级写锁或业务写操作。查询服务无预约或历史调用，不触发 FR-018。目前没有预约或历史模型，不将未建表述为已测。普通 SELECT 的正常读锁不等于写锁。 |

**R1。** 仅说明 `dd` 改为 `white-space: pre-wrap`，没有改动变量取值、空说明默认分支、Django 自动转义，也没有引入 `safe`、`mark_safe` 或关闭自动转义。隔离库回读值与合成三行说明一致。Chrome 从 Django 实际响应的离线快照中读到计算样式 `pre-wrap`，`innerText` 与原文字相等（包含连续空格、换行、引号、与号、标签和脚本文字），第二行的纵坐标后移，说明无被解析出的子元素。该用例无跳过。此证据是实际渲染，不代表正式业务库运行通过。 [模板](../../equipment/templates/equipment/detail.html) · [原始输出](story-1-3-independent-recheck-output.txt)

**T-03。** `/equipment/` 与 `/equipment/<int:pk>/` 的 GET／HEAD 逐个核对。无会话／未知会话 **8/8** 拒绝，302 至正确登录地址，合成档案的五个正文值均未泄露，未运行设备查询，快照无业务副作用。另核对两个视图均在取设备前由 Django 的 `login_required` 进入不含正文的重定向，只带登录和 `next` 路径，未构造设备状态或详情。既有 R11 是未来状态正文断言缺口，不改写为既有测试已经断言状态。启用学生、教师、业务管理员 **12/12** 返回 200，GET 显示合法档案，HEAD 无正文，无业务副作用。另四个注入身份守卫及两条 POST 拒绝独立计数。该结果不是完整 NFR-002 或全项目 T-03 验收。

## 3. 四视角发现与裁决

先保留来源和逐项判定，再合并。0 项 Decision、0 项 Patch、1 项非阻塞验证观察延期、3 项驳回。R1 是先前已批准的 Patch，本轮取得可关闭的复审证据，不计为新增问题。D-029 的十项延期和三项原始驳回原样保留。

| # | 来源 | 结论 | 核对及去向 |
| --- | --- | --- | --- |
| 1 | blind-hunter | low | `equipment/tests.py:376–388` 未配置 Chrome 时，源码转义断言即使成功，整个方法仍报告跳过。报表不单列浏览器前已执行的转义断言。与 #5 同源，延期验证维护。 |
| 2 | blind-hunter | low | `equipment/tests.py:368–373` 的单行详情断言依赖说明 `dd` 的属性和样式，未来等价重构会连带调整测试。当前断言覆盖一致，拆分断言需重构测试，不作为本次修补。驳回。 |
| 3 | blind-hunter | low | `equipment/tests.py:377–405` 未加入缩进和连续空行的坐标矩阵。现有真实三行文本的完整 `innerText` 与首两行坐标已覆盖 R1，未发现其他合法文本实际退化。扩展组合不作为本次修补。驳回。 |
| 4 | blind-hunter | maybe-false | `detail.html:11` 的超长无断点串在窄屏可能溢出，但未证明 R1 新增该行为或违反正式 AC。认定需同内容、同窄视口的整改前后对照及正式布局要求。本次不引入新样式规则。驳回。 |
| 5 | verification-gap | low | 常规 README 回归没有启用 Chrome。没有 Chrome 时，未来计算样式退化可漏检。与 #1 合并为同一非阻塞观察，本轮明确启用 Chrome 且无跳过。 |

延期观察仅描述常规命令未含浏览器布局验证。项目原有普通套件并不要求浏览器，本轮独立 R1 命令已明确失败前置而非静默省略。后续维护 README 测试入口或 CI 时可区分默认回归与启用 Chrome 的 R1 验证，不新增本次整改范围。 [延期台账](deferred-work.md)

## 4. 正式库最小 SELECT 与运行验证方案（仅核对）

目前历史证据显示 `lab_booking_app` 已有主键 `SELECT(id)` 和六列 INSERT。目录 SELECT 主键、编号、名称、类别、位置、状态，按编号排序。详情 SELECT 后五列及 `description`，按主键过滤。合并投影后，只需补以下六列。保留原 INSERT 与主键读权限，不做表级 SELECT、额外写入、序列权限或转授权。 [D-026 实际授权](story-1-2-runtime-evidence.md#实际授权) · [现行查询](../../equipment/services.py) · [部署方案](../../README.md#windows-本地启动)

```sql
GRANT SELECT (number, name, category, location, description, status)
ON TABLE public.equipment_equipment TO lab_booking_app;
```

1. 另获负责人批准后，才用 `lab_booking_migrator` 核对实际目标 `127.0.0.1:5433/lab_booking`、当前与会话角色、服务器版本、表所有者及既有有效权限。有漂移先停止。事务内执行唯一增量 GRANT 并复核七列有效 SELECT、原 INSERT 和禁止新增的权限。区分列级全读与表级 SELECT。
2. 用新 `lab_booking_app` 连接做只读目录、详情投影，对照既有获准演示档案。另批浏览器运行后，用三类现有预置账号实际登录、从身份页点击目录和目标档案、直达同一详情、比对数据并验证 404 和退出后跳转。记录状态码、角色、设备全字段前后对照。认证会话及 `last_login` 不算设备业务写入。
3. 多行、空目录及维修／停用继续以隔离证据覆盖。不为演示创建设备、修改说明或状态、清空目录，不打印凭据。隔离角色的 55/55 不证明正式运行角色的授权已生效。

## 5. 课程与状态

第 26 页的需求、架构、AC 到实测已可追溯。第 27 页保留首轮未执行、负责人 D-029、整改、自测、独立复审的分立证据。第 33 页保存本报告、命令原始输出及故事状态。第 34 页不改实验 A，不把本轮数据计入对照。第 36 页只记录已有实际决定和本轮结果，不代签 R1 关闭、授权或最终验收。PPT 页码依据课程基线和团队记录，未声称逐页核验原件。Story 1.3 保持 `review`，1.4 保持 `backlog`。本轮未改业务代码、未连接或修改业务库、未执行授权、未暂存、提交或推送。 [课程要求](../../docs/course-requirements.md) · [D-029](../../decision-log.md#d-029-2026-11-25-负责人批准-story-13-独立评审处置) · [Sprint 跟踪](sprint-status.yaml)
