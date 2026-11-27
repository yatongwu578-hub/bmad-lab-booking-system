# Sprint 1 整体验收与回顾准备

**2026-11-27（北京时间）整理，团队整体验收与回顾尚无发生记录。** 原计划 11 月 22～26 日，最后一条 Story 的正式证据和负责人批准实际发生在 11 月 27 日。不追改计划，不替团队发言，不把本材料当作 Epic 2 回顾。Sprint 8／5、实验 A 原候选与控制条件均不变。

| Story | 状态 | 可运行入口和追溯 |
| --- | --- | --- |
| 1.1 | done | 登录、身份及退出；[规格与验收](spec-1-1-preset-account-login.md) |
| 1.2 | done | 管理员新增设备；[验收](story-1-2-final-acceptance.md) |
| 1.3 | done | 三角色设备目录和详情；[验收](story-1-3-final-acceptance.md) |
| 1.4 | done | 管理员编辑基础字段，不改设备身份；[验收](story-1-4-final-acceptance.md) |
| 2.1 | done | 师生申请、冲突保护和按需失效；[验收与 NFR-001](story-2-1-final-acceptance.md) |
| 2.2 | done | 三角色按具体设备和北京日期查占用；[验收](story-2-2-final-acceptance.md) |
| 2.3 | done | 师生本人预约、状态和历史；[验收](story-2-3-final-acceptance.md) |
| 2.5 | done | 管理员预约列表、设备筛选、详情和历史；[验收](story-2-5-final-acceptance.md) |

按 [README](../../README.md) 启动 Python 3.13.17／Django 5.2.19／PostgreSQL 17.12，用现有角色演示申请→占用→本人结果→管理员查询。Sprint 1 无批准、拒绝、本人或管理员取消及维修停用操作。2.4、2.6、2.7、2.8、3.1 保持 backlog。 [PRD](../planning-artifacts/PRD.md) → [Architecture／ADR](../planning-artifacts/architecture.md) → [Story／AC](../planning-artifacts/epics.md) → 上表逐项验收与原始证据。 [计划](../planning-artifacts/sprint-plan.md) · [状态](sprint-status.yaml)

## NFR-002 已交付入口实际分母

沿用 PRD 的拒绝、无泄露、无业务变化口径。每个 Story 取已归档成对矩阵；开发、独立复验和正式重复证据不叠加，合法对照、一般输入错误和未交付操作不加入分母。

| Story | 拒绝通过／分母 | 合法对照单列 |
| --- | --- | --- |
| 1.1 | 16／16 HTTP，另有直接视图 1／1 不入合计。 | 三角色登录、身份、退出。 [矩阵](story-1-1-dev-evidence.md) |
| 1.2 | 6／6，匿名、学生、教师各 GET 和 POST。 | 管理员合法新增。 [验收](story-1-2-final-acceptance.md) |
| 1.3 | 8／8，无会话／未知会话 × 目录／详情 × GET／HEAD。 | 三角色合法 GET／HEAD，12／12。 [独立复验](story-1-3-independent-recheck.md) |
| 1.4 | 6／6，核心角色拒绝矩阵；CSRF、诊断及等锁边界另留证。 | 管理员合法读、编辑且编号状态不变。 [验收](story-1-4-final-acceptance.md) |
| 2.1 | 13／13，独立权限组。 | 师生合法申请和本人路径。 [D-040](story-2-1-targeted-independent-recheck/d040-independent-final-review.md) |
| 2.2 | 3／3，匿名、停用会话和等锁撤权。 | 三角色合法详情、日期占用 HTTP 200。 [独立复验 AC-5](story-2-2-independent-recheck.md) |
| 2.3 | 13／13，直接 12、等锁撤权 1。 | 师生本人列表和历史，伪造归属参数的受限 200 另列。 [独立复验](story-2-3-independent-recheck.md) |
| 2.5 | 21／21，初始拒绝 20、等锁撤权 1。 | 管理员全量、筛选与详情。正式 9 次拒绝、7 次管理员管理请求单列，不重复入分母。 [隔离矩阵](story-2-5-m01-independent-run-result.md) · [正式回执](story-2-5-w01-final-evidence/verified-receipt.json) |

**已交付入口上述主矩阵 86／86（100%），失败 0。** 不是全项目 NFR-002 结论，取消、审核及设备状态转换待后续独立验收。NFR-001 复用历史 20 请求 × 10 轮，每轮 1 个 201、19 个 409、1 条有效待审，未重跑。 [NFR 定义](../planning-artifacts/PRD.md#nfr-002-权限隔离) · [NFR-001 原证](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

## 团队回顾待讨论

- 已验证有效的做法：可测 AC 和独立复审、用隔离证据覆盖正式不造数场景、最小权限与独立读回、提交后分阶段恢复不重放写操作。
- 待讨论的改进：从 W01 的序列比较、原生编码和运行中 stdout 共享三类实际失败提炼预检；工具变化优先做同形 Windows 活进程验证并归档原生退出码。第二台 Windows 复现仍跟踪。 [失败与恢复](story-2-5-w01-recovery-evidence.md) · [延期台账](deferred-work.md)
- 不预填团队意见、回顾结论、获批行动项、会议日期或实验 A 五项实测。课程第 25、26、27、33、34、36 页按[课程基线](../../docs/course-requirements.md)及团队既有审核落实，不声称取得 PPT 原件。
