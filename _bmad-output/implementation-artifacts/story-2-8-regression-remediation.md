# Story 2.8 · 首批回归失败与集中复验

BMAD 6.12.4 Step 3，规格与 Sprint 保持 `in-progress`。 [失败批次](story-2-8-run-20261128-215250-720/archive.sha256) · [Checkpoint 1](story-2-8-checkpoint-1.md)

## 首批实测

Django 发现并计入 159 项，158 项未跳过，157 通过、1 个方法失败、1 个既有可选 Chrome 项跳过，无错误。失败方法为 `AdminCancellationTests.test_blank_reason_preserves_legal_expiry_without_rendering_stale_form`。三个失败子例均为 `fields={}`，分别在待审核预约开始前、等于开始和开始后。其他 8 个新增方法通过。已有 150 项中 149 通过，只有上述 Chrome 项跳过。批准、拒绝、本人取消、管理员导航及权限的既有用例通过，没有观察到这些功能回归。 [stdout](story-2-8-run-20261128-215250-720/regression.stdout.txt) · [stderr](story-2-8-run-20261128-215250-720/regression.stderr.txt) · [原生退出码 1](story-2-8-run-20261128-215250-720/regression.receipt.json)

失败是新增测试的请求夹具问题，不是旧断言误判、数据库环境故障或本次证据支持的业务缺陷。Django 测试客户端对 `urlencode({})` 得到的空 body 不设置 `CONTENT_TYPE`，因此视图正确拒绝了这个非原生表单请求。只改新增测试，用实际确认页签发的 CSRF token 构造原生 URL 编码的 POST，`reason` 仍分别缺省、为空和为全空白。保留原有原因必填、FR-018 失效与历史、无重复提交表单及无不当写入断言。不改生产代码或旧测试。

## 隔离目标、回滚与探针核对

预检、Django 系统检查、迁移漂移检查及前后基线命令退出均为 0。原归档 27 个文件散列核对一致。两份基线字节一致，SHA-256 为 `6EDF380E544390AC1B975BE960C34049EBB73494111DDA3DED12086C259AC7F8`。目标为 `127.0.0.1:5433/test_lab_booking`、`lab_booking_test`、PostgreSQL 17.12、Read Committed，12 张表、19 条迁移。账号、会话、设备、预约和审计记录均为 0，ACL 与结构前后相同。首批回归失败使批次没有启动 34 组探针，不能把 Django 夹具已清理记成探针已执行或清理通过。 [预检](story-2-8-run-20261128-215250-720/preflight.stdout.txt) · [前基线](story-2-8-run-20261128-215250-720/baseline-before.json) · [后基线](story-2-8-run-20261128-215250-720/baseline-after.json)

| 静态核对 | 结论 |
| --- | --- |
| 夹具编号与清理 | 短随机前缀 17 字符，设备编号加序号不超过 32 字符。探针仅在隔离空基线启动，结束后按本批前缀和会话键清理并核对全量基线。 |
| 路径及泄露 | 发现潜在误判。匿名或禁用会话登录跳转的 `next` 合法包含取消路径，而该路径恰有详情路径前缀。改为解析 URL 并断言站内登录与精确原请求路径，403 不得带跳转，正文不得含该详情链接或私有字段。业务 SQL 和状态不变断言保留。 |
| SQL 与时序 | 复用限定表和参数化查询，锁前定位、设备锁、锁后账号复核、目标重读、真实 SQL 判时和提交次序均保留。快照 JOIN 使用别名限定字段，F2 有意注入的临时表写入定位在 `pg_temp`。 |
| 证据和退出码 | 延用既有批次及 W01 工具。JSONL 明确 UTF-8 且仅在探针子进程退出后读取，分流 stdout/stderr，使用实际进程退出码。首批已正确捕获退出 1 并在失败时保存后基线。复验使用新目录，不覆盖旧批次。 |

## 单批复验

在普通 Windows PowerShell 执行现有批次，保持同一隔离目标。不重复设置环境、不连接正式库。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\run-story-2-8-isolated.ps1"
```

批次成功时应有 `STORY28_ISOLATED_BATCH_OK`。需复核 159 项回归的真实结果、34 组 JSONL 与清理标记、前后快照及散列，再按 BMAD 进入 `review`，由新会话执行独立评审。不标 done、不提交推送。Sprint 8/5、实验 A 原始证据、度量与观察截止不变。 [课程基线](../../docs/course-requirements.md)
