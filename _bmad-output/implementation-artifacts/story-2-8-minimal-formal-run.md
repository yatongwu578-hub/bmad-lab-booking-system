# Story 2.8 · 最小正式运行验证方案

**方案已备，未连接正式库或执行正式浏览器。** P01/P02 的隔离独立复验已通过。本方案只确认管理员取消入口、确认原因输入和放弃返回，不提交取消、不新增预约、不触发 FR-018 写入。不重新跑隔离场景，也不把现场控制范围外的场景宣称已现场通过。 [隔离独立复验](story-2-8-independent-run-result.md)

## 1. 只读资格与样本

预计**无需迁移或授权**。2.8 使用的仍是既有设备行锁、预约 `UPDATE(status)`、历史 `INSERT`／主键回读及历史列级 `SELECT`。在正式窗口先核对 `127.0.0.1:5433/lab_booking`、`lab_booking_app`、PG 17.12、Read Committed、精确列权限和无缺列，同时用正式环境已有只读迁移查询逐条与独立批的 19 条迁移账本比较，不只对数量。发现缺项、过宽授权或迁移漂移即留证停止，不自动 `migrate`、`GRANT` 或重启现有服务。 [既有 ACL](story-2-1-targeted-independent-recheck/d041-authorization-reviewed.sql) · [2.6/2.7 已验证基线](story-2-6-2-7-final-acceptance.md)

复用 [2.5 W01 只读检查](story-2-5-review-support/inspect-story-2-5-w01.ps1) 的 `-CaptureSnapshot`，不带 `-ToolFixture`，不执行 2.5 的完整发布脚本。下例仅供之后的正式窗口，运行前确认端口未被占用也未被本批其他进程保留，本轮未执行。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\story-2-5-review-support\inspect-story-2-5-w01.ps1" -OutputRoot "F:\softwork\outputs" -BrowserPort 8007 -CaptureSnapshot
```

- 复用 2.4 正式工具的 `SET TRANSACTION READ ONLY` 迁移账本核验与 2.6/2.7 的单样本只读资格检查。运行时使用已有启用管理员和一位现存普通账号；保护 passfile 和账号清单，不打印内容，不写入凭据。样本选择以数据库时钟及该批 `safe_until` 为准，从现有单条预约优先选 `approved` 且 `end_at > safe_until`，允许已开始。若无此类，才考虑 `pending` 且 `start_at > safe_until`。查询只取候选 ID、状态、设备及必要时界，在同一只读窗口复核。W01 的默认 `detail` 排序偏好有历史的样本，**不能**用其选到终态来推断不存在安全正例。
- 主流程只打开该 ID 的详情和确认页。缺省**不打开完整列表、不点击筛选列表**。若要实测列表导航，先对确切查询范围核对全部候选无 `pending` 且 `start_at <= safe_until`，再将此单一安全筛选加入守卫。锁等待或超窗时停止，若页面仍试图执行 FR-018 的 UPDATE/INSERT，由 SQL 守卫阻断，不计作页面正例。
- 无安全正例时，如有既有终态样本只核实详情和无取消表单的确认响应；没有可用样本则不造样。记录确切未覆盖分支（正向入口、输入或返回），由隔离批 AC-1、AC-2、AC-4、AC-6、AC-7、AC-8 的相应真实证据承接，不将终态演示称为正向现场验证。

## 2. 复用现有守卫与浏览器，检查一次往返

| 已验证工具 | 本次最小复用 |
| --- | --- |
| 2.4 的 [确认与返回流程](run-story-2-4-minimal-formal.ps1)、[只读样本与防写适配](serve-story-2-4-formal-smoke.py) 和 [CDP 操作](story-2-4-formal-browser-drive.mjs) | 复用只读账本、子进程调度、DOM 断言、文档对账与归档。仅把原本人目标和点击序列适配成一个管理员详情 ID、对应确认地址及详情返回。 |
| 2.5 的 [W01 SQL 守卫](story-2-5-review-support/serve-story-2-5-w01-smoke.py)、[CDP 记录器](story-2-5-review-support/capture-story-2-5-browser.mjs) 和 [日志合约](story-2-5-review-support/w01-log-contract.ps1) | 保持安全期、现有 SQL 分类及自动日志不变。只允许精确的详情／确认 GET、已有登录／退出及身份路由，禁止所有预约业务 POST、业务 DML、DDL 和未知 SQL。仅允许现有登录会话和 `last_login` 技术写入。 |
| 2.6／2.7 成功批的 `Check-GuardReady`、单样本防写和请求比对 | 复用 `F:\softwork\outputs\experiment-a-preparation-10c193e\integration-prep-20261128\run-formal-detail-26-27.ps1` 的已验证 PID 检查函数及日志模式。Python `.venv` 启动器不能当成服务 PID，HTTP readiness 头、守卫就绪 JSON、端口监听 PID 必须指向同一个服务进程，且是已启动解释器本身或其验证过的直接子进程，并匹配本次脚本、端口、计划散列和启动时间。 |

旧浏览器脚本固定本人路由或固定已失效样本，**不能原样执行后当作 2.8 证据**。正式窗口只做上述目标路由与点击序列的薄适配，不重写浏览器驱动、SQL 分类、日志解析或进程守卫。用精确路径比较，详情 `/reservations/manage/<id>/` 和确认 `/reservations/manage/<id>/cancel/` 分开；如果使用合法设备筛选，其查询只允许已预检的那个值。匿名 302 的 `next` 应是原确认地址，不因共享详情前缀误判为泄露。

1. 启用管理员进入同一安全详情，检查「取消预约」链接并点击。确认页应为 200，显示目标、状态、设备及北京时间区间，包含取消原因输入框、对应本地表单动作、确认键和返回按钮。可输入一段非业务测试文字，**不按回车、不点击确认、不提交**。只点「返回预约详情」，检查原状态不变。若筛选列表不在已证安全范围，只检查返回管理的链接指向，不实际跟随。
2. 同一确认地址最少补匿名 302、普通用户 403，检查无受限详情。使用守卫阻断的任何请求都标记为守卫事件，不当成应用拒绝或正向通过。确认后不要增加正式占用、异常、边界、并发或 CSRF 实验，这些使用已绑定的独立隔离证据。

## 3. 自动归档与停止条件

- 在本机唯一运行目录沿用 W01 的 `Start-Process -Wait -PassThru`（有限命令），分开 stdout/stderr、保存原生退出码和原始散列；成功需退出码和结构化核对同时满足。活动 Chrome `DevToolsActivePort`、JSONL 就绪和其他活日志只经 `FileShare.ReadWrite` 读，完成的日志待进程退出后按明确 UTF-8／原生诊断合约读，不把 Windows 转码或读取时机误判成业务错误。单批退出、按守卫停止文件关闭专属服务，不停止未知 PID。
- 只读前置和后置使用同一 [W01 检查器](story-2-5-review-support/inspect-story-2-5-w01.ps1)，后置加 `-BeforeEvidence <本批前置 w01-inspect.json>`。保存输入散列、正式身份和迁移／ACL 结果、HTTP 暴露范围、两个 PID 的父子校验、浏览器与守卫的 `method + exact path + query hash + status` 对账、业务 POST 为 0、业务写为 0、前后预约／设备／历史及账号安全属性散列一致。忽略已批准的会话技术变化，不把时间流逝造成的有效占用计算变化误写成数据库变更。
- 原始正式日志仅保存在本机受控目录。入库使用脱敏汇总、退出码和散列，不记 Cookie、令牌、密码、输入原文或真实预约私有内容。无安全样本、窗口过期、端口／PID 不符、权限或迁移漂移、守卫阻断或前后快照有意外差异时，保留本批原始阶段，止于安全边界，不盲目重新操作。不要求人工填写额外表格，团队只需审阅自动回执和现场覆盖结论。

本方案不改变 Sprint 8/5、实验 A、9 项延期或最终判定。未授予本轮正式库访问、正式发布、标 done、开发 3.1 或 Git 提交推送。 [课程基线](../../docs/course-requirements.md)

## 4. D-064 授权后的本机入口（2026-11-29）

负责人确认 D-063 并授权按本方案做最小正式验证，以及条件成立后的验收、提交及推送。现有工具已接入一个薄适配，不改业务源码或原 2.4～2.7 工具。直接复用 W01 只读 ACL/快照、SQL 防写及 CDP 取证；从原 2.6／2.7 已验证脚本复用调度、PID 核验和 Chrome 进程处理。本适配只变更路由、只读样本选择、浏览器点击序列及本 Story 对账要求。 [调度入口](run-story-2-8-minimal-formal.ps1) · [Chrome 路由与断言](story-2-8-formal-browser-drive.mjs) · [真实决定](../../decision-log.md#d-064-2026-11-29-负责人批准-story-28-最小正式运行与条件验收)

原 .venv 的独立版本探针以实际进程返回 **103**，沙箱访问受保护账号文件时返回拒绝。已做不接触凭据或数据库的准备检查，PowerShell 解析、Node 语法检查和生成守卫的本地纯函数路由检查通过，14 项非文档独立复验输入散列保持匹配。没有调用正式数据库、启动正式应用或执行 Chrome 流程。准备检查不是正式验证结果。

在普通 Windows PowerShell 执行以下**一条命令**，无须手工录入数据。使用本机既有凭据及 2.6／2.7 原工具目录，为本批在 `F:/softwork/outputs` 下创建唯一证据目录。若成功，应得到 `STORY28_FORMAL_SMOKE_OK`；若失败，保留首批目录和日志，不在未知状态下重跑。请回传终端显示的证据目录路径，无需传送凭据或私有响应。只有核验正式回执及 AC 证据后才同步最终状态、整理脱敏入库范围及执行 Git 操作。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\run-story-2-8-minimal-formal.ps1"
```
