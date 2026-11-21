# bmad-lab-booking-system

实验室设备预约管理系统｜软件工程管理课程大作业｜3人团队

## 2026-11-05 老师最新通知

老师取消 M1～M4 阶段性门禁检查和实验 B（需求变更注入），不再下发临时需求变更。团队根据已定需求继续按 BMAD 与敏捷流程完成项目，内部审查和负责人确认后可进入下一工作流，无需等待老师阶段批准。负责人补充的**最终截止日期为 2026 年 11 月 30 日**，最终只提交本 GitHub 项目仓库链接。 [课程要求基线](docs/course-requirements.md)

实验 A 仍为必做；其余产物、两个真实 Sprint、测试、决策、三人贡献及持续 Git 历史要求继续保留。实验 B 取消后的评分处理待老师明确，不自行重分配分数。

## Sprint 规划与审核处置（2026-11-21）

实施就绪结论为[CONCERNS](_bmad-output/planning-artifacts/implementation-readiness.md)，负责人已接受并有条件允许规划，未改为PASS。安装版BMAD 6.12.4已生成[sprint-status.yaml](_bmad-output/implementation-artifacts/sprint-status.yaml)，3个Epic及13条Story全部backlog，epics正文Story仍draft；3个回顾项为模板optional，不免除课程回顾。格式校验不是软件测试。

罗思婕、周何馨于 2026-11-19 完成业务与质量审核。吴亚彤于 2026-11-21 批准两轮范围和逐项处置，随后确认排期并正式批准 Sprint 1 启动。Sprint 1 为 11 月 22 日至 26 日，保留 1.1～1.4、2.1、2.2、2.3、2.5。Sprint 2 为 11 月 27 日至 29 日，保留 2.4、2.6、2.7、2.8、3.1。2.1 首次验收保留 NFR-001 的 20 个独立授权请求 × 10 轮，实验 A 的 2.6／2.7 保留为候选。R-01、R-03 沿用批准和验收证据，R-04、Read Committed 与 T-01～T-04 按既定节点落实。 [Sprint 启动交接](_bmad-output/planning-artifacts/sprint-plan.md#9-sprint-1-启动确认与-story-11-交接) · [D-017](decision-log.md#d-017-2026-11-21-负责人正式批准-sprint-1-启动)

正式开发一条Story一个独立bmad-build会话，代码实现后新开会话执行bmad-code-review；真实测试、问题处置及负责人验收满足后才能done，不批量完成13条Story。实验Y的一句需求干净对照路径须实验前确认，不能自动加载规划材料污染隔离。当前不开发、不运行测试、不执行Git提交或推送；不使用Docker、不增加PRD外业务。当前更新优先于下文旧轮次的历史进度说明。

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
| M2 Epic/Story | [定稿](_bmad-output/planning-artifacts/epics.md)文档final，3 Epic/13 Story的Story状态仍draft；[组员原文](docs/team/m2-epics-requirements-review.md)、[质量原文](docs/team/m2-epics-quality-review.md)及[处置记录](docs/team/m2-epics-review-disposition.md)；[Step-04报告](_bmad-output/planning-artifacts/epics-step-04-validation.md)保留历次验证，第三次复核零开放发现，负责人已批准并完成[C]；见报告第11节 |
| M2 后续就绪及 Sprint 计划 | CONCERNS 保留，两轮日期及 8／5 范围已确认。Sprint 1 启动已获批准，首条 Story 按实际开发状态推进。 [Sprint 1 启动交接](_bmad-output/planning-artifacts/sprint-plan.md#9-sprint-1-启动确认与-story-11-交接) |
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
| M2 | Architecture及8条ADR、[project-context](_bmad-output/planning-artifacts/project-context.md)及14条PC已定稿；Epic/Story文档已final，3 Epic/13 Story的Story状态仍draft，组员5项意见已按负责人决定修改，见[本轮汇总](docs/team/m2-epics-summary.md)。第三次Step-04复核已获负责人批准并完成Finalize；后续就绪检查及sprint-status.yaml尚未开始，不表示M2整体完成 |
| M3 | 核心Demo、Sprint 1状态及实现/评审/测试证据待开展；实验B已取消，不等待老师变更 |
| M4 | Sprint 2、必做实验A及结果和局限、根目录retrospective.md、源码/测试、启动说明、10分钟录屏及最终版本证据均待完成 |
| 人机决策 | [D-001～D-014 共 14 条真实决策](decision-log.md)。D-013 为条件接受，D-014 为真实审核后的正式范围批准，按批准类统计。课程累计至少 15 条的要求随真实决定继续积累。 |
| FR追溯 | 18条FR已有ADR/PC及Story/AC和待执行验证场景落点；尚无真实Test运行证据末端，不宣称完整链路已验证 |
| NFR | 已有2条可测NFR；实际测试证据尚未产生，不能据文档审查宣称测试通过 |
| Architecture及project-context后续待办 | R-03 本机环境和数据库连接已验证。R-04、Read Committed、T-01～T-04 按原节点落实，应用迁移和第二台机器复现随后取证。 [project-context 第 4 节](_bmad-output/planning-artifacts/project-context.md#4-deferred处理及后续确认节点) |

## AI使用声明与证据限制

Codex协助完成简报与PRD的讨论、草稿、意见映射、审查、结构文字整理、Finalize及本次课程证据整理。吴亚彤实际作出并传达人工决定、审核批准；罗思婕和周何馨提供原始审核记录。Finalize使用了独立AI审查子代理，其结果不冒充组员意见或老师验收。

当前无业务实现、业务运行测试或实验数据。课程 PPT 原页未在仓库发现，依据[课程基线](docs/course-requirements.md)及团队审核材料记录的第 27 页口径。2026-11-05 通知由团队转述，未另附通知原件。历史文档及过去记录保留当时事实。后续需保存实际工具与模型、会话和 Git 证据、每条 NFR 的运行测试及实验 A 数据。R-03 本机环境验证已验收，Sprint 1 启动已批准，Story 1.1 的实际实施证据将在独立工作流中产生。
