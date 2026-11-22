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
