# Story 1.3 最终验收记录

2026-11-25，项目负责人正式批准「查看设备目录与具体设备详情」最终验收通过。实施规格和 Sprint 跟踪为 `done`。Epic 1 保持 `in-progress`，Story 1.4 及其余未开始的 Story 保持 `backlog`。 [负责人决定 D-031](../../decision-log.md#d-031-2026-11-25-story-13-负责人最终验收) · [实施规格](spec-1-3-view-equipment-catalog.md) · [Sprint 状态](sprint-status.yaml)

## 正式验收依据

FR-003／FR-002 → ADR-001／002／003 → PC-003／008／011 → 正式 AC → 独立回归及业务库核证。以下只覆盖本 Story，不等同于完整 NFR-002。 [正式 PRD](../planning-artifacts/PRD.md) · [正式 Architecture](../planning-artifacts/architecture.md) · [正式 Story 与 AC](../planning-artifacts/epics.md#story-13-查看设备目录与具体设备详情)

| AC | 负责人接受的实证 |
| --- | --- |
| AC-1 | 学生、教师和业务管理员可见目录及五字段，隔离夹具准确区分可用、维修、停用。 |
| AC-2 | 目录链接及直达均对应所选设备，六字段与读库一致，不承诺指定时段可预约。R1 多行说明、连续空格和安全转义通过独立 Chrome 验证，已由 D-030 关闭。 |
| AC-3 | 隔离库无设备时返回 200 和「暂无设备」，不显示虚构设备。 |
| AC-4 | 不存在的设备返回 404，无替代对象，设备数据不变。隔离库及本机业务库均取证。 |
| AC-5 | 未登录或退出后受保护页面引导登录。隔离 T-03 中 8 个拒绝用例及 12 个合法对照分别通过，未泄露受限资料或改变设备数据。 |
| AC-6 | 隔离 SQL 检查及快照表明普通读取只 SELECT，不获业务写锁、不触发 FR-018。业务库三角色浏览器操作前后设备数量和七列摘要一致。 |

- **独立回归**。本轮沿用原 Python 3.13.17、隔离 PostgreSQL 17.12 的 55/55 独立结果，无跳过，含真实 Chrome 的 R1 布局和转义。不把开发自测或首轮独立 0 项记作独立通过。 [独立复审](story-1-3-independent-recheck.md) · [原始输出](story-1-3-independent-recheck-output.txt)
- **正式库运行**。D-030 已完成六列 SELECT，原 `SELECT(id)` 和六列 INSERT 保持不变。三种既有账号经 Chrome 实际点击和直达详情，字段与 `EQ-DEMO-S12-20261125` 一致，404、匿名及退出后拦截均通过。前后各一台设备、17 条迁移、一条既有会话，设备全字段摘要一致。 [业务库运行](story-1-3-runtime-evidence.md) · [原始输出](story-1-3-runtime-output.txt)
- **过程与人工体验**。保留开发自测、首轮静态独立评审及未执行测试、负责人处置、R1 整改、实际独立复审、授权和真实运行。三人共同操作和审阅的范围沿用已记录事实，本次没有新增逐人浏览器体验、评价或投票记录。 [开发证据](story-1-3-dev-evidence.md) · [首轮独立评审](story-1-3-independent-review.md) · [处置](story-1-3-review-disposition.md) · [整改交接](story-1-3-remediation-handoff.md)

## 课程证据与后续

| PPT 页 | 核对 |
| --- | --- |
| 26 | 已有正式 FR、ADR、PC、Story、AC 和 Test→实际结果链。 |
| 27 | 保留 `review → in-progress → review → done` 的实际评审整改和负责人验收决定。 |
| 33 | 同仓保留实现、测试、评审、运行证据和真实 Sprint 跟踪。 |
| 34 | 既有实验 A 条件不变，不计入 Story 1.3 的任何运行或测试结果。 |
| 36 | 根目录 D-028～D-031 保留真实建议、人工判断、结果和验证。 |

页码按课程基线及团队记录核对。D-029 已批准的延期、后续浏览器测试入口观察及第二台 Windows 待复现事项保留。R2 已取得本机验证证据，历史记录不删除。此次只按 6.12.4 Build 收尾和负责人授权更新状态、归档并办理 Git 同步，未重复跑测试，未修改业务代码或数据库，未开始 Story 1.4。凭据、备份、虚拟环境、临时脚本和渲染缓存不纳入交付。 [课程基线](../../docs/course-requirements.md) · [延期台账](deferred-work.md) · [Git 基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/09085cbc0b03dc5a3e03f54ba8604f15579b2533)
