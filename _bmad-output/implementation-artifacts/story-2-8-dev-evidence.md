# Story 2.8 · 开发自测与复验

2026-11-28（北京时间）｜BMAD 6.12.4 Step 3 实证完成，转入独立评审。复验由负责人在普通 PowerShell 执行，本会话只读核对实测记录，未重新运行。唯一基线为 [2c6380ac608b356df5f0be8251fa4882327e3eab](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/2c6380ac608b356df5f0be8251fa4882327e3eab)。 [实施规格](spec-2-8-admin-cancellation.md) · [正式 AC-1～AC-8](../planning-artifacts/epics.md#story-28-管理员取消预约并记录原因)

## 批次结果与证据链

- **首次失败保留。** 首批 `215250-720` 的 27 个归档散列一致。原生回归退出 1，159 项中 157 通过、1 个新增方法失败（3 个子例）、1 项既有 Chrome 跳过。缺省原因夹具已用确认页签发的 CSRF token 构造合法表单，未改原断言。本轮该方法通过。 [首次失败归档](story-2-8-run-20261128-215250-720/archive.sha256) · [整改记录](story-2-8-regression-remediation.md)
- **复验通过。** 新批 `220430-872` 的 35 个归档散列及 7 个阶段回执均复算一致。原生退出码全为 0，含预检、前/后基线、系统检查、迁移漂移、回归和专项探针。Django 计入 159 项，158 通过、0 失败或错误、1 项历史可选 Chrome 跳过，9 个新增方法全通过。原批准 6 项、拒绝 9 项、本人取消 10 项及原导航／权限用例通过。无迁移漂移。 [归档](story-2-8-run-20261128-220430-872/archive.sha256) · [Django 明细](story-2-8-run-20261128-220430-872/regression.stderr.txt) · [回归原生回执](story-2-8-run-20261128-220430-872/regression.receipt.json) · [总标记](story-2-8-run-20261128-220430-872/outcome.txt)
- **实测对象与清理。** `127.0.0.1:5433/test_lab_booking`，`lab_booking_test`，Python 3.13.17、Django 5.2.19、PostgreSQL 17.12、Read Committed。专项 JSONL 36 行（起始账本、34 个唯一案例组、清理账本），`cleanup=true`。前后基线字节一致，SHA-256 `6EDF380E544390AC1B975BE960C34049EBB73494111DDA3DED12086C259AC7F8`。12 表、19 迁移，账号/会话/设备/预约/审计均归零，ACL 和结构相同。14 个输入散列前后一致且在移交前比对当前文件一致。相较首批，输入只变了新测试、新探针和规格过程备注，未改业务源码。移交改动仅涉及文档状态和说明。 [前基线](story-2-8-run-20261128-220430-872/baseline-before.json) · [后基线](story-2-8-run-20261128-220430-872/baseline-after.json) · [输入散列](story-2-8-run-20261128-220430-872/source-before.sha256) · [探针 JSONL](story-2-8-run-20261128-220430-872/probe.jsonl) · [探针原生回执](story-2-8-run-20261128-220430-872/probe.receipt.json)

## 正式验收逐项核对

下表的 Django 方法均已运行并通过，探针组名对应原始 JSONL 的 `case`。只有开发验收结论，尚无独立评审或最终验收。 [Django 断言](../../reservations/test_admin_cancellation.py) · [探针断言](../../reservations/management/commands/verify_admin_cancellation.py)

| 正式依据 | 实际核对的通过证据 |
| --- | --- |
| AC-1 · FR-014/008 · ADR-003/004 | `test_confirmation_successful_post_and_authorized_history_with_filter`、`test_locked_start_end_boundaries_and_device_status`、`test_pending_cancel_releases_future_slot_and_approved_running_slot_projects_unoccupied`。列表／详情确认、回原筛选、待审核和已批准合法取消、维修/停用不另禁、原记录保留。真实 `submit-cancel-first` 的取消 200、后申请 201，最终仅新申请占用。 |
| AC-2 · FR-018 · ADR-004/005/006 | `test_locked_start_end_boundaries_and_device_status` 与 `wait-crosses-pending`。到开始时只写目标失效和一条系统历史，邻项保留。四个到期查询交错组分别证明先后均只失效一次。 |
| AC-3 · FR-014 · ADR-004/007 | `test_locked_start_end_boundaries_and_device_status` 覆盖已批准开始前、恰到开始、进行中、结束相等及之后。真实 `wait-crosses-approved` 和 `approve-first-wait-crosses-end` 保持已批准，无取消或失效历史。 |
| AC-4 · FR-014/018 · ADR-005/006 | `test_blank_reason_preserves_legal_expiry_without_rendering_stale_form` 覆盖结构合法的缺省、空串和全空白。未到期提示必填且无写；到期提示必填和未取消，只提交失效和系统历史。两种状态分支的故障证据见 AC-8。 |
| AC-5 · FR-014/015 · PC-013 | `test_confirmation_never_expires_due_target_and_terminal_or_missing_never_changes` 覆盖三种终态、404 和快照不变。真实 `cancel-cancel-first` 为 200/409，仅一条取消历史。 |
| AC-6 · FR-002/018 · ADR-002～005 · PC-003～005/008 | 角色、CSRF、畸形及陈旧身份 Django 断言通过。专项 `permissions`、`invalid-requests`、`revoke-role`、`revoke-active` 实跑通过。读取并比对记录中的权限复核、目标定位、设备锁、锁后重读与唯一数据库时钟；降权和停用均在等锁后返回 403，不判时、不提交。旧多设备升序锁用例通过。 |
| AC-7 · FR-009/014/015 · ADR-002/006 | `test_confirmation_successful_post_and_authorized_history_with_filter` 证明管理员可看完整历史、原申请人仅看本人状态及转义原因、其他用户和占用投影不泄露。独立回读核对历史管理员、对象、前后状态、原因、判时与记录时间。系统失效历史与人工取消分开。 |
| AC-8 · FR-008/015/018 · ADR-003～008 · PC-014 | 15 个争用顺序组、5 个真实时间边界组和 10 个故障组通过。核对独立 PID、实际阻塞和提交前无部分可见。批准先且未到结束，两项均成功，历史顺序为批准→取消；取消先则批准 409，拒绝与取消只允许先行者转换。状态/历史约束失败和 COMMIT 拒绝返回确认回滚。F3 真实断连后无持久化，F4 真提交后模拟确认丢失并独立回读到持久化，两者均只提示待核查，不重试。 |

## T-01～T-04 和 NFR

- **T-01** 按真实数据库阻塞证据核对取消与重复取消、申请、批准、拒绝、管理员/本人查询和到期失效的顺序，不以随机并发替代。申请先为冲突 409，取消先可重新申请。
- **T-02** 精确前/等/后来自 Django 受控判时，真实等锁跨开始/结束与判时后提交跨界来自独立连接探针。状态与历史未部分可见，实际时间分层记录。
- **T-03／NFR-002（仅 2.8）** 角色拒绝 22/22，含匿名/学生/教师/标志不等于角色/禁用会话 20 次以及锁后撤权 2 次，均拒绝、无泄露、预约/设备/占用/审计不变。CSRF 及畸形 14/14，分开计数。登录跳转仅保留原取消路径的 `next`，本轮未误判为详情泄露。合法管理员和本人读取作为独立对照，不计入拒绝分母。
- **T-04／NFR-001** 预约竞争基础没有变更。只读核验并复用 2.1 的 20 请求 × 10 轮，每轮 1 成功、19 明确冲突、1 条有效占用。2.8 新交错独立归档，不合并统计、不重跑标准组。 [2.1 验收](story-2-1-final-acceptance.md) · [原始标准组](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/nfr001-standard.jsonl)

## 课程与移交边界

保留规格冻结区和 8/5 Sprint 范围，实验 A 原始材料、五项口径、观察截止不变。依据仓库课程基线和团队记录执行 PPT 第 20～39 页适用条款，不声称见到了仓库未提供的原 PPT。保留失败与实际决策、不代签三人审阅。本次未访问正式业务库，不启动 3.1，不标 done、不提交推送。 [课程基线](../../docs/course-requirements.md) · [D-061](../../decision-log.md#d-061-2026-11-28-负责人批准-story-28-实施) · [独立评审交接](story-2-8-code-review-handoff.md)
