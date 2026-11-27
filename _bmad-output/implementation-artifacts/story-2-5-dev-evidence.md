# Story 2.5 · 开发自测证据

**M01 后续实测。** 原全量记录以下原样保留。D-050 后的 M01 专项另批通过并交回原独立评审会话，见 [M01 开发实测](story-2-5-m01-dev-evidence.md)。

2026-11-27（北京时间）｜BMAD 6.12.4 Build Step 3 实证完成，进入评审待交接。团队在普通 Windows PowerShell 执行 `verify-story-2-5.ps1 -Remediation`。本会话只读复算原始证据，未重新运行测试或连接数据库。适用正式 AC-1～8，基线 `1cedf9687208b20645b1acce3c7755e8525cd9fc`。 [规格](spec-2-5-admin-reservation-query.md) · [正式故事](../planning-artifacts/epics.md#story-25-管理员查询预约详情并按设备筛选)

## 结果和来源

- 18:41:46～18:43:07，原 `.venv` Python 3.13.17、Django 5.2.19、PostgreSQL 17.12，仅 `127.0.0.1:5433/test_lab_booking`，角色 `lab_booking_test`、Read Committed。真实 **5/5** 针对性、**125/125** Django（113 个原用例同名、12 个新增、零跳过）、**17/17** 独立 PostgreSQL 探针。12 个阶段均退出 `0`。独立探针原输出为 `STORY25_PROBE_OK cases=17`，包装记录最终 `complete exit=0`。本批已校验散列的脚本在此终行后直接输出 `STORY25_VERIFICATION_OK`，外层 PowerShell 控制台未另录，不重造转录。 [阶段](story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4/stages.txt) · [针对性](story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4/targeted.stderr.txt) · [全量原始回归](story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4/regression.stderr.txt) · [脱敏机器核对](story-2-5-development-evidence.json)
- 87 个输入前后散列清单相同，并在本文档状态更新前与工作区逐项比对。归档运行时规格的原始字节，便于复算状态转换导致的文档散列差异。四份隔离库基线逐字节相同，独立探针内部前后快照也与其一致。五个受控表均为零行，角色、表／迁移及记录的 ACL 与清理均相同。该摘要不声称覆盖序列值或完整 schema 定义。 [输入清单](story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4/before.sha256) · [运行时规格快照](story-2-5-tested-spec.md) · [清理后基线](story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4/baseline-after-independent.json)
- 首批 **124/125、1 失败、零跳过**，原失败批次及日志 SHA-256 未变。原断言把管理路径 `/reservations/manage/` 中的公共前缀误当本人入口。修复保留同名用例并核对完整链接、管理员无本人入口且直访 403、师生无管理入口及真实 201 本人链接。原本人越权零业务读取用例也在针对性和全量中通过。业务与共享权限代码未因这次修复变更。 [首批原始失败](story-2-5-run-20261127-183352-994-46675338857946d49b0469ce105ed1e6/regression.stderr.txt) · [整改记录](story-2-5-regression-remediation.md)

## 正式 AC 对照

| AC | 实际证据 |
| --- | --- |
| 1 | `navigation-history` 的真实身份与列表/详情响应，跨申请人、设备与五态。逐行核对编号、申请人、设备、日期、完整时段、双状态及原因。维修、停用、已结束与终态仍保留。 |
| 2 | `filtered-affected` 的唯一数据库时刻及固定目标上两条有效结果。已结束待审先失效，目标外设备行／占用／历史不变。可控时间的 Django 用例覆盖开始相等及批准结束前／等于／之后，`commit-after-end` 另有真实跨结束。 |
| 3 | `ordered-locks` 的四把相关设备锁按 PK `906 → 908 → 910 → 911` 升序，权限复核、固定重读、一次取时后三组状态与历史写入。`no-pending-clock` 有一次结束筛选时钟、零设备写锁和 DML。 |
| 4 | `frozen-concurrent-additions` 实际观测阻塞；同设备新增只在下一次出现，目标外新增不处理，重复读取零历史写。`submit-first`／`query-first` 给出独立连接的双方顺序。 |
| 5 | `navigation-history`、`filtered-affected` 与 Django 状态矩阵交叉证明全历史与设备影响筛选语义独立，不以设备当前状态隐藏历史。 |
| 6 | `navigation-history` 的五类持久处理记录逐字段核对。批准无原因不造值，系统明确标注且有固定原因，实际记录时刻与业务时刻分开。历史详情只读、无额外设备写锁，无关预约及设备审计不泄露。`crossed-start` 另证明合法详情失效只追加一次系统历史。 |
| 7 | 20 个逐例请求（8 个匿名或停用跳转，12 个 403）无业务 SQL、无泄露、四类业务状态前后相同。锁中撤权另有真实等待后的 403，已取得必要锁但复核后零取时、零 DML、零提交。合法管理员 200 单列，不混入拒绝分母。仅为本 Story 的 NFR-002 入口证据。 |
| 8 | `edge-input` 核对空匹配与无设备 200、六个非法条件 400、缺失详情 404，未回退全量。迟发投影／第二笔历史／明确提交拒绝的真实 SQLSTATE 分别为 `42703`／`23514`／`23505`，前后相同。提交前真实断开未持久，实际提交成功后驱动确认丢失模拟确实持久；两种未知都返回待核查 503，不声称回滚、不重试。 |

[17 个完整逐例原始记录](story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4/independent.jsonl)

## T-01～T-03 和 NFR-001

T-01 保留可观测的申请先／查询先锁交错、独立连接与不重复历史。T-02 区分精确边界的可控时间、真实等锁跨开始、实际越过结束后提交但保持原判定，以及真实故障与驱动确认丢失模拟。T-03 保留真实路由、实际角色、逐例前后快照、SQL 和响应。聚合脱敏文件不复制响应正文、会话、凭据或账号名，原始批次保留。 [脱敏机器核对](story-2-5-development-evidence.json)

对照 2.1 交付版本 `930d3cb1c6ce02a934a93295b850c9109165dcf1`、本 Story 基线和当前代码，原申请授权／复核、时间解析、设备锁、冲突／申请、唯一判定时钟、失效、历史追加及持久事务函数块一致。模型、SQLSTATE 分类和 PostgreSQL 连接守卫无差异。只读复算 D-040 指向的标准组散列和 10 轮原始响应，每轮 20 个独立连接、有真实锁重叠、1 个 201、19 个明确冲突、1 条有效待审占用。沿用 **历史 20×10**，不计作本 Story 新运行，不重复压测。 [D-040](story-2-1-targeted-independent-recheck/d040-independent-final-review.md) · [历史原始指针](story-2-1-remediation-run-20261126-205236-052-255e13d05b24/historical-evidence.json)

## 状态和边界

开发证据齐备后规格 `in-review`、Sprint Story 2.5 `review`。独立 Code Review 必须新会话执行，本会话未自行评审。正式浏览器与 AC-6 五列 SELECT 尚未执行，仍须另行只读复核和授权，不代表正式验收。PPT 第 25／26 页保留 Story→FR／ADR／PC→AC→证据，第 27 页区分开发、自测、独立评审，第 33 页保留真实产物和状态，第 34 页保留 Sprint 8／5 与实验 A，第 36 页记录实际决定及后验依据。按课程基线和已核对团队资料落实，不代签三人意见，不提前做 Sprint 2 或 Sprint 1 回顾，不标 `done`、不暂存、不 commit/push。 [课程基线](../../docs/course-requirements.md) · [新会话交接](story-2-5-code-review-handoff.md)
