# Story 2.5 · M01 独立复验回执与 W01 移交

2026-11-27（北京时间），续接 BMAD 6.12.4 原独立评审。D-050 的 M01 **通过整改后独立实跑，具备代码问题关闭条件**。正式 AC-1～AC-8 的隔离功能验收证据齐备，没有发现新增代码阻塞。**W01 仍阻塞正式业务库发布，不把隔离验收当作正式运行或负责人最终验收。** 规格和 Sprint 仍为 `in-review`／`review`。不标 `done`。 [D-050](../../decision-log.md#d-050-2026-11-27-负责人批准-story-25-独立评审处置) · [此前源码复审](story-2-5-m01-independent-recheck.md)

## 实际独立批次

团队从普通 Windows PowerShell 执行最新评审脚本。新批根在 `F:\softwork\outputs\story-2-5-isolated-review-20261127-205155-201-532c39d28e5240d286211a51b403131f`。20:51:55～20:53:18，原 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12，`127.0.0.1:5433/test_lab_booking`、`lab_booking_test`、Read Committed。复读原始文件而非只读控制台摘要，重新得到相同审计结果。 [46 个原文件散列与审计](story-2-5-review-support/story-2-5-m01-independent-run-audit.json) · [运行时规格快照](story-2-5-review-support/story-2-5-m01-independent-tested-spec.md)

- 专项 5/5、Django 125/125（113 个旧用例、12 个新增，零跳过）、17/17 PostgreSQL 探针。12 个内层阶段退出 0，外层离线审计子进程退出 0、无错误输出或失败回执，两个位置归档的内层标记均为唯一 `STORY25_VERIFICATION_OK`；实际探针终行 `STORY25_PROBE_OK cases=17`，审计终行 `STORY25_OFFLINE_AUDIT_OK`。
- 外层脚本最后向控制台输出的 `STORY25_REVIEW_RUN_OK` 与该外层 PowerShell 进程退出码没有单独入档。现有两个门槛回执及脚本末尾逻辑支持成功路径，但不冒充实际归档了外层终行或外层进程退出码。原始运行证据足以判定功能用例和 M01。若需要补形式记录，可转存当时控制台回执，不重新跑测试。
- 前后 87 项清单逐字节相同并对运行输入复算，四份业务／ACL／表迁移基线同散列 `6EDF380E544390AC1B975BE960C34049EBB73494111DDA3DED12086C259AC7F8`。原始 JSONL 首尾快照与外层一致，`cleanup=true`，夹具恢复。摘要不声称完整 schema 定义或序列递增不变。
- `edge-input.m01` 对同一到期待审预约 #1215。空、空白、重复、33 字符、NUL 各 400，零业务 SQL、锁、时钟、业务提交或历史尝试，仍为待审核。合法导航 200，一次设备锁、一次取时，一次提交中持久化预约失效和系统历史 #585。随后无参 200，零写，未重复新增历史。初始到期待审已无逻辑有效占用，本组不夸称释放一个占用。

## 正式 AC 裁决

| AC | 整改后独立隔离裁决及主要原证 |
| --- | --- |
| 1 | 满足。身份导航、全量五态、具体详情、北京时段、申请人与双状态，终态及历史不隐藏。 `navigation-history` |
| 2 | 满足。精确设备选择，先查已结束待审，严格结束边界且不改无关设备。 `filtered-affected`、`commit-after-end` |
| 3 | 满足。固定候选，在四把需要的设备锁 985→987→989→990 后权限复核和重读，一次业务时钟；无待审筛选取时但不锁。 `ordered-locks`、`no-pending-clock` |
| 4 | 满足。实际等锁、申请先与查询先、并发新增留待下一次查询。 `frozen-concurrent-additions`、`submit-first`、`query-first` |
| 5 | 满足。全量含终态与已结束，筛选仅目标设备受影响范围，恢复导航均区分。 `navigation-history`、`filtered-affected` |
| 6 | 隔离功能满足。详情呈现已持久化的实际历史、执行者类型、两种时刻和适用原因；合法失效不重复。正式运行的列权仍由 W01 验证。 `navigation-history`、`crossed-start` |
| 7 | 满足。20 次初始拒绝和 1 次锁中撤权，无业务提交或数据泄露，合法管理员对照另列。 `permissions`、`revoked-while-waiting` |
| 8 | 满足。空匹配、非法输入、404、M01 五个 400 零业务影响；实际迟发故障及服务器明确拒绝提交均回滚，连接确认未知与实际提交后模拟丢确认均明确返回待核查，不自动重试。 `edge-input.m01`、五项故障探针 |

中央台账 17 项和原处置不变，未追加。原有 NFR-001 20 请求 × 10 轮证据逐轮复核保留，不重跑。遵循正式 AC → 原证、独立会话和真实人工决定的课程要求，PPT 原件仍未取得，按课程基线及既有团队核对落实第 25／26／27／33／34／36 页要求。不改 Sprint 8／5、实验 A，不分拆个人任务，三人共同操作。没有修改任何业务代码、提前开发、提交或推送。 [中央台账](deferred-work.md) · [课程基线](../../docs/course-requirements.md)

## W01 当前状态

上一条正式证据表明五列均缺，但不能代替当前有效 ACL。已检查本机监听，5433、8000、8001 在用，当时未见 8005 监听。此次沙箱对现有受保护 passfile 的可用性检查返回拒绝，未连接正式库。准备了普通 PowerShell 只读预检，会自动出实测缺列、既有账号／样本概况和 FR-018 风险窗口。**未执行迁移或 GRANT。** [W01 只读预检、实际运行和自动归档](story-2-5-review-support/story-2-5-w01-execution.md)
