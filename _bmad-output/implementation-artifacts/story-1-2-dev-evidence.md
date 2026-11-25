# Story 1.2 开发与自测证据

## 执行范围

2026-11-25，按已批准的 [实施规格](spec-1-2-create-equipment.md) 开发 Story 1.2。复用 Story 1.1 的账号、Django 会话认证、角色、CSRF、PostgreSQL 连接守卫及隔离测试运行器。本轮未实现设备列表、详情、编辑、状态转换或预约。

## 实际变更

- 新增设备模型、初始迁移、服务端表单、业务服务、管理员专用 GET/POST 页面及成功/异常结果页。
- 数据库具名唯一约束 `equipment_number_unique` 处理编号竞争；仅匹配 PostgreSQL 唯一约束 SQLSTATE、表和约束名时转为重复提示。创建成功后读取已保存对象展示，状态固定为可用。
- Django 的 PostgreSQL OPTIONS 显式设置 psycopg `IsolationLevel.READ_COMMITTED`，供 runtime、migration、test 三种模式共用。未执行 PostgreSQL 服务器、数据库或角色配置变更。
- 保留原回滚式测试运行器，增加仅允许已迁移 `test_lab_booking` 的真实连接事务验证命令，使用预检唯一编号并在 `finally` 按精确合成值清理。

## 自测结果

使用项目虚拟环境 Python 3.13.17、Django 5.2.19。

| 检查 | 实际结果 |
|---|---|
| `manage.py check` | 0 项问题 |
| `makemigrations --check --dry-run` | 无模型差异 |
| `migrate --plan` 后的测试库迁移 | 仅应用 `equipment.0001_initial` 到 `test_lab_booking` |
| `manage.py test --keepdb --parallel 1 -v 1` | 38 项通过，失败／错误／跳过均为 0 |
| 测试运行器前后状态 | 10 张表、17 条迁移；0 个账号、0 条会话 |
| AC-6 `manage.py verify_equipment_transactions` | 两个独立连接在真实 PostgreSQL 执行同号插入，一成功、一明确重复，最终一条合成设备；清理后测试库不留该编号 |
| 显式隔离级别实测 | runtime=`lab_booking/lab_booking_app`、migration=`lab_booking/lab_booking_migrator`、test=`test_lab_booking/lab_booking_test`，均为 PostgreSQL 17.12／127.0.0.1:5433；各新连接 `SHOW transaction_isolation` 均为 `read committed` |

自动化用例覆盖管理员合法新增及状态伪造、重复不覆盖、编号缺失／空白、匿名／学生／教师 GET 与 POST 拒绝、缺失及有效 CSRF、数据库失败不得伪装成编号重复。独立并发命令仅使用合成值并确认最终状态。

AC-7 的数据库提交阶段真实连接中断注入与“提交已持久化但响应丢失”分支尚未在 PostgreSQL 中完成，不能把模板提示视为已验证该故障时序。开发自测未访问业务库迁移或写入，未申请运行角色 GRANT。此项证据缺口交独立评审和团队验收前处置，Story 当前进入 review 供团队检查。

## 流程状态

开发自测后 Story 1.2 和规格进入 `review`，Story 1.1 保持 `done`，Story 1.3 保持 `backlog`。本会话未进行独立 Code Review，未标记 `done`，未提交或推送 Git。

## 2026-11-25 D-025 整改增量

| 整改项 | 实现与验证方法 |
| --- | --- |
| R1 | 服务区分提交前与提交退出阶段。提交阶段缺少可靠结果时返回 503 待核查。真实约束拒绝归入失败，只有 PostgreSQL 23505 且表和具名编号约束同时匹配时才提示重号。应用只执行一次写入尝试。 |
| R2 | 新增表单只读展示初始状态「可用」，状态由服务写入。经真实 HTTP 提交后，通过独立数据库连接读回五个字段和初始状态。 |
| R3 | 所有 POST 都绑定表单。回归和探针使用有效 CSRF 覆盖空请求体、缺字段、空字符串、空白、超长和 NUL，逐例核对编号字段错误及零写入。 |
| R4 | 表单复用模型字段生成的校验器，移除 ModelForm 的约束预查。回归测试断言合法表单校验执行零条 SQL，并验证去首尾空白和保留大小写。顺序重号和真实并发重号由数据库唯一约束验证。 |
| R5 | durable 原子块拒绝普通嵌套，服务显式拒绝已关闭自动提交的手动事务。Django TestCase 允许其专用回滚包装，真实提交以隔离探针及独立连接读回为证。 |

[整改探针](story-1-2-remediation-transaction-probe.py)在独立首轮探针基础上把 HTTP 成功路径移出外层事务，使用随机隔离夹具和精确清理，并保留 PostgreSQL 锁等待及 COMMIT 前后断连测试。首轮探针和原失败证据继续可追溯。 [首轮探针](story-1-2-review-transaction-probe.py) · [首轮独立评审](story-1-2-independent-review.md)

### 整改后实测

使用项目 `.venv` 的 Python 3.13.17、Django 5.2.19 与 test 模式。探针核对 PostgreSQL 17.12、`127.0.0.1:5433/test_lab_booking`、会话及实际角色 `lab_booking_test` 和 Read Committed。整批命令退出码为 0。

| 检查 | 本次结果 |
| --- | --- |
| `manage.py check` | 0 项问题 |
| `manage.py makemigrations --check --dry-run` | 无模型差异 |
| `manage.py test --keepdb --parallel 1 -v 2` | 45/45 通过，14.253 秒。Story 1.1 回归 32/32、设备用例 13/13。数据库测试前后均为 10 张表、17 条迁移、0 个账号和 0 条会话。 |
| `manage.py verify_equipment_transactions` | 原并发命令通过，用于回归。实际锁等待由适配探针单独观测。 |
| `.\.venv\Scripts\python.exe _bmad-output/implementation-artifacts/story-1-2-remediation-transaction-probe.py` | 退出码 0。完成下表的 HTTP、锁等待及真实数据库断连验证。 |
| 整改探针 R5 | 真实连接关闭自动提交后调用服务，操作被拒绝，零条新增。常规回归另覆盖普通嵌套原子块。 |

| 验收 | 应用响应与数据库观察 |
| --- | --- |
| AC-1 | 表单显示只读可用状态。提交伪造停用状态仍返回 201。HTTP 独立读回连接 PID 36252 找到 `H-b0eaa68a4f6e45c9bb32`，五项字段与提交及成功页一致，状态为 `available`。 |
| AC-2 | 顺序同号返回 200 并明确报重。原记录整行未变化。 |
| AC-3 | 有效 CSRF 下，空请求体、缺字段、空字符串、空白、超长和 NUL 均返回 200，显示编号字段错误，零条新增。 |
| AC-4 | 匿名 GET/POST 均返回 302 跳转登录。学生和教师 GET/POST 均返回 403。六例均未泄露新增页受限内容，设备快照保持一致。Story 1.2 尚无预约或处理历史模型。 |
| AC-5 | 缺失和错配令牌均返回 403，分别核对零新增。有效令牌对照返回 201。HTTP 结束后合成设备、会话、用户均零残留。 |
| AC-6 | 观察连接 PID 4088，A 为 17088，B 为 31452。A 插入未提交时，`pg_blocking_pids(31452)` 返回 `[17088]`，观察连接此时读到零条。放行 A 后，A 返回 201，B 返回 200 并明确报重，各尝试插入一次。独立读回仅有 A 的 `R12-364e7fa3b1584db8aa8c`，五项字段和状态均匹配。 |
| AC-7 真实写入回滚 | 连接 PID 5236 在插入后触发 PostgreSQL 23514（`equipment_status_valid`），返回 503「设备新增失败」。插入尝试 1 次、提交尝试 0 次，独立读回零条。 |
| AC-7 COMMIT 前断连 | 连接 PID 27712 在 COMMIT 前被终止。驱动报无 SQLSTATE 的 OperationalError，返回 503「提交结果待核查」。插入和提交各尝试 1 次，独立读回零条。 |
| AC-7 真实 COMMIT 后丢确认 | 连接 PID 24772 发送真实 COMMIT，独立连接读回记录后模拟应用丢失确认。驱动报无 SQLSTATE 的 OperationalError，返回 503「提交结果待核查」。插入和提交各尝试 1 次，独立读回一条 `R12-7478262d98f34ab18b06`。 |

事务探针清理两条已持久化的合成设备，并核对零残留。针对这两类待核查结果，常规回归另断言页面不显示成功、失败或重试提示。整改验证只访问隔离测试库。本记录供独立复评和负责人验收。 [负责人原处置](story-1-2-review-disposition.md) · [课程基线](../../docs/course-requirements.md)
