---
title: 'Story 2.3 查询本人全部预约及处理结果'
type: 'feature'
created: '2026-11-27'
status: 'done'
route: 'dispatch'
baseline_commit: 'c4912cb911ffeccbd4a8cfefa0b7eaaf26dab64d'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-3-checkpoint-1.md'
---

<frozen-after-approval reason="human-owned intent">

## Intent

师生目前只能按编号查看单条结果。补齐「我的预约」列表及详情，保留全部本人历史，显示当前设备状态与经授权的处理原因。

## Boundaries & Constraints

以 epics.md 正式 AC-1～8 为准。登录账号限定本人，不接受外部归属。遵守 FR-018、D-024；复用现有模型、权限和事务。仅隔离 PostgreSQL 测试；正式库新增授权另批。不做取消、管理、审批、拒绝、设备状态维护或统一美化。

## I/O & Edge-Case Matrix

| 场景 | 条件 | 结果 |
| --- | --- | --- |
| 导航 | 师生身份页、预约成功页 | 进入「我的预约」，列表可往返详情；管理员无师生入口 |
| 空与拒绝 | 无本人记录、他人或不存在、匿名或管理员 | 空列表 200；他人同不存在 404；匿名登录跳转、管理员 403 |
| 事务异常 | 确认回滚或提交未知 | 各自 503 文案；不显示旧列表，不重试，不把未知说成回滚 |

</frozen-after-approval>

## Code Map

- `reservations/services.py`：沿用 `require_applicant`、`_recheck_applicant`、`_durable_operation`、`_decision_time`、`_expire` 和 `equipment/services.py::lock_equipment`；参考 `get_daily_occupancy` 冻结候选。不改申请和设备占用路径。
- `audit/services.py`：保留 `append_reservation_expiry`；增加受限原因投影，不查整行。现有历史读权仅 `id`，精确列投影与待审授权详见检查点。
- `reservations/urls.py`、`reservations/views.py`：新增 `reservation-list`，保留 `reservation-result` 原 URL 和成功页 201 契约。

## Tasks & Acceptance

- [x] `reservations/services.py`、`audit/services.py`：统一本人列表和详情的候选限制、排序锁、锁后复核与重读、判定和投影；返回提交后的状态。
- [x] `reservations/views.py`、`reservations/urls.py`、`reservations/templates/reservations/{list,result}.html`：GET 无缓存，展示北京时间和分离的双状态，处理导航、空态与异常。
- [x] `accounts/views.py`、`accounts/templates/accounts/identity.html`：用现有师生角色策略控制入口。
- [x] `reservations/test_own_reservations.py`、`reservations/management/commands/verify_own_reservations.py`、`_bmad-output/implementation-artifacts/verify-story-2-3.ps1`：执行正式八条 AC、边界矩阵、权限和真实独立连接探针，保留 103 项原回归。

- AC-1 给定本人五态及他人记录，查询列表和详情时，显示本次本人全部记录及完整设备、日期和时段，保留已结束及终态。
- AC-2 给定已批准预约和变动设备，查询时显示设备最新可用／维修／停用状态，预约仍为已批准。
- AC-3 给定关联的拒绝或管理员取消历史，查询时仅显示匹配原因，不显示其他操作历史。
- AC-4 给定待审，查询时早于开始保持；等于或晚于开始（含已结束）持久失效、释放占用并仅追加一次系统历史，其他状态不变。
- AC-5 给定固定本人候选，查询时仅按主键升序锁相关待审设备，锁后复核、重读、取一次数据库时钟并同事务收尾；无待审不加设备写锁。
- AC-6 给定匿名、管理员或其他账号，直访或篡改参数时拒绝或不扩大范围，不泄露、不写；合法本人访问单测。
- AC-7 给定冻结后新增或无匹配，查询时新记录下次才见，空列表或统一 404 按矩阵返回。
- AC-8 给定跨设备收尾发生确认失败或提交未知，返回区分的 503；前者状态及历史一起回滚，后者不推断持久性。

### Review Findings

BMAD 6.12.4 full，2026-11-27。初审 0 Decision、8 Patch、2 Defer、9 Rejected。负责人在 Step 4 选择 2，P01～P08 保留为未完成行动项并批准非阻塞延期，W2 保持原延期，W1 保留原分类及编号但在处置后单列为未关闭的 High 发布门槛。0 项修复，待一次独立隔离复验。 [独立评审与逐条裁决](story-2-3-independent-review.md) · [人工处置](story-2-3-review-disposition.md)

- [ ] [Review][Patch] P01 中：明确旧 I7 的版本边界或更新可执行探针，保留历史证据 [reservations/management/commands/verify_reservation_transactions.py:121]
- [ ] [Review][Patch] P02 低：将取时 → 双写 → 提交的完整顺序断言下沉到常规探针 [reservations/management/commands/verify_own_reservations.py:320]
- [ ] [Review][Patch] P03 低：将异主／不存在请求的精确归属绑定与零设备锁／原因读取断言下沉到常规探针 [reservations/management/commands/verify_own_reservations.py:374]
- [ ] [Review][Patch] P04 低：在 201 的常规回归补齐编号、设备与完整北京时段逐字段断言 [reservations/test_own_reservations.py:99]
- [ ] [Review][Patch] P05 低：保持原因文本的原始换行与空格布局，继续自动转义 [reservations/templates/reservations/list.html:29]
- [ ] [Review][Patch] P06 中：补写入成功后原因 SELECT 失败的混合列表回滚探针 [reservations/management/commands/verify_own_reservations.py:518]
- [ ] [Review][Patch] P07 低：同起始时刻的预约按编号次序补常规回归断言 [reservations/services.py:181]
- [ ] [Review][Patch] P08 低：可在本人页面明确判定口径，采样时复用已有北京时间，不额外取时 [reservations/templates/reservations/list.html:7]
- [x] [Review][Release Gate] W1 高，已关闭。原发现为运行角色缺历史原因四列 SELECT [audit/services.py:17]，保留初审 Defer 及后续单列发布门槛的处置。批准的授权已提交，本轮最后一次正式前后只读核验均精确，无表级 SELECT 或转授。见 [最终验收](story-2-3-final-acceptance.md)。
- [x] [Review][Defer] W2 中：共享隔离库的旧租约协调 [verify-story-2-3.ps1:94] — deferred：沿用 RD01／2.2-D1，现阶段同库串行，中央台账待安全合并。

#### Rejected

- #02 false：正式状态机只允许有效操作形成对应终态历史，当前入口也不创建该类矛盾历史。
- #03 false：空的管理员原因与重复终态转换均不是合法历史，组合不会由业务入口产生。
- #04 low：每条失效的双写确有成本，但当前无可证实的短事务违约，无必要引入批写重构。
- #07 low：已结束夹具不证明曾经占用，但真实跨开始探针另有有效集合 1→0 及持久读回，无须另加重叠预约矩阵。
- #10 false：仅认证受控表摘要、表与所有者清单及迁移登记，不宣称完整 schema、ACL 或序列指纹。
- #11 false：exit 0 是原生进程退出事实，不等同该阶段最终通过，必需标记失败不会出现完整成功信号。
- #14 false：当前业务不存在并且正式状态机禁止更改既有预约设备；任意数据库侧重挂不属于本 Story 写入口。
- #16 low：八秒窗口测不到时探针失败，不会伪通过。该批已真实进入等待，不增加隐式重跑。
- #23 low：不重叠 201 不证明原窗口。真实跨边界探针、已验收占用规则及同源提交回归已分别覆盖正式目标。

## Implementation Notes

- 主代理复读了 Story 2.3 范围内的新旧差异，前三项为实现交付，最后一项真实测试仍待执行。提交、设备占用、失效写入、判定时钟和事务实现保持原代码。
- 沙箱使用项目原解释器测得退出 `103`。本轮不把静态检查当测试通过，保持 `in-progress`，尚未进入 BMAD Step 4。 [验证交接](story-2-3-verification-handoff.md)

- 2026-11-27 普通 PowerShell 开发批次 `story-2-3-run-20261127-111101-492-41d9eb74` 的 113/113 Django（原 103 项同名、10 项新增、零跳过）、15/15 独立探针、10/10 阶段退出 0、83/83 输入与隔离夹具清理均以原始回执复核。正式 AC-1～8 满足开发验证，规格及 Sprint 进入评审，独立评审须新开会话。 [开发证据](story-2-3-dev-evidence.md) · [归档](story-2-3-run-20261127-111101-492-41d9eb74/README.md) · [独立评审交接](story-2-3-code-review-handoff.md)

## Spec Change Log

## Review Triage Log

- **2026-11-27，D-047**。负责人选择 2。P01～P08 保留为未完成行动项，批准非阻塞延期，分别记录依据、残余风险及下次处理节点。W2 延用，W1 原记录保留但单列为 High 必须通过的正式发布门槛。九项驳回未改，不将负责人接受评审视作通过独立复验或最终验收。规格和 Sprint 同步为 `in-progress`。 [人工处置](story-2-3-review-disposition.md) · [决策记录](../../decision-log.md#d-047-2026-11-27-负责人处置-story-23-独立评审)

## Verification

普通 PowerShell 先用原 .venv 执行只读预检，批准开发后在 `127.0.0.1:5433/test_lab_booking` 运行独立单批脚本。以检查点的逐例证据、退出码及精确标记为准。完成自测后进入 review，另开会话独立评审。

- **Step 4 后一次独立复验待执行。** 经语法、源码前置检查及开发归档离线审计，原 [review-story-2-3-isolated.ps1](review-story-2-3-isolated.ps1) 可直接在普通 PowerShell 运行，不追加整改轮。新实测以原 `.venv`、Python 3.13.17、`127.0.0.1:5433/test_lab_booking` 的新批次和唯一 `STORY23_INDEPENDENT_REVIEW_RUN_OK` 为准。旧 I7 没有重跑，混合列表迟发原因 SELECT 故障未单独实测。复用已独立核验的 NFR-001，不重跑 20×10，不等整点。

- **2026-11-27 独立隔离复验通过。** 新批次由团队普通 PowerShell 实际执行并保留唯一 `STORY23_INDEPENDENT_REVIEW_RUN_OK`。独立评审只读复算 113/113 Django、15/15 PostgreSQL、10 个退出 0、83 项散列、夹具清理和全部正式 AC 原证。中央台账合并一次，P01～P08、W2 和单列 W1 完整，原内容不改。保持负责人处置和证据限制，规格/Sprint 回到 `in-review`/`review`，待 W1 正式只读复核、另批最小授权及真实 Chrome；不标 done。 [独立复验核对](story-2-3-independent-recheck.md) · [正式运行与取证](story-2-3-formal-runtime-handoff.md)

- **2026-11-27，D-048 最终验收。** 负责人确认实际浏览器权限体验，接受教师本人详情未在正式 Chrome 执行、用独立实测支持功能验收。学生 FR-018、正式零预约 POST 补证及五项 Finish 断言均有原证。W1 关闭，规格与 Sprint Story 2.3 更新为 `done`，P01～P08、W2 不关闭。 [最终验收](story-2-3-final-acceptance.md) · [正式原始证据](story-2-3-formal-runtime-evidence/README.md)
