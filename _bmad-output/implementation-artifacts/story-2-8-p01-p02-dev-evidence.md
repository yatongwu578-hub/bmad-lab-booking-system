# Story 2.8 · P01／P02 整改候选与专项验证

2026-11-28（北京时间）｜原 BMAD 6.12.4 Build 续接 D-062。以下先保留运行前的候选和验证准备记录，实际批次与状态见[实测回执与交接](#实测回执与交接)。 [负责人决定](../../decision-log.md#d-062-2026-11-28-负责人批准-story-28-评审处置) · [首评](story-2-8-independent-code-review.md) · [整改交接](story-2-8-remediation-handoff.md)

| 行动项 | 本轮最小改动与待核验断言 |
| --- | --- |
| P01 | 仅管理员取消入口读取原始 WSGI 查询串，在设备筛选表单前严格检查百分号转义和 UTF-8。不触碰角色、CSRF、合法返回筛选或取消业务服务。既有 Django 方法增加七种畸形编码，对未来与到期目标各测 GET 和有效 CSRF 的 POST，共 28 个拒绝请求。断言通用 400、无泄露、无预约/设备/历史业务 SQL、设备锁和判时均未调用，预约/设备/占用/历史不变。合法编码导航、缺省筛选、原因必填、到期 FR-018 和正常取消分别对照。 |
| P02 | 在既有隔离探针增加 `owner-cancel-admin-first` 和 `owner-cancel-owner-first`。使用同一条合法未开始预约、真实管理员和申请人 POST，与现有共享设备锁及最外层事务。独立观察连接验证 `pg_blocking_pids`、提交前不见部分变化、后手锁后重读与 409、最终只转一次且恰一条归属正确的历史。管理员先写非空原因，本人先按原规则写申请人取消和空原因。核对有效占用释放、原预约不替换、清理回到原基线。 |

已完成 Python/PowerShell 语法检查、限定差异核对，以及原始查询校验纯函数的 7 个拒绝和 4 个合法输入检查。这里只是静态和纯函数结果，未运行 Django、HTTP 或连接 PostgreSQL。已静态核查设备编号前缀长度、精确 POST 路由及身份、参数绑定、独立连接与清理、UTF-8 JSONL 和输出分流。原 `.venv` 已有沙箱退出 103 的真实记录，本轮遵照要求未重试。 [103 原生回执](story-2-8-sandbox-preflight/receipt.json)

## 运行方式

开发只在普通 Windows PowerShell 执行一个整改批次，目标仅为 `127.0.0.1:5433/test_lab_booking`。预期 1 个已有 Django 方法（扩充断言，零跳过）及 2 个真实探针组。脚本自动保存 `Start-Process -Wait -PassThru` 的阶段退出码、分流日志、输入散列和前后基线；成功标记为 `STORY28_REMEDIATION_BATCH_OK`。 [现有隔离批次](run-story-2-8-isolated.ps1)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\run-story-2-8-isolated.ps1" -RemediationOnly
```

开发专项回执通过后同步为 `in-review`／`review`，交回原独立评审会话，用同一命令去掉 `-RemediationOnly` 进行一次完整独立复验。全量保留 159 个 Django 方法（其中 9 个 Story 2.8 方法）和 36 个 PostgreSQL 组（原 34＋2）。以上为候选预期分母，实跑须核对实际值。原 150 项回归与旧证据不删不改。申请竞争机制未改，继续复用原 20 请求 × 10 轮 NFR-001 证据。 [历史 NFR-001](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/nfr001-standard.jsonl)

## 整改候选输入 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| `reservations/views.py` | `F4E234D76D98F22BAB422AC81DD3DF007BAE496A78CB4118D09872BC5AC4B945` |
| `reservations/test_admin_cancellation.py` | `75A1A2DAD1452FA8169FB860DA0EE4E672AC3963F962D602442A6C1DEEFF120E` |
| `reservations/management/commands/verify_admin_cancellation.py` | `A296AB44409D903406614FD9B04403EB9E7B66113E91E1727F3E10FB3698DF20` |
| `run-story-2-8-isolated.ps1` | `1FFB6504B7DFC152E170B9A01BD5216665AA6B0202A466602122C8213DE2F3EE` |

冻结规格、正式 AC、D01～D09 延期、两项原始不采纳、Sprint 8/5、实验 A 原件/度量/观察截止保持不变。未访问正式库，未新增迁移或授权，未改 3.1、未标 done、未提交推送。 [课程基线](../../docs/course-requirements.md) · [中央延期台账](deferred-work.md)

## 实测回执与交接

2026-11-28，负责人在普通 Windows PowerShell 运行 `-RemediationOnly`，产生批次 `233025-956`。本会话只读复算，未重跑。Django 专项 **1/1**，零失败、零跳过，两个 PostgreSQL 专项均通过。5 个阶段的原生退出码均为 0，27 份归档文件及其回执中的 stdout/stderr 长度、散列均一致，总标记为 `STORY28_REMEDIATION_BATCH_OK`。 [完成标记](story-2-8-run-20261128-233025-956/outcome.txt) · [归档散列](story-2-8-run-20261128-233025-956/archive.sha256) · [Django 输出](story-2-8-run-20261128-233025-956/regression.stderr.txt) · [探针输出](story-2-8-run-20261128-233025-956/probe.stdout.txt)

- **P01** 对照已绑定的测试源码及通过回执。7 种畸形编码 × 2 类目标 × GET/有效 CSRF POST，共 28 个拒绝请求。逐例断言通用 400、无私有内容或跳转、无受保护业务读取、无设备锁及业务判时，预约、设备、占用及历史快照不变，亦未触发 FR-018。合法编码筛选及站内返回、缺省筛选、非空原因取消、空白原因到期仅失效等对照通过。此证据来自 Django 专项断言，不把每个子例冒充为独立探针。
- **P02** JSONL 证实请求均为真实 POST，与观察者分别使用独立 PostgreSQL 后端。逐组重算阻塞 PID、锁后重读后单次判时、提交前不可见和先后状态/历史。

| 组名 | 先手／后手／观察者数据库 PID | 实际结果 |
| --- | --- | --- |
| `owner-cancel-admin-first` | 29376／44748／22984，后手阻塞于 29376 | 200／409，原记录转为已取消，占用释放。唯一历史归真实管理员，保存非空原因。 |
| `owner-cancel-owner-first` | 27164／2220／22984，后手阻塞于 27164 | 200／409，原记录转为已取消，占用释放。唯一历史归真实申请人，保持本人取消的空原因。 |

两组均由后手锁后重读终态，无状态覆盖或追加历史。独立读回和清理为真。运行前后 15 个输入 SHA-256 完全一致，交接前与工作区逐一相符。数据库仅为 `127.0.0.1:5433/test_lab_booking`，PostgreSQL 17.12、Read Committed；前后基线字节相同且与原开发基线一致，SHA-256 `6EDF380E544390AC1B975BE960C34049EBB73494111DDA3DED12086C259AC7F8`。ACL、12 张表和 19 条迁移不变；账号、会话、设备、预约及审计均归零。 [探针原件](story-2-8-run-20261128-233025-956/probe.jsonl) · [输入清单](story-2-8-run-20261128-233025-956/source-before.sha256) · [前基线](story-2-8-run-20261128-233025-956/baseline-before.json) · [后基线](story-2-8-run-20261128-233025-956/baseline-after.json)

实际通过后按 BMAD 转规格 `in-review`／Sprint `review`，交回原独立评审会话。P01/P02 的正式关闭仍待针对性复审及一次完整独立复验。 [复审交接](story-2-8-p01-p02-review-handoff.md)
