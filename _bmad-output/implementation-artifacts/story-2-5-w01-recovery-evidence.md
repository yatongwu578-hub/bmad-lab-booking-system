# Story 2.5 · W01 首批失败、修复与恢复边界

## 22:31 正式授权已提交，阶段 D Windows 日志共享整改

- 正式失败批 `F:/softwork/outputs/story-2-5-w01-formal-20261127-223121-117-fe32f2d5cf74485abb1aa9c00ec76474/` 先通过 22:29 工具资格，B 实际退出 0 并输出唯一 `STORY25_W01_GRANT_COMMITTED`。C 及失败后两个归档均由 `lab_booking_app` 独立读回，显示 `EXACT_COLUMNS_PRESENT`、缺列 0，原始输出散列已核对。预约、设备、历史、账号安全四组快照故障前后均相同。当前沙箱无法读取正式 passfile，未另行连接。恢复必须新取正式只读回执和 FR-018 窗口，实际 ACL 不精确就中止。
- 第 D 阶段的旧等待器在异步重定向仍打开时以 `ReadAllBytes` 读取 `server.stdout.txt`，真实共享冲突先于 Chrome 业务访问。旧批没有 `server-http.jsonl` 或可确认的就绪 PID，检查时本机 8005 无监听且可独占绑定，未终止任何未知进程。
- 同一 Windows `Start-Process` 重定向实测 `F:/softwork/outputs/w01-encoding-42435441397f4c80bb35b5732ffcf7f4/` 实际复现旧读取共享冲突。同一个持续写入 stdout 和 stderr 的子进程，经本机 HTTP HEAD 返回 204，专用 JSONL 通过 `FileShare.ReadWrite` 读取，HTTP PID、文件 PID 和进程 PID 一致。正常退出 0，末尾标记齐备，两路原始文件已算 SHA-256，三份文件在退出后均可独占打开。专项资格与通过的 22:29 批组合，未经专项测试的清单变化照常拒绝。
- 正式启动及可选访问服务均改用 HTTP 与实际进程检查等候，不读在写的重定向文件。启动后再核对本机监听 PID、专用回执、解释器、工具及当批输入散列。正常结束后才读取、散列和归档完整日志。浏览器恢复模式不重放 B、不接管未知监听、不新增预约或重跑业务测试。

正式 ACL 已提交的实际恢复入口，从普通 PowerShell 执行。脚本刷新只读检查并强制禁止 `GRANT`。未生成 `STORY25_W01_FORMAL_OK` 前不判正式验收通过。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\story-2-5-review-support\run-story-2-5-w01-formal.ps1' `
  -InspectionEvidence 'F:\softwork\outputs\story-2-5-w01-formal-20261127-223121-117-fe32f2d5cf74485abb1aa9c00ec76474\story-2-5-w01-inspect-20261127-223146-633-691246d96c01479e9a9492ffb02a5392\w01-inspect.json' `
  -ToolchainEvidence 'F:\softwork\outputs\story-2-5-w01-toolchain-20261127-222918-637-6d0cee8b81c640bfb2e2ed3e738fa83c' `
  -LiveIoEvidence 'F:\softwork\outputs\w01-encoding-42435441397f4c80bb35b5732ffcf7f4' -BrowserPort 8005 -ResumeBrowser
```

## 22:02 及之前的历史证据

**22:02 后续。** 团队的普通 PowerShell 正式只读检查成功，隔离批因实际 CP936 的 initdb 诊断被误当成 UTF-8 而中止。全链路编码整改、新只读回执和复用 17 项原证的定向命令见[编码整改及恢复证据](story-2-5-w01-log-encoding-evidence.md)。下文保留之前的实际记录，不使用旧命令替代最新定向入口。

2026-11-27，北京时间。BMAD 6.12.4 独立评审后续，沿用 D-051 的最小授权决定。本轮未修改业务代码、数据库结构、正式数据或权限。Story 仍为 `in-review`，Sprint 项仍为 `review`，M01 已关闭，W01 未关闭。Sprint 8／5、实验 A、三人共同审阅安排和原始独立证据均不变。

## 第一批正式运行的事实

- 原目录 `F:\softwork\outputs\story-2-5-w01-formal-20261127-213159-095-50b6670fc5064ba38ae5714b6f67c3f7`。授权阶段原始 stdout 为空（0 字节），stderr 276 字节。真实原生退出码 3，时间 21:32:13.5347390。之前正式账号只读、迁移账本和运行角色预检均为 0。原始文件不改。
- 原 `story-2-5-w01-grant.sql:69` 在匿名 PL/pgSQL 块第 39 行抛出 `ACL changed since runtime role readback; no grant applied`。类型为 `raise_exception`，SQLSTATE `P0001` 由原语句的无显式状态码 `RAISE EXCEPTION` 得出。原始 stderr 未打印 SQLSTATE。新版打开 `VERBOSITY verbose`，下述隔离失败分支已实际打印 `P0001`。
- 原运行者列表是 `actor_id,before_status,after_status,decision_at,recorded_at`。SQL 按 `COLLATE "C"` 排成 `actor_id,after_status,before_status,decision_at,recorded_at` 后进行字符串比较。同一集合不同顺序被误判成权限漂移。这是部署工具缺陷，不是 Django 业务回归，也不是 PostgreSQL 拒绝授权。
- 抛错发生在 `EXECUTE GRANT` 前，且 `ON_ERROR_STOP` 阻止执行后面的 `COMMIT`。此批未提交，没有授权成功标记。原 SQL SHA-256 为 `F4984E9CEC9D6AFA874A00AF3C8091517E8024B7D11D9CB2E1BE6B6E42321A0A`。保留与原批散列匹配的八份工具源码，归档于 `F:\softwork\outputs\story25-w01-failed-source-64e9f5d40f844ab190b5b8f6b014e940`。
- 21:32 旧只读回执显示五列当时均缺失，不能代表现在。新版正式只读探测实际在 `Test-Path` 访问既有受保护 passfile 时返回 `UnauthorizedAccessException`，未启动 psql，原回执 `F:\softwork\outputs\story-2-5-w01-inspect-20261127-215432-903-099f0356595b4fac967ea0e0cdcc958d`。当前正式 ACL 未知。

## 工具变更与 A～E 恢复规则

| 阶段 | 完成证据 | 失败如何继续 |
| --- | --- | --- |
| A · 只读预检 | 运行角色独立 `REPEATABLE READ READ ONLY` 回执，实际有效和显式 ACL，完整预约候选，UTC 新窗口，既有账号和目标端口。正式执行器在任何授权之前用独立 Chrome profile 确认页面执行 CDP 命令，不只检查调试端口。 | 重新取 A，不复用过期窗口。存在全量 FR-018 风险、已有账号或角色不符、8005 不能绑定、Chrome 页面不响应均不授权。 |
| B · 必要列级授权 | 只允许实际缺少的 D-051 五列 SELECT，集合双向包含并拒绝重复与多余成员。表级、列级额外权限、INSERT 或 SELECT 转授均拒绝。空和 NULL ACL 规范化传给 `aclexplode`。验证显式 ACL 增量及有效权限后才提交。 | 无提交回执不得推测结果。用独立运行角色重读，权限已正确则跳过 B，仍缺则仅按新的实测差集。浏览器恢复模式绝不执行 B。 |
| C · 授权后读回 | 运行角色在同一只读快照内核对身份、显式及有效 ACL、原写权、增加的列和业务摘要。 | 发现额外权限或非预期变化立即停止，不自动撤权。C 成功后不重复 B。 |
| D · 浏览器自动化 | PID 与 8005 监听者、脚本 SHA、原 `.venv` 入口及对应回执一致。匿名、学生、教师、管理员使用独立 Chrome profile，同源原生 CSRF 登录和退出，记录请求、重定向、状态码、响应散列及 DOM 结果。优先用安全的预约 #1/#2，保留安全现存样本回退。动态通过全量扫描及截止时间，应用执行包装器拒绝非技术写入并记录业务读取/锁类别。 | 页面失败立即停止该批服务并尝试后置独立快照和 ACL 读回。之后更新窗口，ACL 已正确时以无授权模式继续，不种预约、不重做成功写入。 |
| E · 后置及归档 | 再读 ACL 及业务投影散列，校验浏览器和服务端请求一一对应。比较结构化 ACL 而不是 tuple/list 的文本，不记录 Cookie、口令、令牌、正文或原始 CDP 帧。GUID 新目录保存各退出码、唯一标记、JSON/JSONL 和源码散列。 | 只读排查差异，不覆盖初次归档，不把缺失的外层退出码或成功标记补写成通过。 |

## 隔离实测

工具专项实际使用安装的 PostgreSQL 17.12 一次性集群 `127.0.0.1:55435/test_lab_booking`，独立数据目录、SCRAM 合成口令。Chrome 合成站仅监听 `127.0.0.1:49173`。不接触原有 5433 测试库或正式库，不运行 Django 回归，不使用正式账号。

- [实际隔离工具批](../../../../outputs/story-2-5-w01-toolchain-20261127-215403-170-2ded2bab12dc445682054831fb2e5329)的 `cases.txt` 有 17 项实际通过。覆盖 NULL/空 ACL、全缺/部分缺/全具备、无序正确差集、旧差集和重复成员拒绝、额外列权限和表级权限、转授权拒绝、全范围 FR-018 风险、过期窗口、真实占用端口和业务快照漂移。零差集 SQL 仅在隔离自测，正式恢复不会调用它。
- 使用只存在于一次性隔离库的事件触发器，在实际 `GRANT` 后人为引入越界 ACL。真实 SQL 在提交前复核抛 `P0001`，psql 退出 3，移除故障触发器后由应用角色独立读回，原 ACL 未变。另用独立读回验证提交回执缺失但权限已正确时，恢复判断为跳过 B。
- 以实际 PostgreSQL JSON 验证 Python 归一化函数接受 ACL 行顺序变化和字符串形式 OID，拒绝转授布尔值变化。PowerShell、SQL 及 Python 使用 UTF-8，异常保留原始字节，成功标记要求原生退出 0 和唯一完整行。脚本语法检查不计为真实运行。
- 17 项通过后真实 Chrome 在沙箱中启动 CDP，但 GPU 子进程反复退出，Chrome 日志为 `GPU process isn't usable. Goodbye.`。Node 在 `Network.enable` 超时并实际退出 1，未到预期注入的 HTTP 409，也未完成真实四角色、CSRF 和浏览器/数据库联合归档。完整工具批无 `STORY25_W01_TOOLCHAIN_OK`。隔离 PostgreSQL 正常停止，`shutdown.exit=0`。没有关闭 Chrome 安全机制或使用伪造浏览器结果。
- 模拟 Chrome 启动参数的额外失败原证保存在 `F:\softwork\outputs\story25-chrome-probes-0b7f311740b54ecba496749e6ba2b74a`。首次工具批中 Windows 拒绝绑定原合成端口 55436，已换 49173，实际占用测试通过。原证未删。

## 普通 PowerShell 当前能够运行的安全入口

执行只读确认。不会授权、迁移、启服务或请求预约页面。标准凭据走普通 PowerShell 中已有的受保护 passfile，无需提交内容。退出 0 且有 `STORY25_W01_INSPECT_OK` 才读取新目录的 `w01-inspect.json`。

```powershell
$W01 = 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\story-2-5-review-support'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $W01 'inspect-story-2-5-w01.ps1') -BrowserPort 8005
```

运行隔离工具专项，解决沙箱未完成的 Chrome 取证。该命令永远不访问正式库。指定 Python 仅供合成工具夹具，不替换项目 `.venv`。

```powershell
$W01 = 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\story-2-5-review-support'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $W01 'test-story-2-5-w01-toolchain.ps1') -FixturePython 'C:\Users\15860\miniconda3\python.exe' -Chrome 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

保留新目录即可，无需补填表格。仅在隔离批退出 0、存在 `STORY25_W01_TOOLCHAIN_OK`、散列匹配且新正式只读结果明确后才进入正式恢复。当前不下发正式写入命令，没有已核验的在线访问链接。不重跑 125/125 Django、17/17 PostgreSQL 探针、5/5 专项、M01 独立复验或历史 NFR-001。正式验收建议暂缓。
