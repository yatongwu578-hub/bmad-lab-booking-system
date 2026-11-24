# Story 1.1 开发证据

[实现规格](spec-1-1-preset-account-login.md) · [正式 Story 1.1](../planning-artifacts/epics.md#story-11-使用预置账号登录并获得明确业务身份) · [课程要求](../../docs/course-requirements.md)

## 首迁前实测

| 实际用途 | 认证角色 | 数据库 | 服务器 | 会话时区 | `public` 表数 |
| --- | --- | --- | --- | --- | --- |
| 业务迁移计划 | `lab_booking_migrator` | `lab_booking` | `127.0.0.1:5433`，17.12 | UTC | 0 |
| 隔离测试迁移计划 | `lab_booking_test` | `test_lab_booking` | `127.0.0.1:5433`，17.12 | UTC | 0 |

两次连接使用 Windows 本机 `psql -X -w`，查询 `current_database()`、`current_user`、`inet_server_addr()`、`inet_server_port()`、`current_setting('server_version')`、`current_setting('TimeZone')` 和 `pg_tables`。凭据通过已受保护的本机 `PGPASSFILE` 提供。此前环境准备记录包含三个角色的独立连接和服务端跨库拒绝结果。 [实际环境与版本](../../docs/team/sprint-1-environment-preparation.md#r-03-批准后执行记录)

项目 `.venv` 中，`manage.py check`（迁移和测试模式）均返回 `0 silenced`，`makemigrations --check --dry-run` 返回 `No changes detected`。在迁移模式和隔离测试模式分别执行 `manage.py migrate --plan`，均得到以下 16 项，顺序一致。

```text
contenttypes.0001_initial
contenttypes.0002_remove_content_type_name
auth.0001_initial
auth.0002_alter_permission_name_max_length
auth.0003_alter_user_email_max_length
auth.0004_alter_user_username_opts
auth.0005_alter_user_last_login_null
auth.0006_require_contenttypes_0002
auth.0007_alter_validators_add_error_messages
auth.0008_alter_user_username_max_length
auth.0009_alter_user_last_name_max_length
auth.0010_alter_group_name_max_length
auth.0011_update_proxy_permissions
auth.0012_alter_user_first_name_max_length
accounts.0001_initial
sessions.0001_initial
```

`manage.py sqlmigrate auth 0001` 的默认 `User` 操作为 `(no-op)`。`manage.py sqlmigrate accounts 0001` 的 SQL 创建 `accounts_user`，`role` 为 `varchar(7) NOT NULL`，约束 `accounts_user_valid_role` 仅允许 `student`、`teacher`、`admin`。账号模型依赖 `auth.0012_alter_user_first_name_max_length`。按计划预计有九张 Django 表，实库写入及表清单复查等待负责人批准。

| 检查 | 实际结果 |
| --- | --- |
| 缺少数据库模式 | `manage.py check` 失败，指出 `LAB_BOOKING_DB_MODE` 缺失 |
| 缺少密码文件配置 | `manage.py check` 失败，指出 `PGPASSFILE` 缺失 |
| 测试发现 | 直接调用 `unittest` 未初始化 Django，导入失败。改为 `django.setup()` 后发现 13 个测试方法，尚未运行数据库测试 |
| 工作区检查 | `git diff --check` 成功，Git 提示 Windows 行尾转换 |

### 实施会话复核

用项目 `.venv/Scripts/python.exe` 重新执行 `manage.py check` 和 `manage.py makemigrations --check --dry-run`，分别得到 `System check identified no issues (0 silenced).` 和 `No changes detected`。`manage.py shell -c` 读取到 `accounts.User`、`login/` 与 `identity/` 两个路由，以及 `django.db.backends.postgresql`。

用 `psql -X -w -h 127.0.0.1 -p 5433 -U <角色> -d <获授权库> -v ON_ERROR_STOP=1 -c <只读查询>` 分别认证连接三次。只读查询使用 `has_database_privilege(current_user, <库名>, 'CONNECT')` 和 `has_schema_privilege(current_user, 'public', 'CREATE')`。实际结果如下，各连接均为 PostgreSQL 17.12。

| 当前身份 | 实际连接库 | 业务库 CONNECT | 测试库 CONNECT | 当前库 public CREATE | 当前库 public 表数 |
| --- | --- | --- | --- | --- | --- |
| `lab_booking_migrator` | `lab_booking` | 是 | 否 | 是 | 0 |
| `lab_booking_app` | `lab_booking` | 是 | 否 | 否 | 0 |
| `lab_booking_test` | `test_lab_booking` | 否 | 是 | 是 | 0 |

以上是迁移前实际连接和权限目录结果。首次迁移、运行授权和测试库写入计划已展示，实际执行待确认。

## FR、ADR 和验收用例

FR-001／FR-002 对应 ADR-001（运行形态）、ADR-002（Django 会话和角色）及 ADR-008（真实隔离测试）。[正式 PRD](../planning-artifacts/PRD.md) · [架构](../planning-artifacts/architecture.md)

| 验收 | T-03 实际路由及配对 | 断言位置与阶段 |
| --- | --- | --- |
| AC-1 | 三种角色均 `POST /login/`，随后 `GET /identity/` 和刷新 | `AccountLoginTests.test_ac1_preset_roles_log_in_and_refresh` 检查本人账号、角色、认证会话及 `last_login`。待运行 |
| AC-2 | 同一路由的未知账号、错误密码、缺用户名或缺密码分别与 AC-1 配对，再直接 `GET /identity/` | `test_ac2_unknown_wrong_and_missing_credentials_are_denied` 检查表单错误、无认证 Cookie、身份页拒绝和账号表前后相同。待运行 |
| AC-3 | 匿名、无效会话或禁用账号 `GET /identity/` 与有效会话 `GET /identity/` 配对 | `test_ac3_anonymous_and_invalid_session_are_redirected` 和 `test_identity_rejects_disabled_accounts_and_invalid_roles` 检查重定向、无受限内容、账号表前后相同及无效角色拒绝。待运行 |
| AC-4 | 学生提交伪造角色、他人 ID 至 `/login/` 并访问同参数 `/identity/`，与普通学生本人登录配对 | `test_ac4_server_role_ignores_forged_values_and_management_flags` 核对业务角色及身份、他人 `last_login` 和角色。`test_identity_rejects_post_without_account_changes` 核对身份页写请求拒绝。待运行 |
| AC-5 | `/login/` 同一合法凭据配对有效、缺失和无效 CSRF 令牌 | `test_ac5_csrf_valid_token_authenticates` 和 `test_ac5_missing_and_invalid_csrf_tokens_are_denied` 检查合法会话，失败 403、无泄露、无会话及账号表变化。待运行 |
| AC-6 | `/admin/`、`/register/`、`/accounts/register/` 与共有 `/login/` 配对 | `test_ac6_admin_and_self_registration_routes_are_absent` 检查 URL 无匹配、404、无受限内容和账号数据不变。待运行 |
| AC-7 | Windows、PostgreSQL 17.12、实际迁移、预置、运行账号启动及浏览器访问以上路由 | 首迁前连接、计划、配置错误已核对。业务迁移和测试库写入待批，按规格在迁移后另行确认真实预置清单 |

`AccountStorageTests` 覆盖 PostgreSQL 拒绝省略／空值／空串／非法角色、首次预置及哈希、同角色重跑保留已有字段和权限、同名异角色整批回滚、规范化后重复或非法条目整批拒绝。PC-011 的未授权通过数、分母及合法对照将在实际执行后填写。当前程序只定义账号及认证相关表，未产生预约、设备、占用或历史数据的测试结论。

## 2026-11-22 首迁与开发自测

本轮从 [首迁前开发检查点](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083) 继续。开工时本地 `HEAD`、`origin/main` 同为 `dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083`，工作区干净。负责人在本次会话批准仅使用 PostgreSQL 17.12 的 `127.0.0.1:5433` 上两个项目库。执行环境为 Windows 11 Pro 64 位（10.0.26200）、Python 3.13.17、Django 5.2.19。

`.venv/Scripts/python.exe -m pip list --format=freeze` 核对 asgiref 3.13.0、psycopg／psycopg-binary 3.3.9、sqlparse 0.6.1、tzdata 2026.6，与固定依赖一致。对开发基线至当前工作区的 Git 差异检查凭据文件路径、常见密钥模式和 Python 字面值配置，未发现候选项。`git diff --check` 通过，仅有本机 Git 行尾转换提示。

### 实库迁移与 D-016 权限

1. 以 `psql -X -w -h 127.0.0.1 -p 5433 -U <角色> -d <批准库> -v ON_ERROR_STOP=1 -c <查询>` 连接三次。以只读事务核对主机、端口、17.12、UTC、两库 CONNECT、public USAGE／CREATE 和非系统关系对象。两个库当时均无关系对象，三角色的 SUPERUSER、CREATEDB、CREATEROLE、REPLICATION、BYPASSRLS 均为否。迁移账号拥有业务库和 schema 创建权限，测试角色在测试库拥有对应权限，运行角色仅可连接业务库且无 schema 创建权限。
2. 在迁移和测试模式都运行 `manage.py check`、`makemigrations --check --dry-run`、`migrate --plan`，通过且两库的 16 项顺序与首迁前记录匹配。`manage.py shell -c` 确认 `accounts.User → accounts_user`。`sqlmigrate accounts 0001` 确认角色字段及约束，`sqlmigrate auth 0001` 确认默认 User 操作为 no-op。
3. 写入前在同一 Django 连接中再次断言实际库、角色、地址、端口、版本、schema 权限、空库及 16 项正向计划，并由 `call_command('migrate', interactive=False)` 以 `lab_booking_migrator` 执行。16 项均为 `OK`，复查计划为 `No planned migration operations.`
4. `pg_tables` 确认 9 张表均为迁移角色所有。清单为 `accounts_user`、`accounts_user_groups`、`accounts_user_user_permissions`、`auth_group`、`auth_group_permissions`、`auth_permission`、`django_content_type`、`django_migrations`、`django_session`。迁移记录计数为 accounts 1、auth 12、contenttypes 2、sessions 1，accounts 和 sessions 的记录均为 `0001_initial`。角色列是 `varchar(7) NOT NULL`，无默认值。`accounts_user_valid_role` 已验证且只接受 student、teacher、admin。迁移后业务账号和会话均为 0。
5. 确认业务库、所有者、17.12、5433、9 张表和 16 条记录后，在单事务执行 README 的 5 条 `GRANT`。以运行账号查询 ACL，确认 public 仅 USAGE、账号仅读及列级更新 last_login／password、迁移记录只读、会话表允许 SELECT／INSERT／UPDATE／DELETE。其余 6 张表及所有序列无运行权限，各表无 TRUNCATE 权限。运行账号执行零行探针，PostgreSQL 拒绝角色更新、管理标志更新、账号删除和直接权限表读取。运行模式调用 `seed_accounts --manifest intentionally-unused.json` 在读取路径前退出 1。
6. 业务预置的默认受保护清单路径在本机不存在。业务库实际预置、真实密码哈希及重跑对比等待负责人提供已批准的清单或明确授权生成。测试库哈希与重跑验收见下节。

### 13 项测试和 AC 映射

Django 5.2.19 的原生 PostgreSQL 测试库启动会尝试连接维护库。为执行本轮仅两库的限制，实际用 `.venv/Scripts/python.exe -` 读取 UTF-8 Python 代码，先校验 `test_lab_booking`、`lab_booking_test`、17.12、5433、空库及正向计划，再把该进程中默认连接的 `_nodb_cursor` 限定为同一个已验证的测试库 cursor。随后执行 `call_command('test', 'accounts', keepdb=True, parallel=1, interactive=False, verbosity=2)`。正常 Django 测试流程在预建测试库应用同样的 16 项迁移。13 个测试均为 ok，`Ran 13 tests in 6.234s`，退出 0。测试库保留，复查 16 条迁移、0 个账号、0 条会话。两个测试类均为 PostgreSQL 上的 `TestCase`，测试数据走事务回滚。

| 正式 AC | 隔离数据库自动化实测 | Windows Chrome 实测 |
| --- | --- | --- |
| AC-1 | 三类测试预置账号登录成功，正确显示本人角色并保持刷新会话，持续检查 last_login | 待真实清单验证三类登录 |
| AC-2 | 未知账号、错误密码、缺用户名、缺密码四个子例均失败，随后身份页拒绝且账号不变 | 未知账号与两种缺字段均有表单错误，身份页继续跳转且无会话 Cookie。已存在账号的错密待真实清单 |
| AC-3 | 匿名／无效会话重定向、禁用账号拒绝，账号不变。另验证无效角色被服务端拒绝 | 直接打开 `/identity/` 跳至 `/login/?next=/identity/`，页面无受保护内容 |
| AC-4 | 伪造角色及账号 ID 仍显示学生本人，管理标志不覆盖业务角色，身份页 POST 返回 405 | 待真实账号验证带伪造参数登录 |
| AC-5 | 有效令牌建立会话，缺失／无效令牌均为 403 且无会话或数据变动 | 浏览器提交缺失／无效令牌均为 403，随后身份页仍拒绝且无会话 Cookie。有效令牌与正确凭据配对待真实清单 |
| AC-6 | 三条关闭路由均无匹配、返回 404、无泄露。三类账号共用 `/login/` | `/admin/`、`/register/`、`/accounts/register/` 均为 404。三类账号实际登录待真实清单 |
| AC-7 | Windows 本机版本、实库迁移和分权已核对。缺 `LAB_BOOKING_DB_MODE` 或 `PGPASSFILE` 时 `manage.py check` 均明确报缺项并退出 1 | 运行账号启动成功，实测匿名和失败流程。实际预置与真实账号登录仍待完成 |

四个 `AccountStorageTests` 同次通过。分别验证 PostgreSQL 拒绝遗漏、NULL、空串和未知角色，首次预置只保存可验证哈希且无管理标志／组／直接权限，同角色重跑保留完整账号字段和权限，异角色冲突整批回滚，规范化重复和非法清单拒绝整批。

按 PC-011 统计这次同时断言拒绝、无受限内容及账号数据不变的用例，共 11／11。包括 AC-2 四种错误输入、AC-3 匿名／无效会话、AC-5 两种 CSRF 拒绝、AC-6 三条未挂载路由。AC-3 两例及 AC-6 三例各共享同一前后数据对照。合法对照为三类账号登录及有效 CSRF 请求，单列。当前仅涉及 Story 1.1 的账号与认证，开发证据只计当前权限切片。

### 本机启动、浏览器与恢复证据

- 运行模式实际执行 `.venv/Scripts/python.exe -u manage.py runserver 127.0.0.1:8000 --noreload`，17:35:38（北京时间）启动，系统检查 0 问题。
- Windows 执行工具和可视浏览器插件首先报 `helper_unknown_error: setup refresh had errors`。命令经工具批准后运行。浏览器改用已安装的 Chrome 159.0.8154.13，以独立临时配置启动 headless 浏览器，由 Node 24 通过本机 DevTools 控制，实际访问运行服务。应用不会把表单凭据放进 URL，浏览器脚本只返回断言结果。
- 第一次配置错误断言脚本通过 PowerShell 管道时，中文字符串编码不匹配。显式设置 `$OutputEncoding = [Text.UTF8Encoding]::new($false)` 后，两个缺失配置断言均通过，浏览器用相同 UTF-8 设置再跑一次，确认中文受保护标题检查也通过。

## 2026-11-22 正式预置与 Chrome 验收

### D-015 业务初始化

负责人在本次 Story 1.1 会话明确批准三个本地演示账号及保护条件。审批、依据及验证回指见 [D-019](../../decision-log.md#d-019-2026-11-22-负责人批准-story-11-业务预置和退出验收)。

- 设 `LAB_BOOKING_DB_MODE=migration`，通过 `.venv/Scripts/python.exe -` 实际认证为 `lab_booking_migrator`，在同一事务核对 `lab_booking`、`127.0.0.1:5433`、PostgreSQL 17.12、迁移计划为空和预置前账号表为空。锁定账号表的插入及更新路径，防止并行预置改变对照。
- 本机用 `secrets.token_urlsafe(36)` 分别生成三个独立密码，保存到仓库外负责人 Windows 用户的专用目录。凭据文件及父目录 ACL 均经核验，仅该 Windows 账户有授权。密码和哈希值均未写入证据。
- 实际调用管理命令 `call_command('seed_accounts', manifest=manifest, stdout=output)` 两次，使用了原命令内的 `set_password()`。首次结果 `新增 3，跳过 0。`，重跑结果 `新增 0，跳过 3。`。在内存比较重跑前后账号完整记录一致，三个哈希均为 `pbkdf2_sha256` 且与对应初始密码匹配，角色和权限配置保持一致。
- `student_demo → student`、`teacher_demo → teacher`、`admin_demo → admin`。三者均启用，`is_staff`、`is_superuser` 均为 false，组及直接 Django 权限为空。初始化事务已提交。

### 本机应用与真实浏览器

发现原实现只有登录和只读身份页，无法通过页面退出。按负责人要求使用 Django `LogoutView` 加入 `POST /logout/`，身份页通过 CSRF 表单提交。对既有 AC-5 测试方法补充 GET 返回 405、无 CSRF 的 POST 返回 403、有效退出后身份页引导登录的断言，测试方法数量保持 13。2026-11-22 17:57:10（北京时间）以 `LAB_BOOKING_DB_MODE=runtime` 重新执行 `.venv/Scripts/python.exe -u manage.py runserver 127.0.0.1:8000 --noreload`，Django 检查为 0 问题。

实际执行 `node -`，由本机 Node 24 启动 Chrome 159.0.8154.13（headless 和独立临时配置），用 DevTools 操作实际登录及退出表单、刷新、独立会话和本机 HTTP 请求。表单密码由进程直接读取本机保护清单，只向环回应用提交。脚本退出 0，输出只含用例、状态和批准的演示账号名。

| 正式 AC | 本轮实测结果 |
| --- | --- |
| AC-1 | 三类账号实际提交 `/login/` 表单后均进入 `/identity/`，显示各自账号与角色，有 HttpOnly 会话 Cookie，刷新后仍为本人。逐个点击退出成功并回到登录，原身份页再次引导登录。 |
| AC-2 | 未知账号、缺用户名、缺密码及三个已存在账号各自使用错误密码均显示表单错误。随后请求身份页均引导登录，浏览器没有认证会话。 |
| AC-3 | 匿名及退出后实际访问 `/identity/` 均引导登录且无身份内容。此前 13 项测试含无效会话、禁用账号和数据前后对照。 |
| AC-4 | 学生凭据提交实际管理员账号 ID 和伪造 admin 角色，登录身份仍为学生本人。携带同样参数直接访问身份页，结果一致。管理标志独立于业务角色的对照在此前测试通过。三类演示账号管理标志保持 false。 |
| AC-5 | 有效 CSRF 表单登录和退出均成功。以三类正确凭据分别发出缺失、无效令牌，均为 403 且没有会话。已登录时对退出路由发 GET 得 405，缺失或无效 CSRF 的 POST 得 403，随后原会话仍可访问身份页。 |
| AC-6 | 三条关闭路径均实际返回 404，三类账号通过同一个登录地址。 |
| AC-7 | Windows、PostgreSQL 17.12、迁移、预置、运行账号启动和浏览器实测已核对。再次执行 `manage.py check`、`makemigrations --check --dry-run`、`migrate --plan` 均通过。分别移除 `LAB_BOOKING_DB_MODE` 或 `PGPASSFILE` 时明确报缺项并退出 1。本地扫描确认三条实际初始密码均未出现在 Git 跟踪文件或差异。 |

浏览器后以 `psql -X -w -h 127.0.0.1 -p 5433 -U lab_booking_app -d lab_booking -v ON_ERROR_STOP=1` 只读核对三条账号记录，三人均有登录记录，角色及两个管理标志保持正确，`django_session` 剩余 0 条。

### 重跑与评审交接

业务预置和浏览器验收结束时，自动化重跑因当轮只批准业务库而暂缓。2026-11-22，负责人随后明确批准仅为这 13 项测试使用 PostgreSQL 17.12 的 `127.0.0.1:5433/test_lab_booking`。

以 `LAB_BOOKING_DB_MODE=test` 运行 `.venv/Scripts/python.exe -`。写入前核对 Django `NAME`、`TEST.NAME` 和实际会话均为 `test_lab_booking`，实际角色为 `lab_booking_test`，服务端为 PostgreSQL 17.12。通过测试库系统目录确认该角色在本库的 public 有 USAGE／CREATE，业务库 CONNECT 为 false，CREATEDB、CREATEROLE、SUPERUSER、REPLICATION、BYPASSRLS 均为 false。前置状态为 9 张本角色表、16 条迁移记录、0 个账号、0 条会话，计划无待迁移。本次运行的所有数据库连接均指向测试库。

同一 Python 进程把 Django 的 `_nodb_cursor` 限定到已验证的测试库，实际执行 `call_command('test', 'accounts', keepdb=True, parallel=1, interactive=False, verbosity=2)`。运行器返回 `No migrations to apply` 并保留数据库。未触发重建或整库清空。隔离测试的记录在事务内回滚。结束后用 `psql -X -w -h 127.0.0.1 -p 5433 -U lab_booking_test -d test_lab_booking -v ON_ERROR_STOP=1` 只读核对，仍是 16 条迁移记录、0 个账号、0 条会话。

| 发现 | 通过 | 失败 | 错误 | 跳过 | 耗时 | 退出码 |
| --- | --- | --- | --- | --- | --- | --- |
| 13 | 13 | 0 | 0 | 0 | 6.217 秒 | 0 |

逐项输出均为 `ok`，汇总为 `Ran 13 tests in 6.217s` 和 `OK`。本次重跑无错误日志，无需修复后重跑。四个存储测试覆盖角色约束、哈希、规范化与非法输入、同角色幂等及异角色回滚。既有 AC-5 方法的新增退出断言与登录断言一并通过。

| 正式 AC | 与本次重跑合并核验的证据 | 结果 |
| --- | --- | --- |
| AC-1 | `test_ac1_preset_roles_log_in_and_refresh`，三个演示账号在 Chrome 的登录、本人身份与刷新 | 通过 |
| AC-2 | `test_ac2_unknown_wrong_and_missing_credentials_are_denied`，Chrome 的未知账号、错密、缺字段和身份页拒绝 | 通过 |
| AC-3 | `test_ac3_anonymous_and_invalid_session_are_redirected`、`test_identity_rejects_disabled_accounts_and_invalid_roles`，Chrome 匿名和退出后跳转，账号数据前后对照 | 通过 |
| AC-4 | `test_ac4_server_role_ignores_forged_values_and_management_flags`、`test_identity_rejects_post_without_account_changes`，Chrome 同一学生会话忽略伪造管理员 ID 和角色 | 通过 |
| AC-5 | 两个 `test_ac5_*` 方法与 Chrome 的合法令牌、缺失或无效令牌，以及退出后会话失效 | 通过 |
| AC-6 | `test_ac6_admin_and_self_registration_routes_are_absent`，Chrome 三条关闭路径 404 和三类账号共用登录入口 | 通过 |
| AC-7 | Windows 运行记录、17.12 首迁及分权、D-015 实库初始化、Chrome 验收、缺配置错误与 Git 凭据检查 | 通过 |

根据 BMAD 6.12.4 和负责人本轮指令，Story 1.1 开发自测通过后进入 Sprint `review`，实施规格同步为 `in-review`。本会话停在交接，独立 `bmad-code-review` 待新会话执行。

证据按[课程基线](../../docs/course-requirements.md)对应第 26 页的一致性链条、第 33 页的运行软件与测试、第 36 页的真实人机决策。第 27 页逐故事开发和独立评审按照[负责人提供的页码口径](../../docs/team/sprint-planning-review.md)执行。第 34 页实验 A 的 X/Y 数据沿用独立试验记录，本故事开发自测不计作实验数据。课程 PPT 原件未在仓库中找到。

## 2026-11-23 独立评审整改与开发自测

### 工作区与执行边界

- 按 BMAD 6.12.4 `bmad-build` 恢复已评审实施规格，依据 D-020 进入已批准的 patch 分支。现有独立评审结论作为输入，独立复审和人工最终验收交下一会话。约 16:26 从 `review` 转回 `in-progress`。开发检查点为 [dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083)。开工前 Git 显示 8 个已修改文件及未跟踪的负责人处置记录，保留既有退出表单、原评审报告和预置证据。
- Django 每次连接前检查固定库、用户、主机／实际地址、端口和密码来源，连接后先用同一会话核验实际库、认证用户、当前用户、地址、端口和 PostgreSQL 17.12。测试角色还检查业务库 CONNECT 为假，SUPERUSER、CREATEDB、CREATEROLE、REPLICATION、BYPASSRLS 为假。全量测试与临时浏览器测试只连接 `127.0.0.1:5433/test_lab_booking`。隔离测试入口绕过 Django 建库、迁移和销毁流程，预检无待迁移项，测试前后逐表与逐条迁移记录比对一致。
- 业务库只执行运行角色的只读身份查询、Windows 启动及匿名 GET，以及迁移角色的 `migrate --plan`。没有在本轮执行迁移、授权、预置或用业务账号重新登录。PostgreSQL 17.12 业务首次迁移及真实演示账号的哈希和浏览器证据见上轮 D-019。

### 自动化测试与失败恢复

命令为 README 的全量入口 `manage.py test --keepdb --parallel 1 -v 2`，使用现有 Windows venv Python 和受保护 `PGPASSFILE`。初始沙箱无法访问本机 uv/Python 和密码文件，渲染及实测经工具授权恢复。`16` 条迁移记录和 `9` 张表的清单在两轮均保持一致，测试前后均为 0 个账号、0 条会话。

| 执行 | 发现 | 通过 | 失败 | 错误 | 跳过 | 耗时 | 退出码 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 账号整改套件首次全量 | 19 | 19 | 0 | 0 | 0 | 7.453 秒 | 0 |
| 补入口和连接负例后全量复跑 | 26 | 26 | 0 | 0 | 0 | 7.484 秒 | 0 |

另核对 Windows `runserver` 在 migration/test 分别退出 1，直接导入 WSGI 在两个模式也分别退出 1。自动化替身确认拒绝发生在父类／应用初始化调用之前。runtime 的 `manage.py check` 退出 0，`runserver --noreload` 启动检查 0 问题，匿名 GET `/login/` 为 200、GET `/identity/` 为 302。migration 的 `migrate --plan` 退出 0 且无待执行项目。test 的 `makemigrations --check --dry-run` 退出 0 且无模型变更。分别缺少 DB_MODE、PGPASSFILE 和 SECRET_KEY 时均报对应配置名并退出 1。

直接抽取 README 的 PowerShell 代码块执行替身验证。模拟预置退出 17 时仅调用 `seed_accounts` 并抛错，模拟退出 0 时顺序调用 `seed_accounts,runserver`。模拟 psql 中途错误返回 3 时抛错，成功返回 0 时继续。替身核对同一 psql 调用内的目标、版本检查、`ON_ERROR_STOP=1`、`--single-transaction` 和五条既有最小授权语句。本轮未执行 GRANT。

### 真实浏览器复测

使用 Chrome 159.0.8154.13 无头模式，临时环回 WSGI 测试服务与 Django 设置的应用请求处理器，合成账号预置及请求写入均封在同一个测试库回滚事务。临时脚本不经生产 WSGI 入口，Windows runtime 的正常启动另行核验。

1. 首次脚本停在错密提示断言，退出 1。前后隔离库清单相同。随后让临时服务像 Django 测试客户端一样保留外层测试事务连接，增加 HTTP 状态观测。
2. 第二次已跑通学生流程，教师退出后下一次导航停住，终止该次脚本。为临时服务的空闲 TCP 连接加读超时，再执行完整复测。
3. 第三次实测 Chrome 退出 0。学生、教师、业务管理员均以实际 HTML 表单登录，展示各自账号和固定标签，刷新保留 HttpOnly 会话。伪造字段没有改变结果。三类账号均实际提交退出表单，附带 `next=/logout/` 后仍去登录页。GET、缺失和无效 CSRF 的退出分别为 405、403、403，之后原身份仍可访问。错密显示错误，登录缺失／无效 CSRF 均为 403，匿名访问身份页为 302，三个关闭入口均为 404。临时服务记录两次空闲 TCP 的 `TimeoutError`，三类账号断言仍全部完成，隔离库回滚后保持 9 张表、16 条迁移、0 个账号、0 条会话。

### 正式 AC 逐项核对

| AC | 本轮实际结果 |
| --- | --- |
| AC-1 | 三种角色均由预置命令创建合成账号，从渲染表单取得 CSRF 后认证，服务端会话账号匹配，页面显示固定标签，刷新保留。Chrome 三角色复测通过。 |
| AC-2 | 未知账号、错密、缺用户名、缺密码均为 200 且渲染可见错误，无认证会话，直接访问身份页为 302。Chrome 错密对照通过。 |
| AC-3 | 匿名、无效会话、禁用账号均为 302，无身份内容，账号数据不变。直接视图非法角色被拒绝。 |
| AC-4 | 合法凭据附加伪造角色／账号 ID 后仍为本人，管理标志不能覆盖业务角色。Chrome 合成账号对照通过。 |
| AC-5 | 合法表单按凭据判定，缺失或无效 CSRF 为 403，账号和会话集合不变。真实退出表单、重放旧会话及退出拒绝分支自动化通过。 |
| AC-6 | Admin 及两条注册路由均无法解析并返回 404。三个角色共用登录地址。 |
| AC-7 | Windows runtime 启动、只读迁移计划、缺配置拒绝、隔离库完整复跑及真实浏览器均有本轮证据。实际业务库首迁和真实账号预置使用 D-019 既有证据。第二台 Windows 机器未复验。 |

### PC-011／T-03 拒绝矩阵

以下为本 Story 账号和认证切片。每一行均有独立的拒绝结果、受保护身份标签和账号内容检查，以及请求前后账号字段（含哈希、角色、登录时间）相等的断言。失败登录后对身份页的 302 是同一场景的附加断言。直接视图和合法对照单列。

| 层级 | 操作与输入 | 预期／实际 | 会话结果 |
| --- | --- | --- | --- |
| HTTP | 登录：未知账号 | 200／200，显示错误 | 无认证，服务端会话集合不变 |
| HTTP | 登录：错误密码 | 200／200，显示错误 | 无认证，服务端会话集合不变 |
| HTTP | 登录：缺用户名 | 200／200，显示错误 | 无认证，服务端会话集合不变 |
| HTTP | 登录：缺密码 | 200／200，显示错误 | 无认证，服务端会话集合不变 |
| HTTP | 登录：缺 CSRF | 403／403 | 无认证，服务端会话集合不变 |
| HTTP | 登录：无效 CSRF | 403／403 | 无认证，服务端会话集合不变 |
| HTTP | 身份页：匿名 | 302／302，去登录 | 无认证，服务端会话集合不变 |
| HTTP | 身份页：无效会话 | 302／302，去登录 | 无认证，服务端会话集合不变 |
| HTTP | 身份页：原账号已禁用 | 302／302，去登录 | 请求无认证，原会话行仍保留 |
| HTTP | 身份页：有效 CSRF 下 POST 伪造角色 | 405／405 | 原会话及服务端账号保留 |
| HTTP | 退出：GET | 405／405 | 原会话及同一身份保留 |
| HTTP | 退出：POST 缺 CSRF | 403／403 | 原会话及同一身份保留 |
| HTTP | 退出：POST 无效 CSRF | 403／403 | 原会话及同一身份保留 |
| HTTP | `/admin/` | 无路由、404／404 | 无 Cookie，服务端会话集合不变 |
| HTTP | `/register/` | 无路由、404／404 | 无 Cookie，服务端会话集合不变 |
| HTTP | `/accounts/register/` | 无路由、404／404 | 无 Cookie，服务端会话集合不变 |
| 直接视图 | 已认证用户对象带非法角色 | 抛出 PermissionDenied／同预期 | 账号字段前后相同。数据库约束测试单独验证非法角色无法存储 |

HTTP 拒绝矩阵为 **16／16**，直接视图为 **1／1**。合法对照包括三类账号通过同一表单登录、刷新，以及合法退出和附带额外跳转字段退出。两种合法退出均检查旧服务端会话已删除，重放原标识仍拒绝身份页。完整 NFR-002 的设备、预约及归属部分由其对应 Story 验证。

交接前 `git diff --check` 退出 0。扫描已跟踪差异和未跟踪文件，凭据、私钥、哈希等常见敏感模式命中 0，敏感路径命中 0，未跟踪文件无尾随空白。`.venv/` 由 Git 忽略，暂存区无改动。本轮工作区未提交。

课程第 26、27、33、36 页证据分别由 FR／ADR／AC 链路、逐故事实际状态与独立评审、运行与测试、D-020 人工判断及事后证据承接。第 34 页实验 A 沿用 Sprint 计划，本轮数据未录入实验度量。CR 逐项链接见[处置记录](../../docs/team/story-1-1-review-disposition.md#开发整改与自测结果)。开发自测完成后交回 `review`，等待独立复审和负责人最终验收。

## 2026-11-24 第二轮整改与开发自测

### 修改内容及规则

- 新增 [账号表单约束](../../accounts/forms.py)：`AccountAuthenticationForm` 是预置命令与登录页面共用的字段来源。密码服务器端最大值为 4096 个 Unicode 码点；浏览器使用 8192 个 UTF-16 单元的 `maxlength`，`data-max-code-points=4096` 供前端按码点约束。最坏情况下每个补充平面字符 UTF-8 占 4 字节并进行 URL 百分号编码，4096 码点表单体约 48 KiB，低于 Django 2.5 MiB 默认请求体上限。
- [预置命令](../../accounts/management/commands/seed_accounts.py) 在打开事务前校验共享的登录用户名／密码字段，同时保留 `User.username` 模型验证器。非法或超限输入不进入写入路径，同角色重复初始化保持哈希不变。
- [登录路由](../../lab_booking/urls.py) 使用共享表单；[登录模板](../../accounts/templates/accounts/login.html) 的用户名和密码输入均按 Unicode 码点限制。用户名服务端上限取 `User.username.max_length=150`，HTML 容纳 300 UTF-16 单元，前端按 150 码点截断，服务端仍独立拒绝超限值。
- [账号回归测试](../../accounts/tests.py) 新增四个用例：76 个补充字符用户名端到端登录、混合字符 150 合法／151 拒绝、4096 个补充字符密码通过预置并实际表单认证、4097 密码在预置与登录表单均拒绝且已有哈希／字段不变。原有 NUL／CR／LF／孤立代理项、角色非法、JSON 结构、同角色重跑及账号完整字段保持回归保留。测试使用隔离库回滚。

### 测试过程与真实结果

全量测试使用 Windows venv Python 3.13.17、Django 5.2.19、psycopg 3.3.9 和已核验的 PostgreSQL 17.12 测试库。命令为 `manage.py test --keepdb --parallel 1 -v 2`，连接为 `127.0.0.1:5433/test_lab_booking`／`lab_booking_test`。最终发现 31 项，通过 31、失败 0、错误 0、跳过 0，耗时 10.609 秒，退出码 0。执行前后均为 9 张表、16 条迁移、0 个账号和 0 条会话；项目测试运行器确认没有触发创建、迁移、flush 或删除测试库。

保留的失败／修复／复测过程：

1. 首次边界组 5 项中 3 项通过、1 项失败、1 项错误。浏览器控件实际仍渲染 `maxlength=150`，测试类也误用字典实例方法。将 widget 上限在表单初始化后设置为 300 UTF-16 单元，并修正测试夹具。
2. 第二次 5 项中 4 项通过、1 项错误，定位为测试把清单字典当作已加载模型实例；改为读取并比较实际模型对象。
3. 第三次边界组 5/5 通过。第一次全量 30 项发现 3 个失败断言：使用登录字段的表单级验证器替代模型级用户名验证器，导致无效用户名可被接受，后续批次比较也暴露出测试缺少独立前后快照。恢复 `User.username` 模型验证器，并让各非法清单子场景分别比较数据库前后完整记录。
4. 针对性 3 项复测 3/3，随后完整 30 项复测 30/30。追加 4097 密码登录表单明确拒绝断言，并把合法最大密码改为 4096 个补充字符后，针对性 2 项 2/2、最终完整套件 31/31 全部通过。

### Windows runtime 真实浏览器

使用已批准三条预置账号，不读取、输出或更改密码；在 Windows runtime 运行本机 Chrome 159.0.8154.13，命令为 `.venv/Scripts/python.exe -B -u manage.py runserver 127.0.0.1:8000 --noreload`。应用通过固定数据库后端实际连接 `lab_booking`／`lab_booking_app`／`127.0.0.1:5433`／PostgreSQL 17.12。Django 临时 `SECRET_KEY` 存放在仅当前 Windows 用户可读的仓库外临时目录，未写入代码、日志或证据。

| 浏览器实测 | 学生 | 教师 | 管理员 |
| --- | --- | --- | --- |
| 渲染登录页／正确表单提交 | GET 200／POST 302 | GET 200／POST 302 | GET 200／POST 302 |
| 身份标签和账号 | student_demo／学生 | teacher_demo／教师 | admin_demo／业务管理员 |
| 刷新 | GET 200，身份保留 | GET 200，身份保留 | GET 200，身份保留 |
| CSRF | 登录缺 token 403；退出无效 token 403，原身份保留 | 同左 | 同左 |
| 退出及匿名访问 | POST 302 回登录，服务端会话删除；匿名身份页 302 | 同左 | 同左 |

三者会话 Cookie 均为 HttpOnly；退出前数据库会话记录与当前用户一致，退出后对应记录删除。实际 Chrome 对 76 个 U+20000 输入显示 76 码点／152 UTF-16 单元且值完整；151 码点输入经前端监听变为 150。runtime 退出后只读复核仍为 3 个既有账号、角色和启用／管理标志不变、会话 0 条。按 Django 正常登录行为，`last_login` 更新是验收预期。真实库未迁移、预置、授权、删库或清空，账号密码未修改。

浏览器执行过程另有两次未通过的自动化尝试：首次 Windows 启动包装器的健康判断误报失败，但实际服务日志为 `/login/` 200；修正检查后继续。首个 Chrome 自动化子进程使用了不同的临时 Django 签名密钥，导致只读会话身份核验失败；该次已登录的学生会话由后续恢复脚本在 Chrome 中提交实际 CSRF 退出表单，服务端会话恢复为 0。一次密钥生成 API 用错导致 runtime 未监听，随后停止本次进程并只清理其空临时文件。换成共享的用户专属临时密钥后，完整 Chrome 三角色流程全通过；这些失败、恢复结果未算作通过运行。

### AC 和约束复核

AC-1 三角色预置、正常及最大边界凭据登录、身份显示和刷新均通过。AC-2 未知账号、错误密码、缺字段、超限密码均由登录表单拒绝且无会话。AC-3 匿名、无效会话和禁用账号均被拒绝。AC-4 伪造身份字段及管理标志不能覆盖业务角色。AC-5 正常 CSRF 登录／退出成功，无效或缺失 token 被拒绝，退出删除原服务端会话。AC-6 登录共用入口，管理及自助注册路由不存在。AC-7 Windows runtime 与已批准 PostgreSQL 17.12 的连接、真实 Chrome 登录、缺配置拒绝和隔离测试均有本轮证据；第二台 Windows 机器仍未复现，环境准备说明待后续补齐。

D-015～D-020、FR-001／002、ADR-001／002／008、project-context 的角色来源、runtime／migration／test 隔离、最小权限与范围边界保持不变。D-020 限定的业务库不迁移／不清空／不授权规则遵守；本轮唯一业务侧写入是实际登录必需的 `last_login` 与会话创建，三次正常退出后会话清零。独立复审和负责人最终验收尚未发生。运行器与账户测试库最终检查均只针对 `test_lab_booking`，业务库只作 runtime 认证和只读核对。

## 2026-11-24 输入边界最终整改

负责人根据正式 Step 4 复审只批准处理用户名和密码的输入边界，并要求隔离实测后在独立 Code Review 会话复审。沿用 FR-001／002、ADR-001／002／008、D-015／016 和 PC-001／002／008／011。规格冻结区、正式 AC 和 Sprint 范围保留。 [负责人决定 D-021](../../decision-log.md#d-021-2026-11-24-负责人限定-story-11-输入边界整改)

### Python 运行环境对照

Codex 受限 PowerShell 中，读取 `pyvenv.cfg` 指定的基础解释器路径返回 `Access is denied`，项目 `.venv/Scripts/python.exe --version` 退出 `103`。同机获准的普通 PowerShell 中，基础解释器与 `.venv/Scripts/python.exe --version` 均返回 `Python 3.13.17`、退出 `0`。首次附加位数探针被 PowerShell 参数引号解析误传为无引号的 `P`，用标准输入重跑成功，确认项目环境为 Python 3.13.17 64 位、Django 5.2.19、psycopg 3.3.9。故障来自执行环境权限差异，未重装解释器或覆盖 `.venv`。实施子代理曾以 3.14.7 做无数据库探查，超出此前解释器用途约定。本节的正式测试使用原 `.venv`，未采用该探查结果。

### 代码和真实测试

- 登录和预置共用 `UsernameField`、账户模型原有 `UnicodeUsernameValidator` 及密码字段。Django 先去除用户名外围空白、执行 NFKC，再检查长度与允许字符。浏览器不再按 UTF-16 单元或码点截断。正常密码保留外围空白，超限在表单字段校验时拒绝，预置在开启事务前拒绝并保留已有账号和哈希。 [表单](../../accounts/forms.py) · [预置命令](../../accounts/management/commands/seed_accounts.py) · [登录模板](../../accounts/templates/accounts/login.html)
- `manage.py check` 报告 0 项，`manage.py makemigrations --check --dry-run` 返回无变更。`manage.py test --keepdb --parallel 1 -v 2` 在 `127.0.0.1:5433/test_lab_booking` 以 `lab_booking_test`、PostgreSQL 17.12 运行，32 项通过，失败、错误、跳过均为 0，13.057 秒，退出 `0`。前后均为 9 张表、16 条迁移、0 个账号、0 条会话。 [仓库回归](../../accounts/tests.py)
- Chrome 159.0.8154.13 在临时环回 WSGI 服务上操作实际模板。临时 `TestCase` 在同一线程、同一回滚事务内处理合成账号预置和请求。首次等待响应超时，第二次记录 `POST /login/` 返回 500，原因定位到临时请求生命周期和测试连接处理。给临时服务设置空闲套接字超时，并按 Django 测试客户端的方式保护测试事务后重跑，6 个真实 HTML 表单均以 `application/x-www-form-urlencoded` 提交，1 个浏览器回归测试通过，4.674 秒，退出 `0`。隔离库前后同为 9 张表、16 条迁移、0 个账号、0 条会话。临时运行记录不含密码或会话值。

| 实际 Chrome 用例 | 输入与响应 |
| --- | --- |
| 正常密码 | 带外围空白的正常密码完整提交，登录 `302`，身份页 `200` |
| 合法用户名边界 | 150 个补充平面码点加一个前导空格，浏览器完整保留 301 UTF-16 单元，登录 `302`，身份页 `200` 且用户名为规范值 |
| 151 码点用户名 | 保留完整输入，登录 `200` 显示用户名长度错误，匿名身份页 `302` |
| 内部空格 | 保留完整输入，登录 `200` 显示用户名字段错误，匿名身份页 `302` |
| 合法最大密码 | 4096 个补充平面码点，浏览器保留 8192 UTF-16 单元，登录 `302`，身份页 `200` |
| 超长密码 | 合法 4096 码点密码附加一字符，浏览器完整提交，登录 `200` 显示密码长度错误，匿名身份页 `302` |

### 正式验收条件与课程证据

| AC | 本轮证据 |
| --- | --- |
| AC-1 | 三角色经真实渲染表单建立会话并刷新保持，账号与角色与服务端一致。另验证带外围空白的 150 码点用户名、NFKC 规范化、正常密码及 4096 码点密码。 |
| AC-2 | 未知账号、错密、缺字段及越界值均显示错误且无认证会话。保持合法 4096 码点密码前缀的超长用例验证认证函数没有调用。 |
| AC-3 | 匿名、无效会话、禁用账号及直接视图非法角色拒绝，检查对应响应与账号数据。 |
| AC-4 | 伪造身份及角色值和 Django 管理标志不会改变本人业务身份。 |
| AC-5 | 合法 CSRF 登录与退出，缺失及无效 CSRF 拒绝，成功退出删除旧会话。 |
| AC-6 | 共用登录入口，Admin 和自助注册路由关闭。 |
| AC-7 | 本机原环境、系统与迁移一致性检查、隔离库、真实浏览器和配置拒绝路径有证据。业务库首迁、预置及实际运行账号的浏览器验收沿用此前记录。此轮未连接业务库，第二台机器未复现。 |

课程第 26 页追溯沿 FR-001／002 → ADR-001／002／008 → Story AC → 测试。第 27、33 页由正式评审、整改、实测和真实状态承接。第 34 页实验 A 维持已定候选与条件，本轮测试不计入对照指标。第 36 页记录本轮实际人工授权，负责人最终验收待发生。PPT 页码依据[课程基线](../../docs/course-requirements.md)及[团队审核材料](../../docs/team/sprint-planning-review.md)。Story 1.1 为 `review`，Story 1.2 为 `backlog`，现有 [Git 检查点 `dd2ec5c`](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/dd2ec5cee55e14d03f72fdaf3cf73920c1e9e083) 后的整改为工作区差异。
