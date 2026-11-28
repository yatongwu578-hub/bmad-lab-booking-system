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

团队发言、议定行动及实际启动记录在[同一次集中确认](_bmad-output/planning-artifacts/sprint-2-startup-and-experiment-a.md#三人一次集中确认)补录真实事实。Sprint 2 共同回顾及录屏仍待实际发生。 [课程基线](docs/course-requirements.md)

## 实验 A 业务实施截面（D1，非 C 封账）

两组在 2026-11-28T21:10:43.0878369+08:00 正式 done。X、Y 各 3 个计入的实际独立 Story 会话，首轮均 0/1（0%）。Y 的 R1 命中 PC-004/005，X 无已确认命中。R1 截面有两个可区分的 Y ADR 实现偏离，期末累计和 done 后返工仍待共同观察截止 C，不能先填 0。

目前 Y−X 的故事会话差为 0、首过率差为 0 个百分点、R1 规则命中差为 +2。命中主要集中在锁后唯一取时和业务拒绝不能撤销合法 FR-018 的边界。12 个故事的机械情景是 0 个额外首过、0 个额外会话，规则命中差情景为 24；这些计数不能直接抵扣规划工时。共同计时与 C 期末证据未齐，净收益不预判。样本仅两条，处理方式与不同故事绑定，另有 Y 的 S0 后、整改前跨组评审材料暴露，必须限制因果解释。详见 [实际度量及分析材料](docs/team/experiment-a-implementation-evidence.md)。

正式验证不造样，只对已核验的终态详情进行 Chrome 验证，批准与拒绝正向、并发和故障仍绑定隔离证据。正式工具第一次启动器/子进程 PID 判断失败及后续真实恢复均保留，没有覆盖首评或印证业务回归。下一步仅 [Story 2.8 开发准备](_bmad-output/implementation-artifacts/story-2-8-build-handoff.md)，Sprint 8/5 不变。
