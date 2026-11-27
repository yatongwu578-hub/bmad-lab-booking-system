---
title: 'Story 2.5 管理员查询预约详情并按设备筛选'
type: 'feature'
created: '2026-11-27'
status: 'done'
route: 'dispatch'
baseline_commit: '1cedf9687208b20645b1acce3c7755e8525cd9fc'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/story-2-5-checkpoint-1.md'
---

<frozen-after-approval reason="人工确认的实施意图">

## Intent

让业务管理员从身份页进入「预约管理」，查询全部预约、查看单条详情及实际转换历史，或按具体设备编号筛选受影响预约。

## Boundaries & Constraints

以 `epics.md` 正式 AC-1～8 为准。先授权，固定候选，按需失效。仅开发 2.5，不加处理按钮、其他操作、审计模块或统一美化。只在隔离库开发和测试。正式授权和运行另批。Sprint 8／5、实验 A 不变。

## I/O & Edge-Case Matrix

| 输入 | 结果 |
| --- | --- |
| 有效条件无匹配 | 200 明确空态，不回退全量 |
| 筛选格式错误、合法编号不存在、详情不存在 | 分别 400、200 空态、404；无业务副作用 |
| 匿名、非业务管理员 | 登录跳转或 403，无受限信息 |
| 确认回滚、提交未知 | 不同 503 文案，均无成功结果，不自动重试 |

</frozen-after-approval>

## Code Map

- `reservations/services.py` 复用 `_durable_operation`、`_decision_time`、`_expire`、`RESULT_FIELDS`；参考 `_read_own_reservations` 与 `get_daily_occupancy`，不改旧路径或核心协议。
- `equipment/services.py` 复用 `lock_equipment`，原管理员谓词与 `accounts/policies.py` 共享；`audit/services.py` 保留旧原因投影和失效追加。

## Tasks & Acceptance

- [x] `accounts/{policies,views}.py`、`accounts/templates/accounts/identity.html` 落实角色策略及入口；`equipment/services.py` 保留原谓词接口和行为。
- [x] `audit/services.py` 为结果集合批量读取适用原因，为授权详情精确读取已有转换历史。
- [x] `reservations/services.py` 实现列表、设备筛选和详情。先查数据库有效角色再冻结，锁后复核并重读，单次取时后收尾、筛选和投影，提交后返回。
- [x] `reservations/{forms,views,urls}.py`、`reservations/templates/reservations/admin_{list,detail}.html` 接入 GET、表单、双状态、详情及返回路径。
- [x] `reservations/test_admin_reservations.py`、`reservations/management/commands/verify_admin_reservations.py`、`_bmad-output/implementation-artifacts/verify-story-2-5.ps1` 覆盖下列 AC 和异常矩阵，复用现有验证器模式。

- AC-1／5 给定多设备、五态和多申请人，查全量或详情时保留终态及已结束记录，呈现申请人、设备、北京时间时段、双状态和适用原因；清楚区别筛选与全量。
- AC-2 给定目标设备，筛选时先检查含已结束待审的固定候选，仅返回未到开始的待审和 `end_at > t_decision` 的已批准，两类均须未结束。
- AC-3／4 给定固定候选或并发新增，仅锁待审候选涉及设备，去重升序，锁后按固定 ID 和原限定重读；无待审不锁，筛选仍取唯一时刻；新增留待下次。
- AC-6 给定持久转换，授权详情展示原预约、实际执行者、动作、前后状态、记录及判定两种时刻和适用原因；历史投影只读，系统与人工分离，无虚构记录。
- AC-7 给定非管理员或锁后撤权，请求不返回业务信息、不触发失效或写入；初始未授权不取业务锁。
- AC-8 给定边界输入或事务故障，按矩阵返回；确认失败整体回滚，未知不承诺持久性。

### Review Findings

BMAD 6.12.4 full 独立评审。0 Decision、13 Patch 候选（仅 M01 必须整改）、5 Defer、3 驳回，另有 W01 正式 ACL 门槛。原始分类已保留。负责人在 Step 4 选择 2「保留为行动项」。M01 待原 Build 会话整改；P01～P12 转条件延期，D01～D05 及三条驳回保留；W01 仍开放且不延期。规格及 Sprint 回到 in-progress，不标 done。 [人工处置](story-2-5-review-disposition.md) · [整改交接](story-2-5-remediation-handoff.md) [独立核验](story-2-5-independent-review.md) · [23 条逐项裁决](story-2-5-review-triage.md) · [原始四视角](story-2-5-review-raw.md)

- [x] [Review][Patch] **M01（Medium，原阻塞 AC-8，D-051 已关闭）** 原问题为详情传入无效设备参数后仍查询并可触发 FR-018。已在授权后、任何预约读取前拒绝无效 equipment，保持缺省及合法返回导航。 [reservations/views.py:205]
  - 开发专项及整改后独立实跑已通过，负责人接受独立结论并正式批准关闭。 [M01 开发实测](story-2-5-m01-dev-evidence.md) · [独立实跑及其证据边界](story-2-5-m01-independent-run-result.md) · [D-051](story-2-5-w01-authorized-run.md)
- [x] [Review][Defer] P01 原因摘要按 ID、时间线按记录时间，未来多条历史应统一选择口径。 [audit/services.py:54] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P02 摘要未标已有原因的动作来源，待多动作集成完善。 [reservations/templates/reservations/admin_detail.html:25] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P03 探针固定 history/reasons 查询的确切授权 ID 绑定。 [reservations/management/commands/verify_admin_reservations.py:84] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P04 下次故障维护补独立的迟发列表原因读错场景。 [reservations/management/commands/verify_admin_reservations.py:448] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P05 以独立预期核对跨日与小数秒，不全复用产品格式器。 [reservations/management/commands/verify_admin_reservations.py:160] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P06 失败案例在触发断言前归档，保留原始响应和 SQL。 [reservations/management/commands/verify_admin_reservations.py:130] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P07 定义基线覆盖边界，下次需要时补 schema 定义。 [reservations/management/commands/verify_admin_reservations.py:43] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P08 独立断言详情摘要，并在正式浏览器采证。 [reservations/test_admin_reservations.py:136] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P09 针对详情带有效 CSRF 的 POST 加 405 和无业务写断言。 [reservations/test_admin_reservations.py:196] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P10 针对管理员路径核对实际缓存头。 [reservations/views.py:177] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P11 同时刻历史次序的 ID 断言。 [audit/services.py:77] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] P12 在现有显示口径中说明候选冻结，新增下次刷新可见，不额外取时。 [reservations/templates/reservations/admin_list.html:23] — D-050 批准条件延期，未修复。
- [x] [Review][Defer] D01 交付包须含现有规格、检查点和旧基线名清单。 [verify-story-2-5.ps1:58] — 延至授权打包及干净环境验证。
- [x] [Review][Defer] D02 旧入口共享隔离验证租约非完整互斥。 [verify-story-2-5.ps1:117] — 沿既有 RD01/2.2-D1/2.3-W2，同库串行。
- [x] [Review][Defer] D03 最终授权检查后在途撤权，当前未证。 [reservations/services.py:229] — 如开放业务角色修改，再定义语义与实测。
- [x] [Review][Defer] D04 行锁长期等待。 [reservations/services.py:250] — 既有事务运维，不增改本故事约束。
- [x] [Review][Defer] D05 将来批准/取消与只读路径交错的一致性。 [reservations/services.py:256] — 实际人工转换 Story 集成时验证，不提前实现。
- [x] **W01（High，正式运行门槛，D-052 已关闭）** 正式缺列 SELECT 已按 D-051 单次提交。恢复批刷新窗口、只读核验精确 ACL 并跳过 GRANT，正式四角色 Chrome 和后置核验通过。AC-1～AC-8 按正式运行与独立隔离实证分列，负责人条件已满足，规格与看板推进为 `done`。 [最终验收](story-2-5-final-acceptance.md) · [失败及恢复证据](story-2-5-w01-recovery-evidence.md)

#### Rejected

- 01 false。上界越界的数据库人工植入时间不是正式预约输入或数据库生成历史可达状态，模板不进入事务。
- 04 low。没有本项目中超过可用规模的证据，禁止通过新分页或截断变更正式范围。
- 12 maybe-false。数据库实际 collation 未证可触发，目前正式写入的系统原因固定非空，拒绝增添低风险旁支。

## Implementation Notes

- 2026-11-27，用户在当前会话回复「批准并继续」，规格从 `draft` 经 `ready-for-dev` 进入 `in-progress`，看板仅同步 2.5。上述勾选只表示代码已落盘，不表示 AC 实测通过。管理员导航、服务、投影、模板和验证入口已落盘。沙箱拒绝 `equipment/services.py` 写入，现有管理员谓词接入共享策略的单文件补丁可应用检查通过，尚未应用。
- 已准备 12 个 Django 测试及 17 个独立 PostgreSQL／实际 HTTP 探针。沙箱批次在原 `.venv` Python 预检停止，尚未连接测试库或运行用例。不进入 BMAD Step 4，不变更正式库。 [验证交接](story-2-5-verification-handoff.md)
- 2026-11-27，团队在普通 PowerShell 实际应用共享权限补丁，隔离预检通过。125 项 Django 中 124 项通过，12 项 2.5 用例和 40 项设备用例全通过。唯一失败为 Story 2.3 导航断言把管理员路由公共前缀当作本人入口。已校正同名测试并补充双方导航和直接访问断言。新验证入口一次串行完成针对性、全量和探针。本会话的原解释器仍报 `103`，整改后的实测回执待取得，规格／Sprint 维持 `in-progress`。 [故障证据和复验命令](story-2-5-regression-remediation.md)
- 2026-11-27，普通 PowerShell 实际整改复测通过。原始证据交叉核对为 5/5 针对性、125/125 Django、17/17 独立 PostgreSQL 探针、零跳过、12/12 阶段退出 0、87 个输入一致及四份隔离库基线和清理一致。正式 AC-1～8 取得隔离开发自测证据，规格进入 `in-review`、Sprint 进入 `review`。新会话独立评审未执行，正式运行和授权另批。 [开发证据](story-2-5-dev-evidence.md) · [独立评审交接](story-2-5-code-review-handoff.md)

## Spec Change Log

## Review Triage Log

- 2026-11-27，D-050 批准 BMAD Step 4 处置。M01（AC-8）是唯一必修，交回原 Build。P01～P12 条件延期，沿用 D01～D05 与三条驳回。W01 不延期，不授正式访问或执行权限。17 项已合并至中央台账并留存前后散列。无新运行或代码变更，整改后统一独立复验。 [处置](story-2-5-review-disposition.md) · [中央台账](deferred-work.md) · [原始证据](story-2-5-dev-evidence.md)
- M01 代码已落盘。详情授权后、进入业务服务前校验已有筛选表单，非法值明确返回 400。扩展现有三个专项断言及隔离 `edge-input`，独立批的 125 项 Django 和 17 项探针分母不变；普通 PowerShell 的 `-M01Only` 先跑三项定向和一个真实 DB/HTTP 探针。沙箱原 `.venv` 既有 `103`，本轮未重试、未运行实测。保留 M01 开放和 `in-progress`，待新实跑回执后转回独立评审。 [命令与原评审交接](story-2-5-remediation-handoff.md)
- 2026-11-27，已核对团队实际 `-M01Only` 批次，3/3 Django、1/1 真实 HTTP/PostgreSQL、10 阶段零退出、87 个输入、三份基线和夹具清理一致。五个 400 均在业务读取前返回，同一预约的后续合法读取恰好写一条系统历史，缺省参数重复读取不再写。已按本次条件授权回 `in-review`／`review`，交回原独立 Code Review 会话。P01～P12、D01～D05、驳回及 W01 不改。 [原证与复审交回](story-2-5-m01-dev-evidence.md)

- 2026-11-27，D-050 M01 整改后的独立批实际通过 5/5 专项、125/125 全量、17/17 PostgreSQL 探针及 edge-input.m01。AC-1～8 隔离功能验收证据齐备，M01 具备代码问题关闭条件。外层控制台终行和原生退出码未单独存档，内层与离线审计的成功原证及退出码已核对，不重复跑。保持 in-review，W01 未关闭，正式实权和运行待处理。 [独立实跑回执](story-2-5-m01-independent-run-result.md)

## Design Notes

读取字段、精确列级授权、并发交错和开发／独立／正式取证分界见同目录检查点。正式 GRANT 不属于本次批准。

## Verification

运行 `verify-story-2-5.ps1`，以现有 113 项名称、新增断言和真实 PostgreSQL 探针为准。退出码、原始证据和清理全通过后才进 `review`，另开会话独立评审。

- `-Remediation` 批次 `story-2-5-run-20261127-184145-780-3e98e34427d9447091b75b2d1fc5ebe4` 已通过。空列表、无效筛选与缺失详情、匿名和非管理员、真实回滚与提交未知矩阵均有已运行的 Django 或独立探针。沿用已复算的 Story 2.1 NFR-001 20×10，不重跑。 [脱敏核对](story-2-5-development-evidence.json)
