---
title: 'Story 1.4 管理员维护设备基础信息并保护设备身份'
type: 'feature'
created: '2026-11-25'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'e200fee335536941e0705c112aefbf6751b244c3'
context: ['{project-root}/_bmad-output/planning-artifacts/project-context.md', '{project-root}/docs/course-requirements.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

让启用的业务管理员原位维护同一台设备的名称、类别、位置和说明。[正式 AC-1～AC-8](../planning-artifacts/epics.md#story-14-管理员维护设备基础信息并保护设备身份)是唯一验收口径，追溯 FR-016／002、NFR-002 本入口、ADR-002／003／006／008。

## Boundaries & Constraints

**必须**保留主键、唯一编号、当前状态和记录数量。按 D-024 使用 Read Committed，短事务设备行锁、锁后重读，仅更新四列。服务端角色与 CSRF 拒绝无泄露、无业务变化。

**不做**删除和重建、状态转换、预约／历史实体、FR-018、迁移或业务库改动。未知提交不重试。只用原 .venv 和隔离测试库，完成自测停在 review，另开会话独立评审。不提前 done、commit 或 push。

</frozen-after-approval>

## Code Map

- `accounts/models.py:Role`、`equipment/views.py:require_equipment_admin`、设置中的 CSRF 中间件提供现有边界。不以 Django staff 推导业务角色。
- `equipment/models.py:Equipment` 复用具名唯一约束和状态枚举；`services.py:create_equipment` 提供事务分类先例，编辑不报告重号。
- `lab_booking/settings.py`、`postgresql/base.py`、`test_runner.py` 复用连接守卫；运行器禁止 flush。[前置核验与探针设计](story-1-4-checkpoint-1.md)。

## Tasks & Acceptance

**Execution**

- [x] `equipment/forms.py`、`views.py`、`urls.py` 与设备模板接入管理员 GET/POST `/equipment/<pk>/edit/`。详情仅管理员见链接。编号、状态只展示，不作表单字段。拒绝受保护键、其他额外键或重复键，不部分保存。
- [x] `equipment/services.py` 先授权，最外层事务按主键取锁、独立语句重读、原位更新四列，确认提交才跳转详情。无效表单只读确认目标；404 不写。失败和未知分别提示，未知只引导核查。
- [x] `equipment/test_edit.py` 加回滚式 AC／T-03 测试；`equipment/management/commands/verify_equipment_edit_transactions.py` 加隔离 T-01／异常探针，不改现有 runner。
- [x] `README.md` 记录入口与运行授权边界；`story-1-4-dev-evidence.md` 记录实际命令、AC、回归、夹具清理和 review 交接。

**Acceptance Criteria**

1. **AC-1** 已登录管理员提交合法四字段时，详情及重读匹配输入，主键、编号、状态和总数不变。
2. **AC-2** 已有设备编号只读。提交不同编号时整体拒绝、明确提示、全字段不变；真实数据库拒绝重复编号。
3. **AC-3** 对任一合法状态伪造状态时整体拒绝，不保存任何变更，不处理预约或历史。
4. **AC-4** 匿名、学生、教师直达 GET/POST 时拒绝且无泄露、无业务变化；有效 CSRF 管理员成功，缺失或错配则拒绝。
5. **AC-5** 管理员 GET 或通过 CSRF 的 POST 指向不存在的目标时明确 404，不创建记录也不影响其他设备。
6. **AC-6** 旧表单打开后，独立事务提交维修／停用时，合法提交更新四字段且保留最新状态；取得设备锁后重读。
7. **AC-7** 检查维护入口并尝试删除时，无可执行删除路径；编辑保留原记录、主键和编号。
8. **AC-8** 确认失败时不报成功、无部分持久化；COMMIT 结果不明时仅提示待核查，不断言回滚，不重试或冒报重号。

### Review Findings

2026-11-25，BMAD 6.12.4 `full` 四视角独立评审。初次并发启动遇到线程上限，Acceptance Auditor 随后在新独立上下文中完成，四份报告实际收齐。原 7 项建议整改、2 项延期跟踪、12 条原始发现驳回。负责人在 Step 4 选择「保留为行动项」，批准 **3 项待整改、6 项延期跟踪、12 条保持驳回，0 项修复**。延期标记只表示纳入跟踪，不表示关闭。 [原始裁决](story-1-4-independent-review.md) · [人工处置](story-1-4-review-disposition.md) · [原 Build 会话交接](story-1-4-remediation-handoff.md)

- [x] [Review][Patch] **R1 High** 锁后角色及启用状态复核已实施，独立复验停用／撤权 2/2，负责人依据 D-035 正式关闭。
- [x] [Review][Patch] **R2 Medium** 说明空白与原值保真独立复验通过，负责人依据 D-035 正式关闭。
- [x] [Review][Patch] **R7 Medium** T-03 六例请求、响应及前后数据证据独立复验通过，负责人依据 D-035 正式关闭。
- [x] [Review][Defer] **R3 Low** 只读状态项的精确断言 [equipment/test_edit.py:79] [equipment/management/commands/verify_equipment_edit_transactions.py:150] — 当前模板显示正确，真实锁等待和末态有独立数据库断言。风险是免责声明掩盖标签缺失或错值。下次修改状态展示或维护 T-01 时按三种状态补定位断言。
- [x] [Review][Defer] **R4 Low** 保存表单 POST 方法和有效目标的渲染断言 [equipment/test_edit.py:84] — 当前表单和路由正确。风险是手写测试请求漏掉浏览器保存动作回归。下次维护表单或编辑浏览器回归时从实际渲染提交。
- [x] [Review][Defer] **R5 Low** 未知提交页原设备核查链接断言 [equipment/test_edit.py:205] — 当前链接正确，提交分类和独立末态另有证据。风险是链接将来误指其他页面而未被发现。下次维护结果页或 AC-8 回归时冻结原设备链接。
- [x] [Review][Defer] **R6 Low** 显式空说明清除对照 [equipment/test_edit.py:75] — 现有实现允许空说明，无当前失败证据；R2 整改须保留该语义，不以此延期为由改变空值处理。风险是将来误设必填。下次维护说明边界测试时补清除、详情占位和原身份断言。
- [x] [Review][Defer] **W1 Medium** 正式运行角色四列授权及运行验证。D-035 已另批有限范围，当前实际授权、运行取证及后续关闭尚未完成，隔离结果不替代正式运行。
- [x] [Review][Defer] **W2 Medium，未证实** 其他明确 COMMIT 拒绝能否被归为未知 [equipment/services.py:102] — deferred: 当前批准结构未证明可达；若出现新的真实驱动诊断，以隔离证据、独立读回和客户端响应重新裁决。

**Rejected**

- 02（Low）。未定义运行时等锁阈值，不在本 Story 增设事务参数。
- 04（Low）。只读错误不同于合法提交 AC-8，不新增故障页面。
- 05（False）。当前唯一业务调用只传经校验的 `form.cleaned_data`，没有未校验的业务调用路径。
- 06（Low）。阶段日志可优化，但不影响已覆盖的业务结果分类，不增加额外日志机制作为验收条件。
- 08（Low）。实际探针已清理，额外恢复分支属于隔离工具增强。
- 09（Low）。原脚本要求人工核对；独立复验包装已核对数量、跳过和清理，不重复改原脚本。
- 11（Low）。跨请求是独立认证；优先处理 R1 同一请求等待期间的锁后权限复核。
- 12（Low）。不以探针超时冒充实际运行 SLO，也不凭假设加超时策略。
- 13（Low）。只读错误未写设备，不把它当作 AC-8 的合法提交失败。
- 15（Low）。嵌入换行的单行字段不是正常表单输入，不夹带新输入规则。
- 17（Low）。本次没观察到残留，先保留实际清理失败时停止复跑的边界。
- 18（Low）。建连不受语句超时保护，但实际本机探针通过，不扩充连接参数作为验收门槛。

**整改后针对性独立复审，2026-11-25**

BMAD 6.12.4 `full` 四层初次裁决为 0 项需需求决定、3 项针对性测试／证据 patch、0 项新增延期、11 条驳回、1 条沿用已有 R6。当时已核对团队开发自测 68/68、10/10，但尚无新独立运行。随后按 D-034 处置及完成隔离复验，见下文复验记录。 [本轮完整裁决](story-1-4-targeted-independent-recheck.md)

- [x] [Review][Patch] **Q-3 Low** 已有 CRLF 专项独立复验通过（1 项、两种提交形式），改名称时原字节不变；负责人依据 D-035 正式关闭。 [专项独立复验](story-1-4-targeted-independent-recheck.md#2026-11-26-独立复验结果)
- [x] [Review][Defer] **Q-1 Low** R1、T-03 无泄露字段断言补强。现有拒绝及不变证据满足 AC 时延期。风险是类别、位置或状态的单字段泄露可能漏检，后续维护设备权限探针或 T-03 时补强。
- [x] [Review][Defer] **Q-2 Low** R7 匿名登录跳转地址归档。已有实际精确跳转断言，证据补强条件性延期。后续维护 T-03 或登入路由时分别留存预期和实测地址。

**本轮 Rejected（沿用 R6 的 03 未计入驳回）**

- 01（Low）。账号复核后的撤权优先级不属于 D-033 要求的锁等待窗口，不扩展跨表协议。
- 02（False）。原 Chrome 回归会检查实际样式和呈现；本轮新 R2 测试另核对精确内容及转义。
- 06（Low）。历史清单及原始输出已独立完整核对，不为冒号修正增加新的打包协议。
- 07（Low）。现有操作者占位留档原样保留，不代填；本轮独立运行要求实际操作者。
- 08（Low）。锁后判断之后的跨表撤权次序不在本轮批准范围，理由同 01。
- 09（Low）。浏览器文本没有单独线尾格式选择，保留纯传输等价内容符合 R2。
- 12（Low）。实际提交使用同客户端有效 CSRF，合法与缺失／错配对照齐全，未发现混淆，不加中间件测试钩子。
- 13（Low）。包装固定模式是已知元数据，区分执行委托与实际运行者，不在本轮改包装。
- 15（Low）。本轮六条实际记录按夹具与原请求另行核验匹配，不新增证据生成或签名协议。
- 16（Low）。无账号分支已安全拒绝，工程没有账号物理删除功能，D-033 只要求停用与撤权探针。
- 17（Low）。AC-1 不要求新增独立的换行编码编辑行为，理由同 09。

## Implementation Notes

- 2026-11-25 项目负责人明确批准 Checkpoint 1 并继续，原则接受四列最小授权方案但未批准正式库变更。见 [D-032](../../decision-log.md#d-032-2026-11-25-负责人批准-story-14-实施规格)。
- 2026-11-25 Step 3 已准备 [实现补丁](story-1-4-edit-equipment-basics.patch)，但当前会话无法写入实际 `equipment/`，原解释器亦未能启动。通过补丁预检查，不等于应用或测试通过。普通 PowerShell 续跑见 [开发证据](story-1-4-dev-evidence.md)。继续保持 `in-progress`，未把任何 AC 记为通过。
- 2026-11-25 团队在普通 PowerShell 应用补丁和实际自测。当前 9 个业务及测试文件完整匹配补丁，未重复应用。AC-1～AC-8 开发自测通过，原 55/55、新增 12/12，无跳过，真实探针 8/8。状态转为 `in-review`，Sprint 同步为 `review`，等待新会话独立 `bmad-code-review`。本会话仅核验日志与差异，未复跑或进行独立评审。 [开发证据](story-1-4-dev-evidence.md)
- 2026-11-25 按 D-033 续接原 Build 的 Patch 路线，仅 R1、R2、R7。原实现补丁保持已应用；沙箱写入和原解释器访问仍受限，本轮以 [整改证据和本机验证步骤](story-1-4-remediation-evidence.md) 留档，实际自测通过前保留 `in-progress`，三项不提前勾选。
- 2026-11-25 团队在普通 PowerShell 应用四文件增量并实际自测 **68/68 Django、10/10 PostgreSQL**。原汇总误把 R2 冒号格式认作标记缺失；仅修正验证包装的精确匹配，用原始日志复核全部断言及前后 47 文件散列，不重跑、不修改业务代码。三项勾选只表示整改开发自测完毕，未独立关闭。规格回到 `in-review`，Sprint 回到 `review`，交原独立 Code Review 会话。 [本轮整改证据](story-1-4-remediation-evidence.md)

## Spec Change Log

## Review Triage Log

- 2026-11-25，负责人实际选择方案 2「保留为行动项」，随后明确批准本整改周期只修复并验证 R1、R2、R7。R3～R6 仅在不影响正式 AC、安全性和数据一致性时延期，W1/W2 及 12 条驳回的原裁决保留；均未关闭。Story 从评审转入 `in-progress`，未执行整改。整改后统一独立复验，当前独立执行为 0 项，原 67/67 和 8/8 保留为团队开发自测。 [D-033](../../decision-log.md#d-033-2026-11-25-负责人批准-story-14-独立评审处置) · [处置记录](story-1-4-review-disposition.md)
- 2026-11-26，针对性复审后负责人选择方案 2。Q-1、Q-2 条件性延期，Q-3 作为待独立验证的行动项保留，依 Step 4 将规格及 Sprint 转为 `in-progress`。68/68、10/10 仍为开发自测，不关闭 R1／R2／R7。独立复验复用原隔离入口并单列已存 CRLF 补证。 [D-034](../../decision-log.md#d-034-2026-11-26-负责人处置-story-14-针对性独立复审发现)
- 2026-11-26，团队按独立评审委托执行并回交新证据。独立复验核对 68/68 Django、10/10 真实探针、1/1 Q-3（两个提交子用例）、均无跳过，前后源码和工具散列一致。未发现新增阻塞，规格转为 `in-review`、Sprint 恢复 `review`，建议关闭 R1／R2／R7／Q-3，未代作关闭或正式库授权。 [本轮证据](story-1-4-targeted-independent-recheck.md#2026-11-26-独立复验结果) · [待审批授权方案](story-1-4-runtime-authorization-plan.md)
- 2026-11-26，负责人依据独立证据正式关闭 R1／R2／R7／Q-3，保持其它延期，并另批限定正式库四列授权及指定演示设备 Chrome 核验。当前只完成执行前核对并备妥本机批次。受保护路径在沙箱拒绝访问，未连接／授权正式库或启动新服务。继续 `in-review`，等待团队实际运行和最终验收。 [D-035](../../decision-log.md#d-035-2026-11-26-负责人关闭-story-14-四项发现并批准正式库验证) · [本机执行交接](story-1-4-runtime-handoff.md)
- 2026-11-26 11:46，团队普通 PowerShell 恢复实测通过。确认正式库四列 UPDATE 已提交且未重复授权，Chrome 未授权六例和伪造两例均被拒，管理员一次四字段编辑由独立回读确认原身份及状态不变。两次早期工具中止和恢复日志原样保留。W1 验证证据完成，结合隔离复验满足正式八条 AC，无新增阻塞。规格仍为 `in-review`，Sprint 为 `review`，负责人最终验收尚未发生。 [正式库证据及 AC 对照](story-1-4-runtime-evidence.md) · [收尾清单](story-1-4-closeout-checklist.md)
- 2026-11-26，项目负责人明确批准正式最终验收。按 BMAD 6.12.4 Build Step 5 将规格归档为 `done`，Sprint 对应 Story 同步为 `done`。W1 发布验证完成，R1／R2／R7／Q-3 的已决结论和其余延期不变。没有复跑测试、重新授权或修改业务源码。 [最终验收](story-1-4-final-acceptance.md) · [Sprint 状态](sprint-status.yaml)

## Verification

- 仅 `127.0.0.1:5433/test_lab_booking`。原 .venv Python 3.13.17，`manage.py check`、`makemigrations --check --dry-run`、`test --keepdb --parallel 1 -v 2` 启用既有 Chrome R1，原 55 项与新增用例分别计数。
- 上述隔离探针单独串行运行，观察实际锁等待、确认回滚和两种未知提交；比对完整末态、尝试次数与零夹具残留。合法对照与 T-03 拒绝分母分列。
- 若沙箱不允许执行原解释器或访问受保护密码文件，保留 `in-progress`。提供普通 PowerShell 的完整隔离验证命令或脚本，保存未经代跑的真实输出，绝不替换解释器或降低验证。禁止用本次批准执行正式 GRANT。
- 实测在原 Python 3.13.17、PostgreSQL 17.12、指定隔离库完成。T-03 同时满足拒绝、无泄露、无业务变化 6/6，管理员合法对照和 CSRF 拒绝单列。T-01 4/4，含两组真实锁等待；AC-8 4/4，区分回滚、明确拒绝、提交前断连及提交后丢确认。夹具清理通过。 [团队原始日志](story-1-4-verification-20261125-221855-930.txt)
