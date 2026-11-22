---
title: 'Story 1.1 使用预置账号登录并获得明确业务身份'
type: 'feature'
created: '2026-11-21'
status: 'in-progress'
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
- [ ] `accounts/models.py`、`accounts/migrations/0001_initial.py` 在首迁创建 User 与角色约束。用 venv 执行 `manage.py check`、`makemigrations --check --dry-run`、`migrate --plan`。查库、角色、端口、版本及依赖顺序。负责人确认目标及计划后以迁移账号执行 `migrate`，再核对运行授权。
- [ ] `accounts/management/commands/seed_accounts.py` 在迁移成功且负责人单独确认目标及受保护清单后，用迁移账号执行 `seed_accounts --manifest <路径>`。只输出计数及脱敏错误。
- [ ] `lab_booking/urls.py`、`accounts/views.py`、`accounts/templates/accounts/{login,identity}.html` 提供 `/login/` 与只读 `/identity/`。
- [ ] `accounts/tests.py` 逐 AC 测试并覆盖预置矩阵、角色约束。`README.md` 给出 Windows 配置、授权和启动命令。

**Acceptance Criteria**

- AC-1 给定三类预置账号，提交正确凭据后，均建立会话并显示本人的账号和角色，刷新保持身份。
- AC-2 给定匿名会话，分别提交未知账号、错误密码或缺字段，均提示失败且无认证会话。每次失败后直接请求身份页，均拒绝返回受保护内容。
- AC-3 给定无有效会话，直接请求身份页时引导登录，无受限内容或业务写入。
- AC-4 给定合法凭据，附加伪造账号 ID 或角色后，只能获得服务端确认的身份。切换 Django 管理标志，业务身份依旧由 `role` 决定。
- AC-5 给定正常 CSRF 流程，合法令牌按凭据认证，缺失或无效令牌返回 403，无认证会话或角色变化。
- AC-6 给定配置完成，检查 URL 配置并直接访问 Admin 与自助注册路径，均无匹配。三类账号从同一登录入口进入。
- AC-7 给定获准环境，按 README 在 Windows 连接 PostgreSQL 17.12、迁移、预置并启动，在浏览器验证 AC-1～6。缺数据库配置时明确失败，Git 差异无秘密。

## Implementation Notes

- 2026-11-21 22:57（北京时间），项目负责人明确回复“批准并继续”，随后正式批准修订规格通过 Checkpoint 1，并要求“现在开始执行Story 1.1开发”。据此完成本规格的 `ready-for-dev` 转换。批准依据和执行边界见[决策 D-018](../../decision-log.md)。
- 2026-11-21 22:58（北京时间），按负责人本次实际开工指令进入 Step 3。Story 1.1 与父 Epic 同步为 `in-progress`。
- 账号、预置命令、登录和身份页、13 个测试方法及 Windows 启动说明已落盘。只读检查通过，实库迁移计划与角色／库隔离见[开发证据](story-1-1-dev-evidence.md)。当前停在实际迁移与授权的确认点。

## Spec Change Log

## Review Triage Log

## Verification

- 实测 `lab_booking_app`、`lab_booking_migrator` 连 `lab_booking`，`lab_booking_test` 连 `test_lab_booking`。三者跨项目库均由服务端拒绝。运行账号仅获账号读取、必要认证字段更新及会话 DML，无 DDL。核对无独立占用表及其授权。
- 测试模式 `NAME`、`TEST.NAME` 均指向测试库。用 `test accounts --keepdb --parallel 1 -v 2` 验证角色遗漏、空值、空串、非法值拒绝入库，预置哈希可验证、重跑零新增且原值保留、异角色整批回滚。运行身份执行 `runserver 127.0.0.1:8000 --noreload`。
- 实施目录 `story-1-1-dev-evidence.md` 按 FR-001／002 → ADR-001／002／008 → AC 记录实际环境及依赖版本、连接、启动、命令、预期／实际、会话、角色、失败原因与复测。T-03 登记成对路由。PC-011 逐项核对拒绝、无泄露及前后数据，记录三项均满足的未授权用例数／总数，合法对照单列。
- `sprint-status.yaml` 状态关联实证。负责人批准 Checkpoint 1 后置为 `ready-for-dev`。按 [Sprint 计划](../planning-artifacts/sprint-plan.md) 开工时，Story 和父 Epic 进入 `in-progress`。开发自测完成后停在 `review`。新会话 `bmad-code-review`、修复、真实复测及负责人验收通过后才到 `done`。
