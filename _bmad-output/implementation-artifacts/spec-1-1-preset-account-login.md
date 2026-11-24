---
title: 'Story 1.1 使用预置账号登录并获得明确业务身份'
type: 'feature'
created: '2026-11-21'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '685f358daa050cb28e1ee7672a2d55f20ef1b842'
context: ['{project-root}/docs/course-requirements.md', '{project-root}/_bmad-output/planning-artifacts/project-context.md', '{project-root}/docs/team/sprint-1-environment-preparation.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 系统尚无登录入口或服务端业务身份。

**Approach:** 三类预置账号用 Django 会话查看本人身份。以[正式 Story 1.1](../planning-artifacts/epics.md#story-11-使用预置账号登录并获得明确业务身份) AC-1～7 为准。

## Boundaries & Constraints

**Always:** D-015 用 `AbstractUser`，唯一业务角色字段 `role` 用 `TextChoices`，无默认值，数据库非空且仅允许 `student/teacher/admin`。服务端仅允许已登录、启用且角色有效的账号访问身份页。D-016 使用 Windows、Python 3.13.17、Django 5.2.19、PostgreSQL 17.12／5433。

**Never:** 迁移默认 User，开放注册、Admin 或账号管理，创建 Profile、设备、预约、占用或审计表，使用 Docker、SQLite 或触碰旧实例 5432。明文账号密码、数据库密码、密钥和会话标识不进入 Git、迁移文件、公开文档或测试日志。

## I/O & Edge-Case Matrix

| 场景 | 输入或状态 | 预置结果 | 异常处理 |
| --- | --- | --- | --- |
| 首次运行 | 负责人确认的受保护清单 | 事务内按唯一用户名补齐，`set_password()` 仅存哈希，两个管理标志均为假，组和直接权限留空 | 按登录规则规范化并校验用户名。发现重复或非法项即拒绝整批 |
| 重跑 | 已有同名账号 | 同角色跳过，保留哈希、角色、启用状态、权限及历史 | 异角色整批回滚 |

</frozen-after-approval>

## Code Map

- 沿用 `requirements.txt`、`.gitignore` 与[决策日志 D-015／D-016](../../decision-log.md)。
- 复用 Django `LoginView`、`AuthenticationForm`、`ModelBackend` 和数据库会话。成功登录写入 `last_login`。

## Tasks & Acceptance

**Execution**

- [x] `manage.py`、`lab_booking/settings.py`、`lab_booking/wsgi.py` 设置 CSRF、会话、北京时间及数据库模式。首迁前在 `INSTALLED_APPS` 注册 `accounts` 并设 `AUTH_USER_MODEL = "accounts.User"`。
- [x] `accounts/models.py`、`accounts/migrations/0001_initial.py` 在首迁创建 User 与角色约束。用 venv 执行 `manage.py check`、`makemigrations --check --dry-run`、`migrate --plan`。查库、角色、端口、版本及依赖顺序。负责人确认目标及计划后以迁移账号执行 `migrate`，再核对运行授权。
- [x] `accounts/management/commands/seed_accounts.py` 在迁移成功且负责人单独确认目标及受保护清单后，用迁移账号执行 `seed_accounts --manifest <路径>`。只输出计数及脱敏错误。
- [x] `lab_booking/urls.py`、`accounts/views.py`、`accounts/templates/accounts/{login,identity}.html` 提供 `/login/` 与只读 `/identity/`。
- [x] `accounts/tests.py` 逐 AC 测试并覆盖预置矩阵、角色约束。`README.md` 给出 Windows 配置、授权和启动命令。

**Acceptance Criteria**

- AC-1 给定三类预置账号，提交正确凭据后，均建立会话并显示本人的账号和角色，刷新保持身份。
- AC-2 给定匿名会话，分别提交未知账号、错误密码或缺字段，均提示失败且无认证会话。每次失败后直接请求身份页，均拒绝返回受保护内容。
- AC-3 给定无有效会话，直接请求身份页时引导登录，无受限内容或业务写入。
- AC-4 给定合法凭据，附加伪造账号 ID 或角色后，只能获得服务端确认的身份。切换 Django 管理标志，业务身份依旧由 `role` 决定。
- AC-5 给定正常 CSRF 流程，合法令牌按凭据认证，缺失或无效令牌返回 403，无认证会话或角色变化。
- AC-6 给定配置完成，检查 URL 配置并直接访问 Admin 与自助注册路径，均无匹配。三类账号从同一登录入口进入。
- AC-7 给定获准环境，按 README 在 Windows 连接 PostgreSQL 17.12、迁移、预置并启动，在浏览器验证 AC-1～6。缺数据库配置时明确失败，Git 差异无秘密。

### Review Findings

2026-11-22，BMAD 6.12.4 独立代码评审，范围为 `685f358` 至 `dd2ec5c` 及当时工作区。仅在预建的 `127.0.0.1:5433/test_lab_booking` 以测试角色复跑，进程内限定维护游标到本测试库。13 项通过，耗时 6.189 秒，退出码 0。库内前后均为 16 条迁移、0 个账号、0 条会话。对业务库仅执行只读核查，三种角色的实际库连接与分权符合当前配置。本轮以合成输入发现预置校验接受登录表单会拒绝的密码，未使用真实账号进行浏览器复测。全部待负责人确认处置。

- [ ] [Review][Decision] CR-01 确认隔离测试的正式复跑入口。README 的原生命令先尝试维护库，开发和独立评审的实测均限定到测试库。建议提供可复现的仅测试库入口，或由负责人明确确认维护库允许条件及对应命令。[README.md:64]
- [x] [Review][Patch] CR-02 预置校验接受浏览器登录不可用的密码。[accounts/management/commands/seed_accounts.py:36]（第二轮共享上限、边界拒绝和实际表单登录已验证。）
- [ ] [Review][Patch] CR-03 libpq 继承的连接地址和口令设置可改变实际连接参数。[lab_booking/settings.py:23]
- [x] [Review][Patch] CR-04 Web 入口可用迁移角色初始化，缺少运行模式校验。[lab_booking/wsgi.py:6]（第二轮三角色 Windows runtime 实际浏览器登录和退出已验证。）
- [ ] [Review][Patch] CR-05 README 的预置失败不会阻止同一代码块继续启动服务。[README.md:53]
- [ ] [Review][Patch] CR-06 当前 PC-011 证据缺少逐案角色内容、数据变化断言及新增拒绝用例的分母。[accounts/tests.py:52]
- [ ] [Review][Patch] CR-07 Django 退出视图存在尝试渲染缺失模板的分支。[lab_booking/urls.py:9]
- [ ] [Review][Patch] CR-08 退出测试绕过渲染的表单，且未核对服务端原会话失效。[accounts/tests.py:161]
- [ ] [Review][Patch] CR-09 预置测试未固定运行模式先拒绝、后读取输入的边界。[accounts/management/commands/seed_accounts.py:63]
- [ ] [Review][Patch] CR-10 重复 JSON 字段的拒绝逻辑缺少原始清单回归断言。[accounts/management/commands/seed_accounts.py:13]
- [ ] [Review][Patch] CR-11 会话 Cookie 否定断言的失败消息可能包含测试会话值。[accounts/tests.py:101]

**Rejected**

- `false`：认为同源 `next` 表示 AC-1 要求所有成功登录都必须固定重定向。正式 AC-1 要求认证后可访问身份页，默认跳转与匿名访问后的回跳均指向身份页，同源回跳本身符合该要求。

## Implementation Notes

- 2026-11-21 22:57（北京时间），项目负责人明确回复“批准并继续”，随后正式批准修订规格通过 Checkpoint 1，并要求“现在开始执行Story 1.1开发”。据此完成本规格的 `ready-for-dev` 转换。批准依据和执行边界见[决策 D-018](../../decision-log.md)。
- 2026-11-21 22:58（北京时间），按负责人本次实际开工指令进入 Step 3。Story 1.1 与父 Epic 同步为 `in-progress`。
- 账号、预置命令、登录和身份页、13 个测试方法及 Windows 启动说明已落盘。只读检查通过，实库迁移计划与角色／库隔离见[开发证据](story-1-1-dev-evidence.md)。当前停在实际迁移与授权的确认点。
- 2026-11-22，负责人在本次会话授权继续执行。业务库首迁和 D-016 最小授权已完成，独立测试库 13 项自测全部通过。Windows 运行账号启动和 Chrome 匿名及失败流程已实测。业务库默认受保护清单不存在，真实预置及三类账号浏览器验收仍待补齐，状态为 `in-progress`。见[首迁与开发自测证据](story-1-1-dev-evidence.md#2026-11-22-首迁与开发自测)。
- 2026-11-22，负责人明确批准三类演示账号、受保护交付和真实浏览器退出验收。业务库预置与幂等复核完成，Chrome 三类账号登录及退出通过，覆盖正式 AC-1～AC-7 的实库浏览器和环境部分。新增退出断言后，完整测试重跑需明确批准隔离库，Story 维持 `in-progress`。见[预置与 Chrome 验收](story-1-1-dev-evidence.md#2026-11-22-正式预置与-chrome-验收)。
- 2026-11-22，负责人明确批准在隔离的 `test_lab_booking` 重跑。含退出断言的 13 项全部通过，结合真实数据库初始化及 Chrome 证据核对正式 AC-1～AC-7 均通过。Sprint 进入 `review`，本规格进入 `in-review`，等待独立代码评审。见[重跑与评审交接](story-1-1-dev-evidence.md#重跑与评审交接)。

## Spec Change Log

- 2026-11-22 按负责人明确要求补上真实退出流程。新增 Django `LogoutView` 的 `POST /logout/`，在身份页提供带 CSRF 的退出表单，扩展原 AC-5 测试方法覆盖 GET 和无 CSRF 请求的拒绝及有效退出。正式 AC 与冻结意图沿用原文。决策见 [D-019](../../decision-log.md#d-019-2026-11-22-负责人批准-story-11-业务预置和退出验收)。

## Review Triage Log

### Story 1.1 独立评审续审与修复任务清单

2026-11-23，恢复 BMAD 6.12.4 上轮独立评审，逐项复核 CR-01～CR-11。建议修订后复审。Sprint 仍为 `review`，实施规格仍为 `in-review`。负责人本轮接受 CR-01 的隔离入口方案。其余处置和下表中的必修判断为本轮评审建议，等待负责人确认修复方案、修复后复测及最终人工验收。

以 [规格起点 685f358](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/685f358daa050cb28e1ee7672a2d55f20ef1b842) 为差异基线，覆盖本地 HEAD、`origin/main` 对应的 [首迁前检查点 dd2ec5c](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083) 及评审开始时工作区。评审范围共 22 个文件，新增 960 行、删除 6 行。检查点之后的开发证据、状态和评审处置目前在本地工作区。核对 [AGENTS](../../AGENTS.md)、[课程要求](../../docs/course-requirements.md)、[PRD](../planning-artifacts/PRD.md)、[架构](../planning-artifacts/architecture.md)、[项目约束](../planning-artifacts/project-context.md)、[正式 Story 1.1](../planning-artifacts/epics.md#story-11-使用预置账号登录并获得明确业务身份)、[开发证据](story-1-1-dev-evidence.md)、[Sprint 状态](sprint-status.yaml)和[决策日志](../../decision-log.md)。

#### 实测与证据来源

- **本轮独立实测。** Windows、Python 3.13.17、Django 5.2.19。进程限定所有 psycopg 连接为 `127.0.0.1:5433/test_lab_booking` 与 `lab_booking_test`，把 Django 的维护游标限定到同一测试库。移除会影响测试连接的继承 PostgreSQL 环境配置，仅保留获准密码文件来源。提交测试前校验实际服务器 PostgreSQL 17.12、库、角色、地址、端口、测试角色对业务库 `CONNECT=false`、测试 schema 权限及角色无集群管理权限。预检迁移历史一致、无待迁移，再运行 Django 现有 `accounts` 套件，使用 `keepdb=True`、`parallel=1`。13 项通过，0 失败、0 错误、0 跳过，6.174 秒，退出码 0。测试库前后均为 9 张测试角色表、16 条迁移、0 个账号、0 条会话。Django 报告无待执行迁移、系统检查 0 问题。连接检查全程在测试库完成。
- **本轮静态核对和独立模拟。** 检查了 `manage.py`、`lab_booking` 设置、路由和 WSGI、账号模型、首迁、预置命令、视图、模板、13 个测试方法及本机 Django、Python 标准库相关源码。用无数据库依赖的替身命令确认 PowerShell 在预置命令非零退出时会继续运行下一语句，增加显式退出码检查的对照停止了后续语句。Git 差异检查通过，存在本机行尾转换提示。忽略规则覆盖环境文件、虚拟环境、凭据目录、密码文件和密钥文件，对已经跟踪的忽略文件检查无结果。 [源码入口](../../manage.py) · [数据库设置](../../lab_booking/settings.py#L14) · [账号及会话测试](../../accounts/tests.py)
- **已有证据。** 上轮 BMAD 评审记录了 13 项通过（6.189 秒）、合成密码表单不一致、WSGI 非运行模式初始化和 libpq 参数检查。开发记录提供业务库首迁、9 张表、三角色分权、受保护凭据、三账号哈希与幂等、Chrome 正反例和预置后浏览器退出证据。 [既有评审](#review-findings) · [业务库迁移及授权](story-1-1-dev-evidence.md#实库迁移与-d-016-权限) · [预置及 Chrome](story-1-1-dev-evidence.md#2026-11-22-正式预置与-chrome-验收)
- **待验证。** 本轮未连接业务库或维护库，未打开真实预置清单，未重查业务库授权、真实哈希、Windows 文件 ACL 或 Chrome 实际流程。并发预置交错、第二台 Windows 评审机复现、后续设备与预约权限以及整改后复测仍待取证。CR-07 和 CR-11 的边界影响基于源码判断，本轮未运行相应失败分支。课程 PPT 原件未在仓库中找到，页码检查依据课程基线和有来源的团队记录。

#### 逐项结论与待办

以下分工沿用 D-017 的职责作为拟分派。吴亚彤负责技术实施及最终验收，周何馨负责质量验证，罗思婕负责业务审核。表中每项均待实施，CR-01 已有人工作出方案选择。 [D-017](../../decision-log.md#d-017-2026-11-21-负责人正式批准-sprint-1-启动)

| 编号与严重度 | 最终结论、位置与依据 | 必修与拟负责人 | 最小修复及验证方法 |
| --- | --- | --- | --- |
| CR-01 中 | **环境与复现入口缺口。** README 的直接 Django 命令先尝试维护库，隔离实测依赖进程内维护游标限制。测试配置指向独立库仍不足以约束维护连接。负责人已明确仅允许 `test_lab_booking`。涉及 AC-7、D-016、PC-002、ADR-008。 [README](../../README.md#L64) · [开发证据](story-1-1-dev-evidence.md#重跑与评审交接) | **必修，方案已接受。** 吴亚彤实施，周何馨复核。 | 交付一个 README 可直接调用的隔离入口，核验地址、5433、实际库、角色和 PostgreSQL 17.12，限定所有连接并指定保留预建库。参数或实际会话不符时在写入前退出。以连接记录与库前后清单验证只使用测试库，禁止业务库或维护库连接及整库清理。不增加数据库授权。 |
| CR-02 中 | **代码缺陷。** 预置只检查密码类型、非空及 UTF-8 可编码。上轮合成输入证明 Django 密码字段会拒绝预置允许的输入，浏览器密码控件也有单行约束。同角色重跑保留原哈希，因此不能通过重跑纠正。涉及 AC-1、AC-7、D-015、冻结规格非法项整批拒绝。 [预置校验](../../accounts/management/commands/seed_accounts.py#L36) · [HTML 密码字段规范](https://html.spec.whatwg.org/multipage/input.html#password-state-(type=password)) | **必修。** 吴亚彤实施，周何馨验证。 | 在事务前复用登录密码字段的值校验，拒绝浏览器单行输入不能保留的字符。保持原密码语义和脱敏错误。隔离库验证合成非法项导致整批拒绝、已有记录与哈希完全保留、合法三类预置账号仍能通过登录。业务账号若需重置或补种，另行申请批准。 |
| CR-03 中 | **代码配置缺口，由环境触发。** 显式 `HOST` 和 `passfile` 仍不足以固定 libpq 实际网络地址和凭据来源。上轮确认驱动读取继承参数，本轮核对框架实现和 PostgreSQL 规范。无需推定已经连错库或暴露过口令。涉及 D-016、PC-001、PC-002、AC-7。 [数据库设置](../../lab_booking/settings.py#L23) · [连接参数](https://www.postgresql.org/docs/17/libpq-connect.html#LIBPQ-PARAMKEYWORDS) · [环境变量](https://www.postgresql.org/docs/17/libpq-envars.html) · [密码文件](https://www.postgresql.org/docs/17/libpq-pgpass.html) | **必修。** 吴亚彤实施，周何馨复核。 | 固定环回实际地址，拒绝或隔离会改写地址、凭据来源的继承配置，保持受保护密码文件并同步 README 的预检。获准迁移和预置在同一连接核对实际地址、端口、版本、库与角色后才写入。用无外连的合成配置验证冲突被拒绝或不影响参数，再做测试库正常连接对照。权限或迁移策略变更须先审批。 |
| CR-04 中 | **代码缺陷。** WSGI 接受启动进程中的任意受支持数据库模式。上轮确认迁移模式可初始化 WSGI，未连接数据库。迁移角色因此可被误选为 Web 进程身份。涉及 D-016 运行与迁移职责分离、PC-001。 [WSGI](../../lab_booking/wsgi.py#L6) · [模式映射](../../lab_booking/settings.py#L14) · [命令入口](../../manage.py#L7) | **必修。** 吴亚彤实施，周何馨验证。 | WSGI 仅允许 runtime，`runserver` 在可能触发数据库检查前尽早拒绝 migration 和 test，保留管理任务原模式。验证两个非运行模式均在连接前退出，runtime 可启动并完成正常登录，环境检查和测试仍可按各自模式运行。 |
| CR-05 中 | **启动文档缺陷。** 预置返回非零后，同一 PowerShell 代码块继续切换模式并启动。无数据库模拟已验证。涉及 AC-7、D-015 预置失败处置。 [README 启动示例](../../README.md#L52) | **必修。** 吴亚彤更新命令，周何馨复核。 | 在预置命令之后立刻检查 `$LASTEXITCODE` 并中止当前启动流程。用替身命令核对非零时没有启动、成功时允许继续，再在获准隔离环境执行有效清单对照。 |
| CR-06 中 | **权限测试和证据缺口。** 既有 11/11 是当时选定子集。部分请求共用一组前后快照，身份页负向断言缺角色字段检查。当前还有禁用、写请求和退出拒绝等分支，退出已登录的拒绝用例应核对原会话保留。未发现实际角色泄露。涉及 AC-2～AC-6 的拒绝场景、PC-011 和 T-03。 [拒绝断言](../../accounts/tests.py#L52) · [历史分母](story-1-1-dev-evidence.md#L105) · [T-03](../planning-artifacts/sprint-plan.md#L68) | **必修。** 吴亚彤补断言，周何馨逐案核证，罗思婕核对业务口径。 | 对实际路由逐案检查状态或流程拒绝、无受保护身份字段、账号业务数据不变。会话结果单列，区分无认证、原会话保留和成功退出。覆盖登录、身份页、退出及关闭路由，直接视图检查注明测试层级。保存逐案预期、实际和前后对照，重算真实分母，合法对照单列。 |
| CR-07 低 | **代码缺陷。** Django 退出视图接受可选同源跳转，存在退出后落入默认模板渲染的分支，项目未提供该模板。标准退出表单流程通过。涉及 D-019 的退出验收及 AC-7 的浏览器流程。 [退出路由](../../lab_booking/urls.py#L9) · [身份页表单](../../accounts/templates/accounts/identity.html#L17) | **必修。** 吴亚彤实施，周何馨验证。 | 固定退出后的目标为登录页，保留 Django 的 POST 和 CSRF 防护。验证合法表单及附带额外跳转参数时均回登录且原会话失效，GET、缺失和无效 CSRF 均拒绝。 |
| CR-08 低 | **退出现有测试缺口。** 自动化测试从模板上下文取得令牌，并自行指定退出路由。它未验证实际 HTML 的提交合同，也未按原会话记录核对服务端失效。已有 Chrome 验证实际点击退出及后续身份页拒绝。涉及 D-019、AC-5 的 CSRF 机制和 AC-7 的浏览器验收。 [退出测试](../../accounts/tests.py#L161) · [浏览器证据](story-1-1-dev-evidence.md#本机应用与真实浏览器) | **必修，与 CR-07 合并验证。** 吴亚彤补测试，周何馨复核。 | 从渲染结果验证表单方法、路径和 CSRF 字段，按表单提交。在隔离测试中以布尔断言检查旧服务端会话不存在，检查随后访问身份页被引导登录。拒绝样例验证原会话仍可用。任何断言均不输出会话值。 |
| CR-09 低 | **预置测试缺口。** 命令已在读清单前拒绝 runtime，开发记录也有手工负例，现有自动化未锁定顺序。涉及 D-015、D-016。 [命令模式检查](../../accounts/management/commands/seed_accounts.py#L63) · [既有拒绝记录](story-1-1-dev-evidence.md#L86) | **非必修，建议随 CR-02 补齐。** 吴亚彤补测试，周何馨复核。 | 用合成路径检查运行模式直接返回对应脱敏错误，同时证明未读清单、未调用写路径。用获准测试模式做正常对照。无需改业务代码或数据库。 |
| CR-10 低 | **预置测试缺口。** 已实现原始 JSON 重复键拒绝。现有测试通过字典序列化构造清单，验证了重复规范化用户名，但字典无法保留重复键。涉及 D-015 的先校验后入库及冻结规格非法项整批拒绝。 [JSON 解析](../../accounts/management/commands/seed_accounts.py#L13) · [现有用例](../../accounts/tests.py#L250) | **非必修，建议随 CR-02 补齐。** 吴亚彤补测试，周何馨复核。 | 写入只含合成输入的原始重复键清单。验证脱敏错误、无新增且已有账号不变，并让正常 JSON 通过。无需改解析实现。 |
| CR-11 低 | **测试诊断输出缺陷。** `assertNotIn` 失败时会格式化整个 Cookie 容器，Python 的容器表示会包含 Cookie 值。当前 13 项通过，测试用的是合成会话。涉及正式 Story 的证据脱敏要求及冻结规格。 [断言位置](../../accounts/tests.py#L101) · [正式证据要求](../planning-artifacts/epics.md#L754) | **必修。** 吴亚彤改断言，周何馨复核。 | 改用固定脱敏消息和布尔断言。用合成容器验证失败诊断只含固定消息，无 Cookie 值。应用代码无需调整。 |

#### 正式 AC 与 13 项测试核对

| AC 或约束 | 实际测试与剩余验证 |
| --- | --- |
| AC-1 | 三类账号分别登录，断言会话用户 ID、两次加载的本人账号和角色、缓存头及登录时间。CR-02 覆盖目前合成清单未测试的网页登录兼容性。 [三角色登录](../../accounts/tests.py#L64) |
| AC-2 | 未知账号、错密、缺用户名、缺密码四种子例检查表单报错、未建立认证、身份页跳转和账号前后相等。补 CR-06 的角色内容及逐案证据，补 CR-11 的失败诊断脱敏。 [失败登录](../../accounts/tests.py#L85) |
| AC-3 | 匿名和无效会话检查 302 与无身份内容，当前共用一个账号快照。禁用账号走真实路由。非法角色走 RequestFactory 检查视图拒绝，数据库另有非法值用例。当前无预约、设备、占用或处理历史实体，这些数据不进入本故事的通过统计。 [匿名、禁用和非法角色](../../accounts/tests.py#L105) |
| AC-4 | 学生带伪造账号 ID 和角色登录，再带同样参数访问身份页。断言显示学生、没有目标身份、两人业务角色不变，对照的管理员未记录登录。学生开启两个 Django 管理标志仍为学生。身份页 POST 另测 405 和账号不变。 [角色伪造与只读](../../accounts/tests.py#L133) |
| AC-5 | 强制启用测试客户端 CSRF 检查，有效令牌建立认证会话，缺失和无效令牌分别被拒绝且无新增会话或账号变化。有效 CSRF 已有正确凭据对照，错密分支主要由 AC-2 独立覆盖，可随 CR-06 补有效令牌加错密的联合对照。退出表单与服务端会话证据见 CR-07、CR-08。 [CSRF 测试](../../accounts/tests.py#L161) |
| AC-6 | `/admin/`、`/register/`、`/accounts/register/` 同时断言路由未解析和 HTTP 404。三类共用登录入口由 AC-1 验证。关闭路由现共享数据快照，按 CR-06 补逐案断言。 [关闭路由](../../accounts/tests.py#L192) |
| AC-7 | 依赖本机实库、README 和 Chrome 的组合证据。现有 13 项中没有覆盖完整 Windows 安装与初始迁移的一体化用例。开发证据记录获准环境、缺配置退出、首次迁移、预置及浏览器。续审复跑仅验证已迁移的隔离库。整改后按 CR-01、CR-03～CR-05 复核命令及入口。 [AC-7 开发记录](story-1-1-dev-evidence.md#L138) |
| D-015、PC-008 存储约束 | 四个存储测试覆盖缺失／空值／空串／非法角色被 PostgreSQL 拒绝，首次预置哈希及最小标志权限，同角色重跑保留完整字段和权限，异角色整批回滚，以及重复规范化用户名或非法清单无新增。CR-02、CR-09、CR-10 对应未覆盖的预置边界。 [四个存储测试](../../accounts/tests.py#L204) |

#### 范围、迁移与课程证据

- **架构和范围。** `accounts.User` 继承 `AbstractUser`，账号首迁创建非空、无默认的业务角色字段并检查三种取值。设置在迁移前指定自定义模型，认证、CSRF、数据库会话和哈希沿用 Django。视图只从服务端账号显示身份，活动状态和角色均受检查。没有注册、Admin、Profile 或设备、预约、业务审计入口，退出由 D-019 批准。未发现需要扩大 FR、改 ADR 或推进其他 Story 的事项。 [账号模型](../../accounts/models.py#L5) · [首迁](../../accounts/migrations/0001_initial.py#L7) · [权限视图](../../accounts/views.py#L10)
- **数据库与预置。** 预置先校验再在同一事务按稳定用户名顺序补齐，并以数据库唯一键和已存在行锁处理冲突。同角色不更新，异角色异常退出事务，数据库错误转为脱敏消息。实际并行预置尚无证据。业务首迁、列级修改权、会话表 DML、无运行 DDL 和跨库拒绝属于已有环境／开发证据。本次测试库复跑未产生权限、迁移策略或业务数据变更需求。若后续涉及修改数据库权限、迁移策略或已有数据，先向吴亚彤提交影响、目标与验证办法，取得明确授权后再执行。 [预置事务](../../accounts/management/commands/seed_accounts.py#L63) · [既有业务库授权验证](story-1-1-dev-evidence.md#实库迁移与-d-016-权限)
- **第 26 页。** 已核对 FR-001／002 → ADR-001／002／008 → Story 1.1 七条 AC → 测试和环境证据。保留就绪检查原结论及 T-03，权限证据按 CR-06 补齐。 [课程基线](../../docs/course-requirements.md#L80) · [就绪报告](../planning-artifacts/implementation-readiness.md)
- **第 27 页。** 依负责人记录的逐故事口径，现有证据能定位开发会话、首迁前 Git 检查点、进入 review 与独立评审。修复闭环和负责人最终验收仍待发生。 [团队核对记录](../../docs/team/sprint-planning-review.md#L47) · [Sprint 状态](sprint-status.yaml#L39)
- **第 33 页。** 账号切片已有源码、启动说明和测试证据。按 README 的单入口隔离复现、第二台评审机复现及完整 NFR-002 仍待对应验证。当前 Git 检查点早于进入 review，不能用它证明全部后续状态已入历史。 [课程产物要求](../../docs/course-requirements.md#L88) · [首迁前 Git 检查点](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083)
- **第 34 页。** Sprint 计划仍把 2.6／2.7 列为实验 A 候选。开发证据提及独立实验记录，本轮在仓库中未找到已执行实验的原始记录，Story 1.1 的开发、评审及复跑结果不计为实验 A 样本。 [课程实验要求](../../docs/course-requirements.md#L121) · [分组与控制条件](../planning-artifacts/sprint-plan.md#L75)
- **第 36 页。** D-015、D-016、D-018、D-019 保存此前负责人决定。CR-01 已有本次消息中的明确选择，实施结果、复测证据及其他 CR 人工处置待实际发生后补入根目录决策日志。 [五要素要求](../../docs/course-requirements.md#L110) · [决策日志](../../decision-log.md#L131)

建议先合并处理 CR-01、CR-03、CR-04 的执行边界，再处理 CR-02、CR-05、CR-07 和对应回归，最后复核 CR-06、CR-08、CR-11 的证据。CR-09、CR-10 可随预置回归补齐。负责人确认本清单之前，整改工作待办。复测后由吴亚彤最终验收，当前 Story 1.1 为 `review`，Story 1.2 为 `backlog`。

### 2026-11-23 正式四视角独立代码评审

**结论为修订后复审。** 本轮确认 14 项待处置发现，其中 6 项中等、8 项低、无高严重度。CR-01～CR-11 均经重新核查，保留原编号和严重度。新增 CR-12～CR-14。负责人已确认 CR-01 只使用独立测试库的方向。其他整改方案和最终验收由负责人后续决定。

#### 范围与评审来源

- BMAD 6.12.4，`bmad-code-review` 的 `full` 模式。盲审检查差异，边界审查检查可达路径，验证缺口审查检查会漏掉回归的断言，验收审计检查批准的规格和七条 AC。四个视角均交付结果。子代理槽位有限，验收审计在首个视角返回后启动。初始边界和验证缺口审查读取关联资料时看到了部分上轮记录，因此分别由新子代理在限制读取范围后独立复核。归并在四个视角完成后进行。
- 以 [规格基线 685f358](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/685f358daa050cb28e1ee7672a2d55f20ef1b842) 为起点，覆盖 [开发检查点 dd2ec5c](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083) 及当前工作区。盲审快照为 21 文件、增加 860 行、删除 6 行，SHA-256 为 `d2e7907462dbaec4daae92dfca52b89a0410d869e2c57bc43c9062eca8484e37`。实施规格作为验收依据单独读取。检查点后的全部差异在评审开始时为 8 文件、增加 210 行、删除 9 行。直接核查了新增退出路由、身份页退出表单、测试及 README 使用说明。复跑后重新计算的差异哈希与锁定快照一致。
- 依据为 [正式 Story 1.1](../planning-artifacts/epics.md#story-11-使用预置账号登录并获得明确业务身份)、[FR-001／002 与 NFR-002](../planning-artifacts/PRD.md)、[ADR-001／002／008](../planning-artifacts/architecture.md)、[PC-001／002／008／011](../planning-artifacts/project-context.md)、[D-015～D-019](../../decision-log.md#L131) 和 [课程基线](../../docs/course-requirements.md)。

#### 证据等级

- **本轮独立测试。** 使用 Python 3.13.17 环境的 Django 5.2.19、psycopg 3.3.9 和已预建的 PostgreSQL 17.12 测试库。临时进程约束所有数据库连接和 Django 维护游标，仅接受 `127.0.0.1:5433/test_lab_booking` 与 `lab_booking_test`，并在执行前核对实际库、端口、版本、认证角色、业务库 `CONNECT=false`、无集群级管理权限和无待迁移。以 `keepdb=True`、`parallel=1` 复跑现有 `accounts` 套件，**13 项通过，0 失败、0 错误、0 跳过，5.957 秒，退出 0**。四次连接均指向测试库。前后均为 9 张测试角色表、16 条迁移、0 个账号、0 条会话。未执行迁移、清空、重建或授权。
- **本轮独立辅助核对。** 测试库只读核查确认没有默认 `auth_user`，`accounts_user.role` 是非空、无默认值的 `varchar(7)`，角色检查约束已验证。`makemigrations --check --dry-run` 报告无模型差异。移除数据库模式或密码文件配置时均得到明确报错和退出码 1。无数据库的 PowerShell 替身模拟确认前一命令非零退出时后续语句仍执行。合成检查确认预置命令先拒绝运行模式、解析器拒绝原始 JSON 重复键，两处保护目前有效。Git 差异格式检查通过。对新增行的私钥、带密码的数据库 URI、常见令牌和密钥字面量模式扫描均为 0 命中。
- **静态分析与已有证据。** CR-01～CR-04、CR-06～CR-08、CR-11～CR-14 的原因主要来自当前源码、框架和断言核对。CR-02 的登录校验差异另有上轮合成输入证据，CR-04 另有上轮 WSGI 初始化证据。本轮未触发这些失败分支。业务库实迁、运行账号列级授权、真实账号哈希与 Chrome 验收沿用开发证据。 [开发证据](story-1-1-dev-evidence.md) · [前次复核](#story-11-独立评审续审与修复任务清单)
- **待验证。** 第二台 Windows 机器按 README 复现、实际并行预置交错、业务库当前权限及真实浏览器整改回归尚未独立复验。课程 PPT 原件在仓库内未找到，页码按课程基线及团队记录核对。隔离套件通过只覆盖此账号切片和既有断言。

#### 逐项处置清单

以下均为待处理的 `patch` 项。依 D-017 建议由吴亚彤实施、周何馨复核，罗思婕协助核定 CR-06 的业务口径。建议优先在本 Story 关闭前处理 CR-01～CR-08、CR-11、CR-12。CR-09、CR-10、CR-13、CR-14 建议随相邻任务补齐。 [团队分工](../../decision-log.md#L152)

- [ ] [Review][Patch] **CR-01 · 中 · 隔离复跑入口。** README 用原生 Django 测试命令，已安装后端会先尝试 PostgreSQL 维护库。实际成功复跑使用了额外游标约束，二者操作不同。影响 AC-7 可复现性、D-016、PC-002、ADR-008。 [README](../../README.md#L64) · [实际复跑路径](story-1-1-dev-evidence.md#L146)
  提供项目测试入口，仅在 test 模式接受既定测试库，启动前及建立连接时核验目标，保留预建库。验证日志覆盖每次连接，名称、角色、地址、端口和版本一致，测试前后数据相符。测试库不存在或目标错误时应停止。
- [ ] [Review][Patch] **CR-02 · 中 · 预置密码与登录字段校验不一致。** 清单解析只检查密码非空、字符串类型和 UTF-8 可编码，Django 登录密码字段还拒绝某些字符。若输入不适合浏览器密码字段，预置可生成一个无法使用原凭据登录的新账号，且同角色重跑会保留哈希。涉及 AC-1、AC-7、D-015、PC-008、ADR-002 和冻结规格的整批拒绝。 [预置校验](../../accounts/management/commands/seed_accounts.py#L36)
  在事务前复用登录密码字段校验并遵守浏览器单行输入约束，不改变合法密码值。隔离测试验证非法清单整批拒绝、已有数据与哈希无变化，合法三类账号成功登录。现有业务账号如需处理，另行申请批准。
- [ ] [Review][Patch] **CR-03 · 中 · 连接设置仍受继承环境影响。** 显式设置 HOST 和密码文件，仍可能继承独立的实际连接地址参数和显式口令。错误环境可改变实际端点或凭据来源。尚无本轮串库、泄密或外连实测。涉及 AC-7、D-016、PC-001／002、ADR-001／008。 [数据库设置](../../lab_booking/settings.py#L23) · [libpq 地址优先级](https://www.postgresql.org/docs/17/libpq-connect.html#LIBPQ-PARAMKEYWORDS) · [环境变量](https://www.postgresql.org/docs/17/libpq-envars.html)
  限定实际环回地址和受保护密码文件来源，开启连接前处理冲突的继承配置。迁移或预置前在同一连接确认服务器、库、角色和版本。使用无网络外连的合成配置对照和测试库合法连接验证。
- [ ] [Review][Patch] **CR-04 · 中 · Web 入口可继承迁移或测试模式。** WSGI 初始化直接接受数据库配置的三个模式。Django `runserver` 会在获得 WSGI 应用前检查迁移，单独限制 WSGI 仍无法阻止那次早期数据库访问。涉及 D-016、PC-001／002、ADR-001。 [WSGI](../../lab_booking/wsgi.py#L6) · [命令入口](../../manage.py#L7) · [模式映射](../../lab_booking/settings.py#L14)
  WSGI 与项目 `runserver` 入口只接受 runtime，在数据库检查前拒绝其他模式。验证两个非运行模式均未尝试连接，运行模式完成启动和合法登录，获准的管理和测试入口仍可用。
- [ ] [Review][Patch] **CR-05 · 中 · 初始化失败后启动命令继续执行。** 当前 PowerShell 示例在同一代码块执行预置、切换模式和启动，未读取原生命令退出码。本轮模拟以非零退出验证后续语句仍可运行。涉及 AC-7、D-015／019、PC-001、ADR-001。 [启动示例](../../README.md#L54)
  紧接预置命令检查退出码并中止失败流程。用无数据库替身分别验证非零时不起服务、成功时继续，在获准隔离环境补正常清单对照。
- [ ] [Review][Patch] **CR-06 · 中 · 权限证据的分母与逐案断言不足。** 11/11 只覆盖历史子集，部分直接拒绝共用一个数据快照，受限内容检查遗漏身份角色字段。当前实际拒绝范围还包含禁用账号、身份页写请求和退出拒绝等。属于测试及证据不足，未发现实际角色泄露。涉及 AC-2～AC-6 的拒绝路径、PC-011、ADR-002／008 和 T-03。 [失败断言](../../accounts/tests.py#L52) · [历史分母](story-1-1-dev-evidence.md#L105)
  对每条实际拒绝用例断言响应、无受限身份内容及业务数据不变，分别记录匿名或原认证会话应有状态。应用层角色直调与真实 HTTP 分开标注，按新矩阵重新统计分母及未完断言，合法对照单列。
- [ ] [Review][Patch] **CR-07 · 低 · 退出后存在未配置模板分支。** Django 的退出视图在特定可选同源跳转条件下会回落到默认模板，本项目没有该模板。源码可达性成立，当前版标准退出流程已有通过证据。涉及 D-019、AC-7、PC-008、ADR-002。 [退出路由](../../lab_booking/urls.py#L9)
  固定成功退出目标为登录页，复用 Django 的 POST、CSRF 和会话清理。验证正常和附带跳转信息的有效退出均回登录，GET、缺失及无效 CSRF 请求仍被拒绝。
- [ ] [Review][Patch] **CR-08 · 低 · 退出表单及服务端会话生命周期缺少自动断言。** 当前测试手工构造路由与令牌，按同一个客户端退出后的回跳判断。它未证明实际 HTML 表单可提交，也未查登录后生成的数据库会话行及退出后的移除。涉及 D-019、AC-1／5／7、PC-008、ADR-002。 [测试](../../accounts/tests.py#L161) · [退出表单](../../accounts/templates/accounts/identity.html#L17) · [会话设置](../../lab_booking/settings.py#L68)
  从渲染响应核对实际表单目标、方法、CSRF 字段并提交。在内存定位登录产生的会话行，核对对应账号，退出后检查该行不存在，拒绝分支保留原认证。断言输出保持脱敏。
- [ ] [Review][Patch] **CR-09 · 低 · 运行模式下的预置防护缺少仓库回归。** 本轮合成检查确认运行模式在读清单前拒绝。现有测试都沿用 test 模式，无法固定该校验顺序。涉及 D-015／016、PC-002／008、ADR-008。 [命令入口](../../accounts/management/commands/seed_accounts.py#L63) · [存储测试](../../accounts/tests.py#L204)
  补轻量用例，断言明确模式错误、清单读取未调用、业务写入未发生。保留测试模式成功对照。
- [ ] [Review][Patch] **CR-10 · 低 · 原始 JSON 重复键缺少仓库回归。** 本轮合成输入确认重复键返回脱敏错误。仓库测试序列化字典，无法构造同一 JSON 对象重复键，已有重复用户名用例验证的是另一项规则。涉及 D-015、PC-008、ADR-002 及冻结规格非法清单要求。 [解析钩子](../../accounts/management/commands/seed_accounts.py#L13) · [既有用例](../../accounts/tests.py#L250)
  使用原始合成 JSON 测试整批拒绝、已存在账号与哈希不变和日志脱敏，再以合法 JSON 核对正常路径。
- [ ] [Review][Patch] **CR-11 · 低 · 会话 Cookie 可进入失败诊断。** Python 的 `assertNotIn` 会在失败时格式化整个 Cookie 容器，容器表示包含值。现有套件使用合成会话，本轮通过日志未触发该输出。涉及 AC-2 取证、D-015 会话机制、PC-008 和冻结规格保密要求。 [失败断言](../../accounts/tests.py#L101)
  以布尔断言及固定脱敏消息取代整个容器的格式化。用合成值检查失败消息不含 Cookie 值，再复跑负向登录。
- [ ] [Review][Patch] **CR-12 · 低 · 新发现，登录测试绕过了渲染的表单。** 正例只检查标题并直接提交字段，失败例读取服务器表单上下文。在模板意外丢失实际输入控件或错误渲染时，现有断言仍可能通过。属于可复现自动化证据缺口，当前模板具备输入控件，已有 Chrome 基线。涉及 AC-1／2／5／7、PC-008、ADR-002。 [登录模板](../../accounts/templates/accounts/login.html#L11) · [登录测试](../../accounts/tests.py#L64) · [失败断言](../../accounts/tests.py#L97)
  核对响应正文包含可提交的用户名、密码、CSRF 控件和表单方法，用实际表单数据提交，按失败场景检查可见的校验提示。
- [ ] [Review][Patch] **CR-13 · 低 · 新发现，README 授权步骤与实测方式有差异。** 示例是五条独立 SQL。前面的检查命令已退出，示例未在同一连接绑定实际业务库和执行事务。若中途失败可能留下部分运行授权，开发时使用的是单事务和已核对连接。涉及 AC-7、D-016、PC-001／002、ADR-001／008。 [授权示例](../../README.md#L42) · [历史授权证据](story-1-1-dev-evidence.md#L82)
  在文档明确连接目标、核对同一连接及事务失败回滚，保持已批准的最小授权项。用无授权动作的模拟检查中途失败不继续和目标不匹配时不写入。任何真实额外授权须先审批。
- [ ] [Review][Patch] **CR-14 · 低 · 新发现，身份标签断言缺少独立预期。** 页面显示值与测试预期都来自 `Role` 枚举。若学生和教师的说明被互换，现有显示断言会随实现一同变化。代码当前映射正确。涉及 AC-1／4、D-015、PC-008、ADR-002。 [角色定义](../../accounts/models.py#L5) · [身份断言](../../accounts/tests.py#L75)
  在三角色对照中独立给出固定角色值对应的业务标签并逐一断言，同时保留会话用户 ID 和角色记录核对。

**归并结论。** 同一问题由多个视角指出时沿用一个编号。CR-01 的维护连接和 CR-03 的驱动继承参数是不同成因。CR-07 是退出代码分支，CR-08 是退出正例和会话生命周期断言，CR-06 是拒绝矩阵及分母。CR-09 和 CR-10 验证不同的预置防护。CR-12 与 CR-14 分别验证登录表单可用性和身份显示正确性。

#### 七条 AC 与课程证据

| 正式 AC | 本轮对照结果 |
| --- | --- |
| AC-1 | 现有 13 项覆盖三类账号、Django 认证会话、重复访问身份页与会话账号 ID。预置值校验、渲染登录表单和独立角色标签预期由 CR-02、CR-12、CR-14 补齐。 [既有断言](../../accounts/tests.py#L64) |
| AC-2 | 未知账号、错密和两种缺字段均通过失败及身份页拒绝断言。CR-06、CR-11、CR-12 补角色内容、失败诊断及页面反馈。 [既有断言](../../accounts/tests.py#L85) |
| AC-3 | 匿名和无效会话引导登录，禁用账号被拒绝。非法角色直接调用视图返回权限异常，数据库独立拒绝非法角色值。当前切片没有设备、预约或业务历史表，数据对照只计当前可观测账号数据。 [身份防护测试](../../accounts/tests.py#L105) |
| AC-4 | 登录和身份页的角色／账号伪造参数不改变本人身份。学生的 Django 管理标志设为真时仍显示学生身份，身份页写请求拒绝。 [既有断言](../../accounts/tests.py#L133) |
| AC-5 | 强制 CSRF 的客户端验证有效登录、缺失和无效令牌。退出扩展已有 GET 和无令牌负例，未自动断言无效退出令牌，已有 Chrome 记录该负例。CR-06～CR-08 补齐退出和会话证据。 [CSRF 测试](../../accounts/tests.py#L161) |
| AC-6 | Admin 和两条注册路由解析失败并返回 404，三类预置账号使用同一入口。按 CR-06 将共用的前后数据快照细化为逐案快照。 [既有断言](../../accounts/tests.py#L192) |
| AC-7 | 依赖与 PostgreSQL 17.12、本轮配置错误和测试库迁移一致性有独立证据。业务迁移、预置、最小授权和真实浏览器沿用开发证据。README 单入口隔离复现及第二台 Windows 机器仍待核验。 [实际开发验收记录](story-1-1-dev-evidence.md#L130) |

- **PPT 第 26 页。** 已核对 FR-001／002 到 ADR-001／002／008、Story 1.1 和测试的证据链。自定义 User、服务器角色、会话和权限入口符合已批准切片范围。测试边界和证据缺口列在处置清单。 [课程基线](../../docs/course-requirements.md#L80) · [首迁](../../accounts/migrations/0001_initial.py#L7) · [权限视图](../../accounts/views.py#L10)
- **PPT 第 27、33 页。** 有真实开发检查点、当前工作区、开发测试记录及独立评审，且需要由负责人完成修复取舍和最后的人工验收。历史 Git 检查点早于本轮评审。 [团队页码口径](../../docs/team/sprint-planning-review.md#L47) · [Git 开发检查点](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083)
- **PPT 第 34、36 页。** Sprint 计划仍将 2.6／2.7 列为实验 A 候选。本轮没有可归入实验 A 的数据。D-015～D-019 分别提供模型、环境、启动、实施规格和真实预置／退出的人工决策依据。本轮既有 CR-01 人工选择已注明，其他问题的处置与修复验证待实际发生再记录。 [实验计划](../planning-artifacts/sprint-plan.md#L75) · [决策日志](../../decision-log.md#L131)

#### Rejected

- 规格状态不同步的判断不成立。盲审差异按计划另行提供规格，本轮直接核对了规格 `in-review` 和 Sprint `review`。
- 清单必须由程序核验 Windows ACL 的建议不列为缺陷。批准规格把受保护清单作为操作前置条件，开发证据记录过真实文件 ACL 核对。
- 并发预置缺少独立实测列为待验证风险。当前有唯一键、行锁、事务回滚和顺序重跑证据，没有可确认的并发破坏。单列为强制整改需要超出本轮已确认验收条件的测试安排。
- README 实验 Y 的说明建议超出本次 Story 1.1 范围。实验计划仍保留干净会话和资料隔离条件。

本轮停在负责人审查问题清单的处置点。Story 1.1 保持 `review`，Story 1.2 保持 `backlog`。修复、实际变更数据库权限或迁移策略、触碰已有业务数据及最终验收分别等待相应授权。

### 2026-11-24 BMAD 6.12.4 渲染恢复后 Step 4 复审

在用户备份旧渲染目录后，使用 `uv run --no-cache --python D:/ttAPP/python.exe` 执行仓库原始 `_bmad/scripts/render_skill.py`，保留项目根和 `bmad-build` 技能参数。渲染退出码 `0`，新快照 `bmad-lab-booking-system-117d4295649a/13340bf8aef33bedeff3` 中的 `workflow.md` 和 `manifest.json` 均可读取。Python 3.14.7 只用于这次渲染。

按快照 Step 1 将既有 `in-review` 规格恢复到 Step 4，并解析到 Sprint 的 `1-1-使用预置账号登录并获得明确业务身份`。三路审查基于从 `685f358daa050cb28e1ee7672a2d55f20ef1b842` 到当前工作区的统一差异，包含未跟踪文件，未暂存。复审时 HEAD 与 `origin/main` 均为 `dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083`。

| 来源与发现 | 判定 | 证据与处理 |
| --- | --- | --- |
| 盲审：带空白的边界用户名被截断 | `medium` | 在 Node 中运行实际模板监听器，150 码点用户名粘贴时若带一个前导空格，监听后再去空格只剩 149 码点。Django `UsernameField` 在长度校验前去除这类空白。归入凭据原值被前端改写。 [登录模板](../../accounts/templates/accounts/login.html#L19) |
| 盲审：超限密码被截成另一值 | `high` | 合成替身输入从 4097 变为 4096 码点，确认提交前的值被改写为原值前缀。服务端超限规则看不到原输入。未发起登录请求。归入凭据原值被前端改写。 [登录模板](../../accounts/templates/accounts/login.html#L19) |
| 盲审：密码边界测试未使用浏览器表单编码 | `medium` | `Client.post` 默认使用 multipart。真实页面表单默认 URL 编码，当前最大密码测试未验证该传输入口。归入 CR-02 的表单编码回归缺口。 [边界测试](../../accounts/tests.py#L474) |
| 盲审：迁移预检和迁移失败后 PowerShell 继续 | `medium` | 承接 11 月 23 日复审。README 相关命令后仍没有退出码判断，原替身证据和修订建议继续有效。 [运行说明](../../README.md#L34) |
| 盲审：新 Windows 环境缺预建隔离库首迁步骤 | `medium` | 承接 11 月 23 日复审中的负责人决定项。现有说明要求隔离库已迁移，R-03 有本机环境证据，独立安装交接和第二台机器的实测仍待完成。 [测试入口](../../README.md#L89) · [R-03](../../docs/team/sprint-1-environment-preparation.md#r-03-批准后执行记录) |
| 盲审：启动器只选择 Python 版本系列 | `low` | 承接 11 月 23 日复审。README 指定 3.13.17，但依赖安装前未核对实际补丁版本。 [启动入口](../../README.md#L12) |
| 盲审：测试运行器接纳可访问数据库的 `SimpleTestCase` | `medium` | 承接 11 月 23 日复审。运行器守卫仍只排除非 `TestCase` 的 `TransactionTestCase`。此前用例已证明守卫可放行该类型。 [测试运行器](../../lab_booking/test_runner.py#L14) |
| 盲审：未知迁移不在计划中 | `low` | 承接 11 月 23 日复审。Django 5.2.19 跳过图中未知的已应用迁移，当前前进计划检查无法弥补。 [迁移预检](../../lab_booking/test_runner.py#L43) |
| 盲审：隔离库前后快照范围有限 | `low` | 承接 11 月 23 日复审。快照仍比较表清单、迁移和账号、会话数量。其余认证数据或序列漂移未纳入。 [快照](../../lab_booking/test_runner.py#L66) |
| 盲审：拒绝响应测试查不到 HTML 属性中的账号 | `low` | 承接 11 月 23 日复审。账号断言仍只检查解析后的文本节点，未观察到当前页面泄漏。 [拒绝断言](../../accounts/tests.py#L108) |
| 盲审：课程证据索引和 AI 使用声明滞后 | `low` | 承接 11 月 23 日复审。README 仍列实测待开展及 D-014 为末项，与当前工作区证据不一致。 [课程索引](../../README.md#L230) |
| 边界审查：超限密码被前端静默改写 | `high` | 同一监听器、相同触发条件及后果，独立报告与盲审相符。归入凭据原值被前端改写。 [登录模板](../../accounts/templates/accounts/login.html#L19) |
| 边界审查：实际连接校验失败时开发服务器可能仍监听 | `low` | Django `check_migrations()` 捕获 `ImproperlyConfigured` 后返回，`runserver` 随后可继续监听。数据库连接守卫仍关闭不匹配连接。仅静态确认异常传播路径。归入启动失败传播，与 README 中独立的 PowerShell 传播问题分别处理。 [启动命令](../../accounts/management/commands/runserver.py#L6) · [连接守卫](../../lab_booking/postgresql/base.py#L36) |
| 验证缺口：仓库常规测试未执行登录页的码点监听器 | `medium` | 动态替身证明当前 76 个补充字符保留完整。若监听器改按 UTF-16 单元切分会只剩 75 个，现有 HTML 属性与 Django Client 断言仍通过。归入前端凭据边界回归缺口。 [用户名回归](../../accounts/tests.py#L173) |
| 验证缺口：最大密码回归未覆盖 URL 编码 | `medium` | 4096 个补充字符的合成密码按 UTF-8 为 16384 字节，独立计算 URL 编码表单超过 48 KiB。当前测试的 multipart 请求未固定实际传输边界。归入 CR-02 的表单编码回归缺口。 [边界测试](../../accounts/tests.py#L474) |
| 验证缺口层补充：前导空格导致合法边界用户名丢字 | `medium` | 独立动态替身与主审复核得到相同 150→149 码点结果。归入凭据原值被前端改写。 [登录模板](../../accounts/templates/accounts/login.html#L19) |

凭据原值改写归为 `bad_spec`。第二轮任务要求输入脚本做码点限制，但没有明确要求保留原始输入，实际截断与该轮的超限拒绝和保留既有用户名语义发生冲突。BMAD 要求先处理该项，再进入补丁处置、复测及展示。保留项包括服务端 150／4096 码点的共享校验、模型用户名验证、事务前脱敏拒绝、补充字符支持、真实表单与 CSRF、三角色隔离和既有账号保护。建议修订非冻结任务，要求客户端提示边界且保留原始值，由服务端完成规范化和拒绝，并补实际 URL 编码提交与前端边界断言。

在执行正式回退前停下。当前工作区包含首迁后的既有未提交实现，需要负责人单独确认回退重做的处理方式。项目 `.venv/Scripts/python.exe --version` 在本次会话以 `103` 退出，配置的 Python 3.13.17 解释器无法启动。新结果为只读差异复审、合成替身及静态核对，没有重跑 Django 测试、登录业务库或修改数据库。之前 31 项通过、Chrome 三角色验收均保留为历史证据，第二台 Windows 机器复现及实验 A 继续按原节点取证。本轮未到达 Step 5，规格仍为 `in-review`，Sprint Story 1.1 为 `review`，Story 1.2 为 `backlog`。本轮未新增人工验收决定或 Git 提交。

课程第 26 页的一致性追溯仍沿 FR-001／002 → ADR-001／002／008 → AC-1～7及对应验证。第 27、33 页证据由实际状态、评审发现和[历史开发自测](story-1-1-dev-evidence.md#2026-11-24-第二轮整改与开发自测)承接。第 34 页实验 A 保留 X／Y 待正式执行，第 36 页沿用[决策日志](../../decision-log.md)中的真实人工决定。课程页码依据[课程基线](../../docs/course-requirements.md)及[团队审核材料](../../docs/team/sprint-planning-review.md#5-11-月-17-日课程核对与规划提交记录)。

## Verification

- 实测 `lab_booking_app`、`lab_booking_migrator` 连 `lab_booking`，`lab_booking_test` 连 `test_lab_booking`。三者跨项目库均由服务端拒绝。运行账号仅获账号读取、必要认证字段更新及会话 DML，无 DDL。核对无独立占用表及其授权。
- 测试模式 `NAME`、`TEST.NAME` 均指向测试库。用 `test accounts --keepdb --parallel 1 -v 2` 验证角色遗漏、空值、空串、非法值拒绝入库，预置哈希可验证、重跑零新增且原值保留、异角色整批回滚。运行身份执行 `runserver 127.0.0.1:8000 --noreload`。
- 实施目录 `story-1-1-dev-evidence.md` 按 FR-001／002 → ADR-001／002／008 → AC 记录实际环境及依赖版本、连接、启动、命令、预期／实际、会话、角色、失败原因与复测。T-03 登记成对路由。PC-011 逐项核对拒绝、无泄露及前后数据，记录三项均满足的未授权用例数／总数，合法对照单列。
- `sprint-status.yaml` 状态关联实证。负责人批准 Checkpoint 1 后置为 `ready-for-dev`。按 [Sprint 计划](../planning-artifacts/sprint-plan.md) 开工时，Story 和父 Epic 进入 `in-progress`。开发自测完成后停在 `review`。新会话 `bmad-code-review`、修复、真实复测及负责人验收通过后才到 `done`。

## 2026-11-23 D-020 整改交接

- 按已批准的 CR-01～CR-14 待办进入 `in-progress`。保留原始评审发现，逐项整改结果和代码／验证映射见[处置记录](../../docs/team/story-1-1-review-disposition.md#开发整改与自测结果)。
- 验证入口使用 README 的 `manage.py test --keepdb --parallel 1 -v 2`，使用已迁移的隔离库。26 项全量自动化测试和 Chrome 三角色表单复测完成，库前后清单一致。Windows runtime 只读启动及错误配置拒绝通过。见[开发自测证据](story-1-1-dev-evidence.md#2026-11-23-独立评审整改与开发自测)。
- 修复和开发自测完成，规格回到 `in-review`，Sprint 回到 `review`。独立复审和负责人最终验收待执行。

## 2026-11-23 D-020 独立代码复审报告

**结论为修订后再进入负责人最终验收。** 原 14 项中，建议关闭 12 项，CR-02 未关闭，CR-04 建议由负责人确认是否接受整改后真实运行账号登录的补证风险。现有三类演示账号路径的证据成立，AC-1 的预置输入边界仍有两处不一致。尚无证据显示真实业务数据受影响，也未发现现有路径的权限绕过、CSRF 失效或会话泄漏。

### 复审范围与方法

- BMAD 6.12.4 `bmad-code-review` 的 `full` 模式。盲审、边界审查、验证缺口审查和验收审计均返回发现。前三层并行，第四层在槽位释放后启动，收齐后逐条裁定。工作流初次读取 uv 缓存失败，经工具授权后解析成功。
- 差异基线为 [685f358daa050cb28e1ee7672a2d55f20ef1b842](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/685f358daa050cb28e1ee7672a2d55f20ef1b842)，覆盖 [dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083) 和复审启动时未提交工作区，包含新增文件。共 29 文件、增 1724 行、删 6 行。取证快照 SHA-256 为 `2b583b975d1d462e3f93ac7342d08c89e5b30d0a77ccee3832b27dc7489c03f1`。
- 核对[正式 Story 1.1](../planning-artifacts/epics.md#story-11-使用预置账号登录并获得明确业务身份)、[PRD](../planning-artifacts/PRD.md)、[Architecture](../planning-artifacts/architecture.md)、[project-context](../planning-artifacts/project-context.md)、本规格的原完整评审报告、[D-020 处置](../../docs/team/story-1-1-review-disposition.md)、[开发证据](story-1-1-dev-evidence.md)及 [D-015～D-020](../../decision-log.md#L131)。

### 独立实测及证据边界

| 检查 | 命令或方法 | 本轮结果 |
| --- | --- | --- |
| 全量自动化 | Windows venv 下 `manage.py test --keepdb --parallel 1 -v 2`，Python 3.13.17／Django 5.2.19／psycopg 3.3.9 | 发现 26，通过 26，失败、错误、跳过均 0，7.577 秒，退出 0。 |
| 两项实库补测 | 内存定义两个临时 TestCase，复审脚本另在驱动入口核对名称、角色、主机、地址和端口 | 首次 2／2 通过，1.851 秒。改为分别断言 schema USAGE 与 CREATE 后复跑仍为 2／2，1.687 秒。两次执行均退出 0，每次记录两条实际连接，均为 `127.0.0.1:5433/test_lab_booking`，认证及当前账号均为 `lab_booking_test`，服务端 17.12。 |
| 实库检查内容 | 两个合法用户独立登录和退出；只读 PostgreSQL 系统目录 | 退出一方后另一方保持身份和服务端会话。测试角色对业务库 CONNECT 为假，运行和迁移角色对测试库 CONNECT 均为假。测试角色在测试 schema 有 USAGE／CREATE。有效角色约束已验证，角色列非空、无默认值，无默认 `auth_user`。 |
| 连接和运行器合成检查 | 独立指定冲突变量集合，替身覆盖预检和后置元数据 | 9／9 变量在驱动调用前被拒绝。6／6 合成拒绝覆盖权限越界、待迁移、残留账号或会话、后置漂移，后置错误仍关闭连接。另确认声明数据库访问的 SimpleTestCase 会进入测试套件，未运行其数据库操作。 |
| Windows 与模型 | 实际启动 `runtime` 的 `runserver --noreload`，只访问匿名 GET；在 test 模式运行 `makemigrations --check --dry-run` | 系统检查无问题，`GET /login/` 200，匿名 `GET /identity/` 302，模型检查无变更。分别缺模式、PGPASSFILE 或项目密钥均报相应名称并退出 1。 |
| README 执行分支 | 直接抽取 PowerShell 代码块，以替身模拟退出码 | 预置失败 17 时停止，成功 0 才启动。授权命令失败 3 时停止，同一 psql 命令包含目标预检、单事务及五条原授权。迁移预检的首命令失败 17 后仍执行其余命令，末尾退出 0。将迁移与授权块连续运行时，模拟迁移失败后仍调用 psql。 |
| 输入边界 | 内存清单解析、表单属性检查、合成密码哈希及本地 Chrome 输入框检查 | 确认过长密码和扩展 Unicode 用户名两处边界未对齐。浏览器对合成文本实际仅保留 75 个码点、150 个 UTF-16 单元。检查未连接数据库、创建账号或向应用发送请求。 |
| Git 与保密 | 基线差异 `git diff --check`，扫描快照的新行和跟踪／未忽略文件路径 | 退出 0，常见凭据模式和敏感路径均 0 命中。当前复审未读取或核验真实秘密值。 |

全量和两次补测的隔离库前后均核对到 9 张表、16 条迁移、0 个账号、0 条会话。表清单及迁移记录逐项相等。PostgreSQL 序列计数不在快照内，事务回滚后可能继续向前。业务库在本轮只随 runtime 启动执行只读检查。未提交业务登录、未迁移、未预置、未清库、未修改授权。

Chrome 安装版本独立核对为 159.0.8154.13。开发证据保留了两次临时脚本失败及第三次合成账号通过，第三次运行在隔离库和临时 WSGI 服务上。D-019 则记载整改前的真实业务账号、正式 runtime 登录和退出。本次核对了两份历史证据及入口对应关系，Chrome 独立实测限于本地长度检查。第二台 Windows 机器尚未复现。

### 原 CR 逐项复审

| 编号 | 建议 | 独立依据 |
| --- | --- | --- |
| CR-01 | 关闭 | README 默认入口独立复跑成功，后端在驱动前限定目标，运行器跳过原生建库、迁移和清库，另外验证实际连接、跨库 ACL 与失败预检。未来测试类与更广的测试数据快照另有待办。 [运行器](../../lab_booking/test_runner.py) |
| CR-02 | **未关闭** | NUL、CR、LF、孤立代理项现已整批拒绝，合法三角色通过。额外合成检查确认超出网页登录传输容量的单行密码仍可通过解析并产生合法哈希，预置后正常表单无法完成认证。 [预置校验](../../accounts/management/commands/seed_accounts.py#L30) |
| CR-03 | 关闭 | 独立指定的 9 个变量全部在驱动前被拒绝，实测两个连接全程落在批准目标。仓库用例与生产清单同源的验证缺口另列。 [连接后端](../../lab_booking/postgresql/base.py) |
| CR-04 | **建议风险接受** | migration/test 启动拒绝及 runtime 启动均复验。整改后真实业务账号登录依赖 D-019 历史证据、当前隔离库实测和 runtime 只读冒烟组合。若负责人需要在当前代码的实际运行角色下重新做有写入的认证，按 D-020 单独授权。 [Web 入口](../../lab_booking/wsgi.py) |
| CR-05 | 关闭 | 独立替身确认预置失败后不调用 runserver，成功才继续。相邻迁移步骤的失败传播另列。 [启动步骤](../../README.md#L78) |
| CR-06 | 关闭 | 逐条对照了 16 个 HTTP 与 1 个直接视图用例的分母，26 项复跑全部通过。合法对照未计入分母，额外 HTML 字段的断言盲区另列。 [断言](../../accounts/tests.py#L108) |
| CR-07 | 关闭 | 固定退出目标，正常和附带跳转参数分别在实际渲染表单用例通过，GET 返回 405，缺失或无效 CSRF 返回 403。 [退出视图](../../accounts/views.py#L12) |
| CR-08 | 关闭 | 表单来源、旧服务端会话删除和拒绝分支均复验。额外确认退出一方不影响另一方的已认证会话。 [退出回归](../../accounts/tests.py#L263) |
| CR-09 | 关闭 | runtime 预置拒绝在读取器及事务调用前，正常 test 预置在账号用例中通过。 [预置顺序](../../accounts/tests.py#L411) |
| CR-10 | 关闭 | 真正重复的 JSON 键在读取阶段即脱敏拒绝，解析发生在开启事务之前，合法 JSON 对照成功。仓库重复键用例的前快照为空，已有哈希保留另有存储回归。 [原始 JSON 回归](../../accounts/tests.py#L423) |
| CR-11 | 关闭 | 合成 Cookie 触发断言失败，固定消息未输出会话标识。 [诊断回归](../../accounts/tests.py#L327) |
| CR-12 | 关闭 | 对真实 HTML 的登录控件、方法、CSRF、可见校验错误均做检查，补测通过表单提交。Unicode 长度差异属于另一个实现缺陷。 [表单合同](../../accounts/tests.py#L89) |
| CR-13 | 关闭 | 同一 psql 事务的目标校验、失败中止与五条已批准授权均经对照核验。本轮无实际 GRANT。 [授权说明](../../README.md#L51) |
| CR-14 | 关闭 | 预期标签独立于生产枚举，逐一核对三类账号的存储角色、页面和会话用户。 [三角色回归](../../accounts/tests.py#L150) |

### 正式 AC 与批准边界

| AC | 结论与证据 |
| --- | --- |
| AC-1 | 三类常规预置账号通过；扩展 Unicode 用户名及过长密码存在已确认的预置与登入不一致，建议补齐后再签收。 |
| AC-2 | 通过。四种无效输入显示表单错误，无认证会话，随后身份页仍拒绝。 |
| AC-3 | 通过。匿名、无效会话、禁用账号均拒绝，直接视图非法角色被拒绝，账号状态前后一致。 |
| AC-4 | 通过。服务端身份为本人，伪造字段与 Django 管理标志不改变业务角色。 |
| AC-5 | 通过。有效 CSRF 进入凭据校验，缺失或无效 CSRF 拒绝，退出与会话生命周期也通过。 |
| AC-6 | 通过。三角色共用登录入口，Admin 及两条注册路由无法解析，HTTP 404。 |
| AC-7 | 已配置本机启动、缺配置报错、隔离测试和历史 Chrome 有证据。全新机器的数据库准备说明有缺口，第二台机器未复现。实际业务库迁移、预置和运行角色成功登录沿用 D-019。 |

D-015 的模型、授权来源和默认标志符合批准方案。D-016 的 17.12 目标、角色分离和隔离库经代码及实际 ACL 核对。D-017／018 的切片范围、规格和状态边界保留。D-019 退出回归通过，业务演示账号记录沿用历史证据。D-020 的隔离、最小授权和业务库只读边界在本轮实际运行中得到遵守，CR-02 的输入整改仍不完整。FR-001／002、ADR-001／002／008、PC-001／002／008／011 仍是当前追溯链。此处的 PC-011／T-03 证据只覆盖账号切片。

### Review Findings

以下为 2026-11-23 正式评审当时的原始发现与状态快照，保留用于追溯；其中的旧待办描述不代表当前处置。后续整改、输入边界独立复审及 D-022 负责人决定见本规格后续章节，并以最终处置表和验收清单为当前状态。

两项凭据边界应在最终验收前处理。较短正常凭据和已证实的三个演示账号路径通过。后续若需处理真实账号，须另行授权。

- [ ] [Review][Decision] **CR-02 残余 · 中 · 密码预置可接受网页登录无法提交的长度。** 合成清单经解析和哈希处理成功，常规 URL 编码表单会超出 Django 请求体上限，认证前即失败。建议确定预置与登录共用的有效上限，将失败放在写库前，保护已有哈希。也可由负责人明确限定受保护清单的支持范围，并记录校验和验证条件。 [预置校验](../../accounts/management/commands/seed_accounts.py#L32)
- [x] [Review][Defer] **中 · 新机的预建隔离库缺少首迁和权限准备说明。** README 与 R-03 记录要求但未提供从新 Windows 实例准备两库、三角色并完成隔离库首迁的可复现步骤。负责人按 D-022 将新机交接和第二台 Windows 复现保留为项目级集成验证；已完成机器的 AC-7 真实运行证据成立。本项不阻塞 Story 1.1。 [README](../../README.md#L89) · [R-03 取证](../../docs/team/sprint-1-environment-preparation.md#L64) · [延期记录](deferred-work.md)
- [ ] [Review][Patch] **中 · 预置接受浏览器输入框装不下的 Unicode 用户名。** 合成用户名通过预置校验。使用相同 `maxlength=150` 本地控件时，Chrome 将 76 个码点、152 个 UTF-16 单元的输入截为 75 个码点。问题已存在于首迁前检查点，未在此次整改修复。对齐表单按 UTF-16 和后端按码点的限制，保持已有用户名语义，并验证真实浏览器输入。 [预置校验](../../accounts/management/commands/seed_accounts.py#L30) · [登录模板](../../accounts/templates/accounts/login.html#L13) · [HTML maxlength](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#attr-fe-maxlength) · [字符串长度](https://infra.spec.whatwg.org/#string-length)
- [x] [Review][Defer] **中 · PowerShell 迁移失败会被后续命令覆盖。** 本轮替身证实连接检查失败仍执行下一行，连续执行迁移和授权块时失败迁移仍进入后续授权调用。负责人按 D-022 接受当前 Story 初始化已成功、README 步骤分隔并保留负责人复核点的证据；下一次全新环境操作前应完善逐条 `$LASTEXITCODE` 中止检查。本项为项目级操作硬化，不阻塞已完成的 Story 1.1。 [README](../../README.md#L38) · [延期记录](deferred-work.md)
- [x] [Review][Defer] **中 · 测试运行器可接纳未封入回滚事务的数据库测试类。** 本轮合成确认指定数据库的 SimpleTestCase 可以进入套件。当前 32 项实库套件使用回滚式 TestCase，且隔离库前后状态一致。负责人按 D-022 将收紧测试类型约束留给项目级测试工具链硬化；本项不否定本轮 AC 回归，不阻塞 Story 1.1。 [运行器](../../lab_booking/test_runner.py#L14) · [延期记录](deferred-work.md)
- [ ] [Review][Patch] **低 · 旧分支未知迁移可逃过计划核验。** Django 5.2.19 会跳过图中未知的已执行迁移，空前进计划也不能发现它。当前隔离库有 16 条正常迁移。考虑核对已应用与当前迁移集合，并保留合并迁移语义。 [运行器](../../lab_booking/test_runner.py#L43)
- [ ] [Review][Patch] **低 · 前后快照数据范围有限。** 看得到表清单、迁移、账号及会话数量。其他认证表内容和非事务性序列不在比较范围，补充证据范围说明与必要断言。 [快照](../../lab_booking/test_runner.py#L66)
- [ ] [Review][Patch] **低 · 拒绝断言看不到 HTML 属性中的账号。** 账号检查使用 HTML 文本节点。当前拒绝模板未发现数据泄漏，补测可检测其他账号进入属性或隐藏字段，同时允许用户提交的用户名在登录页回显。 [拒绝断言](../../accounts/tests.py#L108)
- [ ] [Review][Patch] **低 · 仓库回归缺少若干运行器拒绝分支。** 本轮临时替身已核对 6 个分支。常规套件没有分别固定权限、待迁移、残留数据和后置漂移的失败结果。 [入口回归](../../lab_booking/tests.py#L77)
- [ ] [Review][Patch] **低 · 冲突环境变量测试与生产代码使用相同清单。** 本轮独立枚举全部 9 项已通过，仓库回归仍会随生产清单误删一项而漏测。 [连接回归](../../lab_booking/tests.py#L30)
- [ ] [Review][Patch] **低 · 仓库启动回归缺正向 runtime 入口。** 本轮已独立完成 Windows 正向冒烟，仓库测试只固定拒绝模式，后续可将这一正向检查纳入可复跑证据。 [启动回归](../../lab_booking/tests.py#L104)
- [ ] [Review][Patch] **低 · 已迁移库的测试无法发现初始迁移文件的约束漂移。** 本轮独立执行模型一致性检查通过。保留该检查作为正式验证步骤，避免只靠预建库旧约束来证明新安装。 [初始迁移](../../accounts/migrations/0001_initial.py#L33) · [测试入口](../../lab_booking/test_runner.py#L43)
- [ ] [Review][Patch] **低 · Windows Python 启动器只选版本系列。** 在新机安装依赖前核对 venv 的 3.13.17 和位数。 [README](../../README.md#L10)
- [ ] [Review][Patch] **低 · 课程证据索引和 AI 使用声明更新滞后。** README 末尾仍称 M3、测试及部分状态证据尚未开展，计数停在 D-014，AI 声明尚未纳入实施和评审。补实际 Story 证据链接，同时保留整体验收待办。 [README](../../README.md#L232)

#### Rejected

- **false** · 标准 Django 测试运行器替换会自动实际连接维护库的推断不成立。配置确实支持显式替换运行器，但 Django 5.2.19 原生维护路径生成 `postgres` 目标，项目后端在驱动调用前抛出 ImproperlyConfigured，原生 PostgreSQL 回退只捕获数据库异常。本轮默认入口与独立驱动记录均未发现维护库连接。
- **low** · Django 预检失败后同进程重入可能残留测试环境，全量命令以独立进程运行，退出后自然释放。当前没有同进程重试的调用者，暂不增加生命周期修补。
- **maybe-false** · 同库其他 schema 的同名表或异常 search_path 可能使限定 public 的快照与 ORM 解析不同。本轮无实际偏差证据，已验证当前测试库中的 role 约束和目标，当前部署范围内不单立缺陷。

两项待负责人决定、12 项整改建议、0 项已批准延后、3 项驳回。合并的重复来源分别为：新机准备（盲审、验证缺口、验收审计），PowerShell 失败传播（盲审、边界审查），账户快照／序列（盲审、边界审查），Python 版本（盲审、边界审查）。真实 runtime 登录的证据限度计入 CR-04，未计作产品缺陷。

### 课程证据与交接

| PPT 页 | 本轮证据 |
| --- | --- |
| 26 | 从 FR-001／002、NFR-002 账号切片回指 ADR-001／002／008、PC、正式 AC、实际代码与独立测试。 |
| 27 | 依团队记录的逐 Story 口径，保留首迁前 Git 检查点、历史开发与自测、D-020 整改和本轮独立复审。 |
| 33 | 已配置 Windows 启动、26 项复跑和 2 项临时实库补测有实际数据，第二台机器、洁净环境准备及完整 NFR 证据待后续。 |
| 34 | 本次结果未计入实验 A，Sprint 计划的 2.6／2.7 仍为候选，仓库未见可核验的正式对照数据。 |
| 36 | D-015～D-020 保留既有人工判断。本报告记录实际复审及建议，后续接受、修订或拒绝由负责人落入决策日志。 |

页码按[课程基线](../../docs/course-requirements.md)和[团队记录](../../docs/team/sprint-planning-review.md)核对，仓库未见 PPT 原件。本次仅追加复审证据，未处理整改待办，规格保持 `in-review`，Sprint Story 1.1 保持 `review`、1.2 保持 `backlog`。未更改业务代码、未提交或推送，等待负责人审核。

## 第二轮开发整改范围（负责人本轮明确批准）

- CR-02：为预置清单和实际 `AuthenticationForm` 建立相同的密码最大长度，超限在写库前以脱敏错误拒绝。长度必须保证任何成功预置的密码都可经正常 URL 编码网页登录请求提交；合法边界值可登录。不得改变已有账号密码、角色或权限。
- CR-02 回归：覆盖合法常规密码、合法最大边界、超长、NUL／CR／LF／孤立代理项及其他非法输入；每个拒绝批次都要证明账号集合和已有账号字段／密码哈希完整不变；重复初始化须新增为零且原哈希不变；成功初始化必须用真实渲染登录表单完成认证。
- 新发现 `U-01`（不得改写既有 CR 编号）：统一用户名最大长度为 Django 服务端按 Unicode 码点计算的 150 个字符。登录 HTML 不得使用会在 150 个扩展字符之前截断的 `maxlength=150`；客户端行为须允许全部服务端合法值，服务端仍对超过 150 码点的值拒绝。以隔离测试库构造 76 个补充平面字符用户名，验证预置、实际渲染表单输入、登录和身份显示；同时验证 150／151 码点边界及非 BMP 字符混合输入。
- CR-04：只使用已批准 PostgreSQL 17.12 上 D-019 已有的三类合法预置账号，按当前 Windows `LAB_BOOKING_DB_MODE=runtime` 启动实际 Web 入口。通过浏览器完成三类登录、固定身份显示、刷新保持、有效 CSRF 退出、服务端会话失效；记录启动命令、HTTP／浏览器响应及实际连接目标和角色。不得连接非批准目标、输出凭据或修改密码／角色／授权。认证按正常流程产生的 `last_login` 与短暂会话是本验收的预期副作用；成功退出后核对服务端会话已删除。
- 本轮完整重跑隔离测试套件及新增回归，核对 AC-1～AC-7，更新处置和开发证据；保持 Story 为 `review`，不做独立复审、不开发 1.2、不标记 done、不提交。

**第二轮任务**

- [x] 在 `accounts/forms.py` 定义预置与登录共用的密码长度常量和 `AuthenticationForm` 子类；`accounts/views.py` 使用该表单，`seed_accounts.py` 在打开数据库事务前调用同一字段校验。边界以 4096 个 Unicode 码点为上限，最坏 URL 编码 POST 体约 48 KiB，低于 Django 默认请求体限制；测试常规、4096 合法、4097 超限、控制字符、重复初始化及既有字段／哈希不变，并从实际渲染表单登录边界密码。
- [x] `accounts/forms.py` 和登录模板以服务端 150 个 Unicode 码点为统一用户名上限；HTML `maxlength` 使用 300 个 UTF-16 代码单元，输入脚本按码点友好限制 150，服务端仍严格校验。覆盖 76 补充平面字符、150／151 边界、混合字符的预置、渲染控件、登录及身份页。
- [x] 在批准的 Windows runtime 和 PostgreSQL 17.12 业务目标，使用已有三类账号完成真实 Chrome 浏览器登录、身份展示、刷新、CSRF 退出，并记录实际响应与数据库连接身份；未修改密码、角色、权限或其他业务字段。
- [x] 在隔离 `test_lab_booking` 执行完整自动化测试 31/31，逐项核对 AC-1～AC-7，更新开发证据和整改处置记录，并执行差异及敏感信息检查；Story 保持 `review`、1.2 保持 `backlog`。

### 第二轮整改结果（2026-11-24）

CR-02 已在预置命令和 `AccountAuthenticationForm` 共用 4096 个码点密码上限；超限、控制字符、Unicode 编码错误在事务前拒绝。实际页面的 UTF-16 `maxlength=8192` 配合码点输入限制，避免合法补充字符密码因浏览器单位差异被截断。U-01 以数据库用户名 `max_length=150` 及 Django 模型验证器为服务端规则；前端可承载 300 个 UTF-16 单元并按 150 码点限制，越界值仍由服务端拒绝。Chrome 实测 76 个 U+20000 输入为 76 码点／152 单元并保持完整，151 码点在输入事件后收敛为 150。

CR-04 沿用第一轮已完成的 runtime 入口保护。本轮 Chrome 159.0.8154.13 对 PostgreSQL 17.12 `127.0.0.1:5433/lab_booking` 以 `lab_booking_app` 执行三类真实账号表单登录、身份展示、刷新、缺失／无效 CSRF 和退出。三个会话均在服务端匹配本人并经实际 POST logout 删除；结束时会话数为 0。登录依标准 Django 行为更新 `last_login`，密码、业务角色、启用标志和 Django 管理标志保持不变。第二台 Windows 机器仍未复现。

最终隔离全量命令 `manage.py test --keepdb --parallel 1 -v 2` 发现 31 项，通过 31、失败／错误／跳过 0，10.609 秒、退出码 0。测试前后均为 9 张表、16 条迁移、0 账号、0 会话。开发证据记录了边界回归初次失败、模型验证器修复、针对性复测及最终全量复测。本节为开发自测记录，独立复审和负责人验收仍待执行。

## 本轮实施范围（2026-11-24，负责人授权）

以下任务取代第二轮整改中以 HTML `maxlength` 和脚本截断实现码点限制的做法。冻结意图、正式 AC、数据库连接约束与历史证据保留。仅修改用户名和密码输入边界及对应测试，保留既有工作区内容，不回退其他实现。本轮 Story 1.1 保持 `review`，规格保持 `in-review`，Story 1.2 保持 `backlog`。不提交或推送。

- [x] 给定经 Django 默认 `UnicodeUsernameValidator` 校验的 150 码点用户名（包括 300 UTF-16 单元的值），当从渲染表单提交时，浏览器保持输入值，Django 沿用 `UsernameField` 的外围空白处理及 NFKC 规范化。内部空格、默认规则禁止的字符及规范化后超出 150 码点的值应拒绝。预置和登录共享这一输入校验，并保留已批准的账号模型语义。
- [x] 给定正常和 4096 码点密码，从正常浏览器表单提交的原始值应能到达服务端并按原密码认证。给定 4097 码点密码（包括尾部多一字符且前缀是合法 4096 码点密码的情况），不得截断输入或尝试验证截断后的密码；应展示字段错误并且不建立会话。预置在事务前同样以脱敏错误拒绝超限值，已有字段与哈希保留。
- [x] 通过实际渲染表单及 URL 编码回归覆盖上述边界。保留原 AC-1～AC-7 测试，验证 150／151、UTF-16 边界、外围与内部空白、4096／4097、拒绝后数据与会话不变。仅使用 `test_lab_booking`，严禁连接、重建或修改 `lab_booking`。只有主会话有权执行获准的实库回归，实施子代理先交付代码与测试，不连接任何数据库，不安装或改写 Python 环境。

移除两种输入的 HTML `maxlength` 和页面截断脚本，边界错误经 Django 字段显示。登录和预置统一使用 `UsernameField`、账号模型的默认字符验证器及 4096 码点密码字段。本轮 `accounts` 改动限于表单、模板、预置解析和测试。2026-11-24，原 Python 3.13.17 环境在普通 PowerShell 下通过 32 项 Django 测试与 6 个实际 Chrome 表单用例。第二台 Windows 及本轮业务库部署复现待取证，状态仍为 `in-review`。见[整改实测与 AC 追溯](story-1-1-dev-evidence.md#2026-11-24-输入边界最终整改)。

### Review Findings

#### 2026-11-24 Story 1.1 输入边界独立复审恢复

按 BMAD 6.12.4 `bmad-code-review` full 模式恢复 Step 2，使用已保存的四文件差异（17,486 字节，SHA-256 `46509CF3793D92478472076D7F63EA5D4C0D7E98B0F29289BADBF4AAC643D5ED`）。四个启用视角均实际返回；`failed_layers` 为空。复核依据包括本规格 AC-1～AC-7、PRD、Architecture、`project-context.md`、D-015～D-021、整改记录和当前提交代码。

### Findings triage

本轮没有保留的 `decision-needed`、`patch` 或 `defer` 项。对输入边界差异未发现新的 Critical、High 或 Medium 问题。以下候选逐项核验后驳回：

Blind Hunter 的五个候选和 Edge Case Hunter 的一个候选均在核验后驳回；Verification Gap Reviewer 未报告缺口；Acceptance Auditor 未报告验收差异。逐项裁决完成后，当前输入边界差异为 **0 decision-needed、0 patch、0 defer、6 rejected**。这不是对范围外旧评审行动项的关闭。

### Independent checks carried forward

不重复运行既有测试。复用独立 Django 回归 32/32、真实 Chrome 表单用例 10/10，以及仅连接 `127.0.0.1:5433/test_lab_booking`／`lab_booking_test` 的 PostgreSQL 17.12 隔离验证；测试库前后状态均为 9 张表、16 条迁移、0 个账号、0 条会话。检查点列明 10 个浏览器用例及其输入边界。以上仅为本次评审的既有证据，不声称本轮再次执行。

### CR closure decisions

| 编号 | 本次最终判断 | 依据／保留事项 |
| --- | --- | --- |
| CR-01 | 关闭 | 既有独立复审验证预建库运行器、实际目标和阻断维护库生命周期操作。 |
| CR-02 | 关闭 | 本轮独立确认登录与预置共用 4096 码点字段校验；4096 可正常认证，4097 完整拒绝且不调用认证；沿用 32/32 和 10/10 独立证据。 |
| CR-03 | 关闭 | 既有独立复审确认连接目标与冲突环境变量限制；本轮差异不触及此处。 |
| CR-04 | **负责人接受证据与残余风险，关闭（D-022）** | 最新差异只改表单、模板、预置解析和测试，未改变 runtime、身份/角色、CSRF、会话或退出路径。D-019/开发证据中的 Windows runtime 三角色真实 Chrome 登录、身份展示、刷新、CSRF 和退出证据仍适用于这些路径；独立 32/32 Django 与 10/10 Chrome 证据覆盖本轮新增输入边界。负责人接受未在边界修改后重连业务库复测的残余风险，故不做业务库验证。 |
| CR-05 | 关闭 | 既有独立替身确认预置失败后不启动服务；本轮差异不触及此处。 |
| CR-06 | 关闭 | 既有独立复审核对拒绝矩阵分母及合法对照；本轮差异未削弱断言。 |
| CR-07 | 关闭 | 既有独立复审验证退出目标、方法及 CSRF；本轮差异不触及此处。 |
| CR-08 | 关闭 | 既有独立复审验证渲染表单和服务端旧会话删除；本轮差异不触及此处。 |
| CR-09 | 关闭 | 既有独立复审验证 runtime 预置在读取清单／事务前拒绝；本轮差异不触及此处。 |
| CR-10 | 关闭 | 既有独立复审验证原始重复 JSON 键脱敏拒绝；本轮差异不触及此处。 |
| CR-11 | 关闭 | 既有独立复审验证断言失败不泄露 Cookie／会话标识；本轮差异不触及此处。 |
| CR-12 | 关闭 | 本轮再次核对渲染登录表单上的用户名和密码错误拒绝及保留的 AC 回归。 |
| CR-13 | 关闭 | 既有独立复审核对单事务目标校验及原五条授权；本轮差异不触及此处。 |
| CR-14 | 关闭 | 既有独立复审核对三类存储角色与独立页面标签；本轮差异不触及此处。 |
| U-01 | 关闭 | 本轮确认 150 码点合法用户名未被浏览器截断，登录与预置共享 Django 默认验证；151、NFKC 扩张、外围／内部空白和非法字符按正式规则处理。 |

### AC、状态与负责人验收

本轮没有发现 AC-1～AC-7 回归或新的 Critical／High／Medium 验收问题。AC-1／AC-2 的用户名与密码边界由当前差异和既有独立输入测试直接覆盖；AC-3～AC-7 由已通过的 32/32 回归和既有运行记录承接。CR-04 的真实 runtime 证据有效性及残余风险由负责人按 D-022 明确接受。

此前正式评审中三项未编号 Medium 已由负责人按 D-022 决定延期至项目级集成／工具链节点，详见 [`deferred-work.md`](deferred-work.md)；均不阻塞本 Story。第二台 Windows 复现仍未完成，不能据此声称跨机验证通过。原评审中九项 Low 建议仍保留为非阻塞建议，没有被本次决定默认为关闭。D-022 时的结论是具备负责人最终验收条件；随后负责人于 D-023 正式批准验收，本次按 BMAD 6.12.4 Step 5 将规格状态更新为 `done`，并按负责人批准将 Sprint Story 1.1 更新为 `done`。Epic 1 仍为 `in-progress`，Story 1.2 及其他未开始 Story 保持 `backlog`。不开发 1.2、不提交或推送。

### 最终验收核对清单（D-022）

| 正式条件 | 当前证据／结论 |
| --- | --- |
| AC-1：三类预置身份可登录并显示正确身份 | D-019 真实 Windows runtime 三账号 Chrome 证据；独立回归与身份断言；本轮输入边界 10/10 Chrome 证据。 |
| AC-2：无效凭据明确拒绝且不产生认证身份 | 独立 32/32 回归及 Chrome 实际表单拒绝；用户名 150/151、Unicode/NFKC、空白/非法字符及密码 4096/4097 边界。 |
| AC-3：匿名、错误及禁用身份受限 | 已有 AC-3 自动化拒绝矩阵及 Django 全量回归；本轮无认证/权限路径改动。 |
| AC-4：身份来自服务端账号，不接受客户端角色伪造 | 已有角色/身份断言及三角色 runtime 记录；本轮无权限或身份解析代码改动。 |
| AC-5：CSRF 保护并可靠退出 | D-019 真实 Chrome 缺失/无效 CSRF 与退出、服务端会话删除记录；本轮相关路径未改。 |
| AC-6：管理与注册入口关闭，共用登录入口 | 路由 404 自动断言及三角色共用登录证据；本轮无路由改动。 |
| AC-7：批准 Windows/PostgreSQL runtime 与隔离测试可复现 | Python 3.13.17、Django 5.2.19、PostgreSQL 17.12 的既有 runtime/测试证据；本轮独立测试仅连 `test_lab_booking`，前后状态一致。第二台 Windows 留作后续集成，不虚称完成。 |
| D-015：用户模型与业务角色 | `AbstractUser`、必填单一 `role`、三种固定角色及管理标志不作为业务身份依据均保持；边界改动未修改模型或授权逻辑。 |
| D-016：Windows/PostgreSQL 环境与权限 | Python 3.13.17、Django 5.2.19、PostgreSQL 17.12／5433、库与角色隔离边界保持；独立测试仅使用 `test_lab_booking`。 |
| D-017：Sprint 与团队范围 | 当前 Story 范围与两 Sprint 安排未改变；第二台 Windows 复现和三个 Medium 事项留在项目级后续节点。 |
| D-018：批准的 Story 1.1 实施规格 | 冻结意图及正式 AC 未改变；本轮只按 D-021 完成输入边界整改及评审记录。 |
| D-019：预置账号和退出验收 | 三类既有业务账号的 runtime 登录、身份、刷新、CSRF、退出和会话删除证据仍是 CR-04 的历史运行证据；负责人接受未重跑的残余风险。 |
| D-020：独立评审整改范围 | CR-01～CR-14 最小整改边界及仅允许测试库的要求得到遵守；本轮新增 CR 处置未扩大业务范围。 |
| D-021：输入边界整改授权 | 仅核对 150/151 码点用户名及 4096/4097 码点密码边界，使用既有 Python 3.13.17 项目环境证据，不更改需求或项目环境。 |
| D-022：本轮负责人问题处置 | 仅记录 CR-04 风险接受、关闭授权、三个 Medium 延期和最终 AC 清单；未推进 Story 状态。 |
| D-023：负责人最终验收批准 | 负责人明确批准 Story 1.1 最终验收；按安装版 Build Step 5 将规格标记 `done`，并依负责人指令同步 Sprint 状态。 |
| 课程证据边界 | 第26/27/33页由需求到 AC、代码、独立测试、运行与真实状态记录追溯；第34页实验 A 的 X/Y 条件与数据未被本轮替代或改动；第36页人工决定、理由、风险、缓解及来源记入 D-022。 |

## 负责人最终验收与完成状态（2026-11-24，D-023）

负责人在本次会话正式批准 Story 1.1「使用预置账号登录并获得明确业务身份」最终验收通过，并接受 AC-1～AC-7 的已记录证据、CR-01～CR-14 与 U-01 关闭、四视角独立复审结果、32/32 Django 独立测试、10/10 Chrome 独立测试及 CR-04 的历史运行证据和残余风险。三项未编号 Medium 继续在 `deferred-work.md` 跟踪，九项 Low 继续保留为非阻塞建议，第二台 Windows 机器复现仍待后续集成验证。

按正式 Build Step 5 将本规格 `status` 更新为 `done`。依据负责人明确要求，将 `sprint-status.yaml` 中 Story 1.1 从 `review` 更新为 `done`；Epic 1 保持 `in-progress`，Epic 1 其余 Stories、Story 1.2 和其他未开始 Story 状态保持 `backlog`。仅更新状态与验收记录；未重跑测试、访问数据库、修改业务代码、正式 PRD、Architecture、epics 基线或实验 A 数据。课程第 26、27、33、34、36 页对应证据链保持可追溯；Story 1.1 测试结果不计入实验 A。 [最终独立评审及证据](../../docs/team/story-1-1-independent-review-checkpoint-2026-11-24.md) · [开发证据](story-1-1-dev-evidence.md) · [负责人决定 D-023](../../decision-log.md#d-023-2026-11-24-story-11-负责人最终验收)

#### Rejected

- **false** — 预置删除用户名验证器调用会放过非法用户名。预置调用共享 `UsernameField.clean()`，依 Django 字段清理链执行 validator；字段显式包含 `User.username_validator`，且登录和预置均有非法用户名断言。 [共享表单](../../accounts/forms.py#L10) · [预置](../../accounts/management/commands/seed_accounts.py#L31) · [回归](../../accounts/tests.py#L215)
- **false** — 非法用户名测试只覆盖预置、不覆盖登录。同一测试循环也提交渲染的登录表单，并断言字段错误、无会话及账号状态不变。 [回归](../../accounts/tests.py#L215)
- **false** — 混合 Unicode 边界夹具字符错误。夹具为 U+20000 加全角 `Ａ`；NFKC 规范化为 U+20000 加 ASCII `A`，并断言码点和 UTF-16 单元数。 [回归](../../accounts/tests.py#L196)
- **false** — 超长密码测试 patch 了错误的 `authenticate` 绑定。Django 5.2.19 `AuthenticationForm` 使用 `django.contrib.auth.forms` 模块级导入；测试 patch 此绑定，并对超限密码断言认证未调用。 [回归](../../accounts/tests.py#L243)
- **false** — 4097 密码用例未覆盖 UTF-16／补充字符边界。自动化用例是 4096 个补充字符加一个字符，共 4097 码点／8193 UTF-16 单元；独立 Chrome 证据另覆盖 BMP 与补充字符两种编码的 4096／4097 边界。 [回归](../../accounts/tests.py#L243) · [独立复审检查点](../../docs/team/story-1-1-independent-review-checkpoint-2026-11-24.md)
- **false** — 验证器硬编码在以后改变 `USERNAME_FIELD` 时可能失配。当前 `User` 继承 `AbstractUser` 且未覆盖其 `USERNAME_FIELD=username`；当前运行没有该坏结果的配置或调用路径。 [用户模型](../../accounts/models.py#L1) · [表单](../../accounts/forms.py#L8)
