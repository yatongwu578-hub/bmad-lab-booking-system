# Sprint 1 环境准备记录

检查日期为 2026-11-21（Asia/Shanghai）。负责人在本次会话批准 R-01 自定义用户模型及 R-03 目标栈。环境记录来自本机 PowerShell 执行结果。Sprint 1 的范围依据现有 8 条 Story（1.1～1.4、2.1、2.2、2.3、2.5）。[R-01 决策 D-015](../../decision-log.md#d-015-2026-11-21-负责人批准-r-01-自定义账号模型) · [Sprint 计划](../../_bmad-output/planning-artifacts/sprint-plan.md)

## Python、依赖和时区

| 检查项 | 实际结果 |
| --- | --- |
| Windows | `Win32_OperatingSystem` 显示 Windows 11 专业版、64 位、Build 26200。注册表 `DisplayVersion` 为 25H2，旧 `ProductName` 字段显示 Windows 10 Pro，采用操作系统查询结果及实际 Build。 |
| Python 初检 | `py -0p` 仅列出 3.14 和 uv 托管的 3.12.13。`py -3.13-64` 返回 `No suitable Python runtime found`，检查的 Python 注册项也无 3.13。默认 `python` 解析到 Miniconda。 |
| Python 安装 | Python Software Foundation 的 Windows x86-64 安装包 `python-3.13.17-amd64.exe`。Authenticode 状态 `Valid`。SHA-256 为 `5da012101ba2e17113a9a1cd901e9ce1441086f2b7ecb5de06ec94163899a190`，与发布页相符。安装程序退出 0，显式调用新解释器得到 3.13.17、64 位。 |
| Windows 时区 | `Get-TimeZone` 和 `tzutil /g` 返回 `China Standard Time`，主机基准偏移 +08:00。Python 的 IANA 时区另行做目标 venv 验证。 |
| 项目 venv | `.venv` 的 `sys.prefix` 与仓库内 `.venv` 一致，且不同于 `sys.base_prefix`，解释器为 64 位 Python 3.13.17，pip 26.2.2。 |
| 已装项目依赖 | Django 5.2.19、psycopg 3.3.9、psycopg-binary 3.3.9、tzdata 2026.6、asgiref 3.13.0、sqlparse 0.6.1。均为 PyPI wheel，由 `files.pythonhosted.org` 提供。驱动 wheel 为 `psycopg_binary-3.3.9-cp313-cp313-win_amd64.whl`，导入得到 `binary` 实现、libpq 18.4，并成功导入 Django PostgreSQL 后端。libpq 版本来自驱动的客户端库。 |
| 依赖校验 | `pip check` 输出 `No broken requirements found.`。[requirements.txt](../../requirements.txt) 离线 `--no-index` 核对全部为 `Requirement already satisfied`。依赖及下载报告保存在本机忽略目录 `.venv`。 |
| Python 和 Django 时区 | `zoneinfo.TZPATH` 为 `()`，实际由 `tzdata` 提供 IANA 2026f。脚本断言 `2026-11-21T16:00:00+00:00` 转为 `2026-11-22T00:00:00+08:00`，往返 UTC 相等。Django `USE_TZ=True`、`TIME_ZONE='Asia/Shanghai'` 时，`django.utils.timezone.localtime()` 得到同一结果。 |

在其他机器缺少 3.13 时，从 Python.org 发布页选择 **Windows installer (64-bit)**。本轮安装位置为当前用户的 `%LOCALAPPDATA%\Programs\Python\Python313`，以 `InstallAllUsers=0 Include_launcher=0 Include_pip=1 Include_test=0 AssociateFiles=0 PrependPath=0 Shortcuts=0` 安装，项目命令显式调用其 venv 解释器。[Python 3.13.17 发布页](https://www.python.org/downloads/release/python-31317/) · [Python Windows 安装文档](https://docs.python.org/3.13/using/windows.html) · [Windows 11 发行信息](https://learn.microsoft.com/en-us/windows/release-health/windows11-release-information)

以下是本轮关键命令，省略临时下载文件名变量的准备过程。安装来源为 Python.org 和 PyPI。

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture
Get-TimeZone
tzutil /g
py -0p
py -3.13-64 -c 'import struct; print(struct.calcsize(chr(80))*8)'
Get-AuthenticodeSignature -FilePath $pythonSetup
Get-FileHash -LiteralPath $pythonSetup -Algorithm SHA256
$pythonExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
& $pythonExe -m venv .venv
$venvPython = '.\.venv\Scripts\python.exe'
& $venvPython -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple --only-binary=:all: --report .venv/install-report.json 'Django>=5.2,<5.3' 'psycopg[binary]>=3.1.8,<4' tzdata
& $venvPython -m pip check
& $venvPython -m pip freeze
& $venvPython -m pip --isolated --disable-pip-version-check install --no-index -r requirements.txt
```

时区脚本从标准输入交给 `.venv\Scripts\python.exe -`。用 `zoneinfo.ZoneInfo('Asia/Shanghai')` 验证默认数据来源，再用 `zoneinfo.reset_tzpath(())` 与 `ZoneInfo.clear_cache()` 验证包回退，断言 `astimezone()` 跨日、偏移及 UTC 往返，最后用上述 Django 设置断言 `localtime()`。可在另一机器用 `pip install --only-binary=:all: -r requirements.txt` 安装固定依赖。[Python zoneinfo](https://docs.python.org/3.13/library/zoneinfo.html) · [Django 5.2 数据库要求](https://docs.djangoproject.com/en/5.2/ref/databases/#postgresql-notes) · [psycopg binary 安装](https://www.psycopg.org/install/)

初次使用受限 PowerShell 时，命令运行器返回 `setup refresh had errors`，后续通过获准的执行方式重新运行。Python 安装、venv 创建、包安装及上述断言均已取得成功结果。

## PostgreSQL 实测及隔离方案

| 检查项 | 实际结果 |
| --- | --- |
| 既有服务 | `Get-CimInstance Win32_Service` 仅发现 `PostgreSQL`，状态 Running、启动模式 Auto，服务命令使用 `D:\Software\pgsql\bin\pg_ctl.exe`，数据目录为 `D:\Software\pgsql\data`。 |
| 版本证据 | `postgres.exe --version` 及 `psql.exe --version` 均报告 11.17。旧数据目录的 `PG_VERSION` 为 11。旧实例未做认证 SQL 查询。 |
| 监听 | `Get-NetTCPConnection -State Listen` 显示旧实例在 `127.0.0.1:5432` 和 `::1:5432` 监听。用旧目录的 `pg_isready.exe -h 127.0.0.1 -p 5432 -t 3` 检查为 `accepting connections`。 |
| 17.x 初检 | 在已查的 Windows 服务、进程、PostgreSQL 安装注册项及常见安装目录中未发现 17.x。初检时 `5433` 的 `pg_isready` 返回 `no response`，TCP 监听及 IPv4 端口保留检查均未发现占用。安装后的结果见下节。 |

获批方案采用 PostgreSQL 官网指向的 EDB Windows x64 安装包和独立 17.x 服务 `postgresql-x64-17`。`127.0.0.1:5433` 用于新服务，安装会注册 Windows 服务并初始化新集群和系统数据库。安装目录、数据目录和端口均与旧实例分开。 [PostgreSQL Windows 官方下载](https://www.postgresql.org/download/windows/)

Django 通过 `django.db.backends.postgresql` 显式配置主机、端口、库名和用户名。以下项目库及角色已创建并核验，应用表和序列的授权待迁移创建对象后按实际需求执行。

| 用途 | 数据库 | 角色与权限 |
| --- | --- | --- |
| 业务运行 | `lab_booking` | `lab_booking_app` 只获业务库连接、项目 schema 使用、所需表的 DML 和序列权限。按实际表授权，例如历史表仅授予所需的追加和读取权限。 |
| 业务迁移 | `lab_booking` | `lab_booking_migrator` 持有项目库及迁移对象的所有权，在批准的迁移时使用。 |
| 集成测试 | `test_lab_booking` | `lab_booking_test` 拥有管理员预先创建的测试库及测试对象，不能连接业务库。测试配置将 `NAME` 和 `TEST.NAME` 显式指向该测试库。候选命令为 `manage.py test --keepdb --parallel 1`，由 Django 复用预建库；需要时允许测试角色连接 17 的维护库 `postgres` 以检查数据库是否存在。Story 2.1 的并发请求仍须使用独立数据库连接。 |

三个项目角色都可登录，均为 `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`。创建时撤销两项目库的 `PUBLIC` 库级权限，再按上表授予，核对业务角色无 schema 创建权限及业务、测试角色无交叉连接权限。测试需要清空数据或重建时，先核对实际会话目标并单独确认。Django 的 PostgreSQL 后端在 `--keepdb` 下先检查库是否存在，预建测试库避免为测试角色授予实例级 `CREATEDB`。[PostgreSQL 角色文档](https://www.postgresql.org/docs/17/sql-createrole.html) · [Django 测试数据库](https://docs.djangoproject.com/en/5.2/topics/testing/overview/#the-test-database) · [Django 5.2 PostgreSQL 测试库实现](https://raw.githubusercontent.com/django/django/stable/5.2.x/django/db/backends/postgresql/creation.py)

## R-03 批准后执行记录

负责人于 2026-11-21 在本次会话明确批准 R-03 环境方案。批准与实际执行分别取证。 [决策日志 D-016](../../decision-log.md#d-016-2026-11-21-负责人批准-r-03-本地环境方案)

| 步骤 | 实测结果 |
| --- | --- |
| 安装前复查 | Windows Service `PostgreSQL` 以 `LocalSystem` 运行，服务 PID `4888`。旧端口 `5432` 仍由 PID `6064` 在环回地址监听。`5433` 无监听。当前 PowerShell 会话未提升。 |
| 安装包 | 通过 `curl.exe` 从 EDB 下载 `postgresql-17.12-2-windows-x64.exe`，大小 `416657584` 字节。`Get-AuthenticodeSignature` 返回 `Valid`，签名主体为 `EnterpriseDB Corporation`。`Get-FileHash -Algorithm SHA256` 输出 `b783e094354ddabacad02b4dc9eb89ca7ef901a05c53e430ebef8ac8324a96e9`。 |
| 管理员环境 | 以 `Start-Process -Verb RunAs` 发起 UAC，已观察到提升后的 PowerShell 进程写入启动记录。 |
| 第一次尝试 | EDB `--extract-only 1` 退出 `0`，`postgres.exe --version` 返回 `postgres (PostgreSQL) 17.12`。`initdb` 在 `C:\ProgramData\LabBooking\PostgreSQL17\data` 创建目录时返回 `Permission denied`。首次检查未出现新的 Windows 服务；后续修复只针对新数据目录。 |
| 修复及启动 | 为初始化进程的 Windows 用户显式授予新目录访问权限后重试，`initdb` 及提升后的命令均退出 `0`。新服务 `postgresql-x64-17` 以 `NT AUTHORITY\NetworkService` 运行，安装目录为 `C:\Program Files\PostgreSQL\17`，数据目录为 `C:\ProgramData\LabBooking\PostgreSQL17\data`。新服务只监听 `127.0.0.1:5433`，旧服务及 `5432` 的监听 PID 均与初检一致。两个端口的 `pg_isready` 都返回接受连接。 |
| 建库及授权 | 经管理员认证确认目标为 17.12、5433 和新数据目录后，执行 `CREATE ROLE`、`CREATE DATABASE`、`REVOKE`、`GRANT` 和 `ALTER ROLE`。两个数据库为 UTF-8，所有权及三角色的集群标志与批准方案一致，登录使用 SCRAM-SHA-256。 |
| 权限验证重试 | 首轮跨库检查因 `pgpass.conf` 仅包含授权的库与角色组合，客户端返回 `no password supplied`。该结果不能证明数据库拒绝跨库。用同一角色的正确密码在进程内重跑只读检查，证实 `lab_booking_app` 和 `lab_booking_migrator` 到测试库，以及 `lab_booking_test` 到业务库，均由服务器拒绝。 |
| 正向连接与时区 | venv 的 psycopg 通过认证验证三个角色均能连接各自获授权的库。测试角色还可连接 17 的 `postgres` 维护库。`lab_booking_app` 有业务库 `public` schema 的 `USAGE`、无 `CREATE`。独立 `psql` 以应用角色查得 `lab_booking`、`5433`、`17.12`。临时 Django 设置连接同一实际库，验证会话时区为 UTC，`2026-11-21 16:00+00` 在 PostgreSQL 转为北京时间次日 `00:00`。 |
| 凭据保护 | `Set-Acl` 在当前进程缺少 `SeSecurityPrivilege` 时失败。改用 `icacls` 配置 DACL 后，目录、`pgpass.conf`、`postgres-admin.dpapi` 均仅授予当前 Windows 用户、本地 Administrators 和 SYSTEM。复查初始化明文文件已清理，`psql` 用应用角色再次连接成功。 |

安装包与版本来源见 [EDB 下载页](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads) 和 [PostgreSQL 17.12 发布说明](https://www.postgresql.org/docs/17/release-17-12.html)。

本轮使用 EDB 软件包的只解包模式，在服务启动前配置环回监听。下列命令记录本轮关键参数，凭据文件参数用变量表示。

```powershell
$pgBin = 'C:\Program Files\PostgreSQL\17\bin'
$pgData = 'C:\ProgramData\LabBooking\PostgreSQL17\data'
& "$pgBin\initdb.exe" -D $pgData --username=postgres --encoding=UTF8 --locale=C --auth=scram-sha-256 "--pwfile=$pgPwfile"
& "$pgBin\pg_ctl.exe" register -N postgresql-x64-17 -D $pgData -U 'NT AUTHORITY\NetworkService' -S auto -e LabBookingPostgreSQL17 -w
Start-Service -Name postgresql-x64-17
& "$pgBin\pg_isready.exe" -h 127.0.0.1 -p 5433 -t 5
$env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf'
& "$pgBin\psql.exe" -X -w -h 127.0.0.1 -p 5433 -U lab_booking_app -d lab_booking -v ON_ERROR_STOP=1 -c 'SELECT current_database(), current_user, inet_server_port(), current_setting(''server_version'');'
```

新实例显式使用 `listen_addresses='127.0.0.1'`、`port=5433`、`timezone='UTC'`、`password_encryption='scram-sha-256'`。项目使用本机生成的单独数据库密码，经受保护的 `%LOCALAPPDATA%\LabBooking\PostgreSQL17\pgpass.conf` 提供，也可在 Django 的 `OPTIONS['passfile']` 传入此文件路径。引导管理员密码以 Windows DPAPI 保存，初始化用临时明文文件，执行完成后清理。 [EDB 安装参数](https://www.enterprisedb.com/docs/supported-open-source/postgresql/installing/command_line_parameters/) · [PostgreSQL initdb](https://www.postgresql.org/docs/17/app-initdb.html) · [PostgreSQL pg_ctl](https://www.postgresql.org/docs/17/app-pg-ctl.html)

### 负责人验收与只读复查

负责人在本次会话正式接受 R-03 本机环境准备和连接验证，指定项目使用独立 PostgreSQL 17.12 服务及 `5433`，保留原 PostgreSQL 11.17 服务和数据库。原安装命令、失败与修复、连接与权限实测均保留。 [决策日志 D-016](../../decision-log.md#d-016-2026-11-21-负责人批准-r-03-本地环境方案)

2026-11-21 抽查使用项目 `.venv` 运行 `pip check`，输出 `No broken requirements found.`。已装版本与前表及依赖清单一致，Python `Asia/Shanghai` 跨日和 UTC 往返再次通过。`.venv/install-report.json` 和本机 `install-result.txt`、`install-retry-result.txt` 均仍存在。

`Get-CimInstance Win32_Service` 与 `Get-NetTCPConnection` 显示旧服务仍以 PID `4888` 运行，旧监听 PID `6064`，旧 `pg_isready` 在 `5432` 返回接受连接。新服务仍以 PID `30504` 运行，`127.0.0.1:5433` 监听 PID `29800`。三条 `psql` 用原凭据文件分别执行只读 `SELECT`，均报告服务端 `17.12`、端口 `5433`、会话 `UTC` 和 `transaction_read_only=on`，库级 `CONNECT` 检查如下。

| 认证角色 | 实际连接库 | 可连业务库 | 可连测试库 |
| --- | --- | --- | --- |
| `lab_booking_app` | `lab_booking` | 是 | 否 |
| `lab_booking_migrator` | `lab_booking` | 是 | 否 |
| `lab_booking_test` | `test_lab_booking` | 否 | 是 |

该项验收覆盖本机运行环境、实际数据库连接和隔离。应用模型、迁移、预置账号、业务测试与第二台机器复现各有后续验证节点。 [Sprint 1 启动确认与交接](../../_bmad-output/planning-artifacts/sprint-plan.md#9-sprint-1-启动确认与-story-11-交接)

## R-01 首次迁移与预置账号规则

**首次迁移前**，在 Django 项目设置中配置 `AUTH_USER_MODEL = 'accounts.User'`，并将 `accounts` 加入 `INSTALLED_APPS`。`accounts.User` 继承 `AbstractUser`，在 `accounts` 的首个迁移（通常为 `0001_initial`）中创建。其他应用的用户外键引用 `settings.AUTH_USER_MODEL`，迁移依赖指向该可替换模型。执行 `migrate` 前，核对实际目标库、用户模型和 `migrate --plan` 的依赖顺序。 [Django 自定义用户模型](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model)

**角色存储值**固定为 `student`（学生）、`teacher`（教师）、`admin`（业务管理员）。`role` 由创建方显式提供，应用层采用 `TextChoices`，首个迁移同时落下非空约束及限定这三个值的数据库检查约束。省略、空值、空字符串及未知值均拒绝。角色无默认值。 [Django 字段选项](https://docs.djangoproject.com/en/5.2/ref/models/fields/#choices) · [Django 数据库检查约束](https://docs.djangoproject.com/en/5.2/ref/models/constraints/#checkconstraint)

**默认权限**为拒绝受保护业务。服务端只在用户已登录、账号可用、业务角色有效且满足该操作的角色与对象归属条件时允许访问。学生和教师按 FR-002 访问共享目录和占用信息、提交本人预约并访问授权的本人记录。业务管理员只使用已有授权的维护、查询与处理入口，提交预约的请求一律拒绝。三类预置账号均以 `is_staff=False`、`is_superuser=False` 创建，Django 组和直接权限留空。即使这些 Django 标志或权限被设置，也不产生业务授权。权限核对以 [FR-001／FR-002](../../_bmad-output/planning-artifacts/PRD.md#41-登录与访问控制uj-1uj-2uj-3) 和 [PC-008](../../_bmad-output/planning-artifacts/project-context.md#pc-008-服务端角色归属及单一业务入口) 为准。

**账号预置**在迁移成功后单独执行。从负责人批准的受保护输入读取明确的用户名、角色和新账号初始密码。先校验清单与重复用户名，再在同一事务中按唯一用户名补齐缺失账号。用 Django 的 `set_password()` 生成哈希。对已存在且角色一致的账号直接跳过，保留密码、角色、启用状态、权限与历史。已有用户名与预置角色冲突时报告冲突并回滚本批写入。真实密码仅在获准执行时读取，仓库、迁移文件和日志只保留无秘密的配置或证据。预置通过受控初始化操作执行，项目维持预置登录和专用业务页面。 [Django 密码接口](https://docs.djangoproject.com/en/5.2/ref/contrib/auth/#django.contrib.auth.models.User.set_password)

**待验证证据**包括三种角色均可登录、缺失或非法角色在数据库层写入失败、业务管理员在 Django 管理标志为 `False` 时仍能使用已授权的业务入口、学生或教师即使具备 Django 管理标志也无法越权。初始化首次运行创建缺失账号，第二次运行创建数为零且已有密码、角色、权限和历史保持一致，同名异角色失败后本批无新增账号。

## 初始化操作、影响和批准节点

1. 独立服务安装和集群初始化已执行，服务状态、版本、实际监听和数据目录的取证见 R-03 批准后执行记录。
2. 两库和三个角色已创建，目标和认证权限通过 `psql`、psycopg 和临时 Django 设置验证。跨库连接验证使用只读检查，首轮失败及重试结果已记录。
3. 仓库当前尚无 Django 项目及迁移。项目代码获准实施后，按 [R-01 规则](#r-01-首次迁移与预置账号规则)核对设置、迁移与目标库，先执行 `manage.py check` 和 `manage.py migrate --plan`。迁移会创建或更改 Django 表和数据库对象，按批准的目标和计划执行后核对运行角色的对象权限。
4. 迁移完成后确认预置清单及目标库，再按 R-01 规则执行账号写入并验证重复运行、登录和会话。使用 `USE_TZ=True`、`TIME_ZONE='Asia/Shanghai'`。数据库侧的时间往返、迁移、预置账号及应用启动均记录真实结果。

## 文件保护与 Sprint 启动待确认

- `git check-ignore -v` 检查项目 `.venv/`、`.env`、`.env.local`、`.env.test.local`、`.secrets/`、`.pgpass`、`.my_pgpass`、`pgpass.conf` 及 `.key` 文件的忽略命中。`git ls-files --cached --ignored --exclude-standard` 结果为空。共享示例配置只用占位值。
- 需团队提供实际起止日期、三位成员逐人的净可用工时及不可用时段、八条 Story 的任务估算与开发／独立评审／验收分工，以及 Sprint 1 演示及验收窗口。
- 需负责人确认 Story 2.1 的专项容量和执行人，覆盖实现、T-02 补查、数据夹具、20 个独立授权请求 × 10 轮、时间边界、故障与回滚、权限用例、证据整理和复测。
- R-01 的人工决定及 R-03 的本机安装、数据库连接和权限已取证。应用迁移、预置账号及第二台机器复现仍待各自的实施与验证节点。环境准备基于 [既有 Sprint 规划提交 546faaa](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/546faaa0216b1b765e0e3a3b4d53b3186dbc8c04)。准备时 Story 状态为 `backlog`，负责人随后正式批准启动。课程取证要求见 [课程基线](../course-requirements.md)。

