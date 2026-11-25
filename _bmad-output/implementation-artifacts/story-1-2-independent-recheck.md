# Story 1.2 整改后独立复审

2026-11-25，BMAD 6.12.4 full 模式，针对 D-025 的 R1～R5。团队已确认 Step 1。首轮独立评审快照到整改后工作树的差异为 7 个文件、+472/−30，SHA-256 为 `326137790c3c18192c5f76266231687d744400ef4760cdd9aedf91ff18d22db5`。四个独立视角均返回结果。前三个并行启动，第四个在释放代理槽位后启动。 [正式 AC](../planning-artifacts/epics.md#story-12-管理员新增具体设备基础档案) · [D-025](../../decision-log.md#d-025-2026-11-25-负责人批准-story-12-独立评审处置) · [首轮独立证据](story-1-2-independent-review.md) · [开发整改证据](story-1-2-dev-evidence.md#整改后实测)

## 复审结论

| 原编号 | 独立核对 | 建议 |
| --- | --- | --- |
| R1 | 真实约束拒绝、COMMIT 前断连、真实 COMMIT 后丢确认及具名编号冲突的分类正确，两次未知均只提示核查。 | 可关闭 |
| R2 | GET 只读展示「可用」。伪造停用随表单提交后，独立连接仍只读到可用。 | 可关闭 |
| R3 | 空 POST、缺失、空值、空白、超长及 NUL 均有编号字段错误，零新增。 | 可关闭 |
| R4 | 表单合法校验不查库，顺序和并发重号均由具名数据库约束裁决。 | 可关闭 |
| R5 | 普通外层原子块及手动事务拒绝。正常路径使用真实最外层提交，独立连接读回。标记回滚或提前关闭连接时零提交。 | 可关闭 |

未发现新增验收阻塞。R6～R11 均按 D-025 延期。复审建议进入单独批准的业务库迁移和运行验证，实际业务库运行证据及负责人最终验收仍待取得。规格仍为 `in-review`，Sprint 仍为 `review`，Story 1.3 为 `backlog`。

## 独立运行证据

原项目 `.venv`，Python 3.13.17、Django 5.2.19、PostgreSQL 17.12。全部运行限定在 `127.0.0.1:5433/test_lab_booking`，有效角色及会话角色为 `lab_booking_test`，Read Committed。使用进程内临时 Django 密钥及已有受保护的密码文件。默认沙箱不能执行原解释器，范围内命令获批后以原解释器运行。

| 实际命令 | 结果 |
| --- | --- |
| `.\.venv\Scripts\python.exe manage.py test --keepdb --parallel 1 -v 2` | 45/45，14.995 秒，Story 1.1 为 32/32。前后均为 10 张表、17 条迁移、0 账号、0 会话。 |
| `.\.venv\Scripts\python.exe _bmad-output/implementation-artifacts/story-1-2-remediation-transaction-probe.py` | 退出码 0。HTTP 合成设备、会话和账号清理后均为零。真实事务探针清理两条持久化合成设备，最终零残留。 |
| `.\.venv\Scripts\python.exe -`，复用探针入口补验 `set_rollback(True)` 与 `actor.close()` | 首次命令的中文比较受 PowerShell 管道编码影响，退出 1。改用 ASCII Unicode 转义重新执行后退出 0。观察连接 32924，两个应用连接 26316、36928 均返回 503「设备新增失败」，各写入尝试 1 次、COMMIT 0 次、持久化 0 条。 |

| 正式 AC | 独立结果 |
| --- | --- |
| AC-1 | 通过。表单只读「可用」，伪造 `disabled` 仍返回 201，PID 30888 从独立连接读回 `H-00b08e99fbc148a5994d`，五项资料与提交及成功页一致，状态 `available`。 |
| AC-2 | 通过。顺序重号明确提示重复，原行所有字段及数量相同。 |
| AC-3 | 通过。有效 CSRF 的六类无效请求均返回 200 并显示编号字段错误，逐次比较设备快照均无新增。 |
| AC-4 | 通过。匿名 GET/POST 各 302 至登录，学生及教师各 GET/POST 均 403，合计 6/6 无新增页内容泄露且设备快照无变化。管理员合法对照成功。本 Story 没有预约或处理历史入口。 |
| AC-5 | 通过。缺失及错配 CSRF 均 403，逐次零新增。有效令牌返回 201。 |
| AC-6 | 通过。观察连接 PID 18176，A=14280 已插入未提交，B=25520 经 `pg_blocking_pids` 确认等待 A。放行后 A 返回 201，B 返回 200 并明确报重，各尝试一次。仅持久化 A 的 `R12-575e21ec4bce44c2997a`，资料与状态一致。 |
| AC-7 | 通过。真实写入回滚、两类断连和具名冲突的结果见下表。全套还校验未知页面不出现成功、明确失败或重试提示。 |

| AC-7 场景 | PostgreSQL 及驱动证据 | 独立观察 |
| --- | --- | --- |
| 真实约束错误 | PID 32052，INSERT 后触发 `23514 equipment_status_valid`。 | 503「设备新增失败」，写入／COMMIT 尝试 1／0，持久化 0。 |
| COMMIT 前断连 | PID 29872，观察连接终止对应后端，psycopg 报无 SQLSTATE 的 `OperationalError`。 | 503「提交结果待核查」，写入／COMMIT 路径 1／1，持久化 0。 |
| 真实 COMMIT 后丢确认 | PID 33268，发送真实 COMMIT，观察连接读到已持久化记录后关闭原连接，应用未读取确认。驱动报无 SQLSTATE 的 `OperationalError`。 | 503「提交结果待核查」，写入／COMMIT 路径 1／1，唯一记录 `R12-5f6a4186a07f450cb71a`，资料及 `available` 状态符合输入。 |

事务探针通过 RequestFactory 调用真实视图和服务，权限／CSRF 在单独的 Django 客户端用例验证。断连在驱动边界受控触发。

## 四视角裁决

| 编号 | 视角 | 裁决与证据 |
| --- | --- | --- |
| F1 | Blind Hunter | false（当前入口）。Django 退出还会恢复 autocommit，当前无 psycopg pipeline 或 on_commit 回调。成功后驱动处于 IDLE，恢复只是本地状态设置，未发现能使本入口将已获确认的 COMMIT 改报未知的路径。 |
| F2 | Blind Hunter | false（当前入口）。吞掉游标错误后给出 ROLLBACK 标签的情形需要在 INSERT 后有吞错回调，当前设备创建无此回调或应用内额外 SQL。 |
| F3 | Blind Hunter | low，补证完成。原套件未直接使标志为真，独立补验两个分支均返回明确失败，零次提交。 |
| F4 | Blind Hunter | low，沿用首轮探针的取证边界。原回滚场景记录而未硬断言诊断，在本次输出中已逐项核对 `23514 equipment_status_valid`。记录为工具改进，不阻塞。 |
| F5 | Blind Hunter | low，沿用首轮探针的取证边界。丢确认场景自动断言行数并输出完整行，本次逐项核对了独立回读字段和状态。记录为工具改进，不阻塞。 |
| F6 | Blind Hunter | low，驳回本轮改动。测试按串行、专用隔离库运行，整表比较用于证明未授权请求不改变已有设备。没有证据显示本次发生其他写入，改成仅检查夹具会降低 AC-4 的断言范围。 |
| F7 | Edge Case Hunter | low，驳回本轮改动。独立复测使用未开启优化的普通 Python 3.13.17，已实际观测到被注入的错误与状态计数。优化模式运行不在本次执行方式内。 |
| F8 | Edge Case Hunter | medium，沿用 D-025 R9。若独立第三方连接长时间占锁，Python 的 Future 超时无法约束服务器等待。本轮在专用隔离库顺序执行，正常退出并清理。 |
| F9 | Verification Gap Reviewer | low，补证完成。原探针未触发写入后主动标记回滚，独立补验在真实 PostgreSQL 完成，一次写入尝试、零提交、零持久化。 |
| F10 | Acceptance Auditor | maybe-false（若证实为 Medium），后续条件核查。当前没有延期约束或提交回调可触发审查提出的其他「明确拒绝但归未知」SQLSTATE。当前已知真实约束错误与未知断连均分类正确。新增延期约束、提交回调或复现新的明确 COMMIT 拒绝后，按真实服务端响应补验证。 |

## 业务库迁移及运行验证草案

本轮零业务库连接，下列内容等待负责人批准。其前提是以本次复审的工作树为待部署版本，核对备份和恢复路径，在受控窗口暂停业务写入。任一目标、角色、DDL 或迁移计划不符即停止。

1. **迁移前核对。** 使用现有迁移角色 `lab_booking_migrator`，复核实际库 `lab_booking`、`127.0.0.1:5433`、版本 17.12、登录角色与当前角色。使用原 `.venv`、`LAB_BOOKING_DB_MODE=migration`，依次运行 `manage.py check`、`manage.py makemigrations --check --dry-run`、`manage.py migrate --plan`、`manage.py sqlmigrate equipment 0001`。核对待执行范围仅为 `equipment.0001_initial`，另核对 Django 迁移框架正常登记迁移及 post-migrate 元数据，确认对象归属、编号唯一约束、状态 CHECK 和 `id` 的 identity 定义。 [迁移文件](../../equipment/migrations/0001_initial.py) · [既有运行手册](../../README.md)
2. **获准后执行。** 用迁移角色运行 `manage.py migrate equipment 0001`，再核对迁移记录、待执行计划、约束和表所有者。失败或目标不符时暂停启用，保留错误。若已有业务档案，回退不自动反向删除设备表，按负责人批准的恢复方案处理。
3. **最小授权候选。** 保留既有 `public` schema USAGE 和 Story 1.1 权限。对象所有者在一次受保护事务内校验库、地址、版本、角色和对象身份后，仅向 `lab_booking_app` 增加 `GRANT INSERT (number, name, category, location, description, status), SELECT (id) ON TABLE public.equipment_equipment TO lab_booking_app;`。当前 Django 写入使用 `INSERT ... RETURNING id`，成功页从已保存对象展示，无设备全表读权限需求。确认实际 DDL 为 PostgreSQL identity，隐式生成无需单独序列授权。通过实际 ACL、默认权限与继承关系检查有效权限，保持既有测试角色和跨库隔离。 [PostgreSQL INSERT 权限](https://www.postgresql.org/docs/17/sql-insert.html) · [PostgreSQL identity 定义](https://www.postgresql.org/docs/17/ddl-identity-columns.html) · [PostgreSQL 17 隐式序列实现](https://raw.githubusercontent.com/postgres/postgres/REL_17_STABLE/src/backend/executor/execExprInterp.c)
4. **运行验证。** 用 `LAB_BOOKING_DB_MODE=runtime` 和现有 `lab_booking_app` 以本机监听启动。复核实际连接及 Read Committed。用三类已批准预置账号检查登录、身份、退出与新增页权限。以管理员录入负责人预先批准、应实际保留的一件设备，核对 201、编号、五字段和可用状态，获准的独立只读观察连接复核仅一条记录。用同号不同资料确认明确重复且原行无改动。保留响应、计数、对象权限与迁移证据，业务库保持正常运行，故障注入和并发压力归隔离库。正式负责人验收以运行证据及本轮独立复审共同支撑。

PPT 第 26、27、33、34、36 页按[课程基线](../../docs/course-requirements.md)与[团队记录](../../docs/team/sprint-planning-review.md#l47)核对。留 FR-016／FR-002 → ADR-002／003／008 → AC → Test、开发与评审区分、真实状态、测试和 D-025 人工选择。实验 A 保持原计划。三位组员共同操作与审阅，未分派个人任务。
