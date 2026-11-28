# Story 2.4 · 开发自测证据

**通过开发自测，进入 `review`，未执行独立 Code Review 或最终验收。** 团队在普通 Windows PowerShell 运行原脚本，批次 `story-2-4-run-20261127-234701-350-82341f5be92a40969b6d2e98fef79be1`，2026-11-27 23:47～23:49（北京时间）。本会话只读核验并自动归档，没有另起数据库、浏览器或测试过程。 [正式 AC](../planning-artifacts/epics.md#story-24-取消本人尚未开始的预约) · [批准的设计](story-2-4-checkpoint-1.md) · [D-054](../../decision-log.md#d-054-2026-11-27-负责人批准-story-24-checkpoint-1)

## 批次回执

- 原 `.venv` Python 3.13.17、Django 5.2.19、PostgreSQL 17.12、`127.0.0.1:5433/test_lab_booking`、`lab_booking_test` 和实际事务 `read committed`；无超额角色权限或正式库 CONNECT。8 个阶段各有独立原生退出码 0，stdout/stderr 字节数及散列逐项复算，8 个阶段标记及最终 `STORY24_VERIFICATION_OK` 各唯一。外层 PowerShell 控制台进程的独立退出码未入档，不代填。 [阶段](./story-2-4-dev-run-20261127-234701/stages.txt) · [最终标记](./story-2-4-dev-run-20261127-234701/batch-marker.txt) · [自动回执](./story-2-4-dev-run-20261127-234701/verified-receipt.json)
- 从原始 Django 输出复算 **133/133、125 个既有同名测试 + 8 个新增，零跳过、无缺失或额外项**。既有 125 名称清单散列与 2.5 独立原证一致。Django system check 及迁移漂移检查均通过。 [逐名通过清单](./story-2-4-dev-run-20261127-234701/passed-tests.txt) · [计数](./story-2-4-dev-run-20261127-234701/regression-counts.txt) · [迁移漂移](./story-2-4-dev-run-20261127-234701/migration-drift.stdout.txt)
- **16/16 组 PostgreSQL／HTTP／Chrome 探针**。真实独立连接、请求结果、关键 SQL 绑定、历史及前后读回逐组复核。前后 91 项输入清单逐字节相同，并对运行时工作树重新计算。隔离库三份业务行摘要、ACL、表及迁移记录完全一致，探针首尾数据库对象相等，`cleanup=true`。不推断 PostgreSQL 序列未递增或未覆盖的 schema 细节。 [探针原始 JSONL](./story-2-4-dev-run-20261127-234701/independent.jsonl) · [运行前输入散列](./story-2-4-dev-run-20261127-234701/before.sha256) · [运行时规格](./story-2-4-dev-run-20261127-234701/spec-at-run.md)
- 档案包含 48 个原始文件、运行时规格和核对回执，文件逐份复算；输出中的 CSRF 表单值已掩码，无原始会话凭据。规范化文档与原始 Windows 字节分开保存。 [归档清单](./story-2-4-dev-run-20261127-234701/archive.sha256)

## AC-1～AC-8

| AC | 核验结果 | 对应原证 |
| --- | --- | --- |
| AC-1 | 师生 × 待审核／已批准四个授权正例均 200。原编号、申请人、设备、时段和既有历史不变，独立观察者见占用 1→0。取消先提交后，新合法申请 201 成为唯一有效占用。 | A01-A05、I01、`test_legal_cancellation_retains_record_and_history_and_releases_slot` |
| AC-2 | 五态的开始前、恰等、开始后通过受控 Django 用例，维修／停用设备的已批准预约开始前仍可取消。恰等时，待审核按 FR-018 失效而拒绝取消，已批准保持原状。精确相等由测试专用时钟证明，不声称 PostgreSQL 实际恰好采到同一微秒。 | `test_locked_status_and_exact_start_boundary`、`test_csrf_and_expiry_and_retry_feedback`、I06–I09 |
| AC-3 | 匿名、管理员（含 staff/superuser）、跨归属、停用、无效 CSRF 与锁中撤权共 **16/16** 拒绝、无泄露、无业务变化。同主体下的 6 组异主／不存在对照响应体相同；12 个非法输入或方法另列且零取时、锁和写。确认 GET 对未收尾到期待审只读。 | P01-P07-V01、P08-off、P08-role、权限与只读 Django 测试 |
| AC-4 | 实际业务请求记录了账号复核 → 目标设备锁 → 锁后权限复核／重读 → 唯一数据库取时。I08 两组独立 PID 证实取消请求等待设备锁跨开始，待审核 409 并失效、已批准 409 仍批准。I09 两组取时早于开始、实际提交跨开始仍 200，等待者直到提交后才看到终态，观察者未看到未提交的状态或历史。 | I08、I09 及每个取消正例 SQL 实际绑定 |
| AC-5 | 每次合法取消仅追加一条关联本人历史，真实申请账号、预约外键、`action=cancel`、前后状态、判定时刻与实际记录时间均读回，保留旧历史，不要求理由。状态及历史同事务可见。现有管理员详情读回通过。 | A01-A05、I09、A08、Chrome |
| AC-6 | 到期已结束的待审核目标只提交一条系统 `expire`，系统执行者与固定原因正确，取消响应 409。同设备他人及其他本人待审不被该请求收尾；重复取消零写。已到开始时间的已批准对照仍保留状态和有效占用。到期待审核的数据库收尾不虚报为有效占用从 1→0。 | A06、I06、I07、I08 |
| AC-7 | 两个独立连接的阻塞关系由 PostgreSQL 观测。取消先时随后申请 201，申请先时已返回 409 不改不重试。两个取消竞争仅一次成功。与占用、本人列表、本人详情各测两种先后，含 FR-018 交错，列表保持多设备主键升序，无重叠有效占用、重复转换或历史。 | I01～I09，含 12 条查询交错主路径和两条已批准对照 |
| AC-8 | 取消和失效各 5 个故障，共 **10/10**。真状态／历史错误 23514、提交拒绝 23505 均返回确定回滚；两种分支各有真实隔离后端断开且未持久化、实际 COMMIT 后模拟确认丢失且已持久化。未知均 503「待核查」，仅一次提交尝试，不自动重试，不伪装冲突或报告成功。 | A08 的实际 SQLSTATE、故障前后快照、独立 backend PID 及响应 |

## T 项、浏览器与 NFR

- **T-01／02。** I01–I09 同请求实际先后与独立 PID、锁后唯一判定、受控微秒边界及真实跨界分别留证。A08 的真实 PostgreSQL 故障与实际提交后的模拟确认丢失明确分列。
- **T-03／NFR-002。** 14 个直接拒绝、2 个实际锁中撤权，16/16 同时满足拒绝、无受限数据泄露及预约／设备／有效占用／历史不变。6 个不存在对照、12 个非法输入或方法及授权正例分开；不把本次通过外推为整个系统的 NFR-002。 [本轮分母](./story-2-4-dev-run-20261127-234701/permissions-counts.txt)
- **T-04／NFR-001。** 核心设备行锁、预约申请和冲突判定、共享业务时刻及事务代码未变。只读复算历史 10 轮、每轮 20 个响应，每轮 1 成功／19 冲突／1 有效待审，无其他或无响应。新交错独立计数，不重跑标准竞争，也不把旧 200 请求计为本轮。 [Sprint 1 原证索引](sprint-1-final-acceptance-2026-11-27.md#非功能实证)
- **Chrome。** 159.0.8154.34，师生各 6 条真实文档响应，验证确认、放弃零写、重新进入、取消反馈及返回列表。截图共 4 张。 [学生确认](./story-2-4-dev-run-20261127-234701/chrome-student-confirm.png) · [学生结果](./story-2-4-dev-run-20261127-234701/chrome-student-result.png) · [教师确认](./story-2-4-dev-run-20261127-234701/chrome-teacher-confirm.png) · [教师结果](./story-2-4-dev-run-20261127-234701/chrome-teacher-result.png)

依课程基线和团队既有核对执行 PPT 第 20～39 页适用要求，PPT 原页未直接取得。保持 Sprint 8／5、三位成员共同操作与审阅及实验 A 的原方案；2.6／2.7 必须待实验条件冻结后才可开发。不操作正式库、不授权、不迁移、不自动提交或推送。发布前实际只读权限和迁移状态核验仍未执行。 [课程基线](../../docs/course-requirements.md) · [Sprint 2 与实验 A](../planning-artifacts/sprint-2-startup-and-experiment-a.md) · [独立评审交接](story-2-4-code-review-handoff.md)
