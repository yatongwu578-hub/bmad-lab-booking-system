# Story 2.5 W01 · Windows 日志编码整改与恢复证据

2026-11-27，北京时间。属于 BMAD 6.12.4 的 W01 发布工具整改。沿用 D-051 条件批准和原课程证据，不改变需求、业务代码、迁移、数据、权限范围、Sprint 8／5、实验 A 或 Story 状态。M01 已关闭，W01 仍待正式验证。

## 首次普通 PowerShell 复验发生了什么

- `F:/softwork/outputs/story-2-5-w01-toolchain-20261127-220258-489-66f4c48ec3eb4da2a869b641d52a582e/` 中唯一实际启动的原生阶段是 `initdb.exe`。原始 `initdb.stdout` 为 602 字节，首段十六进制 `B4 CB CA FD BE DD BF E2`，SHA-256 `06E608385B7BC698A73ADA3DF491C9A326B10A95D4AD037A596F94EB2CFC83BC`。stderr 为 0 字节，真实 `initdb.exit` 是 0。
- 旧 `test-story-2-5-w01-toolchain.ps1:46` 无条件用严格 UTF-8 读取全部子进程 stdout。CP936 严格解码为「此数据库系统的文件将归用户……所有」，按 CP936 回编码逐字节相同。Windows 环境的 zh-CN ANSI 和控制台原生代码页检查为 936。兼容的 GB18030 也能解这段字节，因此不能用单段文本宣称区分所有兼容编码，更不能把其他子进程日志一律认作 GBK。wrapper 的退出 1 由解码异常导致，不是 `initdb` 失败。
- 当批未启动 PostgreSQL 服务或 Chrome。私有临时目录仅剩已初始化的数据文件，无 `postmaster.pid`、无临时 passfile、无引导密码文件或 SQL。55435／49173 无残留监听。原始文件和该批历史目录未覆盖。
- 正式普通 PowerShell 只读批 `F:/softwork/outputs/story-2-5-w01-inspect-20261127-220247-474-dd6e606e1c7d4218aa01f6d5071f3bd9/` 原始行 SHA-256 与 JSON 内置值一致。原生 psql 退出 0、`STORY25_W01_INSPECT_OK`、本机 8005 当时空闲。22:02:47 北京时间观察到五列全缺，截止 22:22:47。历史详情预约 #1 与筛选预约 #2 当时安全。该回执只作为历史锚点，正式授权前必须重新实测。

## 采用的编码契约

| 来源 | 输出及消费约定 |
| --- | --- |
| PowerShell 脚本／JSON | 控制台协议显式 UTF-8。UTF-8 有／无 BOM 都可严格解码，格式和唯一成功标记另行验证。失败先落原生退出码、两路原始散列及字节数。 |
| PostgreSQL 客户端 | `PGCLIENTENCODING=UTF8` 的查询行使用严格 UTF-8。错误页、客户端诊断、`initdb`、`pg_ctl` 和 postgres 日志保留原始字节。非结构化原生诊断不决定成功，仅在需要阅读已知来源时用指定 ACP 或 BOM。预期 SQLSTATE 和诊断中的 ASCII 机器令牌在原始字节中核对，不尝试以 UTF-8 解整份混合日志。 |
| Python 和 Node | Python 子进程运行时输出显式 UTF-8。Node JSON 用 fatal UTF-8 解码而不是替换非法字符。两端受控日志文本严格按 UTF-8 读取，不使用替代字符或忽略非法字节。失败先以真实退出码归档和传播。 |
| Chrome 和 Windows netstat | Chrome stdout、stderr 按字节留存，不参与协议判定。Chrome 的专用调试端口文件只收 ASCII；浏览器事件为 UTF-8 JSONL。netstat 仅从保存的原始日志匹配 ASCII 地址和 PID，不依赖本地化状态词。 |

## 已完成的验证及边界

- 离线编码批 `F:/softwork/outputs/w01-encoding-fc64bf467f104d508dd7d7b59709849c/` 实际 11 项通过，退出 0，`STORY25_W01_ENCODING_OK`。验证 UTF-8 中文与英文、BOM JSON、CRLF、CP936、实际 initdb 原件严格往返、截断 UTF-8 拒绝、原始散列不变、子进程真正退出 23、存在成功字样也不判成功及重复标记拒绝。
- 定向批 `F:/softwork/outputs/story-2-5-w01-toolchain-20261127-221233-254-c12473650df5459f941cc194ed8bce1f/` 对原 SQL 文件及历史 17 项证据中的案件列表、源码清单、成功／回滚关键原件和退出码做散列约束。实跑重新初始化的一次性 17.12 集群，真实 `initdb` 退出 0，读回及仅用于合成夹具的五列授权与快照成功，不重跑 17 个旧分支。未与原有 5433 数据库连接。
- 批次到达 Chrome 后再次碰到本沙箱的 GPU 崩溃，Node 在 `Network.enable` 超时并退出 1，不是编码失败或预期 409 注入。Chrome 根进程已退出，synthetic 账号临时文件不进入归档。隔离 PostgreSQL 执行停止并退出 0，本批 scratch 已删除。缺少完整资格标记及真实 Chrome 联合证据。
- 使用正式只读锚点参数的后续定向批 `F:/softwork/outputs/story-2-5-w01-toolchain-20261127-221411-340-f4a42b3365334ba88b296508eb7882e8/` 同样实证编码检查、初始化、A／B／C 全部退出 0，随后 Chrome 同一已知阻塞。关闭进程退出 0，无数据库临时目录、无测试监听，无资格标记、无正式入口。正式只读锚点仅做归档校验，未连接正式库。
- 不把原 125/125 Django、17/17 业务 PostgreSQL 探针及 NFR-001 当成本轮运行，均保留原证。团队共审及原有课程产物照旧。未执行正式授权、未新增样本、未改 Sprint 状态，也未 commit 或 push。

## 普通 Windows PowerShell 定向恢复

```powershell
$W01 = 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\story-2-5-review-support'
$SqlEvidence = 'F:\softwork\outputs\story-2-5-w01-toolchain-20261127-215403-170-2ded2bab12dc445682054831fb2e5329'
$ReadOnly = 'F:\softwork\outputs\story-2-5-w01-inspect-20261127-220247-474-dd6e606e1c7d4218aa01f6d5071f3bd9\w01-inspect.json'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $W01 'test-story-2-5-w01-toolchain.ps1') -FixturePython 'C:\Users\15860\miniconda3\python.exe' -ResumeFrom $SqlEvidence -FormalInspectionEvidence $ReadOnly
```

此命令不连接正式库。只有该批完成真实 Chrome 与后置核验后才生成新目录中的 `formal-ready.ps1`，同时输出实际路径及 `STORY25_W01_TOOLCHAIN_OK`。退出 0 后，运行生成的入口才会连接正式库。它重新执行只读预检、时间窗口及专属端口和真实 Chrome renderer 检查，只按仍然缺失的列授权，并独立 ACL 读回，运行正式 Chrome 和后置检查。若前次授权已提交，重新运行入口自动跳过授权，或加 `-ResumeBrowser` 强制仅允许权限已到位时继续。原始证据每次写入新目录。脚本使用原项目 `.venv` 进行正式运行。
