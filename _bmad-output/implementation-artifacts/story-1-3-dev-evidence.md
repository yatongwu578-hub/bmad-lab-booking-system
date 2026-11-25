# Story 1.3 开发证据

## Checkpoint 1 与实施前基线

- BMAD 安装清单版本为 `6.12.4`。原项目 `uv run --no-cache` 渲染命令退出 `0`，执行其返回的 `13340bf8aef33bedeff3/workflow.md`。2026-11-25 负责人实际回复「批准并继续」。未授权正式业务库授权、Git 提交或推送。
- 代码修改前的基线为 `09085cbc0b03dc5a3e03f54ba8604f15579b2533`。Story 1.1 和 1.2 均为 `done`。Story 1.3 规格实际经历 `draft`、`ready-for-dev`、`in-progress`，Sprint 跟踪从 `backlog` 转为 `in-progress`。
- 受限 PowerShell 中原 `.venv` 的 `--version` 退出 `103`，未开始数据库测试。获具体命令授权后重跑，原解释器报告 `Python 3.13.17`，无需重装或重建虚拟环境。

```powershell
& '.\.venv\Scripts\python.exe' --version
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$env:LAB_BOOKING_DB_MODE = 'test'
if (-not $env:PGPASSFILE) { $env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf' }
$env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
& '.\.venv\Scripts\python.exe' -B manage.py test --keepdb --parallel 1 -v 2
exit $LASTEXITCODE
```

退出码 `0`。连接守卫确认 `127.0.0.1:5433/test_lab_booking`、`lab_booking_test`、PostgreSQL 17.12。测试前后均为 10 张表、17 条迁移、0 个账号、0 条会话。

```text
Found 45 test(s).
System check identified no issues (0 silenced).
Ran 45 tests in 13.832s
OK
```

这是原套件基线结果，不是 Story 1.3 的 AC 验收。 [规格](spec-1-3-view-equipment-catalog.md) · [Story 1.2 Git 基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/09085cbc0b03dc5a3e03f54ba8604f15579b2533)

## 实现后检查与全量回归

首次及修正后均用以下命令。只使用原 `.venv`、既有测试角色和隔离库，无连接或改动业务库。

```powershell
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:LAB_BOOKING_DB_MODE = 'test'
if (-not $env:PGPASSFILE) { $env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf' }
$env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$storyPython = '.\.venv\Scripts\python.exe'
& $storyPython --version
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $storyPython -B manage.py check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $storyPython -B manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $storyPython -B manage.py test --keepdb --parallel 1 -v 2
exit $LASTEXITCODE
```

首次系统检查和迁移检查均通过。测试跑完 54 项，耗时 `17.009s`，退出 `1`。AC-6 测试的三轮子断言误将 Django 生成的 `ORDER BY 2 ASC` 判作失败。投影第二列为 `number`。仅将该断言改为检查返回记录按编号排序，保留 SQL 投影、禁止写入和行锁、目标主键及数据快照断言。业务实现和正式 AC 未改。

同命令复跑退出 `0`，原 45 项和新增 9 项均通过。实际输出摘录如下。

```text
Python 3.13.17
System check identified no issues (0 silenced).
No changes detected
Ran 54 tests in 16.732s
OK
Found 54 test(s).
已核验并保留 127.0.0.1:5433/test_lab_booking，角色 lab_booking_test，PostgreSQL 17.12。
测试前：10 张表、17 条迁移、0 个账号、0 条会话。
System check identified no issues (0 silenced).
测试后：10 张表、17 条迁移、0 个账号、0 条会话。
```

## 正式 AC 自测对照

FR-003／FR-002 → ADR-001／002／003 → Story 1.3 正式 AC → `equipment/tests.py:EquipmentCatalogTests`。以下是开发自测，非负责人最终验收，也不是独立评审。 [PRD](../planning-artifacts/PRD.md) · [Architecture](../planning-artifacts/architecture.md) · [正式 AC](../planning-artifacts/epics.md#story-13-查看设备目录与具体设备详情) · [用例源码](../../equipment/tests.py)

| AC | 复跑通过的断言 |
| --- | --- |
| AC-1 | 学生、教师、业务管理员各经真实 Django 登录表单和 CSRF 校验进入身份页，再读取目录。每个角色逐行匹配三个状态设备的五个列表字段与详情链接。 |
| AC-2 | 三角色、三台设备分别验证列表所给链接及直接访问，共 18 次详情读取。六个字段与目标记录匹配，无其他设备资料，明确不承诺时段可预约。 |
| AC-3 | 无设备时 200，提示「暂无设备」，无占位数据。 |
| AC-4 | 有设备但目标主键不存在时 404，明确「设备不存在」，无替代档案，设备全字段快照不变。 |
| AC-5 | 无会话和未知会话被引导登录。两条路由逐例验证拒绝、无数据泄露、不查询设备、设备快照不变。合法对照单列。 |
| AC-6 | 三轮各读一次目录和三次详情，共 12 次。每次设备只执行一条普通 SELECT，投影对应页面字段，无写入、无行锁，设备数量及全字段快照不变。无预约／历史 SQL 或调用，当前也没有对应模型，未造表取证。 |

### T-03 本 Story 权限成对用例

目录 `/equipment/` 与已有设备的详情 `/equipment/<int:pk>/` 分别验证 GET、HEAD。设备夹具只在回滚事务内使用。

| 组别 | 组合和实测 |
| --- | --- |
| 未授权分母 | 无会话／未知会话 × 两路由 × GET／HEAD，**8/8**。均为 302 至 `/login/`，`next` 正确，拒绝正文不含档案内容，不查询设备，前后快照相同。 |
| 合法对照 | 三角色 × 两路由 × GET／HEAD，**12/12**。均为 200，GET 展示匹配档案，HEAD 无正文，设备数据不变。 |
| 补充守卫 | 注入停用账号和无效角色各访问两路由，**4/4** 返回 403，Django 管理标志不能越权。另有两条管理员 POST 均 405、不读设备、不改业务数据。这两组不混入会话拒绝分母。 |

这些结果只覆盖 Story 1.3 的权限切片，不关闭全项目 T-03 或完整 NFR-002，也不改变 Story 1.2 的延期项。

## 评审交接与课程证据

- 第 26 页的需求、架构、AC 和测试追溯见上表。第 27 页的单 Story 开发已停在 `review`，下一步另开会话执行 `bmad-code-review`，不提前标记 `done`。
- 第 33 页的实现、测试、README 和状态变化在工作区可核对。第 34 页的实验 A 候选与条件维持原计划，Story 1.3 自测不纳入实验，第 36 页只登记实际审批。PPT 页码按仓库课程基线和团队记录核对，未直接核验原件。 [课程基线](../../docs/course-requirements.md) · [团队核对](../../docs/team/sprint-planning-review.md#5-11-月-17-日课程核对与规划提交记录) · [D-028](../../decision-log.md#d-028-2026-11-25-负责人批准-story-13-实施规格)
- 未执行数据库迁移或正式库授权。运行角色的六列 SELECT 待负责人单独批准，隔离测试成功不能代替业务角色验证。Story 1.4 保持 `backlog`，未暂存、提交或推送。 [README](../../README.md#windows-本地启动) · [Sprint 状态](sprint-status.yaml)

## 2026-11-25 R1 整改与开发自测

按 BMAD 6.12.4 Build Step 4 的 Patch 路线续接 [D-029 已批准处置](../../decision-log.md#d-029-2026-11-25-负责人批准-story-13-独立评审处置)。沿用原渲染命令和 `UV_PYTHON=D:/ttAPP/python.exe`，退出 `0`，使用返回的 `13340bf8aef33bedeff3/workflow.md`。原评审会话未能落盘的 Review Findings 和延期台账按批准文本补录。只修正式 AC-2 的多行说明显示，未改规格冻结区、FR、ADR、Sprint 范围或延期裁决。 [处置](story-1-3-review-disposition.md) · [交接](story-1-3-remediation-handoff.md)

设备说明的 `dd` 单独设置 `white-space: pre-wrap`，原「暂无说明」分支和 Django 自动转义保持不变。新增 R1 回归先用隔离库合成设备回读说明，再从已登录测试请求取得 Django 实际响应。Chrome 159.0.8154.34 使用临时文件与配置加载该 HTML，不启动站点。断言浏览器计算样式为 `pre-wrap`、可见 `innerText` 与存储的合成三行文字完全一致、第二行的实际纵坐标低于第一行，说明容器内无被解析出的子元素。连续空格、换行、与号、引号、标签及脚本文字均按原样呈现。不是只检查响应源码。 [模板](../../equipment/templates/equipment/detail.html) · [Django／Chrome 用例](../../equipment/tests.py)

受限命令的原 `.venv --version` 退出 `103`。获准执行具体命令后，原解释器实际为 Python 3.13.17，未重装、重建或替换。以下命令在仓库根目录运行，复审如需运行相同浏览器断言，需设置 `LAB_BOOKING_R1_CHROME` 为本机 Chrome 路径，否则该浏览器用例报告跳过。

```powershell
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$env:PYTHONIOENCODING = 'utf-8'
$env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
$env:LAB_BOOKING_DB_MODE = 'test'
if (-not $env:PGPASSFILE) { $env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf' }
$env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$env:LAB_BOOKING_R1_CHROME = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$r1Python = '.\.venv\Scripts\python.exe'
$r1Version = & $r1Python --version
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$r1Version
if ($r1Version -ne 'Python 3.13.17') { throw '预期 Python 3.13.17，未运行测试。' }
& $r1Python -B manage.py check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $r1Python -B manage.py makemigrations --check --dry-run
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $r1Python -B manage.py test --keepdb --parallel 1 -v 2
exit $LASTEXITCODE
```

实际退出码 `0`。校验输出如下。

```text
Python 3.13.17
System check identified no issues (0 silenced).
No changes detected
test_ac2_description_keeps_multiline_literal_text_in_chrome (equipment.tests.EquipmentCatalogTests.test_ac2_description_keeps_multiline_literal_text_in_chrome) ... ok
Ran 55 tests in 18.453s
OK
已核验并保留 127.0.0.1:5433/test_lab_booking，角色 lab_booking_test，PostgreSQL 17.12。
测试前：10 张表、17 条迁移、0 个账号、0 条会话。
测试后：10 张表、17 条迁移、0 个账号、0 条会话。
```

实际通过数按测试归属为 Story 1.1 **32/32**、1.2 **13/13**、1.3 **10/10**，无跳过。T-03 回归仍为 8 个拒绝、12 个合法对照。这些是开发自测结果，不是独立复审、业务库运行验证或最终验收，也不按测试数量折算 AC 通过数。

课程核对沿用仓库基线。第 26 页保留 FR-003／002 → ADR-001／002／003 → AC-2 → R1 证据链。第 27 页记录整改后回到 `review`，交回原独立会话。第 33 页保留差异、测试及状态证据。第 34 页不改变实验 A，也不纳入本次数据。第 36 页复用 D-029 真实决定，不新增人类审批。没有访问或改动业务库、执行 GRANT 或迁移、开发 Story 1.4、标记 `done`、暂存、提交或推送。 [课程要求](../../docs/course-requirements.md) · [Sprint 跟踪](sprint-status.yaml) · [Git 基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/09085cbc0b03dc5a3e03f54ba8604f15579b2533)
