# bmad-lab-booking-system

实验室设备预约管理系统｜软件工程管理课程大作业｜3人团队

## 2026-11-05 老师最新通知

老师取消 M1～M4 阶段性门禁检查和实验 B（需求变更注入），不再下发临时需求变更。团队根据已定需求继续按 BMAD 与敏捷流程完成项目，内部审查和负责人确认后可进入下一工作流，无需等待老师阶段批准。**最终在老师规定的截止日前仅提交本 GitHub 项目仓库链接**，具体截止日期待老师明确。详见最高优先级[课程要求基线](docs/course-requirements.md)。

实验 A 仍为必做；其余产物、两个真实 Sprint、测试、决策、三人贡献及持续 Git 历史要求继续保留。实验 B 取消后的评分处理待老师明确，不自行重分配分数。

## 项目与当前进度

项目通过支持电脑和手机浏览器的Web系统提供设备查询、预约申请、冲突检查、管理员审核、取消、状态查询和设备维护，按具体实物唯一编号管理。计划服务学生约50人、教师约6人、管理员约2人。当前业务基线见[Product Brief](_bmad-output/planning-artifacts/product-brief.md)和[正式PRD](_bmad-output/planning-artifacts/PRD.md)。

**截至2026-11-11：M1两轮Product Brief和PRD已定稿；M2第一轮Architecture已定稿；M2第二轮project-context已由负责人正式批准Finalize。** 架构文档及审核证据已提交并推送至GitHub，真实提交为[4e2ff4fdbe58](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/4e2ff4fdbe58024e4bbfea0c63808f639f03c2a5)。M2第二轮[project-context.md](_bmad-output/planning-artifacts/project-context.md)于2026-11-11完成文档定稿；本次正式定稿修改尚未提交或推送，Epic/Story尚未开始。M1～M4仅作为内部管理阶段，老师不逐阶段验收。

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
| M2后续Epic/Story、就绪及Sprint计划 | 尚未开始；须按BMAD顺序在独立会话开展 |
| M3、M4及业务代码、运行测试、实验和复盘 | 尚未开始；当前无业务程序启动命令或运行测试结果 |

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
| M2 | 第一轮Architecture及8条ADR已定稿；第二轮[project-context](_bmad-output/planning-artifacts/project-context.md)已于2026-11-11获负责人批准并定稿，本次定稿修改尚未提交；详见[架构](_bmad-output/planning-artifacts/architecture.md)、[M2总结](docs/team/m2-architecture-summary.md)和[审核处理证据](docs/team/m2-architecture-review-disposition.md)。Epic/Story、就绪检查和sprint-status.yaml尚未开始，不表示M2整体完成 |
| M3 | 核心Demo、Sprint 1状态及实现/评审/测试证据待开展；实验B已取消，不等待老师变更 |
| M4 | Sprint 2、必做实验A及结果和局限、根目录retrospective.md、源码/测试、启动说明、10分钟录屏及最终版本证据均待完成 |
| 人机决策 | [D-001～D-012共12条真实决策](decision-log.md)，按五要素记录；课程至少15条总量未达成，否决/实质修改按实际证据核对，不凑数 |
| FR追溯 | 已有18条编号FR；FR→ADR→Story→Test完整链路待后续阶段建立 |
| NFR | 已有2条可测NFR；实际测试证据尚未产生，不能据文档审查宣称测试通过 |
| Architecture及project-context后续待办 | R-03环境方案、Read Committed仍待原节点确认；T-01～T-04未完成；实际补丁、Windows安装、数据库连接迁移和第二台机器复现未验证；见[project-context第4节](_bmad-output/planning-artifacts/project-context.md#4-deferred处理及后续确认节点)及[M2第一轮总结](docs/team/m2-architecture-summary.md) |

## AI使用声明与证据限制

Codex协助完成简报与PRD的讨论、草稿、意见映射、审查、结构文字整理、Finalize及本次课程证据整理。吴亚彤实际作出并传达人工决定、审核批准；罗思婕和周何馨提供原始审核记录。Finalize使用了独立AI审查子代理，其结果不冒充组员意见或老师验收。

当前无业务实现、业务运行测试或实验数据。课程PPT原页未在仓库发现，约束依据docs/course-requirements.md；没有声称已直接核实PPT原页。2026-11-05最新通知依据团队本次转述，未另附通知原件。历史PRD、Product Brief、原始BMAD日志和过去总结保留当时状态，涉及旧门禁的文字不构成当前等待要求。后续需保存真实工具/模型信息、会话与Git证据、每条NFR测试结果及实验A数据。M2第一轮Architecture已正式定稿并提交GitHub，提交证据见上文；M2第二轮project-context已获负责人正式批准并完成文档定稿，本次定稿修改尚未提交。Epic/Story及后续工作流尚未开始，环境和运行验证仍未完成。
