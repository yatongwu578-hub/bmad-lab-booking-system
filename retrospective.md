# 项目回顾

## Epic 1 已完成的回顾

2026-11-26。登录、设备创建、目录详情和基础维护形成已取证的 Epic 1 增量，四条 Story 均最终验收。 [正式 Epic 1 回顾与证据](_bmad-output/implementation-artifacts/epic-1-retro-2026-11-26.md) · [负责人决定 D-036](decision-log.md#d-036-2026-11-26-story-14-最终验收与-epic-1-收尾)

本轮确认的经验是把 Windows 沙箱可做的静态检查与本机运行分开、单独渲染 BMAD 快照、用业务角色验证最小权限、按阶段留存原始输出和独立读回，以及将独立评审集中在风险和差异。问题处置及拟议行动项见 Epic 1 回顾，不代填个人意见。第二台 Windows 复现仍留项目集成验证。

## Sprint 1 基于证据的回顾 · 2026-11-27

以安装版 BMAD 6.12.4 的证据盘点、发现、处置建议和验收判断结构复阅本 Sprint，不以 Epic 2 替代 Sprint 1、也不关闭未交付的 Epic。负责人已确认八条逐项验收。原计划结束 11 月 26 日，最后 Story 的正式验证和验收实际在 11 月 27 日。本文日期是回顾材料整理日期，不是已举行的会议。以下为证据归纳及建议，不代填成员意见或获批行动项。 [整体验收与追溯](_bmad-output/implementation-artifacts/sprint-1-final-acceptance-2026-11-27.md)

| 发现及影响 | Sprint 2 改进建议 |
| --- | --- |
| Windows 沙箱阻断原项目解释器（退出 103）、安装版 BMAD 托管解释器目录及受保护凭据。3.14 仅供 BMAD 工具，不能拿来替代正式 3.13.17。 [2.5 Checkpoint](_bmad-output/implementation-artifacts/story-2-5-checkpoint-1.md) | 开工先用既有只读预检确认解释器、工具、角色和端口。BMAD 用批准的独立临时渲染方式，运行证据从普通 PowerShell 获取。预检明确受限时走已有替代路线，不重装或反复跑失败命令。 |
| 正式授权曾因 SQL 字段或 ACL 处理误报、CP936 被当 UTF-8、Windows 活子进程重定向共享失败而中断。2.5 授权实际成功后仍先失败一次，恢复仅做只读与浏览器，无重授。 [1.4 正式证据](_bmad-output/implementation-artifacts/story-1-4-runtime-evidence.md) · [2.5 正式与失败链](_bmad-output/implementation-artifacts/story-2-5-w01-recovery-evidence.md) | 共用精确列差集、独立读回、受控 UTF-8／原始诊断字节和活进程 HTTP 就绪做法；工具确有变化才定向复验。提交与验后分段，结果不明先只读，禁止盲目回放。 |
| 2.5 略过逐阶段恢复会把已通过检查连同故障阶段重复执行。22:02、22:31 的实际中断及 22:40 恢复说明包装失败可独立于业务。可核实的是多轮等待和恢复，不是团队工时或真实时间预算。 [正式验收](_bmad-output/implementation-artifacts/story-2-5-final-acceptance.md) | 统一复用成熟入口，只对变动风险做必要现场验证；用一次自动归档记录退出码、输入散列、请求与前后快照。既有授权范围内不重复审批，不让组员复抄机器结果，保留新权限的必要决定。 |
| 复用设备锁、锁后授权与重读、固定候选、统一判定时刻、FR-018 与历史同事务，2.1 标准竞争 20×10 据原证明；独立评审实际发现 2.5 M01 短路问题并确认整改，验收不依赖沙箱假通过。 [D-040](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d040-independent-final-review.md) · [2.5 M01](_bmad-output/implementation-artifacts/story-2-5-m01-independent-run-result.md) | 保留共享机制和独立 Review，新增权限、时序、历史和失败路径优先实测；不以已通过的旧风险重复验证替代新行为测试。 |

**前轮跟踪。** epic-1-retro-item-1-windows-preflight 已在 W01 有同形预检证据但还缺第二台 Windows。epic-1-retro-item-2-verification-evidence 已有阶段和独立只读恢复实例。epic-1-retro-item-3-login-return-path 维持原任务，2.5 的拒绝和合法导航不替代编辑路由回归。三项仍按原状态跟踪，未经人工确认不代改。这些都是改进提案，不增加 Story 或自动实施。 [状态与行动项](_bmad-output/implementation-artifacts/sprint-status.yaml)

团队发言、议定行动及实际启动记录在[同一次集中确认](_bmad-output/planning-artifacts/sprint-2-startup-and-experiment-a.md#三人一次集中确认)补录真实事实。Sprint 2 回顾、实验 A 数据及录屏仍待实际发生。 [课程基线](docs/course-requirements.md)
