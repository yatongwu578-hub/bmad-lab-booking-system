# Story 1.2 独立代码评审

日期：2026-11-25。BMAD 6.12.4 `bmad-code-review`，full 模式。团队已确认 Step 1 范围。当前进度为 Step 3 裁决完成、Step 4 等待团队选择问题处置。Story 1.2 仍为 `review`。

## 范围与需求追溯

- [Story 1.1 验收提交](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/2333c0559a948da5cbf6e91f8a6bd2c630395204)为基线。差异覆盖 21 个文件，其中 17 个未跟踪，新增 522 行、删除 4 行。原始快照 SHA-256 为 `6C23CDD97F6A0E247AD20AD73191F64C8DA22B8589B326F273033B92EBBEB369`。本文件与探针是评审产物。
- FR-016 新增及编号唯一 → ADR-003、ADR-008、PC-006、PC-014 → 正式 AC-1/2/3/6/7。FR-002 及 NFR-002 的设备新增入口 → ADR-002、PC-008、PC-011 → 正式 AC-4/5。适用 ADR-001、PC-002 的 PostgreSQL 隔离由测试入口、角色与实际目标验证。AC-6 为设备编号竞争。见[正式 PRD](../planning-artifacts/PRD.md)、[Architecture](../planning-artifacts/architecture.md)、[Project Context](../planning-artifacts/project-context.md)、[正式 Story 及 AC](../planning-artifacts/epics.md#story-12-管理员新增具体设备基础档案)及[实施规格](spec-1-2-create-equipment.md)。
- [D-024](../../decision-log.md#d-024-2026-11-25-负责人批准显式-read-committed)的连接级 `IsolationLevel.READ_COMMITTED` 位于 `lab_booking/settings.py` 的共享 OPTIONS。runtime、migration、test 仅按模式选择库和角色，使用同一配置。独立探针验证 test 新连接为 Read Committed。runtime 和 migration 的实际查询依据开发记录，遵照本轮授权边界没有重新连接业务库。

## 独立测试

原项目 .venv，Python 3.13.17、Django 5.2.19、PostgreSQL 17.12，固定 `127.0.0.1:5433/test_lab_booking`、`lab_booking_test`。`check` 无问题，`makemigrations --check --dry-run` 无变更，`test --keepdb --parallel 1 -v 2` 38/38，其中 32 项为 Story 1.1 回归、6 项为 Story 1.2。前后均 10 张表、17 条迁移、0 账号、0 会话。开发方此前的 38 项及原并发实测见[开发证据](story-1-2-dev-evidence.md)。本会话也重跑了原并发命令，结果一成功、一重复、一条记录。取证强度以独立探针观测为准。

[独立探针](story-1-2-review-transaction-probe.py)使用真实 Django 客户端取证 AC-1～5。事务场景通过 RequestFactory 调用专用新增视图，使用带管理员业务角色的测试对象，真实执行 Django 服务、psycopg 和 PostgreSQL。事务探针不会重新验证登录或 CSRF。业务库零连接，未执行迁移、权限变更或建库。探针退出码 1 表示检出实际验收偏差。

| 正式 AC | 独立验证 | 结论 |
| --- | --- | --- |
| AC-1 | 201，五项提交值与数据库重读及成功页一致，状态为可用，提交伪造停用无效。GET 表单缺少批准范围要求的只读可用状态。 | 未通过（主体写入通过） |
| AC-2 | 重复编号给出明确反馈，前后所有设备字段及记录数一致。 | 通过 |
| AC-3 | 有其他字段时，缺编号和空编号均报错且零新增。有效 CSRF 头配合空请求体时返回 200，未给编号错误，零新增。 | 未通过（空请求体边界） |
| AC-4 | `/equipment/new/`，匿名 GET/POST 均 302 到登录，学生、教师各 GET/POST 均 403。逐例无表单内容泄露，设备集合完全相同。管理员合法对照成功。预约及处理历史功能尚未实现。 | 本入口 6/6 通过 |
| AC-5 | 管理员会话，缺失和合法格式但不匹配的令牌均 403，逐次无设备写入，有效令牌返回 201。 | 通过 |
| AC-6 | 两个真实连接、不同合成档案。观察到 B 等待 A 后才释放 A 提交，A 返回 201，B 明确编号重复，最终仅持久化 A 的档案。 | 通过 |
| AC-7 | 已确认回滚及无关约束分类通过。两个断连场景都误报明确失败，其中一个实际已提交。每个场景只尝试一次新增。 | 未通过，真实取证已补齐 |

### PostgreSQL 时序记录

第二轮探针观察连接 PID 15048。AC-6 合成编号 `R12-325336899d784820bcdc`。A 后端 10792 在 INSERT 后暂停。B 后端 37156 的 `pg_blocking_pids` 返回 `[10792]`，此时观察连接看不到该记录。放行后 A 为 `201 设备已新增`，B 为 `200 该设备编号已存在。`，最终一条 A 的记录，状态 `available`。

| AC-7 注入 | 真实数据库及驱动证据 | 页面、尝试次数与持久化 |
| --- | --- | --- |
| 确定回滚 | PID 36148。真实 INSERT 后触发 PostgreSQL `23514 equipment_status_valid`，整个事务回滚。 | 503「设备新增失败」，新增 1 次、提交 0 次，独立连接 0 条。未报重复。 |
| COMMIT 前断连 | PID 33312。隔离观察连接终止探针自己的后端，随后正常驱动提交路径得到 `OperationalError`，无 SQLSTATE。注入位置在应用进入提交调用时，后端是否已收到 COMMIT 对实际分类器不可见。 | 503「设备新增失败」，新增 1 次、提交路径 1 次，独立连接 0 条。 |
| COMMIT 已生效，应用未收到结果 | PID 25356。探针用原 psycopg 连接发送真实 COMMIT。独立观察连接读到已提交记录后，探针关闭原连接，不读取 COMMIT 结果。Django 的正常提交调用得到 `OperationalError`，无 SQLSTATE。 | 503「设备新增失败」，新增 1 次、提交路径 1 次，独立连接 1 条 `R12-1e3447cd87ae45ca9cdf`。 |

提交后场景在驱动边界控制消息发送和断连。该方法验证了真实持久化及应用未获得提交确认的组合，无需额外网络代理或数据库权限。它没有测量网络设备级丢包。最终删除了两条仅属于本轮探针的合成记录，确认零残留。HTTP 夹具通过外层测试事务回滚。

## Step 3 裁决

四个视角均交回结果。第四个代理初次启动触及会话并发上限，首个代理完成后启动成功。下表按各视角报告顺序分配全局编号，逐条裁决后再按共同成因分组。B 为 Blind Hunter，E 为 Edge Case Hunter，V 为 Verification Gap Reviewer，A 为 Acceptance Auditor。

| 编号 | 来源 | 裁决 | 证据及归并 |
| --- | --- | --- | --- |
| 1 | B | high | 无 SQLSTATE 的真实断连落入明确失败分支。R1 |
| 2 | B | medium | 普通 `atomic()` 嵌套仅释放保存点，违反规格最外层边界。R5 |
| 3 | B | medium | 独立有效 CSRF 空 POST 无字段错误。R3 |
| 4 | B | medium | 模板和独立 GET 均缺只读状态。R2 |
| 5 | B | medium | 命令用固定延时，信号在 B 进入服务前。R6 |
| 6 | B | medium | 固定编号及清理条件无运行归属。R7 |
| 7 | B | medium | 先断言 302/403，再在 200 分支检查，POST 未查正文。R8 |
| 8 | B | medium | 现有套件缺错配令牌和逐拒绝写入断言。R10 |
| 9 | B | medium | mock 直接提供业务分类，不执行真实数据库分支。R1 |
| 10 | E | medium | 空请求体的 QueryDict 为假值，表单未绑定。R3 |
| 11 | E | medium | Django ModelForm 在 `is_valid()` 查询唯一约束，位置在异常处理外。R4 |
| 12 | E | high | 提交后真实持久化与失败提示并存。R1 |
| 13 | E | medium | 同一 SQLSTATE 白名单覆盖 INSERT 及提交，分类不区分阶段。R1 |
| 14 | E | medium | 模块服务在已有事务调用时可提前返回。R5 |
| 15 | E | medium | GET 未显示可用。R2 |
| 16 | E | medium | A 放行依赖延时，B 未必发出 INSERT。R6 |
| 17 | E | medium | 等待 Future 超时后退出 executor 仍会等待 worker。R9 |
| 18 | E | medium | 两次固定夹具预检均可能放行。R7 |
| 19 | E | medium | 命令在 finally 清理前输出通过，且未断言零残留。R7 |
| 20 | E | medium | 403/302 仍可附正文，旧用例未断言。R8 |
| 21 | E | medium | 无错配令牌测试及逐步无写入验证。R10 |
| 22 | E | medium | ModelForm 顺序预查可绕过 SQLSTATE 分类。R4 |
| 23 | E | medium | mock 无法检测实际分类错误。R1 |
| 24 | E | medium | 清理过滤不含主键或运行专属标记。R7 |
| 25 | V | medium | 两个最终结果相同仍可能由串行执行生成，独立探针已补锁等待证据。R6 |
| 26 | V | medium | 原用例没有真实回滚、提交未知、无重试及其他约束取证。R1 |
| 27 | V | medium | 原测试未检查任何拒绝正文，独立探针补齐六例。R8 |
| 28 | V | medium | 原测试缺无效凭据与逐步无写入，独立探针补齐。R10 |
| 29 | V | medium | 原测试只把页面和库值对照，独立探针补逐字段与输入对照。R11 |
| 30 | V | medium | 空 POST 独立复现。R3 |
| 31 | V | medium | 表单渲染缺状态，批准范围明确。R2 |
| 32 | V | high | 白名单挡不住无 SQLSTATE 的 COMMIT 断连，独立探针已复现。R1 |
| 33 | A | high | 断连后失败页建议重试，已持久化时会误导。R1 |
| 34 | A | medium | 最外层事务契约未落实，目前 HTTP 入口没有请求级事务。R5 |
| 35 | A | medium | 开发快照的 AC-7 测试未覆盖故障时序，独立探针已补。R1 |
| 36 | A | medium | 预查异常可逃逸，顺序重复测试并未单独验证数据库分类。R4 |
| 37 | A | medium | 并发命令 A 绕过服务，候选字段相同，且未确认 B 等锁。R6 |
| 38 | A | medium | 原命令共享测试标识，清理归属不足。R7 |
| 39 | A | medium | 空提交产生未绑定表单。R3 |
| 40 | A | medium | 缺只读状态。原测试未与提交值逐字段比较。R2、R11 |
| 41 | A | medium | 旧测试授权正文断言不可达，独立探针补齐。R8 |
| 42 | A | medium | 旧套件缺错配令牌与拒绝后即时断言。R10 |

| 分组 | 严重程度／BMAD 路由 | 建议处置 |
| --- | --- | --- |
| R1 提交阶段异常分类及真实回归 | High / patch | **验收阻塞。** 修复 `equipment/services.py:33–50`。依据写入与提交阶段、数据库明确结果及连接异常判别，未知只提示待核查且无自动重试。保留指定编号唯一冲突映射，重跑独立故障探针。 |
| R2 新增表单只读状态 | Medium / patch | **验收阻塞。** 在 `equipment/templates/equipment/create_form.html:7` 展示默认「可用」，保持服务端设定。 |
| R3 空 POST 未绑定 | Medium / patch | **验收阻塞。** `equipment/views.py:28` 按请求方法绑定表单，空请求须显示编号错误。 |
| R4 表单在事务外查询唯一约束 | Medium / patch | 并入 AC-7 最小整改。确认所有新增入口的数据库异常都得到受控反馈。真实编号冲突已在 AC-6 走到服务分类，顺序重复路径语义保留。 |
| R5 服务未强制最外层事务 | Medium / patch | 补齐实施规格的事务契约，一并验证正常入口及嵌套调用。此项是服务边界缺口。 |
| R6 原命令无法证明真实竞争 | Medium / patch | AC-6 已有独立绿灯证据。可延期加固原命令，保留本轮可复跑探针。 |
| R7 原命令固定夹具及清理 | Medium / patch | 测试工具建议。并行运行前，增加运行专属夹具、归属校验及清理后断言。 |
| R8 权限测试无拒绝正文断言 | Medium / patch | 独立探针已补逐例正文、重定向目标及设备前后对照。常规套件加固可延期。 |
| R9 原命令超时不能保证退出 | Medium / patch | 测试工具建议。通过受控数据库超时限制 worker 等待，可延期。 |
| R10 CSRF 测试缺错配令牌及逐次验库 | Medium / patch | 独立探针已有两种拒绝及合法对照。常规套件加固可延期。 |
| R11 成功用例未对照提交字段 | Medium / patch | 独立探针已逐项对照提交值、重读记录和页面。常规套件加固可延期。 |

## 课程证据与待团队决定

按[课程基线](../../docs/course-requirements.md)和[第 27 页团队记录](../../docs/team/sprint-planning-review.md#l47)核对。第 26 页对应 FR/ADR/Story/Test 追溯，第 27 页对应独立开发、独立评审、真实测试和状态，第 33 页对应源码、测试与证据入库，第 34 页实验 A 沿 Sprint 计划另行开展，第 36 页保留实际人工处置。仓库未发现 PPT 原件，页码依据上述记录。已完成的 Step 1 范围确认只授权继续评审。Step 4 的问题处置，及后续负责人验收，仍需团队实际确认。当前不具备负责人验收条件。Story 1.1 维持 `done`，Story 1.2 维持 `review`，Story 1.3 维持 `backlog`。
