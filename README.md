# bmad-lab-booking-system

实验室设备预约管理系统｜软件工程管理课程大作业｜3人团队

## Windows 本地启动

Story 1.1 提供统一的 `/login/` 和只读的 `/identity/`。Story 1.2 提供管理员新增入口 `/equipment/new/`。使用 Python 3.13.17（64 位）、[固定依赖](requirements.txt)及独立的 PostgreSQL 17.12 实例 `127.0.0.1:5433`。环境准备记录列出两库、三个角色和受保护凭据文件的设置。 [Sprint 1 环境准备](docs/team/sprint-1-environment-preparation.md)

在仓库根目录打开 PowerShell。Python 3.13.17 已安装但启动器不可用时，可用该版本的 `python.exe` 完整路径执行 `-m venv`。

```powershell
py -3.13-64 -m venv .venv
$venvPython = '.\.venv\Scripts\python.exe'
& $venvPython -m pip install --only-binary=:all: -r requirements.txt
$env:PGPASSFILE = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf'
$env:LAB_BOOKING_SECRET_KEY = & $venvPython -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

如密码文件保存在其他受保护目录，将 `PGPASSFILE` 指向其绝对路径。以上密钥只保留在当前 PowerShell 进程环境中，重新生成会使原有登录会话失效。重启时需要继续保留会话，可在受保护的本机环境中沿用原密钥。缺少数据库模式、密码文件或密钥时，Django 会报出对应配置项。

`LAB_BOOKING_DB_MODE` 决定库和角色，连接固定为 `127.0.0.1:5433`，数据库密码只从 `PGPASSFILE` 获取。在运行下方命令前，先在当前 PowerShell 检查冲突环境变量。若存在冲突，在此终端移除提示的变量后重新执行。

```powershell
$pgConflicts = @('PGHOST', 'PGHOSTADDR', 'PGPORT', 'PGDATABASE', 'PGUSER',
    'PGPASSWORD', 'PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS') |
    Where-Object { Test-Path "Env:$_" }
if ($pgConflicts) { throw "请先移除冲突的 PostgreSQL 环境变量：$($pgConflicts -join ', ')" }
```

| `LAB_BOOKING_DB_MODE` | 数据库 | PostgreSQL 角色 | 用途 |
| --- | --- | --- | --- |
| `migration` | `lab_booking` | `lab_booking_migrator` | 审核迁移计划、执行获准迁移及预置 |
| `runtime` | `lab_booking` | `lab_booking_app` | 本地应用运行 |
| `test` | `test_lab_booking` | `lab_booking_test` | 在预建的独立测试库运行测试 |

先以迁移角色检查配置、版本、实际身份及迁移计划。核对连接返回 `lab_booking`、`lab_booking_migrator`、`127.0.0.1`、`5433` 和 `17.12`。负责人确认目标及计划后，执行 `migrate`。Django 在每条新连接上先核验实际库、角色、地址、端口和版本，核验失败即关闭连接。

```powershell
$env:LAB_BOOKING_DB_MODE = 'migration'
$pgBin = 'C:\Program Files\PostgreSQL\17\bin'
& "$pgBin\psql.exe" -X -w -h 127.0.0.1 -p 5433 -U lab_booking_migrator -d lab_booking -v ON_ERROR_STOP=1 -c 'SELECT current_database(), current_user, host(inet_server_addr()), inet_server_port(), current_setting(''server_version'');'
& $venvPython manage.py check
& $venvPython manage.py makemigrations --check --dry-run
& $venvPython manage.py migrate --plan
```

```powershell
& $venvPython manage.py migrate
```

迁移后由项目库对象所有者核对现有权限，经负责人批准后才执行以下授权步骤。连接及授权置于同一 `psql` 会话和事务。目标不符或任一语句失败时整批回滚。账号表仅开放认证需要的读权限和两列更新权限，迁移记录供运行时只读检查，会话表支持登录和退出。测试角色只在隔离库执行测试。设备新增仅开放指定列的 INSERT 与主键返回所需的 SELECT。 [Story 1.2 授权实测](_bmad-output/implementation-artifacts/story-1-2-runtime-evidence.md#实际授权)

```powershell
@'
DO $$
BEGIN
    IF current_database() IS DISTINCT FROM 'lab_booking'
       OR current_user IS DISTINCT FROM 'lab_booking_migrator'
       OR session_user IS DISTINCT FROM 'lab_booking_migrator'
       OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
       OR inet_server_port() IS DISTINCT FROM 5433
       OR current_setting('server_version_num') IS DISTINCT FROM '170012' THEN
        RAISE EXCEPTION 'PostgreSQL target or role mismatch';
    END IF;
END;
$$;
GRANT USAGE ON SCHEMA public TO lab_booking_app;
GRANT SELECT ON TABLE public.accounts_user TO lab_booking_app;
GRANT UPDATE (last_login, password) ON TABLE public.accounts_user TO lab_booking_app;
GRANT SELECT ON TABLE public.django_migrations TO lab_booking_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.django_session TO lab_booking_app;
GRANT INSERT (number, name, category, location, description, status), SELECT (id)
ON TABLE public.equipment_equipment TO lab_booking_app;
'@ | & "$pgBin\psql.exe" -X -w -h 127.0.0.1 -p 5433 -U lab_booking_migrator -d lab_booking -v ON_ERROR_STOP=1 --single-transaction -f -
if ($LASTEXITCODE -ne 0) { throw '数据库授权失败，停止启动流程。' }
```

迁移成功后，由负责人单独确认目标数据库及受保护的 UTF-8 JSON 清单，再执行预置。清单为数组，每项含 `username`、`role`、`password` 三个字符串字段。角色取 `student`、`teacher`、`admin`，账号按 Django 登录表单规则规范化。将真实清单放在仓库外、访问受限的本机目录，并把下例路径替换为实际路径。命令只报告计数或脱敏错误。

```powershell
$env:LAB_BOOKING_DB_MODE = 'migration'
$manifestPath = Join-Path $env:LOCALAPPDATA 'LabBooking\Protected\accounts.json'
& $venvPython manage.py seed_accounts --manifest $manifestPath
if ($LASTEXITCODE -ne 0) { throw '预置账号失败，停止启动流程。' }
$env:LAB_BOOKING_DB_MODE = 'runtime'
& $venvPython manage.py runserver 127.0.0.1:8000 --noreload
```

访问 `http://127.0.0.1:8000/login/`，使用获准预置账号登录后核对身份页的账号、角色和刷新结果。点击身份页的“退出登录”应回到登录页，再访问 `/identity/` 应引导登录。错误或缺失凭据应显示表单错误，`/admin/` 和 `/register/` 应返回 404。三种角色均使用同一登录地址。`runserver` 仅用于本地开发和演示。

管理员登录后访问 `http://127.0.0.1:8000/equipment/new/`，新增后核对成功页与「可用」状态。同号重提会提示编号已存在。学生和教师访问该入口返回 403。D-026 验证过的本机业务库已完成设备迁移与授权，可按运行证据中的本机启动步骤直接运行。 [业务库运行证据](_bmad-output/implementation-artifacts/story-1-2-runtime-evidence.md)

学生、教师或业务管理员登录后，从「我的身份」点击「查看设备目录」，也可直接访问 `http://127.0.0.1:8000/equipment/`。点击设备编号进入 `/equipment/<主键>/` 查看对应设备。目录按设备编号排序。无设备时提示「暂无设备」，标识不存在返回 404。设备「可用」不是指定时段可预约的承诺。

Story 1.3 不新增迁移。本机 `127.0.0.1:5433/lab_booking` 已按 D-030 完成以下增量六列读取授权和三角色 Chrome 验证，保留已有 `SELECT(id)` 与六列插入权限，无表级 SELECT、额外写权限、序列权限或转授权。本机无需重复授权。其他环境须在负责人批准后核对目标、表归属和现有权限，再由迁移角色在事务内执行并验证。 [授权与运行记录](_bmad-output/implementation-artifacts/story-1-3-runtime-evidence.md)

```sql
GRANT SELECT (number, name, category, location, description, status)
ON TABLE public.equipment_equipment TO lab_booking_app;
```

使用已迁移的预建隔离库运行完整自动化测试。入口先核验连接与角色权限，检查无待迁移项且账号和会话为空。随后在单进程运行回滚式测试，并比较前后表清单、迁移记录、账号数和会话数。库不存在或核验失败时停止。此入口保留隔离库，不访问维护库，不执行建库、迁移、清库或删库。

```powershell
$env:LAB_BOOKING_DB_MODE = 'test'
& $venvPython manage.py test --keepdb --parallel 1 -v 2
```

## 2026-11-05 老师最新通知

老师取消 M1～M4 阶段性门禁检查和实验 B（需求变更注入），不再下发临时需求变更。团队根据已定需求继续按 BMAD 与敏捷流程完成项目，内部审查和负责人确认后可进入下一工作流，无需等待老师阶段批准。负责人补充的**最终截止日期为 2026 年 11 月 30 日**，最终只提交本 GitHub 项目仓库链接。 [课程要求基线](docs/course-requirements.md)

实验 A 仍为必做；其余产物、两个真实 Sprint、测试、决策、三人贡献及持续 Git 历史要求继续保留。实验 B 取消后的评分处理待老师明确，不自行重分配分数。

## Sprint 规划与审核处置（2026-11-21）

实施就绪结论为[CONCERNS](_bmad-output/planning-artifacts/implementation-readiness.md)，负责人已接受并有条件允许规划，未改为PASS。安装版BMAD 6.12.4已生成[sprint-status.yaml](_bmad-output/implementation-artifacts/sprint-status.yaml)，初始化时3个Epic及13条Story均为backlog，epics正文Story仍draft；3个回顾项为模板optional，不免除课程回顾。格式校验不是软件测试。

罗思婕、周何馨于 2026-11-19 完成业务与质量审核。吴亚彤于 2026-11-21 批准两轮范围和逐项处置，随后确认排期并正式批准 Sprint 1 启动。Sprint 1 为 11 月 22 日至 26 日，保留 1.1～1.4、2.1、2.2、2.3、2.5。Sprint 2 为 11 月 27 日至 29 日，保留 2.4、2.6、2.7、2.8、3.1。2.1 首次验收保留 NFR-001 的 20 个独立授权请求 × 10 轮，实验 A 的 2.6／2.7 保留为候选。R-01、R-03 沿用批准和验收证据，R-04、Read Committed 与 T-01～T-04 按既定节点落实。 [Sprint 启动交接](_bmad-output/planning-artifacts/sprint-plan.md#9-sprint-1-启动确认与-story-11-交接) · [D-017](decision-log.md#d-017-2026-11-21-负责人正式批准-sprint-1-启动)

正式开发一条 Story 一个独立 bmad-build 会话，代码实现后新开会话执行 bmad-code-review。真实测试、问题处置及负责人验收满足后才能标为 done。实验 Y 的一句需求干净对照路径须实验前确认。Story 1.1 和 1.2 已分别于 2026-11-24、2026-11-25 经负责人最终验收并标记 `done`。Epic 1 保持 `in-progress`。Story 1.3 已由负责人最终验收并标记 `done`，独立复审、R1 关闭及业务库运行均已留证。Story 1.4 及其他未开始 Story 保持 `backlog`。 [Sprint 跟踪](_bmad-output/implementation-artifacts/sprint-status.yaml) · [Story 1.1 验收](decision-log.md#d-023-2026-11-24-story-11-负责人最终验收) · [Story 1.2 验收](_bmad-output/implementation-artifacts/story-1-2-final-acceptance.md) · [Story 1.3 验收](_bmad-output/implementation-artifacts/story-1-3-final-acceptance.md)

## 项目与当前进度

项目通过支持电脑和手机浏览器的Web系统提供设备查询、预约申请、冲突检查、管理员审核、取消、状态查询和设备维护，按具体实物唯一编号管理。计划服务学生约50人、教师约6人、管理员约2人。当前业务基线见[Product Brief](_bmad-output/planning-artifacts/product-brief.md)和[正式PRD](_bmad-output/planning-artifacts/PRD.md)。

**截至2026-11-17：M1两轮Product Brief和PRD已定稿；M2第一轮Architecture及第二轮project-context已定稿；Epic/Story文档已final，保留3 Epic、13 Story；Story生命周期仍为draft。** 架构定稿提交为[4e2ff4fdbe58](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/4e2ff4fdbe58024e4bbfea0c63808f639f03c2a5)。罗思婕1项、周何馨4项真实审核意见已由负责人逐项决定并落实文档修改，见[本轮审核汇总](docs/team/m2-epics-summary.md)及[处置记录](docs/team/m2-epics-review-disposition.md)。负责人已正式批准处理及Step-04第三次复核，并授权[C]完成定稿；[Epic／Story 定稿提交 68c2eab](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/68c2eab98c1dd5fa36a3186d27517bbb2f008fd)。随后完成 Sprint 规划及团队审核。M1～M4仅作为内部管理阶段，老师不逐阶段验收。

| 事项 | 当前状态与证据 |
| --- | --- |
| 选题 | 已确定实验室设备预约管理系统；选题登记已通过（团队于2026-11-05确认） |
| 团队协作 | 吴亚彤负责项目/Codex与人工批准；罗思婕、周何馨已提交两轮原始审核 |
| M1第一轮 | Product Brief已定稿；[第一轮总结](docs/team/round1-summary.md)保留当时历史 |
| M1第二轮 | PRD于2026-11-04正式定稿，18条FR、2条可测NFR；成员意见全部处理；[第二轮总结](docs/team/round2-summary.md) |
| 正式审查 | 0 Critical、0 High、无业务阻塞；负责人已人工确认，四项非阻塞待办继续跟踪 |
| M1内部核验 | 文档审查及负责人定稿确认已完成，可进入M2架构；无需等待老师批准 |
| M2第一轮 Architecture | [课程版architecture.md](_bmad-output/planning-artifacts/architecture.md)、[原生ARCHITECTURE-SPINE.md](_bmad-output/planning-artifacts/architecture/architecture-bmad-lab-booking-system-2026-11-05/ARCHITECTURE-SPINE.md)已final；8条ADR/AD一一对应；[总结](docs/team/m2-architecture-summary.md)及[审核处理记录](docs/team/m2-architecture-review-disposition.md) |
| M2第二轮 project-context | [独立文档](_bmad-output/planning-artifacts/project-context.md)已final，2026-11-11负责人正式批准；五部分结构、PC-001～PC-014共14条约束保留；[02eec258a3ac](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/02eec258a3ac768fe68753914fa77ac994620197)仅为草稿提交，正式定稿修改尚未提交或推送 |
| M2 Epic/Story | [定稿](_bmad-output/planning-artifacts/epics.md)文档final，保留3 Epic/13 Story的批准基线；故事设计稿状态与实施状态分开记录，当前实施状态以 [Sprint 跟踪文件](_bmad-output/implementation-artifacts/sprint-status.yaml) 为准（Story 1.1 和 1.2 已 done，其他未开始 Story 为 backlog）；[组员原文](docs/team/m2-epics-requirements-review.md)、[质量原文](docs/team/m2-epics-quality-review.md)及[处置记录](docs/team/m2-epics-review-disposition.md)；[Step-04报告](_bmad-output/planning-artifacts/epics-step-04-validation.md)保留历次验证，第三次复核零开放发现，负责人已批准并完成[C]；见报告第11节 |
| M2 后续就绪及 Sprint 计划 | CONCERNS 保留，两轮日期及 8／5 范围已确认。Sprint 1 启动已获批准，首条 Story 按实际开发状态推进。 [Sprint 1 启动交接](_bmad-output/planning-artifacts/sprint-plan.md#9-sprint-1-启动确认与-story-11-交接) |
| Sprint 1 实现与验收 | Story 1.1～1.3 已完成负责人最终验收。Story 1.2 正式 AC-1～AC-7 独立通过，Django 45/45（含 Story 1.1 的 32/32），AC-6 真实并发、AC-7 事务故障及 D-026 业务库迁移、最小权限和三角色运行验证均有证据。Story 1.3 正式 AC-1～AC-6 满足，独立 55/55 无跳过，R1 已关闭，正式库六列读取授权及三角色运行取证完成。既有延期和第二台 Windows 复现继续跟踪。这些验收不计入实验 A。 [Story 1.1 证据](docs/team/story-1-1-review-disposition.md#负责人最终验收与状态推进2026-11-24-d-023) · [Story 1.2 证据](_bmad-output/implementation-artifacts/story-1-2-final-acceptance.md) · [Story 1.3 验收](_bmad-output/implementation-artifacts/story-1-3-final-acceptance.md) · [延期台账](_bmad-output/implementation-artifacts/deferred-work.md) |

课程原规划为4周、2个Sprint；M1～M4现为内部里程碑，核心考察BMAD、敏捷过程、人类判断和真实证据。每次新BMAD工作流前先读[AGENTS.md](AGENTS.md)及[课程要求基线](docs/course-requirements.md)；命令以已安装[bmad-help](.agents/skills/bmad-help/SKILL.md)为准，独立工作流使用新会话。未取消的课程产物、实验A及BMAD内部就绪检查不因默认流程裁剪而省略。

## M1第二轮交付与三人审核证据

| 证据 | 文件 |
| --- | --- |
| 课程交付PRD | [PRD.md](_bmad-output/planning-artifacts/PRD.md) |
| 原始BMAD定稿 | [prd.md](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/prd.md)；正文与课程版相同，文末引用定义仅适配所在目录 |
| 吴亚彤人工决定和定稿批准 | [D-007～D-011](decision-log.md)、[定稿记录](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/finalization.md)、[原始memlog](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/.memlog.md) |
| 罗思婕需求审核 | [2026-10-31原文](docs/team/round2-requirements-review.md)、[已有提交96e6619](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/96e6619) |
| 周何馨质量审核 | [2026-11-01原文](docs/team/round2-quality-review.md)、[已有提交41c58d6](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/41c58d6) |
| 意见处理与团队决定 | [处理表](docs/team/round2-review-disposition.md)、[规则落实核对](docs/team/round2-resolution-check.md)、[原待决清单关闭记录](docs/team/round2-open-decisions.md) |
| 正式审查及历史 | [审查报告](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/finalize-review.md)、[Memlog Audit](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/memlog-audit.md)、[审查前原稿快照](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/prd-review-snapshot-2026-11-03.md) |
| 定稿验证与后续待办 | [正文一致性验证](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/finalization-verification.md)、[四项责任人及节点](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/finalization.md#四项非阻塞待办继续跟踪) |
| 本次证据整理 | [第二轮总结](docs/team/round2-summary.md)、[相对链接和简报一致性检查](docs/team/round2-evidence-check.md) |

原稿提交证据为[3c3a09d](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/3c3a09d)。以上已有提交由本地Git历史核对，远程可达性本轮未联网验证；第二轮定稿及证据整理已纳入[63d6fac](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/63d6fac8bb815412e2a2e82c058748a5b9e54a97)，当时本地main与origin/main均指向该提交；GitHub提交成功依据团队当时确认。截至2026-11-10，本地main及origin/main均指向状态同步提交[f31a1d115679](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/f31a1d1156791f6dde7ef5c3918aed4d6873a4f1)，正式架构提交为4e2ff4fdbe58。原审查报告中的draft及“等待确认”是当时事实，M1当前状态以2026-11-04定稿追加记录为准。

## 三人分工

| 成员 | 角色 | 实际工作和证据 |
| --- | --- | --- |
| 吴亚彤 | 项目负责人、Codex操作者 | 组织需求讨论、整合产物、传达团队业务决定，人工审核并批准定稿；[决策日志](decision-log.md)、[定稿记录](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/finalization.md) |
| 罗思婕 | 需求负责人 | [第一轮需求输入](docs/team/requirements-review.md)、[第二轮PRD审核](docs/team/round2-requirements-review.md) |
| 周何馨 | 质量负责人 | [第一轮质量输入](docs/team/quality-review.md)、[第二轮PRD审核](docs/team/round2-quality-review.md)；跟踪四项非阻塞质量验证待办，尚未执行 |

不虚构另一次会议、逐人投票或独立批准记录。技术事项后续与实际架构责任人协作，不提前编造架构任命。

## 实际工具与目录

| 工具 | 已有信息及依据 |
| --- | --- |
| BMAD-Method | 6.12.4，core/bmm及Codex集成；[安装清单](_bmad/_config/manifest.yaml)、[安装说明](docs/bmad-installation.md) |
| Codex | 主要AI工具，已有1个ChatGPT Plus可使用Codex；客户端/模型版本未补造，待实际记录；[技能入口](.agents/skills/) |
| GitHub | origin为yatongwu578-hub/bmad-lab-booking-system；已有三人审核贡献；M2第一轮Architecture定稿及审核证据已提交并推送，提交为[4e2ff4fdbe58](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/4e2ff4fdbe58024e4bbfea0c63808f639f03c2a5) |

以下目录树依据本次 git ls-files 生成；工具目录折叠显示，其余列出全部跟踪文件。仅存在本地的未跟踪目录不列入交付。工具附带代码和测试不属于业务实现证据。

```text
bmad-lab-booking-system/
├── .agents/（已跟踪工具文件，折叠）
├── .gitignore
├── AGENTS.md
├── README.md
├── _bmad-output/
│   └── planning-artifacts/
│       ├── PRD.md
│       ├── briefs/
│       │   └── brief-bmad-lab-booking-system-2026-10-29/
│       │       ├── .memlog.md
│       │       ├── addendum.md
│       │       ├── brief.md
│       │       └── finalization.md
│       ├── prds/
│       │   └── prd-bmad-lab-booking-system-2026-10-30/
│       │       ├── .memlog.md
│       │       ├── decision-log-before-evidence-2026-11-04.txt
│       │       ├── finalization-history-manifest.json
│       │       ├── finalization-verification.md
│       │       ├── finalization.md
│       │       ├── finalize-review.md
│       │       ├── finalize-static-checks.md
│       │       ├── memlog-audit.md
│       │       ├── open-items-triage.md
│       │       ├── prd-review-snapshot-2026-11-03.md
│       │       ├── prd.md
│       │       ├── reconcile-product-brief.md
│       │       ├── reconcile-quality-review.md
│       │       ├── reconcile-requirements-review.md
│       │       ├── review-editorial-prose.md
│       │       ├── review-editorial-structure.md
│       │       ├── review-permissions-scope.md
│       │       ├── review-rubric.md
│       │       └── review-state-concurrency.md
│       └── product-brief.md
├── _bmad/（已跟踪工具文件，折叠）
├── decision-log.md
└── docs/
    ├── bmad-installation.md
    ├── course-requirements.md
    └── team/
        ├── README.md
        ├── quality-review.md
        ├── requirements-review.md
        ├── round1-summary.md
        ├── round2-evidence-check.md
        ├── round2-open-decisions.md
        ├── round2-quality-review.md
        ├── round2-requirements-review.md
        ├── round2-resolution-check.md
        ├── round2-review-disposition.md
        └── round2-summary.md
```

## 第一轮历史与当前简报

- [当前课程版Product Brief](_bmad-output/planning-artifacts/product-brief.md)：D-007已授权加入按需失效，当前与定稿PRD一致。
- [第一轮原始brief.md](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/brief.md)、[addendum](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/addendum.md)、[memlog](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/.memlog.md)、[当时定稿记录](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/finalization.md)、[第一轮总结](docs/team/round1-summary.md)保留历史，不要求与后续已授权范围调整后的版本字面相同。
- [第一轮已有提交0a7bd59](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/0a7bd59499359156c0179e2b9ef5623146c3698f)。

## M1～M4课程产物状态

完整要求见[课程基线](docs/course-requirements.md)。不存在的产物仅列名称，不建立空链接。

| 阶段/要求 | 当前证据及待办 |
| --- | --- |
| M1 | 两轮Product Brief和PRD及内部审核、负责人确认已完成，第二轮定稿已提交main，可进入M2架构 |
| M2 | Architecture及8条ADR、[project-context](_bmad-output/planning-artifacts/project-context.md)及14条PC已定稿；Epic/Story文档已final，3 Epic/13 Story的Story状态仍draft，组员5项意见已按负责人决定修改，见[本轮汇总](docs/team/m2-epics-summary.md)。第三次Step-04复核已获负责人批准并完成Finalize。随后完成就绪检查及 Sprint 计划，CONCERNS 经负责人有条件接受。 [就绪证据](_bmad-output/planning-artifacts/implementation-readiness.md) |
| M3 | Sprint 1 已启动，Story 1.1 和 1.2 已验收。其他故事、完整核心 Demo 继续按 Sprint 计划推进。实验 B 已取消。 [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml) |
| M4 | Sprint 2、必做实验 A、根目录 retrospective.md、剩余源码和测试、第二台 Windows 复现、10 分钟录屏及最终版本证据待完成。 |
| 人机决策 | 根目录日志已记录 D-001～D-027，Story 1.2 对应 D-024～D-027。课程要求的否决或实质修改按原始人工判断核对。 [决策日志](decision-log.md) |
| FR追溯 | 18 条 FR 已映射至 ADR／PC 与 Story／AC。Story 1.2 的 FR-016／FR-002 已链接到独立测试和业务库证据。 [追溯与验收](_bmad-output/implementation-artifacts/story-1-2-final-acceptance.md) |
| NFR | 已有两条可测 NFR。Story 1.2 提供 NFR-002 的设备新增入口证据，NFR-001 的预约并发验收仍按原计划取证。 [正式 PRD](_bmad-output/planning-artifacts/PRD.md) |
| Architecture 及 project-context 后续待办 | R-03 已完成本机环境核验，D-024 的 Read Committed 和 D-026 的设备迁移、授权及业务库运行已留证。第二台 Windows 复现仍待执行，其他待办按既定节点推进。 [运行证据](_bmad-output/implementation-artifacts/story-1-2-runtime-evidence.md) · [延期台账](_bmad-output/implementation-artifacts/deferred-work.md) |

## AI使用声明与证据限制

Codex协助完成简报与PRD的讨论、草稿、意见映射、审查、结构文字整理、Finalize及本次课程证据整理。吴亚彤实际作出并传达人工决定、审核批准；罗思婕和周何馨提供原始审核记录。Finalize使用了独立AI审查子代理，其结果不冒充组员意见或老师验收。 Story 1.2 中 Codex 协助实施、自测、独立评审及证据整理，负责人实际批准 D-024～D-027。 [Story 1.2 验收记录](_bmad-output/implementation-artifacts/story-1-2-final-acceptance.md)

课程 PPT 原页未在仓库发现，依据[课程基线](docs/course-requirements.md)及团队审核材料记录的第 27 页口径。2026-11-05 通知由团队转述，未另附通知原件。历史文档及过去记录保留当时事实。R-03 本机环境验证已验收，Sprint 1 启动已批准。后续继续保存实际工具与模型、会话和 Git 证据、每条 NFR 的运行测试及实验 A 数据。
