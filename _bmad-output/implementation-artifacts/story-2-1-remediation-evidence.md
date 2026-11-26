# Story 2.1 · P01～P03 Build 整改证据

2026-11-26，北京时间。BMAD 6.12.4 `bmad-build` 正式渲染快照 `43b7d217a8d00d947a6b`，恢复已批准实施规格，经 Step 1 的现有状态分流进入 Step 3。`D:/ttAPP/python.exe` 仅用于渲染和离线源码检查。延用 `baseline_commit=e196aba098771a31eb203be4270b460d5e0aab42`。执行授权来自 D-039 和本轮用户指令。三位组员共同操作与审阅，不代填个人意见。

## 2026-11-26 · 普通 PowerShell 真实开发自测回执

项目组报告在普通 Windows PowerShell 执行本 Story 的整改入口。实际证据目录为 [story-2-1-remediation-run-20261126-200731-839-640e421b1fe2](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/stages.txt)，运行至北京时间 20:08:40.734（完成退出 0）。本会话对原始文件作离线复核，未重新执行 Django、Chrome、PostgreSQL 或任何历史测试。以下是**开发自测**，不是独立 Code Review 的新运行。

| 新运行 | 原始结果与要求核对 |
| --- | --- |
| Django 回归 | **91/91，0 跳过，21.990 秒**。按逐项名称与原 90 个通过ID比较，无删除、无重复，新增 P01 专项为 `test_ac3_rejected_half_hour_can_be_corrected_on_bound_form`，R-04 数据库约束及 B1/B2 仍在套件。另有一次系统检查通过、迁移漂移检查为 No changes detected。 [回归原文](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/regression.stderr.txt) |
| 页面导航 | **1/1，0 跳过**，日志含学生及教师各自从实际渲染链接进入设备目录、详情、预约及本人结果。该项是 Django 实际路由测试，Chrome 纠错另列。 [导航](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/navigation.stdout.txt) |
| P01 · AC-3／AC-1 | **Chrome 159.0.8154.34 通过**。实际详情→表单→400→201→本人详情的 HTTP 顺序为 `200/200/400/201/200`。北京时间次日 2026-11-27 的 10:30～11:30 被拒、原值回显，无预约或历史；留在同一 400 页面改为 10:00～11:00，原生验证开启、无 stepMismatch，通过实际点击正常提交。独立连接读到设备 433 的预约 133，当前学生归属、状态待审、唯一有效占用、无历史，UTC 时段与北京时间对应，本人 GET 未改数据。未放宽服务端规则。 [Chrome 原始记录](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/browser-correction.jsonl) |
| P02 · AC-10／T-03 | **13/13 未授权通过**，原 12 个拒绝样本均保留。学生乙 738 读学生甲 735 的记录 134，与读取不存在记录的真实 404 正文一致，无受限字段、无设备写锁或业务时间采样，未有预约／历史写入。三次前后快照指纹一致，记录仍待审核，有效占用和历史不变。随后甲本人正常读取返回 200，仅为该记录创建系统失效历史 61，再读不追加。本人和不存在对照未计拒绝分母。 [权限原始记录](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/permissions.jsonl) |
| P03 · AC-10／T-01 | **交错 15/15，含扩展 I7**。持锁 PID 41024，等待中的读取 PID 29988，独立观察 PID 39448。先固定目标 161，再实际等待设备锁；确认阻塞后才新增同设备同申请人 162 和异申请人控制 163，放锁前观察不到未提交新增。锁后有账号与主键、申请人、设备重读及一次数据库时钟。读取只使 161 失效并写一条系统历史 69；162／163 仍待审核，因已到期均不计有效占用，不产生各自历史。重复读取以及终态控制未加设备写锁、未追加历史。 [交错原始记录](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/interleavings.jsonl) |

运行记录的原 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12、Read Committed 和连接角色均匹配。只连接 `127.0.0.1:5433/test_lab_booking`，`lab_booking_test` 不是过权角色且无正式业务库 CONNECT。逐阶段成功标记、退出码和原始输出互相对应。75 项输入前后散列一致并与当前磁盘一致，数据库前后摘要 SHA-256 都为 `5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272`。12 张表与 19 条迁移登记一致，五张监测表均为零行，各专项夹具清理成立。此处并未宣称验证了所有目录对象或序列未变化。99 个此前归档原始文件 SHA-256 全部未变。 [阶段与退出码](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/stages.txt) · [离线核验摘要及原始文件散列](story-2-1-remediation-run-audit.json)

### 历史复用，不计本轮新测试

- **AC-11／NFR-001**。复用清单所列三组在原始 JSONL、阶段记录和散列上均匹配，逐轮重算 10/10、200 个响应、20 个真实独立连接和实际持锁重叠，各 1 成功、19 明确冲突、1 个有效待审占用。非性能指标。
- **AC-9／故障 5/5**。确认回滚与提交未知的响应、无重试及独立前后数据复核相符。失败分类相关业务源码及实测探针未变化。
- **AC-7／真实北京 18:00**。B3 真等锁跨过 18:00，锁后判定并拒绝。B4 于整点前采样，整点后提交成功，回读后仅一次合法失效。此次未等待新整点，只对同路径历史原始记录重审。

与上述历史运行被测清单对照，核心权限、视图、时钟、锁、事务、故障分类和数据库模型未变。既有测试的变更限于 P01 回归、P02、P03 I7；新增 Chrome 独立验证组。再对改过的命令执行方法语法树比较，确认标准竞争、故障、整点及公共连接／会话／采样探针保持原实现。复用证据与本轮新运行分列。 [明确复用清单](story-2-1-remediation-run-20261126-200731-839-640e421b1fe2/historical-evidence.json)

### AC 覆盖及交接

AC-1/2 经 91 项套件、Chrome 成功读回及权限对照；AC-3 经 P01 Chrome 与规则回归、保留真实边界；AC-4～8 经回归、交错和未改变的真实边界证据；AC-9 为原故障证据及当前分类回归；AC-10 经 P02、P03；AC-11 复用原标准组。冻结的申请、越权与收尾三条 I/O 矩阵均有实际通过用例。故 BMAD Step 3 完成，实施规格 `in-review`、Sprint Story 2.1 `review`。不是最终验收或独立复审通过。

已保留 D-038/D-039、首次 I1 SQL 别名漏采、旧 103 预检、整改前后实际状态及 P04～P18、D01 和原三项驳回。按归档口径核对 PPT 25/26/27/33/34/36 页，保持 Sprint 8/5 和实验 A 不变。三人共同操作和审阅，不单独分配个人任务。未访问正式库、不启动 2.2、不标 done、不自动 commit/push。 [原独立 Code Review 针对性复审交接](story-2-1-remediation-review-handoff.md)


## 整改落盘时的记录（历史）

### 实际落盘

| 编号 | 实现与验证增量 | 当前证据 |
| --- | --- | --- |
| P01 | `reservations/forms.py` 两控件 `step=3600 → any`。无 `min` 时浏览器会取回显的 HTML `value` 为步进基准，这会让合法整点与此前半点相差非整数步。去除原生步进阻断，保留表单时间提示及原服务端时间、权限、事务、CSRF。新增 Django 方法 `test_ac3_rejected_half_hour_can_be_corrected_on_bound_form`；`browser-correction` 组在真实 Chrome 走详情实际链接、非法 POST、400 回显、同页普通按钮再次提交、201 与本人读回。日期由隔离数据库北京时间动态取次日。首个非法请求允许单次测试绕过，纠正时必查原生校验未关闭。 | 源码及静态断言已核对，真实 Chrome 与 DB 待跑。 [HTML 步进基准](https://html.spec.whatwg.org/multipage/input.html#the-step-attribute) |
| P02 | 只在真实隔离 HTTP `permissions` 增加活跃学生乙对甲已到期待审的结果 GET。拒绝 404／同行不存在 404、内容无泄露、无锁／无取时／无预约或历史写、独立数据库指纹一致。合法本人对照在其后独立按需失效并验证唯一历史。旧 12 个拒绝仍保留，预计新真实分母为 13，不存在对照独立。 | 探针已落盘，尚无新 13/13 结果。 |
| P03 | 扩展 `interleavings` 的 I7。锁持有者与 HTTP 请求事务、观察者均为独立 PID。确定 `pg_blocking_pids()` 的真实等待后才插同主、异主两个已到期待审夹具，放锁前还核验观察方看不到未提交新增。记录原目标、申请人、设备、时序、固定条件重读和唯一业务时钟，实际读取只失效原目标并产生一次历史；新增仍待审且不计有效占用，重复与终态读取不追加。 | 探针已落盘，尚无新 I7 实跑。还是 15 个交错实例，旧 15/15 不记进本轮。 |

用户授权的唯一产品行为改动是两个 HTML 字段的原生步进。其余文件为定向测试及包装：`reservations/tests.py`、`reservations/management/commands/verify_reservation_transactions.py`、`reservations/management/commands/_chrome_probe.py`、[普通 PowerShell 验证脚本](verify-story-2-1-remediation.ps1)。真实目标数据库连接与登录、权限、锁、预约写入、历史服务、时钟及事务错误分类未修改。不写不相关业务，不重新应用原 Story 完整补丁。源码写入成功，因此无需补丁替代。

### 核验与 AC 影响（整改落盘时）

- 从原基线生成包含未跟踪源码的完整代码差异（30 个路径、2,942 行），另以整改前工作树提取五路径增量。旧局外日志不纳入。复核四份 Python 源码可静态编译；原预约测试方法未删除，新增一个，故先以真实原 90/90 作分母基准，整改版本预期发现 91 项，导航专项另计 1 项，均以实际运行和退出码为准。
- `ProbeWSGI`、隔离身份 SQL（含限定别名）、账号查询识别、核心 NFR、故障和整点 探针的语法树与前版相同；共用 `pair`、`prepare`、锁及记录方法未改变。对旧 probe 的两项行为改动都限在 permissions 和 I7，额外为 Chrome 独立组和指纹方法。服务、视图、共用事务的文件散列未变。
- PowerShell 解析、文件散列正反例、计数与失败分支、Chrome DevTools 合成传输已静态／替身检查。99 份历史原始文件散列仍与首轮独立审计一致。**替身与静态不能算 Django、Chrome 或 PostgreSQL 实跑。**
- AC-1 成功归属与本人读回由 P01 真流程及回归复验；AC-2 正常权限与 CSRF 由重跑权限及回归覆盖；AC-3 是 P01 的直接整改点且服务端原 B1/B2 与真实 B3/B4 相关路径不变；AC-4/5、AC-6/7/8 通过核心交错、原回归和同一事务探针复核，核心实现未改；AC-9 的故障与提交分类路径未改；AC-10 是 P02/P03 的直接补证点；AC-11 的正式 20 独立连接 × 10、各 1 成功／19 明确冲突／1 份有效占用门槛未改。R-04 模型、迁移和业务行为未改，纳入原套件验证。
- 开发阶段允许复用同路径历史 **NFR-001 200 响应／10/10、故障 5/5、北京 18:00 B3/B4**，复用条件是四份整改源码固定 SHA-256、三份原始 JSONL 的 SHA-256、分组记录数、清理标记皆匹配。FS 路径和静态比较不替代独立复验。故障和 NFR 若需要重新运行，可加 `-RecheckConcurrencyAndFaults`，不降低标准。未必要重等整点。后续独立评审仍按 D-039 取证。
- 按课程基线与团队页码归档落实 PPT 25/26/27/33/34/36。冻结需求、试验 A、Sprint 8／5、P04～P18／D01 与后续 Story 都不改。

### 真实开发自测与归档门槛（整改落盘时，历史）

本会话未重试原项目 Python 已知的沙箱 103。当前没有任何新的 Django／Chrome／PostgreSQL 实跑证据。BMAD Step 3 的矩阵实际通过条件未满足，保留规格和 Sprint `in-progress` 及整改待验证项，未进入 Step 4 或标 `done`。

从仓库根目录在普通 Windows PowerShell 单次执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\_bmad-output\implementation-artifacts\verify-story-2-1-remediation.ps1
```

使用原 .venv、Python 3.13.17、Django 5.2.19、PostgreSQL 17.12，唯一允许的数据库 `127.0.0.1:5433/test_lab_booking`（`lab_booking_test`）。不迁移、不授权、不等待整点。若现有凭据文件或 Chrome 不在默认位置，传入脚本参数 `-Passfile`、`-Chrome`。脚本记录独立运行目录、原始阶段 stdout/err、退出码、动态输入、请求响应、前后数据及文件散列。无论失败或成功，请回传输出的 `Story 2.1 remediation output:` 目录。核对每个真实阶段及清理证明后，才勾选 P01～P03、同步 `review` 并交回原独立 Code Review。没有访问或修改正式库，没有提前开始 2.2，也没有暂存、提交或推送。


## D-040 后的最新复验入口

负责人在针对性独立评审选择 2 并批准 P02/P03 最小取证补强。前面的开发批次及核验仅作为历史证据，不满足新增的实际认证主体与数据库绑定断言。最新只执行 [D-040 单入口](story-2-1-targeted-independent-recheck/run-targeted-recheck.ps1)，见 [处置与回执要求](story-2-1-targeted-independent-recheck/d040-disposition-build-handoff.md)。不先运行旧入口。Story 2.1 当前 `in-progress`，此附注不是新的通过或正式环境验收。



## D-040 新独立回执核验完成

团队普通 Windows PowerShell 独立验证批次 20:52～20:53 实际通过，评审会话另对指针、原始日志、清理、版本及退出码重算核验。新增实际结果和历史复用分别登记，P01～P03 及 R02/R06/R07/R10 建议关闭。Story 2.1 已按条件恢复到 review，不标 done。 [复审收尾](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

