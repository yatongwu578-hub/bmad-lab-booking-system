# Story 1.3 独立代码评审与 Step 4 检查点

2026-11-25 · BMAD 6.12.4 `bmad-code-review` · `full` · 三位组员共同操作 Codex 与审阅，未据此代填个人任务、逐人成果或人工验收。

**当前结论**：四个视角的静态评审与裁决已完成，独立数据库回归尚未执行。R1（Medium）影响 AC-2 的详情显示一致性，建议修复并补证。正式业务运行还待另批最小授权及浏览器核验（R2），本轮不具备提交负责人最终验收条件。人工行动处置尚待确认，Story 1.3 保持 `review`，Story 1.4 保持 `backlog`。

## 1. 输入与实际执行

- 基线为 Story 1.2 最终验收提交 `09085cbc0b03dc5a3e03f54ba8604f15579b2533`。审阅 14 个文件，含 8 个已跟踪和 6 个未跟踪，新增 594 行、删除 6 行。统一差异 757 行、45,548 字节，SHA-256 `E04C85595263E79DDF3625FD06CB80DADD43ACC9BF0CA5EFC5F41852C7B5DCD4`，`git apply --reverse --check` 退出 0。无暂存变更。该快照不包含本次新写的评审记录。
- 已读取仓库约定、课程基线、正式 PRD／Architecture／project-context／epics、Sprint 计划与状态、根目录决策日志、延期台账、实施规格与开发证据。基线比对未见正式规划文件、组件配置、迁移或模型变化。 [课程基线](../../docs/course-requirements.md) · [正式 PRD](../planning-artifacts/PRD.md) · [Architecture](../planning-artifacts/architecture.md) · [项目约束](../planning-artifacts/project-context.md) · [正式 AC](../planning-artifacts/epics.md#story-13-查看设备目录与具体设备详情) · [Sprint 计划](../planning-artifacts/sprint-plan.md) · [决策日志](../../decision-log.md)
- 安装清单为 6.12.4。按已有 `uv run --no-cache --python D:/ttAPP/python.exe` 方式解析配置成功。通用渲染器提示该技能没有 `workflow.md`，不是 `manifest.json` 权限问题。依该版本安装技能规定的 `SKILL.md` 和四个步骤执行。Python 3.14 仅用于 BMAD 工具。
- Step 1 团队实际回复「确认继续」。Step 2 中 Blind Hunter、Edge Case Hunter、Verification Gap Reviewer 三个视角先占用可用席位。Acceptance Auditor 第一次派发得到 `agent thread limit reached`，待席位释放后用独立无继承会话成功派发。四个视角均收到最终报告，未有缺失层，未声称四个同时启动。
- 原 `.venv\Scripts\python.exe --version` 退出 103，未能启动 `C:\Users\15860\AppData\Local\Programs\Python\Python313\python.exe`。`pyvenv.cfg` 记录 3.13.17。本轮具体沙箱提权请求（原解释器、系统检查、迁移检查、全量隔离回归）被自动拒绝，原因是审批策略 `sandbox_approval: false`，未向用户弹出审批。未重装 Python 或重建 `.venv`。
- **独立实测 0 项启动、0 项完成。** 已向团队提供命令脚本，请在已获准的普通 PowerShell 协助取证，截至本检查点未收到实际输出。开发证据为原 45/45、当前 54/54，不能转记为本轮独立通过。静态清点 54 个方法为 Story 1.1 32（accounts 25、lab_booking 7）、Story 1.2 13、Story 1.3 9。Story 1.2 独立并发／事务探针不在 54 项内，本轮未重跑。 [开发证据](story-1-3-dev-evidence.md) · [1.2 最终验收](story-1-2-final-acceptance.md)

获准环境独立复跑须核验原解释器报告 Python 3.13.17，显式设置 `DJANGO_SETTINGS_MODULE=lab_booking.settings` 和 `LAB_BOOKING_DB_MODE=test`，使用已批准 `PGPASSFILE` 与进程临时密钥，顺序运行 `-B manage.py check`、`-B manage.py makemigrations --check --dry-run`、`-B manage.py test --keepdb --parallel 1 -v 2`。每步非零即停止。收录完整输出、退出码、`127.0.0.1:5433/test_lab_booking`、实际角色 `lab_booking_test` 及前后状态。不得连接业务库或换用其他解释器。没有真实运行证据前，不宣称 1.1／1.2 无回归。

## 2. 正式 AC 独立核对

依据 FR-003／002 → ADR-001／002／003 → PC-003／007／008／011 → 正式 AC → `equipment/tests.py:EquipmentCatalogTests`。下表“吻合”仅表示独立静态核对吻合，所有项的独立隔离运行都待补证。

| AC | 独立核对与对应断言 |
| --- | --- |
| AC-1 | 静态吻合。三种角色走真实登录表单测试，一行对应一件设备，验证五字段及三状态标签和详情链接。应用对有效登录／账号／角色先检查后查询，不按设备状态滤除记录。 |
| AC-2 | **部分不符合，R1。** 查询按主键返回目标六字段，目录锚点及直达指向同一目标，明确“可用”不代表指定时段可预约。单行夹具覆盖三角色、三状态及 18 次访问，但模板按默认 CSS 折叠合法说明中的换行与连续空白，页面会丢失分行表达。此为代码与标准语义静态核实，不记作浏览器实测。 |
| AC-3 | 静态吻合。无设备返回正常空页，「暂无设备」以及无表格占位有自动化断言。 |
| AC-4 | 静态吻合。合法格式但不存在的主键查询返回 404 和「设备不存在」，不回退其他记录。测试核对响应及设备全字段快照。 |
| AC-5 | 静态吻合。无有效会话请求先跳转登录，实际视图未读取设备或泄露记录。现有矩阵覆盖 8 个拒绝及 12 个合法对照；R11 是状态无泄露断言缺口，不是已发现的状态泄露。 |
| AC-6 | 静态吻合。服务只构造求值两条普通 ORM SELECT，无 `select_for_update`、写事务或预约／历史调用。测试三轮共 12 个设备读取，检查逐次全快照、SQL 投影、禁止写入和行锁。当前未实现预约／历史模型，不能宣称实际检查了不存在的业务表。普通 SELECT 的正常 PostgreSQL 读锁不等同于设备写锁。 |

R1 的可达来源是原有 `Equipment.description` TextField 与正常管理员新增表单；输入可以包含多行及连续空格，模板 `equipment/templates/equipment/detail.html:11` 的普通 `dd` 没有保留空白规则。默认 `white-space: normal` 折叠这些空白，只影响呈现、不改变数据库内容。可最小采用等价于 `white-space: pre-wrap` 的显示处理，保留 Django 自动转义，并用合法多行夹具及可见文本断言复验，不新增编辑入口。 [W3C CSS Text §3](https://www.w3.org/TR/css-text-3/#white-space-property)

### T-03 本 Story 证据边界

| 组别 | 可检查断言与实际状态 |
| --- | --- |
| 拒绝 | 无会话／未知会话 × 目录／已有详情 × GET／HEAD，共 8 例。断言 302、正确 `next`、否定五个夹具字段、无设备查询、全字段快照不变，状态标签尚未直接断言。源码、开发证据齐备，开发报告 8/8，独立未实测。 |
| 合法 | 学生／教师／业务管理员 × 两端点 × GET／HEAD，共 12 例。断言 200、GET 目标内容与身份、HEAD 无正文、投影与快照不变。开发报告 12/12，独立未实测。 |
| 补充 | 四项注入身份守卫和两项 POST 拒绝不混入 8／12 分母。注入只证明业务守卫，普通测试 Client 的 POST 405 不代表经过真实 CSRF 中间件后的两种结果。 |

范围复核：新路由只有目录和主键详情，现有新增路径未改。无设备编辑、状态转换、预约或按日期占用查询。未关闭项目级 T-03 或完整 NFR-002。

## 3. 四视角原始判定及合并

Blind Hunter 按 45.548 kB 计算要求至少 7 项，实际返回 8 条，其中一条含两个独立核查点，因此归一为 #1–9。Edge Case Hunter 为 #10–12，Verification Gap Reviewer 为 #13–16，Acceptance Auditor 为 #17–19。以下先逐项判定，再按共享根因合并。3 条原始发现驳回。

| # | 来源 | 判定 | 主张与核对 | 位置 | 去向 |
| --- | --- | --- | --- | --- | --- |
| 1 | blind-hunter | `medium` | 发布角色缺少新读取权限。D-026 只授 SELECT(id)，按旧 ACL 上线，两页面无法读到新增投影。另批运行依赖，非代码缺陷。 | `README.md:95;equipment/services.py:33–44` | R2 |
| 2 | blind-hunter | `false` | Role.values 将自动接纳未来角色。当前枚举及数据库约束仅三种角色，规格明确要求 Role.values。无当前误授。 | `equipment/services.py:24–26` | 驳回 |
| 3 | blind-hunter | `low` | 停用账号测试用了身份注入。验证业务守卫，但未覆盖真实会话登录后账号停用的全链路。 | `equipment/tests.py:421–434` | R3 |
| 4 | blind-hunter | `low` | 目录点击路径使用反向 URL 与合成 Referer。HTML 锚点正确且目标读回已测，但未取页面实际 href 发请求。 | `equipment/tests.py:338–363` | R4 |
| 5 | blind-hunter | `low` | SQL 表名识别未覆盖未加引号或 schema 限定。正则仅取 FROM/JOIN 后首个带引号片段，可能漏检其他只读表或误识别 public。当前两个 ORM 查询无此问题。 | `equipment/tests.py:275–297` | R5 |
| 6 | blind-hunter | `low` | 补充 POST 测试绕过 CSRF。默认 Django Client 到达视图验证 405，无法覆盖真实 CSRF 链。非 T-03 8/12 分母。 | `equipment/tests.py:436–445` | R6 |
| 7 | blind-hunter | `maybe-false` | 目录和 HEAD 对全集求值会带来规模风险。全集求值成立，当前规模性能问题未证明。需代表性规模与响应目标才可复评，范围无分页要求。 | `equipment/services.py:33–36;equipment/views.py:22–35` | 驳回 |
| 8 | blind-hunter | `low` | 空说明缺少展示用例。回归夹具均不为空，不能验证已有的空说明占位。 | `equipment/templates/equipment/detail.html:11;equipment/tests.py:231–247` | R7 |
| 9 | blind-hunter | `medium` | 多行说明会失去可见分行。既有多行文本合法，详情未保留换行，与本次读出的说明展示不完全一致。 | `equipment/templates/equipment/detail.html:11` | R1 |
| 10 | edge-case-hunter | `false` | 负主键会使列表无法反向构造链接。Django 转换器确实不接负数，但已批准应用只用正向 identity，运行角色不能指定 id，没有合规写入路径可达。 | `equipment/urls.py:9` | 驳回 |
| 11 | edge-case-hunter | `low` | 预建隔离库未预检设备基线。既有 runner 验证了表／迁移／账号／会话，未查设备。他人遗留记录会报告用例失败而非假通过，当前未见残留证据。 | `lab_booking/test_runner.py:32–55;equipment/tests.py:365–370` | R8 |
| 12 | edge-case-hunter | `low` | 补充 POST 未覆盖启用 CSRF 实际分支。证据仅 405，带／不带有效令牌的中间件行为未覆盖。 | `equipment/tests.py:436–445` | R6 |
| 13 | verification-gap | `low` | 排序断言只查 context，不查表格行序。对每行独立断言，模板仅改变遍历顺序时可漏报。排序不是正式 AC 的单列条件。 | `equipment/tests.py:322–336,447–459` | R9 |
| 14 | verification-gap | `low` | 反向解析未固定文档记录的直达 URL。测试及模板均跟随 reverse；当前路径正确，但改 URL 可能不触发测试失败。 | `equipment/tests.py:229,338–352` | R10 |
| 15 | verification-gap | `low` | 详情没有空说明断言。非空夹具不能证明暂无说明分支，当前模板分支存在。 | `equipment/tests.py:231–247,356–363` | R7 |
| 16 | verification-gap | `medium` | 隔离套件无法检出正式运行角色漏授权。测试角色不同，若漏 description，目录可成功但详情失败，需另批运行复验。 | `equipment/services.py:35–42;lab_booking/test_runner.py:14–26` | R2 |
| 17 | acceptance-auditor | `medium` | AC-2 多行说明被折叠。普通 HTML 空白处理吞并合法文本中的分行／连续空白，仅单行夹具不检出。 | `equipment/templates/equipment/detail.html:11` | R1 |
| 18 | acceptance-auditor | `low` | T-03 无泄露断言未核对设备状态。助手检查五个字段，但没有状态码或标签断言。拒绝分支静态未返回任何设备，属证据覆盖缺口。 | `equipment/tests.py:268–271` | R11 |
| 19 | acceptance-auditor | `medium` | 正式库增量列权限尚未批准。现有已核验 ACL 不覆盖新投影。文档正确标明待审批，不能把隔离回归当运行验收。 | `README.md:95–99;equipment/services.py:35–42` | R2 |

| 编号 | 分级 | BMAD 路由 | 裁决及建议 |
| --- | --- | --- | --- |
| R1 | Medium，阻塞 AC-2 可见一致性 | `patch` | 保留详情中已存设备说明的分行和有意义空白。现有合法多行说明在页面折叠。建议保留安全转义，仅调整说明显示并用隔离库多行夹具验证。（#9,17） |
| R2 | Medium，发布门槛，不是代码缺陷 | `defer` | 另批业务库最小列级 SELECT 与实际运行验证。D-026 只授 SELECT(id)，正式运行缺少六列权限。按本轮已定范围不授权，在负责人另批部署后验证。（#1,16,19） |
| R3 | Low，非阻塞 | `patch` | 补真实会话在账号停用后的现有会话回归。现有注入用例验证服务守卫，但不是启停后既有会话的全链路。（#3） |
| R4 | Low，非阻塞 | `patch` | 使用渲染出的实际 href 验证目录点击路径。已断言锚点和反向 URL，仍可强化由页面锚点直接驱动的证据。（#4） |
| R5 | Low，非阻塞 | `patch` | 增强只读 SQL 断言的表名识别。当前实际 ORM 读取符合边界，测试对无引号或 schema 限定名称的判定不健全。（#5） |
| R6 | Low，非阻塞 | `patch` | 补 POST 的真实 CSRF 中间件对照。测试默认绕过 CSRF，只能证明视图 405。与 8 项拒绝、12 项对照分开。（#6,12） |
| R7 | Low，非阻塞 | `patch` | 覆盖空说明详情的可见提示。合法空值已有暂无说明分支，需补不同于多行值的独立回归。（#8,15） |
| R8 | Low，非阻塞 | `defer` | 隔离库运行器缺少设备数据残留的预检。既有测试工具清点表、迁移、账号与会话，异常设备残留由用例报错。随项目级隔离测试工具加固跟踪，不修改本 Story 的运行器。（#11） |
| R9 | Low，非阻塞 | `patch` | 断言目录实际渲染出的行顺序。当前服务和模板的顺序匹配，无现存可见错误。（#13） |
| R10 | Low，非阻塞 | `patch` | 直达对照固定文档中的字面路由。当前路由匹配 README，纯 reverse 可能让未来入口改名未被测出。（#14） |
| R11 | Low，非阻塞 | `patch` | T-03 拒绝响应补设备状态无泄露断言。静态未见泄露。检查状态字段／标签或直接断言匿名跳转没有响应体。（#18） |

0 项 `decision-needed`，9 项 `patch` 候选，2 项 `defer`，3 条原始发现驳回。仅 R1 建议作为 AC 阻塞缺陷处理。R2 是上线证据门槛，不是代码缺陷。其余为可合理延期的非阻塞测试覆盖或工具问题。为区别评审方建议和团队正式处置，未将 Patch 候选标为已修复、未替团队接受延期或移动 Story 状态。既有 1.1／1.2 延期不重开。

## 4. 正式业务库增量授权与验证计划（未执行）

基于设备迁移及 D-026 的已核验运行证据，实际表为 `public.equipment_equipment`，对象所有者为 `lab_booking_migrator`，应用运行角色为 `lab_booking_app`。目录投影为 `id, number, name, category, location, status`，并按 `number` 排序。详情读取 `number, name, category, location, description, status`，谓词使用 `id`。保留已有 `SELECT(id)` 与六列 `INSERT`，只新增下列六列读取权限。 [D-026 实际授权](story-1-2-runtime-evidence.md#实际授权) · [README](../../README.md#windows-本地启动)

```sql
GRANT SELECT (number, name, category, location, description, status)
ON TABLE public.equipment_equipment TO lab_booking_app;
```

1. 另获明确批准后才用 `lab_booking_migrator` 连接 `127.0.0.1:5433/lab_booking`。先核对 `current_database()`、`session_user`、`current_user`、地址端口、服务器版本及表 owner，读取已有列级和表级有效权限，存在权限漂移即停止。用 `psql -X -w -v ON_ERROR_STOP=1 --single-transaction` 在同一事务内校验目标、执行唯一 GRANT 和校验结果，任何不符均回滚。
2. 逐列用 `has_column_privilege` 验证七列 SELECT（含原 id），原六列 INSERT 保持且 id 无 INSERT，各列无 SELECT 转授权或 UPDATE。用 `has_table_privilege` 验证无表级 SELECT／INSERT／UPDATE／DELETE／TRUNCATE／REFERENCES／TRIGGER／MAINTAIN，无新增 schema CREATE、序列或角色权限。不要以“列全可读”误认“表级 SELECT 已授予”。
3. 用新 `lab_booking_app` 连接复核实际目标和有效权限，在只读事务内执行目录投影及带已存在主键的详情投影，逐项核对已批准保留的 Story 1.2 演示设备。不新增、不编辑、不补业务迁移或夹具。登录产生的会话与 `last_login` 属认证副作用，不等同于设备或预约写入。
4. 负责人另批后，沿用原 `.venv`、`runtime` 模式和受保护凭据，在本机 `127.0.0.1:8000` 用 `runserver --noreload` 启动。确认守卫身份为 `lab_booking_app`。在隔离浏览器会话中先匿名直达目录及已存在详情，记录登录跳转及无设备内容，再用现有三类账号登录。每类经身份页进入目录、实际点击详情链接、直接打开同一详情、核对字段和预约提示，重复访问、验证不存在主键的 404，正常退出后再次检查两端点拒绝访问。保存脱敏响应、角色、页面截图或断言、数据库设备数量及全字段前后比对，结束临时服务，不打印凭据。
5. 空目录与维修／停用通过隔离库验证，不清空业务表或人为调整生产设备状态。若整改后业务库没有合适的多行记录，不为验证 R1 改档案，在隔离库使用合法多行夹具完成浏览器复验。

## 5. 课程和人工检查点

- 第 26 页。正式 FR、ADR、PC、AC 和测试可追溯，未改动已批准方案。
- 第 27 页。独立会话与开发自测分离。保留四视角、首轮问题、权限失败和待补运行证据。人工处置、复审和最终验收尚待实际发生。
- 第 33 页。评审记录、规格、代码、测试、README 和 Sprint 跟踪纳入项目证据，不以本次结果代替项目整体验收。
- 第 34 页。未改变实验 A 的对照范围、条件或数据，未把本 Story 运行或评审计入实验 A。
- 第 36 页。当前只有 Step 1 的真实确认及原 D-028，未代签新的技术处置、授权或最终验收决定。收到人工决定后，再按实际触发、建议、判断、结果及事后验证写根目录日志。

PPT 原件未找到，页码依据课程基线及团队确认口径，并非逐页核查原件。未修改业务代码、未执行正式库权限或浏览器业务访问、未开发 Story 1.4、未标 `done`、未暂存、提交或推送。 [课程基线](../../docs/course-requirements.md) · [团队核对](../../docs/team/sprint-planning-review.md#5-11-月-17-日课程核对与规划提交记录) · [Sprint 状态](sprint-status.yaml)

### Step 4 文件写入检查点

工作区允许创建本报告，但尝试向既有实施规格追加 Review Findings、向既有延期台账追加 R2/R8 时，写入被拒绝。两份原文件未改变。本报告保留所有待写记录，不宣称 BMAD Step 4 的回写或人工处置已完成。工作区有写入能力后，按下列待回填内容分别追加，再由团队决定保留行动项或逐项审阅。

#### 既有规格中待插入的记录

### Review Findings

2026-11-25，BMAD 6.12.4 `full` 四视角静态评审与裁决。0 项 Decision、9 项 Patch 候选（仅 R1 建议阻塞正式 AC）、2 项 Defer、3 条原始发现驳回。原始判定、独立执行状态与验证方案见[独立评审记录](story-1-3-independent-review.md)。不在本会话应用任何修补，行动处置与负责人确认待实际发生。

- [ ] [Review][Patch] R1 保留详情中已存设备说明的分行和有意义空白 [equipment/templates/equipment/detail.html:11] — Medium，阻塞 AC-2 可见一致性。现有合法多行说明在页面折叠。建议保留安全转义，仅调整说明显示并用隔离库多行夹具验证。
- [ ] [Review][Patch] R3 补真实会话在账号停用后的现有会话回归 [equipment/tests.py:421] — Low，非阻塞。现有注入用例验证服务守卫，但不是启停后既有会话的全链路。
- [ ] [Review][Patch] R4 使用渲染出的实际 href 验证目录点击路径 [equipment/tests.py:338] — Low，非阻塞。已断言锚点和反向 URL，仍可强化由页面锚点直接驱动的证据。
- [ ] [Review][Patch] R5 增强只读 SQL 断言的表名识别 [equipment/tests.py:275] — Low，非阻塞。当前实际 ORM 读取符合边界，测试对无引号或 schema 限定名称的判定不健全。
- [ ] [Review][Patch] R6 补 POST 的真实 CSRF 中间件对照 [equipment/tests.py:436] — Low，非阻塞。测试默认绕过 CSRF，只能证明视图 405。与 8 项拒绝、12 项对照分开。
- [ ] [Review][Patch] R7 覆盖空说明详情的可见提示 [equipment/templates/equipment/detail.html:11] — Low，非阻塞。合法空值已有暂无说明分支，需补不同于多行值的独立回归。
- [ ] [Review][Patch] R9 断言目录实际渲染出的行顺序 [equipment/tests.py:322] — Low，非阻塞。当前服务和模板的顺序匹配，无现存可见错误。
- [ ] [Review][Patch] R10 直达对照固定文档中的字面路由 [equipment/tests.py:338] — Low，非阻塞。当前路由匹配 README，纯 reverse 可能让未来入口改名未被测出。
- [ ] [Review][Patch] R11 T-03 拒绝响应补设备状态无泄露断言 [equipment/tests.py:268] — Low，非阻塞。静态未见泄露。检查状态字段／标签或直接断言匿名跳转没有响应体。
- [x] [Review][Defer] R2 另批业务库最小列级 SELECT 与实际运行验证 [README.md:95] — 延期／另批，未关闭。Medium，发布门槛，不是代码缺陷。D-026 只授 SELECT(id)，正式运行缺少六列权限。按本轮已定范围不授权，在负责人另批部署后验证。
- [x] [Review][Defer] R8 隔离库运行器缺少设备数据残留的预检 [lab_booking/test_runner.py:32] — 延期／另批，未关闭。Low，非阻塞。既有测试工具清点表、迁移、账号与会话，异常设备残留由用例报错。随项目级隔离测试工具加固跟踪，不修改本 Story 的运行器。

**Rejected**

- 原始 #2 `blind-hunter`，`false`。Role.values 将自动接纳未来角色 [equipment/services.py:24–26]。当前枚举及数据库约束仅三种角色，规格明确要求 Role.values。无当前误授。
- 原始 #7 `blind-hunter`，`maybe-false`。目录和 HEAD 对全集求值会带来规模风险 [equipment/services.py:33–36;equipment/views.py:22–35]。全集求值成立，当前规模性能问题未证明。需代表性规模与响应目标才可复评，范围无分页要求。
- 原始 #10 `edge-case-hunter`，`false`。负主键会使列表无法反向构造链接 [equipment/urls.py:9]。Django 转换器确实不接负数，但已批准应用只用正向 identity，运行角色不能指定 id，没有合规写入路径可达。

#### 既有延期台账中待追加的记录

## Deferred from: code review of spec-1-3-view-equipment-catalog (2026-11-25)

以下为本轮静态评审的范围路由，不是负责人最终验收或新一轮人工同意。原始评审及执行限制见[独立评审记录](story-1-3-independent-review.md)。

- **R2 另批业务库最小列级 SELECT 与实际运行验证（Medium，发布门槛，不是代码缺陷）。** D-026 只授 SELECT(id)，正式运行缺少六列权限。按本轮已定范围不授权，在负责人另批部署后验证。
- **R8 隔离库运行器缺少设备数据残留的预检（Low，非阻塞）。** 既有测试工具清点表、迁移、账号与会话，异常设备残留由用例报错。随项目级隔离测试工具加固跟踪，不修改本 Story 的运行器。

## 负责人处置后续（2026-11-25）

上述内容保留首轮检查点原貌。负责人随后实际选择保留行动项，R1 必修并保留自动转义，八项 Low 延期，R2/R8 与三条驳回沿用。最新决定已登记在根目录 D-029，Sprint 已推进 `in-progress`。规格和延期台账仍未写入，首轮待回填候选不再使用，改用最新处置记录所附的已批准文本。按负责人要求，独立回归推迟至 R1 修复后统一执行。本会话仍为独立 Django 0 项。 [D-029](../../decision-log.md#d-029-2026-11-25-负责人批准-story-13-独立评审处置) · [最新处置与回填](story-1-3-review-disposition.md) · [原 Build 会话交接](story-1-3-remediation-handoff.md)
