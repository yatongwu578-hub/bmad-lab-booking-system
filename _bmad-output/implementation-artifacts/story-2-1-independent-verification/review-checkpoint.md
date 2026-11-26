# Story 2.1 · BMAD 6.12.4 独立评审记录

## 结论与检查点

建议保留行动项，修订后复审，**当前不建议验收**。本次发现一项可使用恢复缺陷和两项正式验证缺口。没有发现当前实现已产生越权读取、重叠占用或失效与历史部分提交的证据。普通 PowerShell 独立实跑回执尚未取得。以下不以开发方通过冒充本轮运行。

- 基线 e196aba098771a31eb203be4270b460d5e0aab42，Story 2.1 实施规格 in-review，Sprint review；已获小组消息「确认，继续评审」仅作为范围确认，处置及最终验收尚无人决定。
- Step 1 冻结的差异为 28 路径、+2068/−13、2306 diff 行、122875 bytes，SHA-256 `1FF994B61E337EECCFACCD84C7E9BE427C6032FE266DBFC0901B43C593E31B70`。含全部未跟踪的实现和验证源码。旧 server-stderr.txt 排除，历史开发原始日志和规划材料作证据，不计入代码差异。
- 用 D:/ttAPP/python.exe 成功解析 6.12.4 原生配置和 workflow。使用独立临时项目目录试通用渲染，结果为安装版本的 bmad-code-review 无 workflow.md，依 SKILL.md 和四个原生步骤执行。
- Step 2 四层实收。Blind Hunter 122.875 kB 的下限为 10，实报 13；Edge Case Hunter 4；Verification Gap Reviewer 6；Acceptance Auditor 3。首次同时启动第四层遇线程上限，待前层释放槽位以新独立上下文补启，四份均得。Step 3 先逐条裁决，再归并。Step 4 发现记录已写实施规格，等待小组处置。0 Decision、18 Patch、1 Defer、3 原始发现 Rejected。未进行修复或状态同步。
- 课程依据为 AGENTS、课程基线、团队的 PPT 逐页口径、PRD/Architecture/PC、epics AC-1～11、Sprint 计划和跟踪、D-038、既有延期、Build 检查点、实施规格及验证索引。未在工作区发现 PPT 原件，不声称直接逐页审阅。第 25／26／27／33／34／36 页要求按归档口径维持 Story 拆分追溯、就绪边界、独立工作流、真实证据及人类决定。三人共同操作与审阅，不虚构个人意见。8／5 和实验 A 条件不变。
- 未访问正式业务库，不执行任何正式迁移、GRANT、故障、业务操作或服务重启，未改实现、未触及 Story 2.2、未 commit 或 push。

## AC 独立核对

| AC | 本轮证据与结论 |
| --- | --- |
| AC-1 成功、归属、待审立即占用 | 实现按当前账号与路由建单，事务后给 201 与本人链接。开发原始师生正对照和 I1／NFR 持久化相符。已检查实际渲染链的路由与模板，独立 Django 导航用例待回执。 |
| AC-2 申请权限、可信身份与 CSRF | 仅启用学生／教师；服务先检查、拿设备锁后按数据库重读账号角色／启用状态；管理员、匿名、无／错 CSRF 被拒。开发 12 项拒绝和篡改控制经重算，I6 撤权有原始交错。锁后撤权与普通未授权分母分开。 |
| AC-3 北京时间与严格未来 | 服务端解析 Asia/Shanghai、整点、同日、至少一小时、结束≤23:00、start>t_decision。原 B1/B2、B3 支持服务规则；P01 导致合法整点的页面纠正路径不可靠，不能认定已完整通过。 |
| AC-4 锁后设备可用性 | 主键行锁后另 SELECT 读取实际状态；I2/I3 覆盖维修、停用两方向，已成功未来待审不会自动取消。原始证据与代码一致。 |
| AC-5 有效冲突与范围 | 半开区间，待审未来及已批准才冲突；相邻、跨设备、终态可按其它条件提交。开发回归和 I1 原始结果、明确冲突正文及 10 轮记录一致。 |
| AC-6 FR-018 原子失效 | 只扫目标设备相关到期待审，逐项变更和系统历史同事务，重复不追加，批准不误收尾。I4/I5、高风险故障与 R-04 正反约束原始证据相符。多条及后失败组合可加固 P05。 |
| AC-7 唯一数据库判定时刻 | 源码与真 SQL 有锁、目标状态和权限重读、一次独立 clock_timestamp()，同一时刻用于业务，退出事务后渲染。B3/B4 原始实测重算成立，同版复用，不再等整点。探针长期断言加强见 P04。 |
| AC-8 合法失效后业务拒绝 | 不可用、非法时间、冲突以业务值退出；I5 三例落库证据支持合法失效及历史保留，无新增预约。 |
| AC-9 失败、回滚及未知 | 五例原始记录支持 POST 确认失败、实际未提交的未知、实际提交而模拟丢确认的未知。均 503、不报成功/冲突、一次尝试，不自动重试。本人 GET 注入证据仍可加固 P06。 |
| AC-10 最小本人结果及按需失效 | 源码按当前主体及 ID 固定查询，终态无设备写锁。已结束待审、重复读取、异主等价不存在有原始数据。P02/P03 使正式权限矩阵和固定候选取证不完整，当前没有确认的越权。 |
| AC-11 NFR-001 | 开发实测原始 10/10、200 项已由本会话独立复算。未取得新运行回执，不将重新计算记成独立执行。 |

开发实测前后 75 项清单相符，但相对当前规格文件有状态/评审记录变化，本不影响运行。原首轮与当前另有续跑 PowerShell 及账号 SQL 探针两项已披露差异。完成各交错与边界的后两轮探针、业务源码、测试源码与当前一致。99 个原始文件均留档并重算散列。用机所记录 Python 3.13.17／Django 5.2.19／PostgreSQL 17.12，实际目标 test_lab_booking、测试角色、127.0.0.1:5433、Read Committed、无正式库 CONNECT。对六份前后数据库快照，逐字节 SHA-256 相同。12 张表、19 条迁移、五表均零行。首轮 I1 实际失败及两次不可启动的预检保持原样，未合并为通过。

## NFR-001 及 R/T 项

- **NFR-001**。独立逐轮验证同一合法未来时段／设备、每轮起初设备可用无冲突、屏障、两类授权账号各 10 请求、20 个独立 PID、4～10 对真实持锁重叠、唯一锁后采样、全部 201/409 正文，最终一条记录与唯一赢家匹配且仍有效。10/10 轮各 1 成功、19 明确冲突、1 条有效待审核占用。无异常或缺失响应被算为冲突。有效证据为开发实测经独立审计，非本轮独立实跑，亦非性能结论。
- **R-04**。两个真正 PostgreSQL FK 指向预约及设备，object_type 非空及 CHECK 恰好每次只接受一个类型匹配对象；两个 FK 禁止悬空、受引用对象不能删后提交。独立对照迁移 SQL、约束回归项、失效历史及故障回滚记录。仅 Story 2.1 应用服务创建系统失效历史。
- **T-01**。I1～I7 15 个开发实例有真实记录；已见锁后撤权、维修／停用方向、业务拒绝及单一候选序列。I7 追加同人并发证据仍待 P03，不关闭后续审批、取消、设备变更真实入口的交错。
- **T-02**。始于 2026-11-26 的补查不抹除 IR-05 历史延误。B1/B2 为规则测试，B3 北京时间 17:59:48.100164 实际阻塞，18:00:00.003698 后放行，18:00:00.011708 唯一采样，400 且合法收尾。B4 的判定为 17:59:48.085528，过点提交返回 201；观察到一条未收尾待审、不计有效占用；本人 18:00:00.238186 读取收尾一次。核验前后输入 SHA、锁后 SQL、放行时间、响应及独立观察，当前同版复用，不重跑真实整点。B5 见 I4/I5/F1–F4，未来批准结束边界不在本 Story。
- **T-03**。开发 12/12 拒绝真实记录和合法对照已独立核对，非全项目 NFR-002。少活跃学生乙／甲的同角色异主用例及部分更严正文／实际登录跳转断言。未把缺样本当成已通过。
- **T-04**。开发标准条件、十轮证据和独立重算达标，标准与时间组数据分离，不减少下次独立复验的 20×10 门槛。

## 运行与正式库方案

本独立会话新 Django／数据库动态执行 0 项（截至写此检查点）。历史原 .venv 在沙箱 103，不重复尝试，不换解释器。已通过 PowerShell AST、导航 Python AST、77 项实际散列核对。历史 90 项格式及负例、独立导航 1 项格式和原探针记录分母均通过离线脚本校验。普通 PowerShell 运行入口见 [run-isolated-review.ps1](run-isolated-review.ps1)，它只连接预建 `127.0.0.1:5433/test_lab_booking`，不迁移，不 GRANT，不重启，不重等整点。将接收原始回执另记结果。浏览器只运行了无 DB 的最小原生 HTML 试验尝试，受限 Chrome GPU／子进程启动失败、无 DOM，不能列为浏览器通过。表单缺陷判断据实现链及 [HTML step 算法](https://html.spec.whatwg.org/multipage/input.html#the-step-attribute)，可用 [HTML 对照](datetime-step-browser-fixture.html) 在普通 Chrome 测试新控件、回显控件校验差异，完整整改验收再测真实 HTTP 400 后重提。
 
正式库发布**仅提案**。待通过独立复审及另获正式授权后执行：

1. 先核对真实目标、现有迁移角色和应用角色、schema／所有者、17.12、Read Committed 及备份／恢复计划。保存只读迁移计划和生成 SQL；只应用 `reservations.0001_initial`，再应用依赖它的 `audit.0001_initial`。迁移角色核对模型登记、两个真实 FK、CHECK、NOT NULL、索引及 identity。没授权时完全不连接。
2. 应用角色 `lab_booking_app` 在 `public.reservations_reservation` 的 SELECT 列为 id、applicant_id、equipment_id、start_at、end_at、status、applied_at，INSERT 为除 id 外上述六列，UPDATE 只给 status。在 `public.audit_operationhistory` 只给拟写入的 object_type、reservation_id、equipment_id、action、before_status、after_status、actor_type、actor_id、reason、decision_at、recorded_at 的 INSERT，仅给 SELECT(id) 供 RETURNING。沿用现有设备 SELECT 与基础字段 UPDATE 以支持设备 FOR UPDATE，不增设备状态写和账号权限。检查表级、列级、schema、PUBLIC 和继承角色的有效 ACL，不授 DELETE／DDL／转授权／宽列读取或无依据的序列权限。依据 [PostgreSQL SELECT](https://www.postgresql.org/docs/17/sql-select.html) 和 [INSERT](https://www.postgresql.org/docs/17/sql-insert.html)。
3. 另批后用真实 Windows runtime／Chrome，三人共同跟随师生登录→设备目录→详情→预约→本人结果，验证记录编号、时区、真实 201、同设备再次申请为明确 409、管理员无入口且直达被拒、异主不能读；用批准的测试资产及账号和时段。确认运行角色的正向 SELECT/INSERT/UPDATE 和设备锁、留存诊断与批准后的前后数据。只读核对审计可由有权限的授权人员做，不因取证给应用角色广泛读取权限。正式环境不执行注入、标准竞争或清测试夹具。未审批操作均待办。

## 裁决后的行动项

- **P01 · Medium · 必修实现** 拒绝后整点纠正可能被原生表单拦截（`reservations/forms.py:5–6`）。绑定表单保留非整点 value，且 step=3600 无固定基准。依据 WHATWG，浏览器将该 value 当作 step base，纠正为合法整点反而 stepMismatch。重开新表单可绕开，但不应要求用户重开。修正步进基准或移除阻断，复测真实 400 后纠正再提交。
- **P02 · Medium · 必补正式证据** 同角色本人范围缺少成对拒绝验证（`reservations/management/commands/verify_reservation_transactions.py:670`）。现有 12 项未授权确实全部拒绝，但异主查询仅教师读学生。PC-011、T-03 明列活跃学生甲／乙。补乙读甲的到期待审、甲本人正对照，逐例验证拒绝、无泄露、无业务变化，并保留原分母。现有查询按 applicant_id，没有证据显示当前会越权。
- **P03 · Medium · 必补正式证据** I7 未用新增同一所有人的候选挑战固定范围（`reservations/management/commands/verify_reservation_transactions.py:591–619`）。等待期间新增的是教师记录，阻塞请求是学生。错误地在锁后扩大到该学生所有候选也能通过。固定原交错并补并发写入的同人候选，保留异主控制，断言只变更原目标并追加一次历史。当前代码按预约主键＋申请人＋设备重读。
- **P04 · Medium · 非阻塞测试加固** SQL 采样断言未完全冻结锁与业务语句顺序（`reservations/management/commands/verify_reservation_transactions.py:338–351`）。探针检查锁语句包含 id 字样，但未断言真实表与主键谓词，也未要求相关失效、冲突查找和写入位于唯一采样之后。已有真实日志和代码可分别复核现有实现，自动回归仍可放过次序变异。
- **P05 · Medium · 非阻塞测试加固** 多条同设备到期预约与后续历史插入失败缺少组合验证（`reservations/tests.py:245–270`）。提交和现有 F1 每例只有一条到期夹具。补两条独立失效及各自唯一历史，以及后一条历史失败后三表无部分结果。当前 _expire 遍历全部到期 PK，与追加历史同一外层事务。
- **P06 · Medium · 非阻塞测试加固** 写失效历史的本人 GET 未覆盖确认失败／未知（`reservations/management/commands/verify_reservation_transactions.py:717–758`）。现有 F1–F4 注入只打 POST，而到期本人 GET 也写历史。补 GET 的确认回滚／实际提交但模拟确认丢失，以及重复读取后历史数量。两入口当前共享事务封装，各自分出 503 文案。
- **P07 · Low · 非阻塞测试加固** 权限探针未断言拒绝响应的全部字段与实际跳转（`reservations/management/commands/verify_reservation_transactions.py:676–688`）。目前检查名称、编号、无锁及前后快照，异主与不存在正文相等。再检查时段／状态与匿名重定向目标，按 T-03 可保存匿名完成登录后回到入口的正对照。原始记录未见泄露。
- **P08 · Low · 非阻塞测试加固** 成功页和本人页的全部可见字段未逐一冻结（`reservations/tests.py:143–162`）。现有断言包括链接、库行、GET 状态和开始时间，但删掉页面结束时间仍可能绿。独立复验脚本已增加师生 201／200 可见编号、设备、起止及状态断言，待实际回执。
- **P09 · Low · 非阻塞测试加固** 不可用与冲突的 409 断言复用生产常量（`reservations/tests.py:199–219`）。若两种消息误改成同一文案，现有测试会跟随生产常量。应使用独立期望验证两种实际正文；当前原始响应和代码清楚区分。
- **P10 · Low · 非阻塞测试加固** 偏移与秒级非法值的 POST 覆盖不足（`reservations/tests.py:61–70`）。帮助函数有精确用例，原 HTTP 只传分钟或坏格式。独立导航测试加入带偏移 POST 用例，待回执；仍建议补非零秒及无新增业务行断言。
- **P11 · Low · 非阻塞测试加固** 历史记录时间测试未区分业务判定时刻和实际写入时刻（`audit/services.py:22–23`）。现有非空及区间检查会容许错误重用 t_decision。实际 SQL 使用 STATEMENT_TIMESTAMP，真实历史可见时间各自记录。建议用可辨间隔冻结此约束。
- **P12 · Medium · 非阻塞证据工具** 续跑白名单可跳过改动过的已复用断言（`_bmad-output/implementation-artifacts/verify-story-2-1.ps1:102–122`）。续跑容许两个验证工具整体变化，权限或回归校验规则若改变仍可能继承通过。将复用与各阶段真正执行输入绑定，或失配时重跑该阶段。此时的已交付记录已单独核对。
- **P13 · Medium · 非阻塞证据工具** 续跑门槛可仅凭成功标记接受不完整 JSONL（`_bmad-output/implementation-artifacts/verify-story-2-1.ps1:122–143`）。检查退出标记及快照不等于核对被复用阶段逐例原始文件。增加存在、结构、用例计数、清理和散列断言。当前原始文件齐备并已离线解析。
- **P14 · Low · 非阻塞可运维性** 未知结果缺少可安全关联的服务端操作诊断（`reservations/services.py:99–102`）。外层转为无明细 503，默认访问日志可留状态／路径但无足以区分阶段的安全诊断。可记录阶段、类别和非敏感关联信息，不增加重试或对用户泄露 SQL。
- **P15 · Low · 非阻塞文案** 本人结果 GET 的待核查文案误称重复提交（`reservations/views.py:69–70`）。两入口共用的文案在只读结果页容易误导。区分查看结果与新申请，不暗示未知事务已回滚。
- **P16 · Low · 非阻塞证据工具** 截断 HTTP 响应没有被保留为单请求证据（`reservations/management/commands/verify_reservation_transactions.py:264–270`）。http.client.IncompleteRead 不属于当前异常分支，可使探针非零提前退出而非记录该响应。此时不会虚假通过，也绝不能把异常算成冲突。建议补失败形态的诊断留样。
- **P17 · Low · 非阻塞证据表述** 迁移阶段退出零不能单独区分实际应用与 no-op（`_bmad-output/implementation-artifacts/verify-story-2-1.ps1:196–215`）。Django stdout 可区分，包装 stages 只记录退出码。原始运行明示两条 Applying ... OK。将来汇总明确实际应用数与无操作，禁止用新 no-op 冒充初迁。
- **P18 · Low · 非阻塞证据表述** 现有基线并非定义及权限的全量 schema 指纹（`reservations/management/commands/verify_reservation_transactions.py:821–849`）。现有证据是表名／所有者、迁移清单、五表完整行摘要。约束、索引及 ACL 另核，不从摘要相同推导全部目录对象未变。建议收窄措辞或明确扩展目录核验。

### 延期核验 D01

终态读取仍按本人 ID 与活跃请求主体批准。对于认证完成后、终态 SELECT 前的账号撤权，不做已确认安全缺陷的断言，也不为终态加非必要写锁。见原始条目 2。保留针对性双连接实验的裁决条件。

## 四视角逐项归一与裁决

| # | 原层 | 原始发现及位置 | 裁决 | 分组或理由 |
| --- | --- | --- | --- | --- |
| 1 | blind-hunter | 纠正整点被回显值绑定的步长阻止 · `reservations/forms.py:5–6` | medium | P01 |
| 2 | blind-hunter | 终态读取使用请求缓存主体，疑似权限撤销竞态 · `reservations/services.py:135–146` | maybe-false | D01。已确认终态读取不复核 DB 的角色且不取锁，但正式要求的锁后重读只适用实际取锁路径，目前没有正常撤权入口及竞态运行证据。需冻结认证完成、独立撤权与终态查询的时序后再裁决。 |
| 3 | blind-hunter | 异常去掉原始原因且无可关联诊断 · `reservations/services.py:99–102` | low | P14 |
| 4 | blind-hunter | 本人 GET 错误提示用了提交语义 · `reservations/views.py:69–70` | low | P15 |
| 5 | blind-hunter | 缺针对性索引和逐条记录可能使行锁持有过长 · `reservations/services.py:77–84,114–123` | maybe-false | 驳回。代码确实逐条写，设备 FK 索引已存在；未建立实际工作量下有害的延迟或锁持有，没有正式延迟指标，若成立属性能改进。 |
| 6 | blind-hunter | check_order 不充分验证主键条件和业务语句时序 · `reservations/management/commands/verify_reservation_transactions.py:338–351` | medium | P04 |
| 7 | blind-hunter | I7 新增行是他人，未挑战同人候选 · `reservations/management/commands/verify_reservation_transactions.py:591–619` | medium | P03 |
| 8 | blind-hunter | 拒绝正文扫描与跳转断言不完整 · `reservations/management/commands/verify_reservation_transactions.py:634–714` | low | P07 |
| 9 | blind-hunter | 缺同设备多条到期及后写入失败夹具 · `reservations/tests.py:245–270` | medium | P05 |
| 10 | blind-hunter | 缺本人 GET 失效路径故障及重读验证 · `reservations/management/commands/verify_reservation_transactions.py:717–758` | medium | P06 |
| 11 | blind-hunter | 工具文件完全变化仍可复用历史通过 · `_bmad-output/implementation-artifacts/verify-story-2-1.ps1:102–122` | medium | P12 |
| 12 | blind-hunter | 表及迁移快照不是完整 schema／ACL 指纹 · `reservations/management/commands/verify_reservation_transactions.py:821–849` | low | P18 |
| 13 | blind-hunter | 迁移成功标记不区分应用和 no-op · `_bmad-output/implementation-artifacts/verify-story-2-1.ps1:196–215` | low | P17 |
| 14 | edge-case-hunter | 授权 GET 加载表单期间的 DB 错误返回 500 · `reservations/views.py:54–57` | low | 驳回。未捕获读取异常确实会落通用 500。对无副作用 GET，这不是 AC-9 的业务提交结果，低频且单独加错误流程超出直接修正。 |
| 15 | edge-case-hunter | 响应 body 截断会使探针提前退出 · `reservations/management/commands/verify_reservation_transactions.py:264–270` | low | P16 |
| 16 | edge-case-hunter | 登录写入后丢响应可能留下未登记测试会话 · `reservations/management/commands/verify_reservation_transactions.py:278–283` | low | 驳回。少见且仅测试工具，末尾全行摘要及零会话守门会失败并阻止继续，扩大清理扫描复杂度不值得。 |
| 17 | edge-case-hunter | 历史原始 JSONL 缺失也可接受旧标记 · `_bmad-output/implementation-artifacts/verify-story-2-1.ps1:122–143` | medium | P13 |
| 18 | verification-gap | 故障探针只 POST，不证实 GET 503 分支 · `reservations/views.py:64–73` | medium | P06 |
| 19 | verification-gap | 未要求一次提交收尾至少两条同设备记录 · `reservations/services.py:77–84,113–115` | medium | P05 |
| 20 | verification-gap | 缺确认页／本人页完整可见字段断言 · `reservations/templates/reservations/result.html:11–16` | low | P08 |
| 21 | verification-gap | 两种 409 文案相同时测试仍可绿 · `reservations/views.py:14–15,48–52` | low | P09 |
| 22 | verification-gap | 严格时间偏移及精度只从 helper 验证 · `reservations/services.py:58–74` | low | P10 |
| 23 | verification-gap | 测试容许历史记录时间等于判定时间 · `audit/services.py:22–23` | low | P11 |
| 24 | acceptance-auditor | 回显半点值可导致合法整点无法再次提交 · `reservations/forms.py:5–6` | medium | P01 |
| 25 | acceptance-auditor | 遗漏活跃学生乙读取学生甲的拒绝用例 · `reservations/management/commands/verify_reservation_transactions.py:670` | medium | P02 |
| 26 | acceptance-auditor | 等待期间新候选未验证同人范围冻结 · `reservations/management/commands/verify_reservation_transactions.py:591–619` | medium | P03 |


正式 deferred-work.md 的本轮追加在受限 PowerShell 中实际返回 Access denied。D01 已写入规格，待补写内容保存在 deferred-work-pending-entry.md。根延期账未更改，不声称已完成同步。
