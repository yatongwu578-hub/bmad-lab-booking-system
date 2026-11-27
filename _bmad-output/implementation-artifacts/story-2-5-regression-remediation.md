# Story 2.5 · 真实回归失败与整改复验

2026-11-27（北京时间）｜BMAD 6.12.4 Build Step 3，`in-progress`。沿用已批准的 Story 2.5 规格、AC、FR-002／011／015／018、ADR／PC、Sprint 8／5 和实验 A。不是独立评审、正式运行或验收。 [规格](spec-2-5-admin-reservation-query.md) · [检查点](story-2-5-checkpoint-1.md)

## 实际失败

普通 PowerShell 批次 `story-2-5-run-20261127-183352-994-46675338857946d49b0469ce105ed1e6` 的 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12 隔离身份、系统检查和迁移漂移检查均退出 0。实际运行 `manage.py test --keepdb --parallel 1 -v 2`，125 项中 124 项 `ok`、一个用例失败、零跳过。Django 原进程退出 1，包装正确中止，未进入 17 项探针。设备相关 40 项和新增的 2.5 相关 12 项都为 `ok`。 [完整 stdout](story-2-5-run-20261127-183352-994-46675338857946d49b0469ce105ed1e6/regression.stdout.txt) · [完整 stderr 和堆栈](story-2-5-run-20261127-183352-994-46675338857946d49b0469ce105ed1e6/regression.stderr.txt) · [阶段记录](story-2-5-run-20261127-183352-994-46675338857946d49b0469ce105ed1e6/stages.txt)

`reservations.test_own_reservations.OwnReservationsTests.test_ac1_role_navigation_and_actual_201_contract` 的 `role=Role.ADMIN` 子例在原第 105 行 `self.assertNotContains(identity, self.list_url)` 抛 `AssertionError: 1 != 0`。旧断言期望 `/reservations/` 子串出现 0 次，实际出现 1 次，来自 `href="/reservations/manage/"` 的「预约管理」。响应没有 `href="/reservations/"` 的「我的预约」。这是旧测试匹配边界误判，不是业务泄露或授权变化，不是测试数据／数据库权限问题，也不是 PowerShell 误报退出码。原始日志未编辑。

在当前工作区只读反向检查证实原共享补丁已应用。变更前后条件都是有效、已认证且 `role == Role.ADMIN`，只复用函数；原批次设备创建、编辑、目录和直接权限用例均通过。此次不改设备谓词、业务源码、模型、权限或数据库配置。Django teardown 回报 12 张表、19 条迁移、0 账号、0 会话，与该批次首部相同。该旧批因中止没有独立后置基线，不据此断言全表／ACL 已复核。其前后输入散列清单相同，SHA-256 为 `B04FEF85AB331E84808FB44AF38356C549C8C5AC9F958AD4E4C59F95869B47FF`。

## 必要整改与防误判

- 保留原测试名称和全部既有语义。按完整 `href` 检查，管理员无本人链接或标签、本人列表直访 403，并且确有一个管理入口。学生／教师仍须有本人入口、无管理链接，真实 201 仍须含完整本人链接及原有细节。共 125 项，不删用例、不放宽正式 AC。
- `verify-story-2-5.ps1 -Remediation` 在已有隔离门禁、租约和同一新证据目录下，先运行五项准确命名的针对性测试，再执行 125 项回归与 17 个独立探针。以真实进程退出码、完整标记、测试名称／分母／跳过数及原始 PostgreSQL 逐例记录判定。原基线包含业务行摘要、角色、ACL、表及迁移，增加针对性阶段之后的读回；测试／探针失败时也尝试用同一隔离守卫独立读回，标明 `unchanged`、`changed` 或 `unavailable` 并保留原失败。不自动清库或重跑。
- 已静态核查探针 `finally` 关闭服务、按本批前缀和确切会话键处理夹具、独立读回比较后才记清理。失败后的额外基线不写业务数据。PowerShell 语法与日志解析器用实际原始输出核对，准确读出 124 个唯一成功用例。未将这些静态核对计作新测试。

## 普通 PowerShell 一次复验

原共享补丁已应用，整改已直接写入工作区，不再应用任何补丁。使用之前预检通过的原有环境。

```powershell
Set-Location -LiteralPath 'F:\softwork\SE-Management\bmad-lab-booking-system'
& 'F:\softwork\SE-Management\bmad-lab-booking-system\_bmad-output\implementation-artifacts\verify-story-2-5.ps1' -Remediation
```

只使用 `127.0.0.1:5433/test_lab_booking`，不并跑其他批次。新的成功回执需同时具备五项针对性、125 项全量、17 项探针、前后基线及输入散列一致，并出现唯一整行 `STORY25_VERIFICATION_OK`。本会话复查原解释器仍返回 `103`，没有新的数据库或测试执行。收到普通 PowerShell 批次后核对实际证据，才推进 `review` 并交新会话独立评审。未操作正式库、不改 Sprint 2、不提交或推送。
