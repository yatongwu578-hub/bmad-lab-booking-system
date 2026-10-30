# bmad-lab-booking-system

实验室设备预约管理系统｜软件工程管理课程大作业｜3人团队

## 项目简介与课程目标

选题为**实验室设备预约管理系统**，拟围绕实验室设备预约中的实际问题开展需求核验与系统建设。吴亚彤已确认现实预约方式、痛点、约58人的计划服务规模及首版范围，见[产品简报](_bmad-output/planning-artifacts/product-brief.md)。同一设备重叠时段不能存在冲突的有效预约是核心约束，技术实现尚未决定；正式PRD需求基线尚未形成。

课程以4周、2个Sprint、M1–M4四个里程碑组织 AI辅助敏捷交付，重点考察BMAD方法、敏捷过程、人类判断与可追溯证据。所有产物应集中在同一个GitHub仓库，保留真实的文档迭代、决策、评审、测试和Git历史。

开始任何新的 BMAD 工作流前，请先阅读：

- [仓库工作约定](AGENTS.md)
- [课程要求与验收基线](docs/course-requirements.md)
- [BMAD安装与团队配置说明](docs/bmad-installation.md)

课程硬性要求优先于 BMAD 默认流程；如有冲突，应说明差异并由团队决定，不能擅自省略必交产物、实验或门禁。

## 当前进度

**M1 第一轮已完成 Product Brief 工作流、负责人审核和定稿；M1 第二轮 PRD 尚未开始，M1 整体门禁尚未通过。**

| 事项 | 当前状态 |
| --- | --- |
| 项目选题 | 已确定为实验室设备预约管理系统；选题登记及合规核验待完成 |
| 团队 | 3 人；吴亚彤负责项目与Codex操作，罗思婕负责需求，周何馨负责质量；两位成员已提交第一轮记录 |
| 环境与仓库 | 已有BMAD安装快照、Codex技能入口、共享配置及GitHub仓库 |
| 课程与安装文档 | 已存在，见上方链接 |
| M1 第一轮 Product Brief | 已完成工作流、负责人审核及 Finalize；B/C已提交审核记录 |
| M1 第二轮 PRD | 尚未开始 |
| M2、M3、M4 | 尚未开始；架构、ADR、Epic/Story、Sprint及后续实施待开展 |
| 正式业务开发、业务测试、实验及复盘 | 尚未开展 |
| M1 整体门禁 | 尚未通过 |

在完成并确认M1门禁前，不主动开始正式业务代码实现；后续还须按课程顺序完成架构、故事与 M2 就绪门禁。

## 实际工具与仓库结构

| 工具 | 当前实际信息 | 仓库依据 |
| --- | --- | --- |
| BMAD-Method | **6.12.4**；内置 `core`、`bmm` 模块；Codex 集成；`installShims: false` | [安装清单](_bmad/_config/manifest.yaml) |
| Codex | 主要 AI 工具；已有 1 个 ChatGPT Plus 可使用 Codex；具体客户端版本和实际模型待记录 | [安装说明](docs/bmad-installation.md)、[技能入口](.agents/skills/) |
| GitHub | 当前仓库为 `yatongwu578-hub/bmad-lab-booking-system`，用于统一保存产物与版本证据；三人协作权限待确认 | 当前 Git `origin` 配置 |

BMAD 工作流以已安装的 [bmad-help](.agents/skills/bmad-help/SKILL.md) 为准，每个独立工作流使用新会话。安装文件和技能入口的存在不代表正式工作流已运行成功。

当前已纳入 Git 跟踪的主要结构如下，BMAD 附带的脚本和测试属于工具资源，不是业务实现与业务测试证据：

```text
bmad-lab-booking-system/
└── .agents/
└── .gitignore
└── AGENTS.md
└── README.md
└── _bmad/
└── _bmad-output/
    └── planning-artifacts/
        └── briefs/
            └── brief-bmad-lab-booking-system-2026-10-29/
                └── .memlog.md
                └── addendum.md
                └── brief.md
                └── finalization.md
        └── product-brief.md
└── decision-log.md
└── docs/
    └── bmad-installation.md
    └── course-requirements.md
    └── team/
        └── README.md
        └── quality-review.md
        └── requirements-review.md
        └── round1-summary.md
```

M1 第一轮提交凭证：[0a7bd59499359156c0179e2b9ef5623146c3698f](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/0a7bd59499359156c0179e2b9ef5623146c3698f)。

## 三人团队分工

以下团队分工：

| 成员 | 本轮角色 | 本轮实际职责 |
| --- | --- | --- |
| A：吴亚彤 | 项目负责人、Codex操作者 | BMAD工作流、项目规划、GitHub管理和产物整合；本轮完成业务取舍、人工审核和定稿批准 |
| B：罗思婕 | 需求负责人 | 需求分析及功能审核；已提交[第一轮需求记录](docs/team/requirements-review.md) |
| C：周何馨 | 质量负责人 | 质量检查、风险分析及后续测试反馈；已提交[第一轮质量记录](docs/team/quality-review.md) |


## M1 第一轮产物导航

- [课程交付版产品简报](_bmad-output/planning-artifacts/product-brief.md)
- [原始 BMAD 简报](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/brief.md)
- [补充材料](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/addendum.md)
- [原始记忆日志](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/.memlog.md)
- [定稿核对记录](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/finalization.md)
- [罗思婕的需求审核](docs/team/requirements-review.md)、[周何馨的质量审核](docs/team/quality-review.md)
- [第一轮总结与Git贡献证据](docs/team/round1-summary.md)、[根目录人机决策日志](decision-log.md)

## M1–M4 要求与过程产物导航

下表是后续工作要求。尚不存在的产物仅列名称，不建立链接；具体路径以实际生成文件为准。完整约束见[课程要求](docs/course-requirements.md)。

| 里程碑 | 课程要求与门禁 | 产物与证据导航 | 当前状态 |
| --- | --- | --- | --- |
| M1 / 第 1 周 | 选题登记；完成分析、PRD与需求评审；门禁不计分但必须通过 | [产品简报](_bmad-output/planning-artifacts/product-brief.md)、[第一轮总结](docs/team/round1-summary.md)及B/C记录已具备；选题登记证据、PRD及整体门禁待完成 | 第一轮完成；第二轮未开始；整体门禁尚未通过 |
| M2 / 第 2 周 | 先架构与ADR，再 Epic/Story；完成规则、就绪检查与初始Sprint状态；门禁不计分但必须通过 | `architecture.md`（至少 5 条 ADR，含被否决方案及理由）、`epics.md` 与故事卡（至少 3 Epic、12 Story）、`project-context.md`（至少 8 条规则）、就绪检查记录、`sprint-status.yaml` 均待完成 | 待完成 |
| M3 / 第 3 周 | 推进Sprint 1核心史诗与运行Demo；收到老师真实变更后先做影响分析，当天18:00前提交分析，变更实现安排在Sprint 2 | 真实变更通知、影响分析表、人工范围取舍、Story状态历史、开发/评审/测试记录、核心Demo及Git证据均待完成 | 待完成；变更内容待老师下发 |
| M4 / 第 4 周 | Sprint 2、实验 A、实验 B 复盘、最终验收与仓库封存 | 源码与测试、NFR 证据、两实验原始记录及结果、根目录 `retrospective.md`、完整 README、10 分钟演示录屏、最终 Git 证据均待完成 | 待完成 |

### 跨阶段证据要求

| 要求 | 后续应保存的产物与标准 | 状态 |
| --- | --- | --- |
| 人机决策 | 根目录 `decision-log.md`：至少 15 条真实决策，其中至少 5 条否决或实质修改 AI 输出；记录触发、AI 建议、人工判断依据、结果与事后验证 | [已整理6条真实决策](decision-log.md)，课程总量要求尚未达成 |
| 需求追溯 | 编号 FR → ADR / 架构约束 → Story / 验收标准 → Test / 运行证据；支持抽查 2 条 FR | 待完成 |
| NFR 与质量 | 至少 2 条可测量 NFR，每条均有相应测试证据；Story 验收标准可转为测试断言 | 待完成 |
| 实验 A：规划深度对照 | X 完整规划与 Y 干净会话一句需求；难度相当，同人、同日、同宿主、同模型、同评审标准；保存五项度量、三个讨论问题及局限说明 | 待完成，尚无实验数据 |
| 实验 B：变更注入 | 老师正式下发后，依次进行 `bmad-correct-course`、影响分析、人工取舍、Sprint 2 实现；在根目录 `retrospective.md` 复盘 | 待完成，尚无正式变更证据 |
| 敏捷与 Git 证据 | 真实 Story 状态变化、文档迭代、评审闭环；保存 M1–M4 对应 commit 或 tag，最终以封存提交为准 | 里程碑证据待完成 |

规划和实施产物可采用 BMAD 默认目录；`decision-log.md` 与 `retrospective.md` 必须放在根目录。后续新增证据时应同步更新本导航，不得补造会话、人工审批、测试结果或 Git 历史。

## AI 使用声明（当前阶段）

本项目使用Codex协助环境配置说明和仓库文档整理，本README的完善使用了AI辅助。已完成本轮 Product Brief 的AI辅助讨论、草稿整理、文档检查和Finalize，吴亚彤实际作出范围取舍并审核批准；本次课程证据收尾也使用AI辅助。PRD、业务开发及实验尚未开展；后续应按真实使用情况补充工具版本、模型、用途、会话证据与人工决策。AI输出由团队成员实际审阅，不能将AI自检视为人工批准。

## 尚未完成的事项

- 补充负责人已确认业务现状和用户规模的原始依据，核实具体制度；完成选题合规核验、登记并保存凭证。
- 确认M1–M4公历日程和验收形式；记录实际Codex客户端及模型信息。
- M1 第二轮在新会话开展 PRD、需求评审及后续门禁；当前尚未启动。
- 按里程碑顺序生成后续必交产物，持续保存人工决策、工作流、评审、实验和 Git 证据，并补齐导航。
- 实现后补充经实际验证的程序启动步骤、运行环境、测试方法与结果；当前尚无业务程序启动命令或业务测试结果。
- 最终补齐AI使用声明、10 分钟演示录屏和仓库封存证据。

后续 PRD、architecture、epics、stories、sprint-status 等由相应工作流生成到 BMAD 默认目录，不提前建立空白交付物。retrospective.md 尚未创建，后续必须放根目录。
