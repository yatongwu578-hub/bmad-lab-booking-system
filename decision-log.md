# 人机决策日志

本轮记录日期：2026-10-29。依据真实会话及[BMAD记忆日志](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/.memlog.md)整理；日志项按正文顺序计数。本轮整理6项真实决策，保留建议、人工判断、执行结果和证据。

## D-001 2026-10-29 纠正业务现状和痛点分类

1. **触发**：bmad-product-brief Create，记忆日志第2、9、10项；草稿将预约现状与痛点列为未验证假设，罗思婕原始记录也使用“假设”。 证据位置：会话“纠正已经确认的事实”消息；记忆日志第2、9、10项；[简报](_bmad-output/planning-artifacts/product-brief.md)问题陈述；[补充材料](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/addendum.md)证据与验证安排。
2. **AI建议及理由**：在正式核验前以假设口径描述现状和痛点，正文反复标注待核实。理由是：原始记录未明确说明建议理由；原会话将现状和痛点列为“暂无访谈证据”的团队假设，但未明确解释反复标注待核实的理由。
3. **人类判断与依据**：修改后采纳。团队重新核对课程示例后明确上述现状、痛点已经核实；按已确认事实表述。 人工判断依据：按团队最新事实确认纠正分类，不能把未访谈等同于业务事实未知，也不能编造访谈证据。
4. **结果**：简报问题陈述改用确定性表述，证据限制保留addendum；原始内部记录及历史日志未追改。 追溯：对应[产品简报](_bmad-output/planning-artifacts/product-brief.md)的问题陈述中的预约现状与痛点；正式 FR/NFR/ADR 编号尚未建立，后续补充。
5. **事后验证**：已核对定稿中的现状和痛点表述，业务确认与证据背景见补充材料。

## D-002 2026-10-29 明确允许未来日期预约

1. **触发**：bmad-product-brief Create，记忆日志第5项；“当天内按整点选择”的候选时间规则可能被理解为只能预约今天。 证据位置：会话“时间规则：基本接受，但修改一处”；记忆日志第5项；[简报](_bmad-output/planning-artifacts/product-brief.md)问题陈述。
2. **AI建议及理由**：当天内、整点、至少一小时、相邻可预约，不跨天或周期预约。理由是：便于展示、理解和验证；原会话举例说明10–11点与11–12点不算冲突。依据本地原始会话 rollout-2026-10-29T20-41-58-01a187ae-6c9e-7f82-ba7b-0874b9fe1360.jsonl，2026-10-29T12:55:49.597Z 的“时间规则”表格（UTC）。
3. **人类判断与依据**：修改后采纳。基本接受并修改一处，允许提前预约未来日期，但单次不得跨自然日；其余时间约束保留。 人工判断依据：明确区分预约发生日期与单次时间跨度，满足提前预约的产品用途；不额外推断开放时间或提前天数。
4. **结果**：两份定稿写入未来日期、整点、至少一小时、不跨自然日、相邻可预约及无缓冲时间。 追溯：对应[产品简报](_bmad-output/planning-artifacts/product-brief.md)的问题陈述中的预约时间规则；正式 FR/NFR/ADR 编号尚未建立，后续补充。
5. **事后验证**：已核对两份定稿中的时间规则；业务效果留待后续验证。

## D-003 2026-10-29 收敛复杂功能并保留核心一致性

1. **触发**：bmad-product-brief Create，记忆日志第3、4、6、7项；周何馨的质量输入包含临时锁定、候补、签到处罚、危险资格、离线补录及技术实现建议。 证据位置：[周何馨的质量记录](docs/team/quality-review.md)；记忆日志第3、4、6、7项；[简报](_bmad-output/planning-artifacts/product-brief.md)；补充材料“范围取舍背景”。
2. **AI建议及理由**：延后候补及额外释放机制，普通设备首版可排除危险资格管理；停用人工处理、系统内查看结果；数据库方案留待架构阶段。理由是：原会话指出候补会连带引入签到、超时释放、通知和公平性规则；离线补录会引入补录冲突与追溯问题；危险设备资格取决于实际设备范围，涉及危险设备时不能随意省略；课程要求支持3个Epic、12个Story及可测NFR，不意味着首版必须加入这些扩展功能。依据同一本地原始会话2026-10-29T12:47:48.631Z（UTC）。数据库方案延后的独立理由，原始记录未明确说明。
3. **人类判断与依据**：采纳。接受普通设备Web边界；待审核及已批准均占用，拒绝或取消释放，不做临时锁定及自动过期；排除扩展功能和外部通知，管理员处理长期待审核和停用影响。 人工判断依据：吴亚彤强调三人、四周、两Sprint内优先核心流程、冲突正确性、易部署和测试，不追求复杂功能。
4. **结果**：简报明确非目标和占用、释放、停用、取消留痕规则；未选择数据库方案。 追溯：对应[产品简报](_bmad-output/planning-artifacts/product-brief.md)的问题陈述中的占用释放规则及明确不做范围；正式 FR/NFR/ADR 编号尚未建立，后续补充。
5. **事后验证**：已核对范围与原始输入；后续验证核心流程及并发一致性。

## D-004 2026-10-29 补充用户规模并改写成功度量

1. **触发**：bmad-product-brief Create，记忆日志第8、11、12项；最初三个候选目标为核心流程、20并发和3人试用，缺少透明度及管理效率业务指标。 证据位置：会话“完善成功度量”及“最后一次精简修改”；记忆日志第8、11、12、15项；简报对应章节及补充材料。
2. **AI建议及理由**：流程验收、最多一条有效占用、至少2/3人在3分钟内完成查询申请。理由是：原始记录未明确说明建议理由；原会话提出核心流程、一致性和便利性三个候选指标，未明确解释20并发、3人及3分钟等阈值的选择依据。
3. **人类判断与依据**：修改后采纳。补充学生50、教师6、管理员2，合计约58人的计划规模；指标改为上线月后100%记录可查、同20条核对耗时降低50%、20并发最多一条有效占用、至少2/3人3分钟独立完成任务。 人工判断依据：团队要求参照课程PPT第22页，采用具体可测的业务目标；计划人数不是已使用人数，目标不是已测结果。
4. **结果**：简报“目标用户”和“预期成功度量”更新为指定规模及四项目标。 追溯：对应[产品简报](_bmad-output/planning-artifacts/product-brief.md)的目标用户及预期成功度量；正式 FR/NFR/ADR 编号尚未建立，后续补充。
5. **事后验证**：文件已核对；基线未实测、试用及并发测试未开展、上线月后指标未跟踪。

## D-005 2026-10-29 人工要求精简冗长保守的简报

1. **触发**：bmad-product-brief Create，记忆日志第13—16项；草稿包含多节过程说明、反复的“待核验”及后续工作流待办。 证据位置：会话“表达方式过于保守、冗长”及“同意定稿”；记忆日志第13—18项；[定稿核对](_bmad-output/planning-artifacts/briefs/brief-bmad-lab-booking-system-2026-10-29/finalization.md)。
2. **AI建议及理由**：在正文同时呈现产品方向、证据边界、验证限制、课程约束和待办，以较多章节组织。理由是：原始记录未明确说明建议理由；不能将人工要求精简的依据倒推为采用较多章节的理由。
3. **人类判断与依据**：修改后采纳。只保留问题陈述、目标用户、预期成功度量、明确不做范围四部分；已确认决定用确定表述，限制和未决事项移入addendum，保留核心规则。 人工判断依据：团队明确认为原稿过于保守冗长，不符合课程一页纸、定下取舍依据的示例风格。
4. **结果**：正文改为四部分，指标统一以预期标题标识；建立补充材料保存必要深度。 追溯：对应[产品简报](_bmad-output/planning-artifacts/product-brief.md)的正文四部分结构与核心业务规则；正式 FR/NFR/ADR 编号尚未建立，后续补充。
5. **事后验证**：团队审核后明确同意定稿；结构和文字检查无修改发现，未渲染纸张，不声称精确一页。

## D-006 2026-10-29 团队批准定稿并限制后续动作

1. **触发**：bmad-product-brief Finalize，记忆日志第17、18项；精简后的最终草稿已展示，等待人工审核与定稿授权。 证据位置：记忆日志第17、18项；定稿核对；[第一轮总结](docs/team/round1-summary.md)。
2. **AI建议及理由**：审核通过后完成Finalize，后续可在新会话启动PRD。理由是：原始记录未明确说明建议理由；记忆日志第17、18项记录人工授权和Finalize执行结果，不能据此倒推当时提出后续安排的理由。
3. **人类判断与依据**：采纳。明确已人工审核、同意定稿；保留原始BMAD产物，暂不进入PRD或自动提交GitHub。 人工判断依据：仅完成本轮产品简报和过程收尾，后续工作流独立推进。
4. **结果**：brief状态为final，生成根目录交付副本，保留日志、补充材料和定稿检查记录。 追溯：对应[产品简报](_bmad-output/planning-artifacts/product-brief.md)的整体定稿及补充材料中的技术选择安排；正式 FR/NFR/ADR 编号尚未建立，后续补充。
5. **事后验证**：收尾时两份定稿一致；当前正文较Finalize记录少了架构阶段技术选择一句，来源待吴亚彤确认，决定仍保留在补充材料。

## D-007 2026-11-03 人工决定采用按需失效收尾

1. **触发**：bmad-prd Create 续接；罗思婕第二轮“遗漏1、建议1”和周何馨“未清楚5、风险2、建议5”指出过期申请无法收尾。对应 FR-007/008/009/011～015/018、NFR-001 和 PRD 状态表。 证据位置：本次用户消息“我决定采用人工收尾 + 按需失效检查方案”及其6条业务规则和人工理由；[需求审核](docs/team/round2-requirements-review.md)、[质量审核](docs/team/round2-quality-review.md)、[PRD](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/prd.md)、[本轮 memlog](_bmad-output/planning-artifacts/prds/prd-bmad-lab-booking-system-2026-10-30/.memlog.md)、[意见处理表](docs/team/round2-review-disposition.md)。未取得可共享的会话 URL，不虚构链接。
2. **AI建议及理由**：在保留现状、人工收尾、自动过期三种方案中，推荐增加人工收尾，以兼顾状态清晰与原首版边界；指出自动过期与定稿简报排除项冲突，并等待人工决定。
3. **人类判断与依据**：用户明确决定“人工收尾 + 按需失效检查”，实质修改 AI 的人工收尾建议。开始时间已到仍待审核时，在查询预约或管理员处理时更新为已失效，释放时段并保留可查历史；开始前正常批准/拒绝，到达开始时间后不能批准，只能失效；时间检查、状态更新和冲突判断保持一致。不增加自动候补、自动签到处罚、临时锁定或周期后台任务。事务与并发技术实现留到架构阶段。 人工判断依据：“第一版需要避免过期申请长期占用设备，同时控制实现复杂度。采用按需失效检查，可以保持预约状态正确，又不需要额外开发后台定时调度机制。” 范围影响：明确调整 D-003 及简报原“不做自动过期释放”中对本次按需失效方案的排除；没有授权一般自动释放、故障自动取消已批准预约或后台调度。D-003 原记录保留作为历史，不追改人工判断。
4. **结果**：PRD 增加 FR-018 和已失效状态，同步占用定义、查询/审核/取消、操作留痕、状态表、范围及 NFR-001 交错验收；产品简报仅同步本次已授权范围变化；意见处理表将 P-01 标为已决定，另列剩余待确认项。全部文件仅在工作区，PRD 保持 draft，无提交或推送。
5. **事后验证**：本轮仅核对文档一致性及差异格式；未实现、未运行业务或并发测试，不声称已证明该判断有效。实现后按 FR-018/NFR-001 保存边界、交错、最终状态、占用及历史记录证据。

## D-008 2026-11-03 团队确认时间、冲突及预约修改边界

1. **触发**：bmad-prd Create第二轮审核，罗思婕“不明确1/4/5、建议4/5”，周何馨“未清楚3/6、风险3、建议2/3”；A-001/A-002、FR-006/007/008及状态边界待确认。证据为用户本轮“我已阅读剩余9项待确认问题”消息第1～5项，用户明确说明来自团队讨论；不虚构逐人发言或投票。
2. **AI建议及理由**：统一Asia/Shanghai避免时间歧义；无真实开放制度时不臆造窗口；保留跨设备预约、不编辑不重开及不承诺严格先到先得，减少额外限制、状态路径及公平性验证成本。建议见[原待决清单](docs/team/round2-open-decisions.md)。
3. **人类判断与依据**：接受上述规则。统一业务时区；不设额外开放窗口，明确理由为不擅自假定实验室实际开放时间、后续按真实制度调整；允许同一用户同时预约不同设备；改内容需重新申请，符合条件可先取消；不重开已拒绝/取消/失效申请；只保证设备占用唯一，不增候补/排队/优先级。除开放窗口外，用户未逐项另述独立理由，不将AI理由冒充团队发言。
4. **结果**：PRD第3节、FR-007/008、第5节及第9/10节落实，FR-006现有整点等规则保留；A-001/A-002改为已确认。处理表逐条记录结果，旧待决清单标为已关闭。本次与当前Product Brief无范围冲突，未改简报。无ADR或业务代码变更，无Git提交。
5. **事后验证**：核对条文、编号及意见映射，不等于功能或用户效果已验证。实现后需验证统一时区边界、同人不同设备允许、同设备冲突、禁止编辑/重开及并发唯一占用；具体技术方案留待架构。

## D-009 2026-11-03 团队接受轻量故障查询并保留人工处置

1. **触发**：罗思婕“遗漏2、建议2、不明确3、建议3”，周何馨“未清楚4、风险1、建议4”涉及故障预约查找、可见状态及处理期限。对应FR-009/011/014/015/017。证据为用户本轮九项决定第7～9项及两份原始审核。
2. **AI建议及理由**：增加按设备筛选及本人预约显示当前设备状态，减少查找遗漏和“已批准等于可用”的误解；首版不设故障强制期限，避免未定义服务承诺或额外系统动作，保留人工取消及留痕。
3. **人类判断与依据**：接受轻量设备筛选，用户明确理由为便于处理维修和停用设备；接受同页显示当前设备状态，理由为避免误认为已停用设备仍正常可用；不设强制处理期限和自动处罚，管理员人工处理并保留原因/操作记录。期限选择未另给独立理由，不倒推为团队原话。没有授权故障导致已批准预约自动失效。
4. **结果**：FR-009增加并区分预约状态/设备当前状态；FR-011增加目标设备、尚未结束的有效待处理记录筛选及权限/边界验收；FR-017明确无强制期限及自动处罚，FR-014/015留痕要求保留。处理表对应行关闭。与简报人工处理和系统内查询方向一致，本次不改简报、不增加外部通知或处罚功能。
5. **事后验证**：本轮只做文档核对。后续须用多设备/多状态/已结束记录验证筛选，用维修/停用变更验证设备当前状态可见、预约状态不误改，并验证隐私和处理留痕；尚无运行结果。

## D-010 2026-11-03 团队保留两项NFR并要求核验可测性

1. **触发**：周何馨“未清楚1/2、风险4、可测1～5、建议1/6”指出性能指标空缺及不能从局部质量推论整体质量。证据为用户本轮决定第6项，要求检查两条NFR是否有条件、目标及验证方法，按课程PPT第33页要求核验，不无意义增加指标。
2. **AI建议及理由**：首版保留NFR-001并发一致性和NFR-002权限隔离，延后未约定的性能/稳定性指标；两条已覆盖课程数量要求，新增指标需环境和阈值依据，避免只为增加数量制造承诺。
3. **人类判断与依据**：接受保留两条，但以检查明确测量条件、目标值及验证方法为条件；不无意义增加指标。用户未给出任何响应时间或稳定性阈值，AI不代填。此条记录接受与质量核验要求，不冒充否决/实质修改AI输出。
4. **结果**：按课程要求基线第4节（PPT第33页摘录）核验：NFR-001含20请求、10轮、每轮1成功19冲突及结果/最终记录校验；NFR-002含角色/归属场景、100%未授权用例通过及无泄露/无数据变化校验。明确权限用例分母、合法对照独立验证并覆盖新增查询功能；未改目标值、未新增NFR。第6节说明不承诺未纳入指标，核对结论见[本轮核对结果](docs/team/round2-resolution-check.md)。
5. **事后验证**：目前结论为文档具备可测结构，非实现已通过。仓库未找到PPT原文件，未声称复核第33/36页原页；使用docs/course-requirements.md摘录。实际环境、用例及运行证据需在后续实现验证阶段记录，不能虚构。PRD仍draft，未Finalize、未通过M1或进入架构。

## 证据边界

本次核对了原始记忆日志及本机 Codex 会话归档（`C:/Users/15860/.codex/sessions/2026/10/29/`）；会话文件未纳入仓库，以上文件名及时间戳供本机复核，不代表已有共享证据链接。日期沿用本轮记录日期；工作流轮次未完整归档，以记忆日志项定位，不将日志项数当作对话轮次；文档一致性检查不代表功能或业务效果已验证。

记录依据本轮对话与BMAD日志整理；罗思婕、周何馨的Git贡献链接见第一轮总结。业务指标验证结果随后续工作补充。

最终需至少15条真实决策，其中至少5条真实否决或实质修改，随后续工作流积累，不凑数。D-006为定稿授权和流程边界确认，不计为否决或实质修改。

## D-011 2026-11-04 人工批准PRD正式定稿并保留非阻塞验证待办

1. **触发**：当前bmad-prd Create已完成正式审查，报告为0 Critical、0 High、无业务阻塞。证据为用户本轮“我已人工审核本次PRD正式审查结果”及四项确认和七项执行要求，见原工作区finalize-review.md及finalization.md。
2. **AI建议及理由**：前次建议在人工确认后应用少量结构/文字澄清，并保留交错场景、时间边界取证、成对权限案例和并发夹具四项验证待办；文档审查不能替代运行证据，不需因此新增功能或NFR。
3. **人类判断与依据**：用户明确接受审查结果、18FR/2NFR及组员意见处理，确认四项待办不阻碍定稿，批准正式Finalize、保留原始BMAD产物并生成正文一致的课程交付版。依据为其已人工审核本次报告；没有授权提交GitHub、架构或其他工作流。本条为真实定稿批准，不计作新的否决/实质修改AI输出。
4. **结果**：原始prd.md状态为final、updated为2026-11-04；已应用structure/prose建议并追加第11节，不追改历史审查结论。生成_bmad-output/planning-artifacts/PRD.md，正文精确一致，文末链接定义按位置适配。四项待办由周何馨跟踪质量验证，保留原验证节点，技术事项后续与实际架构责任人协作。保存原稿审查快照、定稿记录、历史文件哈希清单及验证记录；未创建Git提交或推送。
5. **事后验证**：本轮已核对两份正文逐字符一致、两份元数据final/日期一致、18条唯一FR/2条NFR、NFR及范围正文未变、链接指向同一文件、审查原稿快照匹配原哈希、15份既有审核与意见材料未改。实际文件/正文哈希见工作区finalization-verification.md。没有执行功能、权限、并发或用户试用测试，不据此宣布系统质量或整项M1门禁通过。

## 2026-11-04 第二轮课程证据整理补记

本次整理没有产生新的业务取舍，因此不新增D编号。D-007～D-010及其真实来源全部保留，D-011为实际人工定稿批准；当前PRD两份正文一致且均final，详见[第二轮总结](docs/team/round2-summary.md)及[本次证据核对](docs/team/round2-evidence-check.md)。四项非阻塞验证待办尚未执行，不能用文档核对替代实际测试。

本轮仅更新证据组织、链接和进度；没有Git提交、推送、M2动作或老师已通过M1门禁的证据。后续仍按真实工作积累决策与验证结果，不凑数。

## D-012 2026-11-10 人工接受ADR-006历史对象关联完整性约束

1. **触发**：M2 Architecture Reviewer Gate的adversarial lens指出AD-6仅规定历史对象类型与ID，但ER图把外键及校验留待实现，独立模块可能采用不兼容的历史对象关联方式。用户要求有阻塞问题先处理、定稿前人工批准，并在审阅建议后给出补充决定。
2. **AI建议及理由**：建议ADR-006/AD-6规定历史记录由audit统一追加读取；每条记录必须且只关联一个预约或设备，类型一致、无悬空关联；预约、设备和历史不得由正常业务操作物理删除；数据库提供关联完整性约束，具体实现留给后续数据模型设计。理由是降低跨模块历史归属和引用完整性分歧，同时不提前指定复杂模式。
3. **人类判断与依据**：用户明确建议并接受上述补充。依据为FR-015追溯要求：管理员必须能定位审批、取消、失效等记录对应的对象；单一关联防止一条历史同时指向两个对象或无对象；这属于既有审计数据一致性约束，不增加业务功能；具体数据库机制可延后选择。
4. **结果**：更新课程版architecture.md的ADR-006、FR-015/018映射及来源；更新原始ARCHITECTURE-SPINE.md的AD-6 Binds/Prevents/Rule。具体数据模型与数据库约束实现仍待后续设计。追加对应BMAD memlog；未修改PRD、未Finalize、未编写业务代码、未运行测试、未提交或推送。
5. **事后验证**：文档核对确认两份架构中的约束一致，AD-6与ADR-006对应，决定仍为draft。尚无实现或数据库运行证据；后续实现阶段需验证恰好一个存在对象的关联、类型一致、关联完整性约束及正常业务路径禁止物理删除。

## D-013 2026-11-17 负责人有条件接受CONCERNS及两轮Sprint候选范围

1. **触发**：实施就绪报告CONCERNS后，负责人明确允许有条件进入安装版bmad-sprint-planning；生成初始状态后，负责人本次再次表示已对照PPT第26/27/33/34页及11月5日通知，初步有条件接受S1八条/S2五条。来源为本次真实用户消息，未取得共享会话URL，不补造。见[就绪报告](_bmad-output/planning-artifacts/implementation-readiness.md)、[Sprint计划](_bmad-output/planning-artifacts/sprint-plan.md)。
2. **AI建议及理由**：建议S1交付安全目录、可靠申请及查询，尽早验证2.1高风险；S2完成审核/取消/设备人工处置并预留2.6/2.7实验候选。不按Story数均分，保留全部验收及未决技术门槛，不因允许规划而声称PASS。
3. **人类判断与依据**：负责人有条件接受S1的1.1～1.4/2.1/2.2/2.3/2.5及S2的2.4/2.6/2.7/2.8/3.1，明确保留CONCERNS、全部backlog、R/T原节点、无Docker及无范围扩展；2.6/2.7仅候选，实验前需人工确认可比性/起点/隔离/评审/证据。负责人要求先整理规划和团队审核材料，等待范围及审核结果确认后再启动。其依据是本人已审核规划并对照课程要求，不代填两位组员意见。该条是条件接受，不计作否决或实质修改AI输出。
4. **结果**：Sprint计划追加初步接受及逐Story开发纪律，新增团队审核清单，README同步入口；sprint-status保持3Epic/13Story backlog，3回顾optional。正式PRD/Architecture/project-context/epics未改；未开始业务开发、软件测试、Git暂存提交或推送。
5. **事后验证**：已检查实际初始文件和只读Git差异，当前仅规划及审核准备；罗思婕、周何馨本轮真实审核、启动确认、技术门槛关闭、两个Sprint执行、实验及测试效果仍待实际发生，不能根据本决定宣布通过。课程至少15条决策仍须真实积累，不以此凑成已达标。

## D-014 2026-11-21 负责人正式批准两轮 Sprint 范围及审核处置

1. **触发**：罗思婕与周何馨于 2026-11-19 分别提交真实业务和质量审核。吴亚彤读完两份审核与 Codex 逐项分析后，在本次真实会话作出正式决定。原文、Git 证据和逐项意见见[审核处置](docs/team/sprint-planning-review-disposition.md)。当前无共享会话链接。
2. **AI 建议及理由**：保留 8／5 划分及原依赖，明确申请查询与后续管理闭环的交付边界。及早估算 2.1 的完整并发验收，保留 CONCERNS 与各节点，容量确有缺口时再评估 2.3／2.5 的后续依赖。建议 2.1 ready 前补 T-02 复核，并将 2.6／2.7 作为实验 A 候选。
3. **人类判断与依据**：吴亚彤正式批准 Sprint 1 的 1.1～1.4、2.1、2.2、2.3、2.5 和 Sprint 2 的 2.4、2.6、2.7、2.8、3.1。接受受控演示、原功能覆盖和依赖，以及在 2.1 内细化完整 NFR-001 验收。当前缺少实际容量，维持 2.3／2.5 的分配。按既定节点落实 R-01、R-03、R-04、Read Committed 及 T-01～T-04，保留 T-02 原复查未闭环并批准补查安排。实验 A 暂留 X=2.6 批准、Y=2.7 拒绝，待实际实验前人工确认控制条件。两轮日期、工时和启动仍待确认。此条是从 D-013 条件接受到真实审核后正式批准范围的独立决定，按批准类统计。
4. **结果**：新增[逐项处置记录](docs/team/sprint-planning-review-disposition.md)，更新[Sprint 计划](_bmad-output/planning-artifacts/sprint-plan.md)、[团队审核材料](docs/team/sprint-planning-review.md)及[README](README.md)。正式 18 FR、2 NFR、8 ADR、14 PC 和 13 条 Story 保持原基线。两份审核原文、CONCERNS 和初始 backlog 状态均保留。
5. **事后验证**：本轮核对文档内容、链接和 Git 差异。实际容量及启动批准、开放技术条件、T-02 补查与运行证据、两个 Sprint 的实现及验收、实验 A 均待相应真实工作节点复核。现有 D 编号共 14 条，课程至少 15 条的总量要求继续随真实决定积累。

## D-015 2026-11-21 负责人批准 R-01 自定义账号模型

1. **触发**：Sprint 1 启动准备中，R-01 按[就绪报告](_bmad-output/planning-artifacts/implementation-readiness.md)和[Sprint 计划](_bmad-output/planning-artifacts/sprint-plan.md)须在 Story 1.1 进入 ready 和首次迁移前决定。依据是负责人在本次真实会话中明确表示已检查 Sprint 1 启动准备报告并批准 R-01。当前无共享会话链接。
2. **AI 建议及理由**：此前规划列出自定义 User 与关联 Profile 两条实现路径，要求人工先确定唯一业务角色来源及迁移依赖。现有 [PC-008](_bmad-output/planning-artifacts/project-context.md#pc-008-服务端角色归属及单一业务入口) 与 ADR-002 约束服务端角色检查，以免权限分散或由 Django 管理标志绕过业务规则。
3. **人类判断与依据**：负责人批准 `accounts.User` 继承 Django `AbstractUser`，添加必填 `role`，只允许学生、教师、管理员。沿用 Django 认证、密码哈希和会话；服务端按 `role` 执行业务授权，`is_staff` 和 `is_superuser` 不作为角色依据。保留预置初始化，关闭自助注册，不额外创建 Profile 表或增设权限框架。决定落实 FR-001、FR-002 与 ADR-002 的既有要求。负责人给出了选择和适用边界，未另述比较理由。本条按方案批准记录。
4. **结果**：本日志记录人工决定，并在 [R-01/R-03 准备记录](docs/team/sprint-1-environment-preparation.md)保留首次迁移和验证交接。R-01 的人工选型已完成，等待实现取证。Sprint 1 启动批准单列。
5. **事后验证**：在 Story 1.1 首次迁移前核对 `AUTH_USER_MODEL = 'accounts.User'` 和 `accounts` 首个迁移的依赖。后续验证三类角色及必填限制、预置账号哈希和会话、业务角色独立于 Django 管理标志以及直接访问权限。实际结果待取得。

**负责人补充要求**：在首次迁移前配置 `AUTH_USER_MODEL`，并明确角色取值、默认权限边界和初始化规则。实施口径已写入 [R-01 首次迁移与预置账号规则](docs/team/sprint-1-environment-preparation.md#r-01-首次迁移与预置账号规则)。其中 `student`、`teacher`、`admin` 是 Codex 据已批准的三个业务角色提出的存储值。文档核对后仍待实际迁移、授权及初始化取证。

**启动准备复核**：负责人在本次会话再次确认沿用 `accounts.User`、`AbstractUser` 和单一必填 `role`，模型与迁移在 Story 1.1 开发中实现并验证。当前仅作选型和实施规则取证，Story 1.1 跟踪状态为 `backlog`。

## D-016 2026-11-21 负责人批准 R-03 本地环境方案

1. **触发**：Python、依赖和时区已完成本机核验，现有 PostgreSQL 11.17 服务位于 `5432`。Codex 提交独立 17.x 实例及项目库隔离方案，等待会创建集群、数据库和角色的操作获准。见 [Sprint 1 环境准备记录](docs/team/sprint-1-environment-preparation.md)。
2. **AI 建议及理由**：通过 PostgreSQL 官网指向的 EDB Windows 安装器准备独立 17.x 服务及数据目录，拟用 `127.0.0.1:5433`。预建业务库 `lab_booking` 和测试库 `test_lab_booking`，分设运行、迁移和测试角色，把集群级建库权限留给部署管理员，避免业务和测试串库及旧实例受影响。建库后核验实际版本、连接和权限。
3. **人类判断与依据**：负责人在本次会话明确回复“二、批准R-03环境方案”。此条记录对上述环境方案的批准，沿用真实结果取证及旧实例隔离约束。负责人未另述比较理由。应用迁移、业务预置账号写入及 Sprint 1 正式启动沿各自的确认节点。
4. **结果与事后验证**：独立 Windows 服务 `postgresql-x64-17` 运行于 `127.0.0.1:5433`，认证查询确认服务端 PostgreSQL 17.12。两库与三个分离角色已创建，`psql`、psycopg 和临时 Django 设置完成实库连接验证，跨库拒绝及凭据访问权限通过实际复查。旧服务仍在 `5432` 接受连接。应用迁移、预置账号和第二台机器复现待各自节点取证。安装与验证失败、恢复命令及结果见 [R-03 批准后执行记录](docs/team/sprint-1-environment-preparation.md#r-03-批准后执行记录)。

**负责人正式验收**：负责人在本次会话正式接受 R-03 本机环境准备及数据库连接验证结果，要求保留 D-016 和真实证据。正式项目采用独立 PostgreSQL 17.12 服务及 `5433`，既有 11.17 服务和数据库受保留。Codex 只读复查了依赖、时区、双服务状态和三角色的认证连接。此时两轮排期和启动尚待决定，后续见 D-017。 [环境复查](docs/team/sprint-1-environment-preparation.md#负责人验收与只读复查)

## D-017 2026-11-21 负责人正式批准 Sprint 1 启动

1. **触发**：负责人补充 2026-11-30 课程最终截止日期并提出两轮候选，随后在本次会话明确回复“我正式批准启动Sprint 1”，同时提供确认日期、分工、进度跟踪方式与技术边界。当前无共享会话链接。
2. **AI 建议及理由**：此前将短窗口评为高风险，建议以人员工时、容量估算及 2.1 评审、修复和复测窗口核对可行性，并继续保留逐 Story 取证与两轮完整要求。
3. **人类判断与依据**：负责人指出 PPT 未要求逐人每日工时记录，决定取消工时表、容量估算和逐小时排期作为启动门槛，以 Codex 辅助真实实施，并按 Story 状态、Git 提交与测试证据跟踪。Sprint 1 定于 2026-11-22 至 11-26，Sprint 2 定于 11-27 至 11-29，11-30 提交唯一仓库链接，沿用 8／5 划分。吴亚彤负责技术实施、代码和最终验收，罗思婕负责业务审核，周何馨负责质量审核和测试证据检查。保留 `CONCERNS`、D-015／D-016、R-04、Read Committed 和 T-01～T-04 原节点。实验 A 保留 X=2.6、Y=2.7 为候选，正式实验前确认公平性和隔离条件。本条是对先前启动门槛的实质修改和本轮启动授权。
4. **结果**：更新既有 Sprint 计划与 README 启动状态，移除候选工时确认表。保留正式 PRD、Architecture、epics 与实际 Story 范围。未创建实施规格或记录虚构状态流转。 [Sprint 1 启动确认与交接](_bmad-output/planning-artifacts/sprint-plan.md#9-sprint-1-启动确认与-story-11-交接)
5. **事后验证**：BMAD 6.12.4 原生校验返回 `valid=true`，同步预演返回 `in_sync=true`、`changed=0`。原生状态工具推荐 Story 1.1，13 条 Story 和 3 个 Epic 均为 `backlog`。1.1 的正式设计、无前置 Story、D-015 与 D-016 已核对，实施规格与 `ready-for-dev` 按独立 Build 的原生检查点实际发生。后续真实开发、评审、测试、负责人验收和 Git 提交尚待取证。

## D-018 2026-11-21 负责人批准 Story 1.1 实施规格

1. **触发**：本次独立 `bmad-build` 会话在 BMAD 6.12.4 Checkpoint 1 展示 Story 1.1 草稿。负责人选择审查规格并同意修订五项发现。
2. **AI 建议**：补齐首次迁移及预置确认、状态交接、AC-2／6／7 测试设计、三种数据库身份的权限验证和凭据保护，按 FR-001／FR-002、ADR-001／002／008、D-015／D-016 复审。复审结果为五项关闭，无规格阻塞。
3. **人工判断**：负责人在本次会话回复“批准并继续”，随后正式批准修订规格通过 Checkpoint 1，要求“现在开始执行Story 1.1开发”，并明确本会话结束于开发自测及 `review`。批准与明确开工指令在 2026-11-21 22:57（北京时间）记录，早于 Sprint 计划所列 11 月 22 日开始日。按本次指令记录 Story 1.1 的实际开工，正式 Sprint 日期和范围沿用 D-017。
4. **结果**：[实施规格](_bmad-output/implementation-artifacts/spec-1-1-preset-account-login.md)和[状态文件](_bmad-output/implementation-artifacts/sprint-status.yaml)记录批准后的 `ready-for-dev` 节点。只授权本 Story，不自动提交或推送。实际数据库迁移目标与计划、预置目标与清单分别确认。
5. **事后验证**：静态复审覆盖正式 AC-1～AC-7。实施、自测、独立代码评审、问题处置和负责人验收分别按实际结果取证。

## D-019 2026-11-22 负责人批准 Story 1.1 业务预置和退出验收

1. **触发**：Story 1.1 业务库首迁与 D-016 最小运行授权已执行，默认保护清单还未创建。依据为本次 Story 1.1 开发会话，首迁前检查点及实际执行见开发证据。
2. **AI 建议及理由**：此前请负责人提供已批准清单，或明确授权生成学生、教师、业务管理员三类演示账号。需要可验证的本机凭据才能执行 D-015 和真实浏览器对照。
3. **人类判断与依据**：负责人明确批准在 `lab_booking` 创建 `student_demo`、`teacher_demo` 和 `admin_demo`，分别对应 student、teacher 和 admin。要求本机独立随机密码、受保护交付、重跑保留同角色账号，三类账号实测登录及退出，以 AC-1～AC-7 和必要检查通过作为转入 `review` 的条件。本条是对具体演示账号和验收方式的批准，依据为 FR-001、FR-002、ADR-002 及 D-015／D-016。
4. **结果**：预置与重跑完成，开发代码加入 CSRF 保护的退出入口并扩展既有测试方法。真实凭据文件保存在负责人本机。正式需求、架构和验收条款沿用原文。
5. **事后验证**：业务库首次新增 3 个，重跑跳过 3 个，三类账号的哈希校验、角色和标志核对通过。Chrome 三类账号登录、退出与拒绝路径已实测。自动化重跑及状态以[开发证据](_bmad-output/implementation-artifacts/story-1-1-dev-evidence.md#2026-11-22-正式预置与-chrome-验收)的实际结果为准。

## D-020 2026-11-23 负责人批准 Story 1.1 独立评审整改范围

1. **触发**：BMAD 6.12.4 独立代码评审完成后，负责人审阅 CR-01～CR-14 及整改建议。本决定来源为负责人在本次会话明确发出的批准指令。
2. **AI 建议**：按 CR 编号处理六项 Medium 和八项 Low，建立处置表后由独立 `bmad-build` 会话按批准范围实施，保持 AC、D-015～D-019 及 Architecture/project-context 约束。
3. **人类判断与依据**：负责人批准 CR-01～CR-14 全部按最小范围整改或补充验证，不扩大业务范围。CR-01 必须仅连接 `test_lab_booking`，核对实际数据库、角色、主机、端口，不清空或重建 `lab_booking`。CR-03 完善连接配置来源和优先级，保持 D-016 的 PostgreSQL 17.12 业务目标、角色分离及最小权限。若需改变已批准连接约束、真实数据库权限或已有数据，另行申请批准。CR-13 仅修正 README 和做必要验证，不执行额外 GRANT，不授予业务角色 SUPERUSER、CREATEDB 或不必要 DDL。其余 CR 按已审阅方案最小修复或补测。正式 AC、PRD、Architecture、project-context 及 D-015～D-019 不变，不引入 Docker、SQLite、自助注册或新业务功能。该决定未声称其他成员共同表决。
4. **结果**：批准建立 `docs/team/story-1-1-review-disposition.md` 并交独立 BMAD 6.12.4 `bmad-build` 会话实施。本会话仅记录决策和交接，不修改业务代码、不迁移数据库、不更改 Story 状态、不执行 commit/push。Story 1.1 保持 `review`，Story 1.2 保持 `backlog`。
5. **事后验证**：整改尚未执行。后续依处置表核对代码和文档差异、测试结果、连接目标、前后数据库状态及敏感日志。测试连接必须仅指向 `test_lab_booking`。真实数据库权限、迁移策略或已有数据改变须先取得单独批准。负责人最终验收和 Git 证据待实际发生后补录。

**整改后的事后验证（2026-11-23）**：独立 `bmad-build` 开发会话完成 CR-01～CR-14 自测，最终全量 26 项通过。已核验测试库目标及前后状态，业务库仅只读核对。Story 1.1 回到 `review`。该补记记录实际结果，人工验收及本轮 Git 提交待发生后再补。 [开发证据](_bmad-output/implementation-artifacts/story-1-1-dev-evidence.md#2026-11-23-独立评审整改与开发自测) · [逐项处置](docs/team/story-1-1-review-disposition.md#开发整改与自测结果)

## D-021 2026-11-24 负责人限定 Story 1.1 输入边界整改

1. **触发**。正式 BMAD 6.12.4 Step 4 复审复现登录页截断合法边界用户名和超限密码，最大密码测试亦未覆盖浏览器默认 URL 编码传输。 [Step 4 复审](_bmad-output/implementation-artifacts/spec-1-1-preset-account-login.md#2026-11-24-bmad-6124-渲染恢复后-step-4-复审)
2. **AI 建议**。保留浏览器接收的原始输入，把用户名规范化、字符校验及密码上限交给 Django，用真实 URL 编码表单及隔离库复验。
3. **人工判断**。负责人确认基础解释器路径存在，要求先区分 Codex 权限与 `.venv` 损坏，仅修复两处输入边界。要求保留 Django 默认用户名规则，确保合法 150 码点不会被截断，4097 码点密码明确拒绝，并以实际测试验证。只允许连接 `test_lab_booking`，随后进行独立 Code Review。Story 1.1 保持 `review`，1.2 保持 `backlog`，不自动提交或推送。依据为本轮负责人明确指令及 FR-001／002、ADR-001／002／008、D-015／016。
4. **结果**。在表单、模板、预置解析和回归中落实原始输入及共用验证。保留正式 AC、冻结区和现有项目环境。 [整改处置](docs/team/story-1-1-review-disposition.md#step-4-输入边界整改2026-11-24)
5. **事后验证**。普通 PowerShell 的原 `.venv` 运行 Python 3.13.17。系统、迁移一致性检查通过，隔离库 Django 32 项及实际 Chrome 6 个表单用例通过。本次未连接业务库。此记录依据负责人实际授权和已完成的测试，最终验收与 Git 提交待实际发生。 [开发证据](_bmad-output/implementation-artifacts/story-1-1-dev-evidence.md#2026-11-24-输入边界最终整改)

## D-022 2026-11-24 负责人接受 Story 1.1 最终复审证据并处置残余事项

1. **触发**：BMAD 6.12.4 四个独立评审视角已恢复并完成；负责人要求在 Story 1.1 最终验收前核对 CR-04 的历史 runtime 证据有效性、列出此前评审范围外的 Medium 项，并形成 AC-1～AC-7 验收清单。依据为本次负责人明确指令、正式实施规格及独立评审报告。
2. **AI 建议及理由**：最新输入边界差异仅改账号表单、登录模板、预置解析和对应测试；没有改动 runtime 启动、登录／身份视图、CSRF、中间件、会话、角色或退出处理。既有 Windows runtime 三角色 Chrome 证据仍能证明实际业务账号的登录、身份展示、刷新、CSRF 和退出；既有独立 32/32 Django 回归与 10/10 Chrome 表单用例覆盖新增输入边界。建议不访问业务库重复认证，关闭 CR-04，并明确记录负责人接受“业务 runtime 登录未在最后一次输入边界修改后重跑”的残余风险。此前三个未编号 Medium 项分别属于新机环境交接、PowerShell 迁移操作失败传播和测试运行器防护，应保留为项目级集成／工具链事项，不扩展 Story 1.1。
3. **人类判断与依据**：负责人正式接受既有 Windows runtime 和三类业务账号 Chrome 证据，接受与最新隔离库回归证据组合满足正式 AC 的判断，并批准关闭 CR-04。理由是边界修复不改变既有业务账号的常规认证路径及认证后的角色、会话、CSRF 和退出行为；Django 32/32 与真实 Chrome 10/10 已独立覆盖新表单边界。负责人接受未在本轮重新连接业务库认证的残余风险。负责人同时确认此前未编号 Medium 项转为后续项目级验证／硬化事项，第二台 Windows 复现继续保留在原定集成节点，不计为Story 1.1阻塞。其他 CR-01～CR-03、CR-05～CR-14 及 U-01 按本次正式独立复审结论关闭。依据 FR-001／002、AC-1～AC-7、D-015～D-021、ADR-001／002／008、PC-001／002／008／011 及真实证据记录。
4. **结果**：将 CR-04 标为关闭；把三项未编号 Medium 发现按负责人决定记为 `defer` 并纳入 `deferred-work.md`；新增 Story 1.1 最终验收清单及证据映射。Story 1.1 仍为 `review`，Story 1.2 仍为 `backlog`，等待负责人另行批准最终状态推进。本次不改业务代码、数据库或正式需求，不运行测试，不开发 1.2，不执行 commit/push。
5. **事后验证**：只读核对最新表单边界差异及既有 runtime、Django、Chrome、隔离数据库证据；确认 AC-1～AC-7 的测试映射、D-015～D-021 未被改变，实验 A 数据和条件未受本轮测试影响。没有重新运行测试或访问 `lab_booking`。第二台 Windows 机器尚未复现，仍待项目集成验证节点取证。 [独立评审结论](_bmad-output/implementation-artifacts/spec-1-1-preset-account-login.md#2026-11-24-story-11-输入边界独立复审恢复) · [开发证据](_bmad-output/implementation-artifacts/story-1-1-dev-evidence.md#2026-11-24-输入边界最终整改) · [独立复审检查点](docs/team/story-1-1-independent-review-checkpoint-2026-11-24.md)

## D-023 2026-11-24 Story 1.1 负责人最终验收

1. **触发**：BMAD 6.12.4 独立代码评审和问题处置完成后，负责人在本次会话正式批准 Story 1.1「使用预置账号登录并获得明确业务身份」最终验收通过。依据是正式 AC-1～AC-7、实施规格、开发证据、整改处置记录、四视角复审检查点及 D-015～D-022。
2. **AI 建议及理由**：按安装版 BMAD 6.12.4 Build Step 5 标记实施规格完成，并同步 Sprint 状态。负责人明确要求 Story 1.1 从 `review` 到 `done`；Epic 1 尚未全部完成，必须保持 `in-progress`；未开始的 Story 保持 `backlog`。不再运行测试或评审，复用既有独立 Django 32/32、独立 Chrome 10/10、PostgreSQL 测试库隔离及四视角评审证据。
3. **人类判断与依据**：负责人正式接受 CR-01～CR-14、U-01 全部关闭，接受正式 AC-1～AC-7 的验收证据及 CR-04 历史 runtime 证据和记录的残余风险；确认四视角独立评审无新增验收阻塞问题。负责人接受三项未编号 Medium 延期事项按项目级节点跟踪、九项 Low 建议继续保持非阻塞且未虚构关闭、第二台 Windows 复现留待后续集成验证。依据 FR-001／002、NFR-002、ADR-001／002／008、D-015～D-022 及已保存的真实测试和运行证据。Story 1.1 测试结果不用于实验 A。
4. **结果**：按 Build Step 5 将 Story 1.1 实施规格 `status` 设为 `done`；将 `sprint-status.yaml` 中 Story 1.1 由 `review` 更新为 `done`，刷新 `last_updated`。Epic 1 保持 `in-progress`，Story 1.2 及其他未开始 Story 保持 `backlog`。更新 README 当前进度、整改处置记录和独立复审检查点的最终验收状态。未修改业务代码、数据库、正式 PRD、Architecture 或 epics 基线；未开发 Story 1.2；未 commit/push。
5. **事后验证**：复用已完成的 32/32 Django 独立测试、10/10 Chrome 独立测试、测试库隔离验证和四视角复审记录，不重复执行。以 Git 差异检查确认本次文件范围仅为状态、验收与进度证据，执行 `git diff --check` 及敏感信息检查；确认实验 A 的 X/Y 条件、数据未被本 Story 结果替代。 [实施规格与 AC 清单](_bmad-output/implementation-artifacts/spec-1-1-preset-account-login.md#负责人最终验收与完成状态-2026-11-24-d-023) · [状态文件](_bmad-output/implementation-artifacts/sprint-status.yaml) · [整改处置记录](docs/team/story-1-1-review-disposition.md#负责人最终验收与状态推进2026-11-24-d-023) · [独立复审检查点](docs/team/story-1-1-independent-review-checkpoint-2026-11-24.md) · [课程要求基线](docs/course-requirements.md)

## D-024 2026-11-25 负责人批准显式 Read Committed

1. **触发**。BMAD 6.12.4 Build Step 2 准备 Story 1.2 的 Checkpoint 1。Sprint 计划要求在本 Story 进入 ready 前确认 ADR-003／AD-3 的隔离级别建议。 [Sprint 计划](_bmad-output/planning-artifacts/sprint-plan.md)
2. **AI 建议及风险**。建议由 Django PostgreSQL `OPTIONS` 统一设置 `IsolationLevel.READ_COMMITTED`，避免部署环境或角色默认值漂移改变事务语义。备选是继续依赖默认值并逐模式核查，改动较小，但检查之间仍有漂移可能。显式配置会影响三个模式的所有新应用连接，配置有误可能阻止连接。仅看到隔离级别正确也无法验证编号竞争结果，仍需执行 AC-6。
3. **人工判断与依据**。项目负责人在本次对话明确批准方案 1。runtime、migration、test 使用同一 Django 连接级设置，PostgreSQL 服务器级、数据库级和角色级设置保持原样。负责人同时明确后续由三位组员共同参与 Codex 开发、检查与验收，按实际参与和人工决定留证。本条只记录本次负责人决定。
4. **结果**。已将批准的设置和验证要求纳入 Story 1.2 实施规格。规格仍为草稿，Sprint 状态仍为 `backlog`，设置在规格批准后的开发阶段实施。 [实施规格](_bmad-output/implementation-artifacts/spec-1-2-create-equipment.md)
5. **验证方式与当前证据**。变更前三个 Django 模式分别以 `lab_booking_app`、`lab_booking_migrator` 连接 `lab_booking`，以 `lab_booking_test` 连接 `test_lab_booking`。实际目标均为 PostgreSQL 17.12、`127.0.0.1:5433`，只读事务中 `SHOW default_transaction_isolation` 和 `SHOW transaction_isolation` 均为 `read committed`。实施后以新连接逐模式核对库、角色、版本和事务内 `SHOW transaction_isolation`，业务库核对保持只读。AC-6／AC-7 在隔离测试库另行取得实际证据。实施后验证尚未发生。

## D-025 2026-11-25 负责人批准 Story 1.2 独立评审处置

1. **触发**。BMAD 6.12.4 full 独立评审的 Step 4 人工检查点。四视角裁决留下 R1～R11。独立测试 38/38 并通过 AC-6，真实故障注入复现 AC-7 提交结果误报，独立页面验证复现 AC-1、AC-3 边界缺陷。 [首轮独立证据](_bmad-output/implementation-artifacts/story-1-2-independent-review.md)
2. **AI 建议及理由**。推荐方案 2，保留行动项并由原开发会话返工。优先修复 AC-1、AC-3、AC-7，随 AC-7 收紧预查和最外层事务边界。已有可复跑的独立证据覆盖当前 AC-6、权限、CSRF 与字段一致性，可在记录残余风险后延期测试工具及常规断言加固。
3. **人类判断与依据**。项目负责人在本次会话选择方案 2。批准 R1～R3 必修、R4～R5 随 AC-7 最小整改，R6～R11 在不影响正式 AC、安全性和数据一致性的前提下延期，并要求逐号保留原因、风险和后续节点。判断依据为正式 AC-1～AC-7、FR-016／FR-002、ADR-002／003／008、PC-002／008／011／014 及独立测试和故障注入。本条记录负责人决定。
4. **结果**。实施规格与 Sprint 跟踪同步为 `in-progress`。记录 5 项待整改、6 项延期、0 项修复、0 项驳回，并生成给原开发会话的一次性任务。Story 1.3 保持 `backlog`。本会话只处理评审文档与状态。 [逐项处置](_bmad-output/implementation-artifacts/story-1-2-review-disposition.md) · [延期台账](_bmad-output/implementation-artifacts/deferred-work.md) · [一次性整改任务](_bmad-output/implementation-artifacts/story-1-2-remediation-handoff.md)
5. **事后验证**。本次静态对照 R1～R11、延期台账与 Story 状态，保留既有独立 Django 38/38、AC-6 真实并发及 AC-7 注入的实际失败结果，无新增运行结果。整改后须以隔离测试库复测并交独立复评，负责人最终验收仍待进行。实验 A 条件及首轮证据原样保留。 [实施规格](_bmad-output/implementation-artifacts/spec-1-2-create-equipment.md#review-findings) · [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml)
## D-026 2026-11-25 负责人关闭 R1～R5 并批准 Story 1.2 业务库验证

1. **触发**。Story 1.2 完成 BMAD 6.12.4 针对性独立复审。AC-1～AC-7 在隔离库通过，Django 45/45，Story 1.1 为 32/32，真实故障注入区分确认失败与提交未知。 [独立复审](_bmad-output/implementation-artifacts/story-1-2-independent-recheck.md)
2. **AI 建议及理由**。依据独立结果建议关闭 R1～R5，单独批准业务库迁移与运行验证。当前新增路径使用六列 INSERT 和 `RETURNING id`，最小授权候选为对应 INSERT 和 SELECT(id)。真实故障注入及并发压力继续留在隔离库。
3. **人类判断与依据**。负责人接受独立复审结论，正式关闭 R1～R5，R6～R11 按 D-025 延期。批准在 `127.0.0.1:5433` 的 PostgreSQL 17.12 `lab_booking` 中，以原迁移角色核对和备份后，仅应用 `equipment.0001_initial`，执行最小授权并用三类现有预置账号验证。批准保留一条明确标识课程演示用途的设备档案。超出范围即停止。依据 FR-016／FR-002、ADR-002／003／008、D-024／025 及正式 AC。
4. **结果**。受保护备份完成。唯一迁移成功，迁移历史 16 → 17；实际授予设备六列 INSERT 和 SELECT(id)，有效权限已核对。Chrome 验证三角色，管理员 201 新增 `EQ-DEMO-S12-20261125`，同号明确重复。正式 PRD、Architecture、epics、实验 A 和延期处置沿用原记录。 [实施规格](_bmad-output/implementation-artifacts/spec-1-2-create-equipment.md#review-findings) · [业务库证据](_bmad-output/implementation-artifacts/story-1-2-runtime-evidence.md)
5. **事后验证**。独立连接复核设备资料、可用状态和唯一记录，三类账号退出后会话数恢复为零。此次复用已有独立 45/45，无需重跑。三位组员共同操作与审阅。第二台 Windows 机器仍待复现。Story 1.2 仍为 `review`，最终验收尚待负责人批准。

## D-027 2026-11-25 Story 1.2 负责人最终验收

1. **触发**。项目负责人在最终验收会话正式批准 Story 1.2。前置证据来自整改后独立复审与 D-026 授权后的业务库运行核验。 [独立复审](_bmad-output/implementation-artifacts/story-1-2-independent-recheck.md) · [业务库核验](_bmad-output/implementation-artifacts/story-1-2-runtime-evidence.md)
2. **AI 建议**。独立复审建议接受隔离环境中的 AC-1～AC-7 验证并关闭 R1～R5，保留 D-025 延期项，业务库变更和最终状态等待负责人分步批准。 [复审裁决](_bmad-output/implementation-artifacts/story-1-2-independent-recheck.md) · [处置经过](_bmad-output/implementation-artifacts/story-1-2-review-disposition.md)
3. **人类判断与依据**。负责人正式接受最终交付，依据 FR-016／FR-002、ADR-002／003／008 所对应的正式 AC-1～AC-7、Django 独立 45/45（Story 1.1 为 32/32）、真实 PostgreSQL 并发与事务故障证据，以及 D-026 已完成的迁移、最小授权和实际运行核验。确认 R1～R5 已关闭、R6～R11 继续延期。团队体验按已有操作记录留证。
4. **结果**。按 Build Step 5 完成规格归档，再依据本次人工验收将 Sprint 的 Story 1.2 从 `review` 推进为 `done`。Epic 1 保持 `in-progress`，Story 1.3 及其他未开始 Story 保持 `backlog`。更新 README、评审处置、延期跟踪及最终验收记录。提交和推送待负责人授权。 [最终验收](_bmad-output/implementation-artifacts/story-1-2-final-acceptance.md) · [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml)
5. **事后核对**。复用已有效的独立和运行验证。第二台 Windows 待复现，Story 1.2 的测试数据不计入实验 A。 [延期台账](_bmad-output/implementation-artifacts/deferred-work.md)

## D-028 2026-11-25 负责人批准 Story 1.3 实施规格

1. **触发**。BMAD 6.12.4 `bmad-build` 的 Checkpoint 1。完成 1.1、1.2 前置及正式 AC 核对后，提交 Story 1.3 规格请负责人决定。 [实施规格](_bmad-output/implementation-artifacts/spec-1-3-view-equipment-catalog.md)
2. **AI 建议及理由**。建议批准并继续。现有模型和登录路径已满足基本依赖，依 FR-003／002、ADR-001／002／003 实施普通只读查询，无需迁移。正式库只需补六列 SELECT，另获授权后才能执行。
3. **人类判断与依据**。负责人在本会话对 Checkpoint 1 回复「批准并继续」。批准对象是保持正式六条 AC 的实施规格，未批准正式库授权或最终验收，未另述比较理由。不视为三人表决或否决／实质修改。
4. **结果**。仅新增目录、详情和对应回归；实现后按要求停在 `review`，未开始 1.4，未改变已批准的 Sprint 范围或实验 A 条件，未提交或推送。 [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml)
5. **事后验证**。隔离库原套件 45/45，新增后全量 54/54。正式六条 AC 均有开发自测证据，业务角色授权、独立评审及最终验收仍待后续。 [开发证据](_bmad-output/implementation-artifacts/story-1-3-dev-evidence.md)

## D-029 2026-11-25 负责人批准 Story 1.3 独立评审处置

1. **触发**。BMAD 6.12.4 `full` 独立评审 Step 4。团队收到四视角裁决与首轮证据。R1 涉及 AC-2 多行说明可见完整性，独立隔离回归因受限解释器未运行。 [首轮独立评审](_bmad-output/implementation-artifacts/story-1-3-independent-review.md)
2. **AI 建议及理由**。保留行动项，交原 Build 会话最小修正说明显示。用 CSS `white-space: pre-wrap` 保留分行与连续空白，不触及业务读写或现有授权。Low 项是当前实现未失效时的覆盖增强，记录风险与触发节点，不把正式库验证混入隔离回归。
3. **人类判断与依据**。项目负责人实际选择方案 2。批准 R1 必修，指定保留 Django 自动转义、不使用 `safe` 或 `mark_safe`。批准其余八项 Low 仅在不影响正式 AC、安全和数据一致性的前提下延期，保留原 R2/R8 和三项驳回的裁决。依据为正式 AC-2、FR-003／002、ADR-001／002／003、PC-008／011 和评审证据。负责人要求 R1 修复后合并进行独立测试，不将开发 54/54 认作独立结果。本条只记录负责人的实际决定，不代填三位组员的个人决定。
4. **结果**。1 项待整改、10 项延期跟踪、3 条原始发现驳回、0 项修复。按 Step 4 规定整改目标为 `in-progress`，规格、延期台账和 Sprint 跟踪的实写结果以处置记录为准。原 Build 会话的 R1 交接已保存。本轮不修改业务代码、不访问业务库、不执行授权、不开发 Story 1.4、不标 `done`、不暂存、提交或推送。 [逐项处置](_bmad-output/implementation-artifacts/story-1-3-review-disposition.md) · [整改交接](_bmad-output/implementation-artifacts/story-1-3-remediation-handoff.md) · [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml)
5. **事后验证**。截至本次决定，独立 Django 实际执行 0 项，开发证据 54/54 保持原口径。待 R1 修复后由独立评审会话在原 Python 3.13.17 的隔离库统一复跑，保存实际分母和退出码，复核 AC-1～AC-6、R1 展示及转义、T-03、Story 1.1／1.2 回归。正式业务库授权、运行验证与最终验收均未获本次批准。实验 A 条件与数据不变。

   **2026-11-25 落实补记**。原 Build 续接已批准的 R1，补录规格与延期台账，仅修说明展示并保留自动转义。隔离开发自测 55/55，含 Chrome 可见分行、空格和字面文本验证。Sprint 回到 `review`，正式库未访问，独立复审与最终验收仍待完成。本补记是实施结果，不是新增人类决定。 [整改证据](_bmad-output/implementation-artifacts/story-1-3-dev-evidence.md#2026-11-25-r1-整改与开发自测)

   **2026-11-25 独立复审补记**。实际重新执行隔离库回归 55/55 无跳过，Chrome 说明渲染、正式六条 AC 和本入口 T-03 均有本轮独立证据。技术判断建议关闭 R1，尚未记录负责人关闭决定、正式库授权或最终验收。此补记只完成 D-029 的事后取证，不新增人类决策，不计入实验 A。 [独立复审](_bmad-output/implementation-artifacts/story-1-3-independent-recheck.md)

## D-030 2026-11-25 负责人关闭 R1 并批准 Story 1.3 业务库验证

1. **触发**。BMAD 6.12.4 Story 1.3 R1 独立复审完成，原 Python 3.13.17 在隔离库通过 55/55，无跳过，Chrome 验证了正式 AC-2 的多行说明和自动转义。 [独立复审](_bmad-output/implementation-artifacts/story-1-3-independent-recheck.md)
2. **AI 建议及理由**。建议关闭 R1。目录和详情实际查询需在原 `SELECT(id)` 之外补六列 SELECT，隔离角色不能替代业务运行角色验证。建议用单事务核查和授权，再用既有三类账号、既有演示档案验证。依据 FR-003／FR-002、ADR-001／002／003、正式 AC 和既有 D-026 ACL。 [授权方案](_bmad-output/implementation-artifacts/story-1-3-independent-recheck.md#4-正式库最小-select-与运行验证方案仅核对)
3. **人类判断与依据**。项目负责人明确接受复审结论，正式批准关闭 R1 并保留此前延期决定。仅批准 `127.0.0.1:5433/lab_booking` 17.12 上六列读取授权、同事务前后核验及三角色真实 Chrome 验证。不得迁移、修改设备、扩大授权或重跑已有有效测试，不批准最终验收、下一 Story 或 Git 提交。三位组员共同查看和审阅，不分派个人任务或代填个人意见。
4. **结果**。规格登记 R1 已关闭，授权批次退出 0，`lab_booking_app` 有效设备 SELECT 由主键扩大到七列，原 INSERT 不变，无新写入或 DDL 权限。三角色浏览器批次退出 0。本机运行服务保留供团队查看，Sprint 保持 `review`，Story 1.4 保持 `backlog`。 [运行证据](_bmad-output/implementation-artifacts/story-1-3-runtime-evidence.md)
5. **事后验证**。运行角色独立只读快照前后各 1 台设备、17 条迁移、1 条既有会话，设备全字段摘要相同。三角色实际从目录点击及直达正确详情，404、匿名和退出后拦截均通过。实验 A 不变，最终验收待负责人另行决定。 [原始授权与运行输出](_bmad-output/implementation-artifacts/story-1-3-runtime-output.txt)

## D-031 2026-11-25 Story 1.3 负责人最终验收

1. **触发**。R1 已由 D-030 正式关闭并完成批准的业务库最低读取授权和真实 Chrome 运行验证，Story 1.3 等待负责人最终验收。 [D-030 运行证据](_bmad-output/implementation-artifacts/story-1-3-runtime-evidence.md)
2. **AI 建议及理由**。独立复审结论为 R1 可关闭、正式六条 AC 在隔离环境满足，无新增验收阻塞。独立 55/55 与 D-030 的本机运行证据支持进入最终验收，不能相互替代。 [独立复审](_bmad-output/implementation-artifacts/story-1-3-independent-recheck.md)
3. **人类判断与依据**。负责人明确批准 Story 1.3 最终验收，接受 AC-1～AC-6、独立 55/55 无跳过、D-030 的 R1 关闭和六列授权、三角色 Chrome 以及只读和设备前后一致证据。确认此前延期和第二台 Windows 复现继续跟踪，并授权检查通过后提交和推送本 Story。不代填其他组员意见。
4. **结果**。按 BMAD 6.12.4 Build Step 5 将规格归档为 `done`，按负责人最终验收同步 Sprint，Epic 1 保持 `in-progress`，Story 1.4 及其他未开始 Story 保持 `backlog`。更新验收记录、README 和评审处置，保留先前真实证据。 [最终验收](_bmad-output/implementation-artifacts/story-1-3-final-acceptance.md) · [Sprint 跟踪](_bmad-output/implementation-artifacts/sprint-status.yaml)
5. **事后核对**。沿用独立 55/55 与 D-030 真实运行结果，未重跑测试或访问数据库。既有实验 A 条件不变，本 Story 结果不计入实验 A，第二台 Windows 复现尚未发生。 [延期台账](_bmad-output/implementation-artifacts/deferred-work.md)

## D-032 2026-11-25 负责人批准 Story 1.4 实施规格

1. **触发**。BMAD 6.12.4 Build Checkpoint 1，核对前置 1.1～1.3 为 done，提交正式 AC-1～AC-8 对应规格。 [检查点](_bmad-output/implementation-artifacts/story-1-4-checkpoint-1.md)
2. **AI 建议**。复用现有设备及角色基础，短事务取设备锁、重读并原位更新四列。建议批准实施规格，四列 UPDATE 留给独立评审后的正式库批准。
3. **人工判断与依据**。负责人回复「批准并继续」，明确以 AC-1～AC-8、D-024 和 Story 1.2 事务验证为依据，原则接受四列授权但不批准本次正式库 GRANT。要求真实隔离锁、异常和 55 项基线回归，权限受阻则提供普通 PowerShell 执行方案，不提前进入 review。
4. **结果**。规格获批进入 ready-for-dev，按正式 Build Step 3 开始实施后进入 in-progress。三位组员共同操作及审阅，不代写个人判断。未批准业务库访问、Git 操作或最终验收。 [实施规格](_bmad-output/implementation-artifacts/spec-1-4-edit-equipment-basics.md)
5. **事后验证**。待以原 Python 3.13.17 以及指定隔离库完成实际测试后补证，历史 55/55 不替代本轮结果，实验 A 条件及数据不变。

   **2026-11-25 事后取证**。三位组员共同操作及审阅，团队在普通 PowerShell 应用补丁并用原 Python 3.13.17 在指定隔离库完成测试。按名称核对原回归 55/55、新增 12/12，零跳过，真实事务探针 8/8，正式 AC-1～AC-8 均有开发自测证据。Codex 仅核对差异和日志，未复跑。Sprint 进入 `review` 待新会话独立评审，不代表最终验收。没有执行正式业务库 GRANT 或迁移，没有变更实验 A。本补记不新增人类决定。 [开发证据](_bmad-output/implementation-artifacts/story-1-4-dev-evidence.md) · [团队原始日志](_bmad-output/implementation-artifacts/story-1-4-verification-20261125-221855-930.txt)

## D-033 2026-11-25 负责人批准 Story 1.4 独立评审处置

1. **触发**。BMAD 6.12.4 `bmad-code-review` `full` Step 4。基于 Story 1.3 最终验收提交 `e200fee` 的四视角独立评审得出 7 项建议整改、2 项原延期跟踪、12 条原始发现驳回。 [首轮独立评审](_bmad-output/implementation-artifacts/story-1-4-independent-review.md)
2. **AI 建议及依据**。建议选择方案 2，把整改留为行动项并交回原 Build 会话。优先解决 R1 锁后权限复核（PC-008、AC-4/AC-6）、R2 多行说明保真（AC-1）和 R7 权限证据留存（PC-011、T-03）；R3～R6 是覆盖增强，不是已确认的实现失败。正式库权限仍由 D-032 约束，不能用测试角色核验代替。
3. **人类判断与依据**。负责人在本次会话实际选择「方案2：保留为行动项」，批准原 Build 在本整改周期修复并验证 R1、R2、R7；R3～R6 仅在不影响正式 AC、安全性和数据一致性的前提下延期，逐项记录理由、残余风险与后续验证节点。原 W1、W2 和 12 条驳回依据保留，不声称关闭。要求整改后才统一独立复验，不复跑整改前版本。三位组员共同操作与审阅，不另分派或代填个人结论。
4. **结果**。记录 3 项整改、6 项延期跟踪、12 条保留驳回、0 项修复。实施规格由 `in-review` 转 `in-progress`，Sprint 项由 `review` 转 `in-progress`；已登记原 Build 交接，不在本评审会话实施。台账实写结果以处置记录为准。未改业务代码、未访问业务库、未执行 GRANT，Story 2.1 仍为 `backlog`，未标记 `done`、暂存、提交或推送。 [处置记录](_bmad-output/implementation-artifacts/story-1-4-review-disposition.md) · [整改交接](_bmad-output/implementation-artifacts/story-1-4-remediation-handoff.md) · [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml)
5. **事后验证**。本轮独立 Django、PostgreSQL 探针实际执行均为 0 项；原 67/67、8/8 仍为团队开发自测，不转记为独立结果。整改后在原 `.venv` Python 3.13.17 和批准的隔离测试库统一验证三项整改、正式 AC-1～AC-8、T-01/T-03 及既有回归，记录实际执行者、被测版本、分母、原始输出和退出码。实验 A 保持不变，未批准正式库核验或最终验收。

   **2026-11-25 Build 整改补记**。R1／R2／R7 四文件增量补丁已通过适用性和临时副本校验。沙箱对实际业务源码写入仍受限，原 `.venv` 启动仍退出 103，本轮整改后的 Django 和 PostgreSQL 实际执行均为 0 项。待团队普通 PowerShell 应用增量并保留实际自测，状态仍为 `in-progress`。不把静态校验当成独立评审或整改关闭。 [整改证据](_bmad-output/implementation-artifacts/story-1-4-remediation-evidence.md)

   **2026-11-25 整改事后验证**。团队在普通 PowerShell 应用增量并以批准的隔离库实测 Django 68/68、真实探针 10/10。汇总退出 1 来自包装未识别 R2 成功输出中的冒号。原日志、错误、清单均原样保留；仅修正精确标记，使用已有原始证据重算全部断言通过，未重跑或改业务代码。规格和 Sprint 回到评审状态，交独立复审和独立复验。六项延期及实验 A 不变，正式库授权及最终验收未执行。本补记不是新的人工决定。 [整改证据](_bmad-output/implementation-artifacts/story-1-4-remediation-evidence.md)

## D-034 2026-11-26 负责人处置 Story 1.4 针对性独立复审发现

1. **触发**。BMAD 6.12.4 `bmad-code-review` Step 4。整改后四层静态复审核对 AC-1～AC-8 与历史团队自测，提出 Q-1～Q-3 三项低风险覆盖改进。 [独立复审](_bmad-output/implementation-artifacts/story-1-4-targeted-independent-recheck.md)
2. **AI 建议及依据**。把 R1 和 T-03 无泄露字段、匿名跳转留档和已存 CRLF 保真分别作为 Q-1～Q-3 呈报。前两项未见业务泄露或错误跳转，第三项属覆盖不足，未观察到说明被改写。依据 AC-1、AC-4、AC-6、PC-008／011 与 D-033。
3. **人类判断与依据**。负责人明确接受静态审查并选择「方案 2：保留为行动项」。现有证据满足正式 AC 时，Q-1、Q-2 条件性延期。Q-3 纳入本轮独立复验，若实际改写按正式 AC 缺陷处理，若补证通过且仅覆盖不足，可作非阻塞改进。68/68、10/10 是团队开发自测，不能充作独立运行。要求原 Python 3.13.17 与批准的隔离测试库，留存实际操作者与完整原始输出，未授权业务代码变更、正式库授权或最终验收。
4. **结果**。Step 4 记录 0 项现改、1 项待复验、2 项条件延期。规格及 Sprint 转为 `in-progress`，Story 2.1 保持 `backlog`。原延期台账写句柄仍被拒绝，Q-1、Q-2 单列已决附录，未覆盖既有内容。新增本机独立复验入口及独立 Q-3 测试工件，不改变现有业务、测试套件或验证包装。 [延期附录](_bmad-output/implementation-artifacts/story-1-4-targeted-review-deferred-appendix.md) · [复验入口](_bmad-output/implementation-artifacts/verify-story-1-4-independent-remediation.ps1)
5. **事后验证**。待团队从普通 PowerShell 回传两目录的新证据再逐项核对正式 AC 和 R1／R2／R7，并据 Q-3 实际回读分类。当前未进行新数据库测试，不重复尝试沙箱的 103 命令，不复用历史结果作独立结果。正式库、实验 A、既有延期及验收状态不变。未暂存、提交或推送。

   **2026-11-26 事后取证**。团队按独立复审委托在普通 PowerShell 新执行，评审仅核验原输出、退出码与前后文件散列，未复跑。68/68 Django、10/10 PostgreSQL、另列 Q-3 1/1 均通过，已有 CRLF 两种传输形式字节完全不变。未发现新增正式 AC 阻塞，Story 1.4 已恢复 `review`。建议关闭 R1／R2／R7／Q-3，Q-1／Q-2 条件延期不变；本补记不代作人工关闭、正式库授权或最终验收。 [本轮证据](_bmad-output/implementation-artifacts/story-1-4-targeted-independent-recheck.md#2026-11-26-独立复验结果) · [待审批正式库方案](_bmad-output/implementation-artifacts/story-1-4-runtime-authorization-plan.md)

## D-035 2026-11-26 负责人关闭 Story 1.4 四项发现并批准正式库验证

1. **触发**。正式四视角独立复审和独立复验完成，已核对 68/68 Django、10/10 真 PostgreSQL 探针、另列 Q-3 1/1，Story 处于 `review`。 [复验](_bmad-output/implementation-artifacts/story-1-4-targeted-independent-recheck.md#2026-11-26-独立复验结果)
2. **AI 建议及依据**。建议关闭 R1、R2、R7、Q-3，并另批正式业务库四列 UPDATE 及正常运行验证。R1、R7 对应角色及证据，R2 与 Q-3 对应说明保真；授权增量按 D-032、AC-1～AC-8、ADR-003 和旧 D-026／030 的权限留档。 [授权方案](_bmad-output/implementation-artifacts/story-1-4-runtime-authorization-plan.md)
3. **人类判断与依据**。负责人接受独立复验，明确正式关闭 R1、R2、R7、Q-3，Q-1、Q-2 和其它延期保持。批准由 `lab_booking_migrator` 在 `127.0.0.1:5433/lab_booking` PostgreSQL 17.12 同事务核对并仅授予 `lab_booking_app` 设备四列 UPDATE。批准原 Python 3.13.17 runtime、三类既有预置账号 Chrome 验证及对既有演示设备 `EQ-DEMO-S12-20261125` 的必要编辑，并验证角色拒绝和伪造编号／状态不造成部分修改。不批准新迁移、旧 5432 实例、服务器配置、全表写权限、正式库并发／故障注入、最终验收或 Git 操作。
4. **结果**。正式关闭四项，规格与 Sprint 仍为 `review` 的对应状态。已备妥 SQL 守卫批次、普通 PowerShell 与 Chrome／独立回读验证。三位组员共同操作及审阅，不代填个人决定；既有 8000 未停止。 [本机执行交接](_bmad-output/implementation-artifacts/story-1-4-runtime-handoff.md)
5. **事后验证**。本会话受保护密码文件元数据访问被拒，具体额外授权自动拒绝，尚未连接正式库、授权、启动新服务或执行 Chrome；实际结果等待团队普通 PowerShell 回执。既有 68／10／Q-3 证据未重跑、实验 A 不变。待归档真实 ACL、浏览器、独立库回读和访问地址，再另行处理 W1 与最终验收。

   **2026-11-26 首次运行失败与事后核验**。团队实际在普通 PowerShell 执行，原始输出记录迁移表的 `app` 列与同名 PL/pgSQL 变量冲突，psql 退出 3。失败发生在 `GRANT` 之前，原批次因 `ON_ERROR_STOP=1` 和 `--single-transaction` 回滚，本次没有新增权限，运行验证未启动。仅修复 SQL 字段限定，原授权断言、快照和运行入口不变。当前有效 ACL 尚未由沙箱读回，团队先只读核验，无更新权限时方可续跑原批准流程；仅已有四列且无额外有效权限时走 `-RuntimeOnly`。原始记录保持不变，Story 1.4 仍为 `review`，W1 及最终验收仍待真实运行证据。本补记不是新人工决定，实验 A、关闭项和延期项保持原口径。 [原始错误](_bmad-output/implementation-artifacts/story-1-4-runtime-run-20261126-105606-102/acl-raw.txt) · [首次汇总](_bmad-output/implementation-artifacts/story-1-4-runtime-run-20261126-105606-102/run-summary.txt) · [修复与续跑](_bmad-output/implementation-artifacts/story-1-4-runtime-handoff.md)

   **2026-11-26 11:20 授权已提交，运行验证待恢复**。团队普通 PowerShell 的授权前只读检查为 `NOT_GRANTED`，授权输出 `D035_ACL_ASSERTIONS_PASSED` 且退出 0，随后原运行角色独立只读查询通过，确认仅四列 UPDATE 生效。现有 8001 服务启动并保留；Node 在启动 Chrome 之前因类别值相同退出 1，没有提交设备编辑。仅更换类别验证值并加固恢复工具及证据核对。团队只可在新的只读核验通过后走 `-RuntimeOnly`，不重授，不停止未知进程。当前会话未连接业务库，运行实测仍待回执，Story 1.4 为 `review`，W1 与最终验收仍未完成。此次记录是 D-035 事后验证，不新增人工决定，不改变实验 A、正式需求或延期。 [授权前只读记录](_bmad-output/implementation-artifacts/story-1-4-runtime-acl-check-20261126-112028-049/acl-raw.txt) · [授权与启动汇总](_bmad-output/implementation-artifacts/story-1-4-runtime-run-20261126-112028-249/run-summary.txt) · [恢复命令](_bmad-output/implementation-artifacts/story-1-4-runtime-handoff.md#普通-powershell-恢复命令)

   **2026-11-26 11:46 恢复执行并完成 D-035 事后验证**。团队普通 PowerShell 实跑，自报操作者 `w`。只读 ACL 为 `GRANTED` 且退出 0，有效权限与原授权后矩阵一致，没有再次 GRANT。复用 8001 的项目服务，业务角色只读和 Chrome 各退出 0。匿名和师生六例拒绝且无泄露、设备不变，伪造编号和状态各 400 且整行不变。管理员正常提交一次，四列变化，主键、编号、状态及设备数量不变，提交后及退出后独立读回一致。原始中止日志保留，全量输入散列匹配。结合独立隔离 68/68、10/10、Q-3 1/1，W1 发布验证证据完成，无新增验收阻塞。Story 1.4 仍为 `review`，Epic 1 仍为 `in-progress`，等待负责人最终验收。本补记不新增人工决定，不计入实验 A，不变更既有问题处置，未执行新的数据库、测试或 Git 操作。 [只读 ACL 汇总](_bmad-output/implementation-artifacts/story-1-4-runtime-acl-check-20261126-114602-047/run-summary.txt) · [运行汇总](_bmad-output/implementation-artifacts/story-1-4-runtime-run-20261126-114602-260/run-summary.txt) · [实证与 AC 对照](_bmad-output/implementation-artifacts/story-1-4-runtime-evidence.md) · [收尾清单](_bmad-output/implementation-artifacts/story-1-4-closeout-checklist.md)

## D-036 2026-11-26 Story 1.4 最终验收与 Epic 1 收尾

1. **触发**。Story 1.4 已完成独立复验及 D-035 正式库只读恢复与运行核验，W1 已取证。此前保留 `review` 等待负责人最终验收。 [实证与正式 AC](_bmad-output/implementation-artifacts/story-1-4-runtime-evidence.md)
2. **AI 建议及依据**。综合八条正式 AC、独立复验和正式库 Chrome／独立回读，无新增验收阻塞。建议验收，再按四条已完成 Story、实证与既有延期核对 Epic 1，不将范围扩大到 Sprint 1 或全项目 NFR。 [验收准备](_bmad-output/implementation-artifacts/story-1-4-closeout-checklist.md)
3. **人类判断与依据**。负责人明确批准 Story 1.4 最终验收，接受 AC-1～AC-8、68/68 Django、10/10 PostgreSQL、1/1 Q-3、R1／R2／R7／Q-3 已关闭、D-035 四列最小授权和真 Chrome、设备主键／编号／状态／总数保持的证据。批准保留延期、第二台 Windows 待复现和实验 A 原安排，并授权满足条件后完成 Epic 1、按指定消息提交及推送 main。本决定不是三位组员分别发表意见。
4. **结果**。Story 1.4 规格与 Sprint 已为 `done`。Epic 1 经 4 条 Story、28 条编号 AC 的实证追溯、跨 Story 差异检查和证据回顾收尾，为 `done`，回顾裁决 `accepted-with-open-items`。其余已批准延期不变，Story 2.1 和其他未开始 Story 仍为 `backlog`。 [最终验收](_bmad-output/implementation-artifacts/story-1-4-final-acceptance.md) · [Epic 1 回顾](_bmad-output/implementation-artifacts/epic-1-retro-2026-11-26.md)
5. **事后验证**。复核已有证据、运行前后输入和 53 项隔离认证散列。没有新测试、业务代码修改、迁移、重授、正式需求变更或实验 A 度量。新提交及同步结果以实际 Git 历史和远程 SHA 为准，不预填。 [Sprint 状态](_bmad-output/implementation-artifacts/sprint-status.yaml)

## D-037 2026-11-26 负责人批准 Epic 1 新增设备导航改进

1. **触发**。团队实际体验报告管理员登录后找不到新增设备页面入口。只读检查确认身份页、目录和详情无新增链接，原新增路由有 Story 1.2 真实运行证据，符合 Epic 1 回顾的既有导航观察。 [Epic 1 回顾](_bmad-output/implementation-artifacts/epic-1-retro-2026-11-26.md)
2. **AI 建议及依据**。归类为非阻塞集成可用性改进。在身份页与目录复用仅启用业务管理员可见的新增模板链接，目录空态也可用。沿用 Story 1.2 原路由及 FR-016／FR-002 的服务端权限，不改变正式 AC。
3. **人类判断与依据**。项目负责人明确接受团队实际体验及只读诊断，批准最小模板改进与隔离验证、独立评审、核对身份后的既有 8001 服务重启。保持学生教师导航、详情、数据库、Story 及 Epic 状态，禁止自动提交推送。此处只记录负责人当轮决定，不代填组员意见。
4. **结果**。四文件增量、四项导航回归和本机验证／重启入口已备妥。实际源目录出现写入拒绝，已撤回仅部分写入的模板改动，工作区补丁预检及临时副本应用均通过。独立静态评审未发现阻塞，未冒充实测。 [补丁和审查证据](_bmad-output/implementation-artifacts/epic-1-create-navigation-evidence.md)
5. **事后验证**。沙箱原 `.venv` 实际退出 103，0 项新 Django 实测，旧 8001 未停止。待团队普通 PowerShell 应用、在隔离库实跑并完成受控重启后核对退出码与回执。GitHub main 实查不含此前本地 Story 1.4 提交。Story 1.1～1.4 和 Epic 1 仍为 `done`，Story 2.1 为 `backlog`，实验 A 不变。

   **2026-11-26 15:55 实测与收尾**。团队自报操作者 `w` 在普通 PowerShell 实际应用并验证，当前四文件差异和散列均匹配已独立静态评审版本。隔离回归 4/4、无跳过、退出 0，覆盖管理员身份页、目录及空态的表单链接、师生不显示且直达 403、匿名或停用管理员跳转。8001 新监听 PID 18648，匿名运行冒烟 200／302。后续实际访问另有两次新增表单 GET 200，脱敏摘录未显示该表单 POST，不归属个人或点击来源。负责人在回执会话明确批准全部证据通过后收尾并提交、推送，本轮按该条件执行。无新 AC 回归，原 Story 或 Epic 状态、既有权限、实验 A 和 Story 2.1 状态不变。 [实际验证与过程](_bmad-output/implementation-artifacts/epic-1-create-navigation-evidence.md) · [原始日志](_bmad-output/implementation-artifacts/epic-1-create-navigation-run-20261126-155547-825/raw.txt)


## D-038 2026-11-26 负责人批准 Story 2.1 Checkpoint 1

1. **触发**。在 BMAD 6.12.4 Build Step 2 提交 Story 2.1 完整实施规格及集中验证设计。基线为 e196aba098771a31eb203be4270b460d5e0aab42，Epic 1 已完成。 [检查点](_bmad-output/implementation-artifacts/story-2-1-checkpoint-1.md)
2. **AI 建议及依据**。用两个真实外键及 CHECK 实现 R-04 单对象完整性，复用设备行锁、显式 Read Committed、会话和数据库隔离。按 FR-018 使状态及历史同事务，区分业务拒绝、数据库失败和提交未知，严守正式 AC-1～AC-11、20 请求十轮以及 T-01～T-04 取证设计。
3. **人类判断与依据**。项目负责人在当前会话明确回复「批准并继续」，批准实施规格、R-04、事务及申请结果、T-01～T-04，要求继续完成全部原 AC，不降并发标准。接受受限时交付增量补丁和普通 PowerShell 验证方案。只允许隔离测试库，正式库另批。保持 Sprint 8／5、小组三人共同操作、无自动 commit 或 push。未记录独立的逐人意见。
4. **结果**。将 Story 2.1 实施规格由 draft 推进到 ready-for-dev，授权正式 Build 继续。本授权不扩展到 2.2 或其他 Story、不批准正式库迁移或权限变更，也不批准标记 done。
5. **事后验证**。待按 AC-1～AC-11 收集真实测试、隔离目标、事务、权限及 20×10 证据。全部开发自测通过才转 review，再交新会话独立 bmad-code-review。 [实施规格](_bmad-output/implementation-artifacts/spec-2-1-submit-reservation.md)

   **2026-11-26 事后实证**。团队报告在普通 PowerShell 完成实测。原始 Django 90/90、权限拒绝 12/12、R-04 与两条隔离迁移证据仍有效。首次 I1 探针漏采带别名的账号 SQL，保留失败并只修验证工具。定向复验交错 15/15、故障 5/5、20×10 标准竞争 10/10 与真实整点验证全部通过，清理及散列一致。依据本轮明确的条件授权，Story 2.1 已进入 Sprint `review`，未执行独立评审或最终验收。这是 D-038 的事后核验，不是新人工决定或逐人表决。正式库、实验 A、后续 Story 及 Git 提交不变。 [复验证据与交接](_bmad-output/implementation-artifacts/story-2-1-dev-evidence.md#2026-11-26-复验核验与独立评审交接)


## D-039 2026-11-26 负责人批准 Story 2.1 独立评审处置

1. **触发。** 安装版 BMAD 6.12.4 `bmad-code-review` `full` Step 4。基线 `e196aba098771a31eb203be4270b460d5e0aab42`，四层报告齐全，原始裁决为 18 Patch、1 未核实 Defer、3 Rejected。依据为当前会话的范围确认、正式 AC-1～AC-11、D-038、R-04、T-01～T-04，以及 [原评审与离线核验](_bmad-output/implementation-artifacts/story-2-1-independent-verification/review-checkpoint.md)。
2. **AI 建议及理由。** 建议选「2 保留为行动项」。P01 是 AC-3 的真实页面恢复缺陷。P02 与 P03 分别缺 AC-10／PC-011／T-03 同角色异主对照和 AC-10／T-01 固定候选真实交错。其余 P04～P18 按原始证据逐项评估为可条件延期，D01 未核实不宣称已关闭。
3. **人类判断及依据。** 负责人在本会话回复「选择2：保留为行动项」，随后明确批准一次只整改 P01、P02、P03。P01 不放宽服务端时段规则，P02 须证明拒绝／无泄露／无业务变化，P03 须证明实际等锁期间新增同一申请人候选仍不会被本次读取收尾。P04～P18 仅在不影响正式 AC、安全性、数据一致性和 NFR 验收的前提下批准延期，D01 保持待核实，原始 #5／#14／#16 继续驳回并保留理由。三人共同操作和审阅，不代填个人意见。不批准本轮改业务代码、访问正式业务库、标 done、提前做 2.2 或自动 commit／push。
4. **结果。** Step 4 裁决为 3 项待整改、15 项有条件延期、1 项仍待核实、3 项驳回、0 项修复。BMAD 状态目标为实施规格和 Sprint 同步回 `in-progress`，实际文件落盘状态以[处置记录](_bmad-output/implementation-artifacts/story-2-1-review-disposition.md)为准。8／5、正式要求和实验 A 不变。交[一次性整改交接](_bmad-output/implementation-artifacts/story-2-1-remediation-handoff.md)，不把批准当作已整改或最终验收。
5. **事后验证。** 当前独立 Django／PostgreSQL 新运行均为 0。保留开发方原始 Django 90/90、交错 15/15、未授权 12/12、故障 5/5、NFR-001 标准组 200 个响应／10/10 轮和实际 18:00 边界。P01～P03 整改、自测并按原 Build 规则回到 `review` 后，在独立会话统一实跑，保存版本、实际分母、无跳过、退出码、真实原始快照及阶段结果，不把原始开发记录冒充独立运行。


## D-040 2026-11-26 负责人处置 Story 2.1 针对性独立复审并批准最小证据补强

1. **触发。** BMAD 6.12.4 `bmad-code-review` full Step 4，P01～P03 四视角复审 0 Decision、10 Patch、1 Defer、4 Rejected。未观察到业务回归，P02 实际认证主体与 P03 SQL 参数仍缺可核验的绑定。 [逐条裁决](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/review-triage.md)
2. **AI 建议。** 选择 2 保留行动项，结论与开发、离线核验、独立实跑三者分开。现有 Chrome 纠错不改业务；同一 404 记录真实请求主体；I7 记录固定授权目标绑定及锁后唯一取时。
3. **负责人判断。** 明确选择 2，接受四视角结果，并指示不把全部测试加固一并实施。必须补足 R02/R06/R07/R10 的证据闭环，同意其余非阻塞项按原编号保留残余风险及节点。P01 只等实际独立复验，原 D-039、P04～P18、D01 和驳回不改。授权限验证工具和一次性隔离复验，不批准访问正式库、迁移、GRANT、2.2、done 或 commit/push。
4. **结果。** 按正式 Step 4 管理为 4 项待验收的必做证据补强、6 项新延期、原 RD01 继续延期、4 项本轮驳回，无业务修复。规格和 Sprint 按行动项回 `in-progress`。原 Build 会话只承接验证工具；Sprint 8/5 和三人共同操作不变。不代填成员个人决策。 [处置与交接](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d040-disposition-build-handoff.md)
5. **事后验证。** 单次独立入口以 91 项版及实际鉴权/SQL 绑定为硬门槛，记录真实退出码、原始日志、文件散列和清理。仅隔离库。历史 NFR-001 20×10／200、故障 5/5 和北京时间 18:00 原证据复用，不计作新独立测试。新动态证据待普通 PowerShell 回执。




   **2026-11-26 D-040 事后验证。** 负责人报告已运行新版入口，团队普通 PowerShell 20:52～20:53 真正执行隔离批次，独立评审会话读取原始日志和输入散列并只读复算，不冒充由评审会话启动运行。Django 91/91（零跳过）、双角色导航、Chrome、13/13 拒绝及 15/15 交错通过。P01～P03、R02/R06/R07/R10 建议关闭，不代填负责人最终验收。正式 AC-1～AC-11 核验通过，历史 NFR 200 响应、5/5 故障和 18:00 边界复用，不重跑。按负责人当前条件授权，规格 in-review／Sprint review，未标 done。中央延期台账仍拒绝写入，前后散列一致，已保留待合并稿，原延期保留。Sprint 8/5、2.2 与实验 A 不变。 [独立复审收尾](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d040-independent-final-review.md) · [正式库发布方案（未执行）](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/runtime-release-handoff.md)



## D-041 2026-11-26 负责人关闭 Story 2.1 独立复验项并有条件批准正式运行

1. **触发。** BMAD 6.12.4 实施与代码评审收尾。D-040 的普通 PowerShell 实跑及独立原始日志复核支持 AC-1～AC-11，旧标准竞争和故障、18:00 未重跑。 [独立复审证据](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d040-independent-final-review.md)
2. **AI 建议。** 关闭 P01～P03、R02/R06/R07/R10。正式库只改获批的两个初始迁移和两张表的候选列权限，发布、有效权限和浏览器分关验证。批准持久创建限一条课程预约，不能把未知提交当失败重做。
3. **负责人判断。** 接受 D-040 并正式关闭上述七项，批准仅在 PostgreSQL 17.12 本机业务库 lab_booking，由 lab_booking_migrator 核对备份、迁移及限定 GRANT，用运行角色和现有师生管理员账号在设备 EQ-DEMO-S12-20261125 验证。允许留下恰好一条课程演示预约，重叠申请应明确拒绝。未知服务不得停止，超范围迁移或授权停。原延期继续，不允许批清理、故障注入、200 响应重跑、后续故事、done 或 Git 发布。
4. **结果。** 正式关闭记录落盘，Story 2.1 保持 review，Story 2.2 保持 backlog，Sprint 8/5、实验 A、三人共同操作保持，不代填成员个人意见。本次沙箱检查受保护 passfile 的存在即被拒绝，未尝试通过替代凭据、未连接正式库。正式执行移交普通 PowerShell 入口。此前证据只读保留。
5. **事后验证。** 以独立正式运行回执核对迁移、R-04、实际有效权限及 Chrome 单条预约/持久化证据。在取得回执前不能宣称已部署或具备最终验收条件。



   **D-041 执行接力。** 已固化普通 PowerShell 单次正式入口、独立延期合并入口和只读恢复路径。沙箱查受保护文件和端口所属进程均受限，中央台账合并拒绝写入且文件未变化。未连接正式库、未启动或停止服务、未执行迁移／GRANT 或正式 Chrome，也没有新增演示预约。实际登录、预约入口及最终验收资格均待执行回执。 [正式运行接力](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d041-production-handoff.md) · [延期合并阻塞](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d041-deferred-merge-result.json)

   **2026-11-26 D-041 事后验证。** 团队普通 PowerShell 首次正式运行取得受保护备份，两条授权迁移均提交并经登记和对象回读确认。部署于 GRANT 前的 ACL 目录探针以 22023 停止，未启动后续服务或 Chrome，未发出本批次演示预约。独立临时 PostgreSQL 17.12 重现零维 ACL 数组报错并核验修复后的空白、精确和过宽权限三种结果；只改部署工具，业务及证书 75 项未漂移。正式库当前状态及后续授权／运行仍待团队只读回执，仅按状态定向续跑。无新增人工决定、无延期关闭，Story 2.1 review、2.2 backlog，8/5 和实验 A 不变。 [原失败与恢复命令](_bmad-output/implementation-artifacts/story-2-1-targeted-independent-recheck/d041-production-handoff.md#2026-11-26-实际故障与定向恢复)


## D-042 2026-11-26 负责人最终验收 Story 2.1

1. **触发。** 团队已打开新版体验，学生可提交。负责人明确说明本人全部预约入口和管理员预约管理入口分别归 2.3/2.5，不作为 2.1 缺陷，要求按 AC 和真实运行证据判断。 [正式运行与失误恢复](_bmad-output/implementation-artifacts/story-2-1-runtime-evidence.md)
2. **AI 判断。** 只读复算同时核对首次仅两项提交迁移、22023 失败、修复后的只读空白 ACL、续跑单次精确 GRANT、实际 Chrome 和独立持久化。中央延期三段逐段匹配。没有新增验收阻塞，建议保持范围并标 2.1 done。
3. **人类决定。** 负责人明确在正式 AC-1～AC-11 均满足且无阻塞时批准最终验收、文档及 Git 同步，指定一个 commit 消息和普通 PowerShell 推送退路。保持 Epic 2 in-progress、2.2 等未开始 Story backlog、Sprint 8/5。三人共同操作，不虚构成员各自意见。
4. **结果。** 条件经独立核对成立，实施规格和 Sprint 的 2.1 均为 done，2.3/2.5 不提前开始，D-041 原关闭、延期和 D01 未核实不变。未执行新的测试、迁移、授权或业务代码修改。Git 实际提交、推送和 SHA 另行如实报告，书面决定不等于已推送。
5. **事后验证。** 保存 91/91、师生 NAV、Chrome、13/13、15/15、5/5、20×10 真实并发和 18:00 原始证据；保留 ACL 失败、修复、只读恢复与实际续跑。体验另有后续 HTTP 201 佐证，不冒充独立验库。 [最终验收](_bmad-output/implementation-artifacts/story-2-1-final-acceptance.md) · [验收索引](_bmad-output/implementation-artifacts/story-2-1-verification-map.md)

## D-043 2026-11-26 负责人批准 Story 2.2 Checkpoint 1

1. **触发。** BMAD 6.12.4 Build Step 2 展示正式 AC-1～AC-8 的实施规格和隔离验收设计。 [检查点](_bmad-output/implementation-artifacts/story-2-2-checkpoint-1.md)
2. **AI 建议。** 直接复用 2.1 的设备锁、单一判定时刻、失效／历史与异常协议，固定目标日期候选，将进行中、历史与未占用分开。仅补本入口交错，不重复不受影响的 NFR-001 标准组。
3. **人类决定。** 负责人在本会话回复「批准并继续」。以正式 AC、D-024、只用隔离测试库及不提前开始后续 Story 为约束。没有代填成员意见或实验数据。
4. **结果。** 规格从 draft 经 ready-for-dev 进入 in-progress，Sprint 同步本 Story。实现范围只含日期占用、需求内按需失效及对应取证，不改 Sprint 8／5，不碰正式库，不执行 Git 提交或推送。
5. **事后验证。** 见本轮实际静态核对和隔离验证交接。新动态验证在成功回执前不记通过，不进入 review，不标 done。 [实施规格](_bmad-output/implementation-artifacts/spec-2-2-query-equipment-occupancy.md)

   **2026-11-26 事后实证。** 团队在普通 PowerShell 完整应用设备入口补丁并实跑，Build 会话复核原始结果及文件散列。Django 103/103（原 91 同名用例及新增 12，零跳过）、真实隔离探针 21/21、夹具清理和正式八条 AC 通过，2.1 不回归，标准竞争原证据继续复用。依据本轮实际授权推进至 review，待新会话独立评审。未触及正式库、后续 Story、实验 A 或 Git 提交。 [证据与交接](_bmad-output/implementation-artifacts/story-2-2-dev-evidence.md)

## D-044 2026-11-26 负责人处置 Story 2.2 独立评审

1. **触发。** 安装版 BMAD 6.12.4 `bmad-code-review` full Step 4。基线 `930d3cb1c6ce02a934a93295b850c9109165dcf1`，四视角返回，0 Decision、6 Patch、1 Defer、13 Rejected。正式依据为 AC-1～AC-8、FR-004／002／018／015、ADR-002～008、project-context 相关规则、D-043 及原始日志。 [独立评审](_bmad-output/implementation-artifacts/story-2-2-independent-review.md) · [逐条裁决](_bmad-output/implementation-artifacts/story-2-2-review-triage.md)
2. **AI 建议及理由。** 建议选 2，保留六项测试与取证待办，不把覆盖增强当成产品缺陷。当前未发现正式 AC、安全性或数据一致性阻塞。P1 原始绑定在注入前采样，不能声称是实际执行绑定，但实际 SQLSTATE 23514、两次 INSERT 尝试、零 COMMIT 及独立前后快照支持 AC-8 原子回滚。用现有隔离入口运行一次，不先新增整改，不重复跑 NFR-001。
3. **人类决定及依据。** 项目负责人在本会话明确回复「选择2：保留为规格中的待办」，并接受四视角及逐项裁决。在现有证据足以支持正式 AC、安全性和一致性要求的前提下，批准 P1（Medium）及 P2～P6（Low）作为非阻塞改进延期。明确区分 P1 注入前记录与实际执行值，不虚构验证结果。原 D1 延期及 13 条不采纳理由保持。不得改业务代码、访问正式库、提前开发 Story 2.3、标 done 或自动 commit/push。原 8／5、实验 A、三位组员共同操作保持，不代录个人审批。
4. **结果与残余风险。** 六项仍未修复且未勾选，实施规格与 Sprint 按选项 2 同步为 `in-progress`，等待独立运行回执，不表示需先整改。后续节点覆盖故障探针执行绑定、清理成功信号、输入文件集、真实日期表单、混合日期补集、历史与未占用 HTML，以及共享租约。中央延期台账的沙箱写入被拒绝，原台账未改，七条完整待合并文本及普通 PowerShell 安全合并入口已提供。 [Step 4 处置](_bmad-output/implementation-artifacts/story-2-2-review-disposition.md) · [逐项理由、风险与节点](_bmad-output/implementation-artifacts/story-2-2-d044-deferred-pending.md)
5. **事后验证。** 已独立核对开发归档 103/103（零跳过）、21/21 探针、11 个退出 0 阶段、文件散列及夹具清理，不计作新独立运行。现有 `review-story-2-2-isolated.ps1` 可直接用于普通 PowerShell 的一次隔离独立复验，仅 `127.0.0.1:5433/test_lab_booking`，见新目录及 `STORY22_INDEPENDENT_REVIEW_RUN_OK` 才记录新结果。NFR-001 的 D-040 历史标准组 20×10 继续复用，不再次等整点。正式 Chrome 和运行还需另行计划，不把本次处置当成最终验收或部署。

   **2026-11-26 D-044 事后验证。** 负责人报告团队在普通 PowerShell 真实执行一次隔离独立入口。实际批次为 `story-2-2-run-20261126-232700-557-c6cf7cc2`，评审会话复读并重算原始 103/103、零跳过、21/21 探针、11 个阶段退出 0、79/79 输入、三份等值数据库基线与夹具清理。AC-1～AC-8 通过，未发现新增阻塞。仍将 P1 的注入前值和实际执行绑定区分，不取消 D-044 延期或改写原裁决。规格与 Sprint 回 `in-review`／`review` 待正式运行，没有标 done。不重跑 NFR-001 或等待整点。仅提供正式运行命令未执行，先只读核对 D-042 权限，复用现有迁移及权限，不迁移或 GRANT。未提前开发 2.3，未提交或推送。 [逐 AC 复验](_bmad-output/implementation-artifacts/story-2-2-independent-recheck.md) · [正式运行命令](_bmad-output/implementation-artifacts/story-2-2-runtime-handoff.md)

## D-045 2026-11-27 负责人最终验收 Story 2.2

1. **触发。** 负责人报告实际体验正常，补充首次登录 POST 302、身份页 200、重复登录 POST CSRF 403 后恢复以及 D-044 台账合并已执行。 [体验记录](_bmad-output/implementation-artifacts/story-2-2-runtime-experience.md)
2. **AI 核验。** 正式前后只读回执均为 0，业务摘要、既有两项迁移和 D-042 权限无漂移。逐项比对 D-044 七项，单次追加且历史原文不变。未留存的角色、日期、查询状态和恢复步骤不推断，正式体验不代替独立隔离验证。
3. **人类决定。** 负责人批准在正式 AC 和证据条件均满足后直接最终验收、按指定消息提交并推送。保持原 Sprint 8／5、实验 A、三人共同操作审阅及 D-044 原处置，不代填个人决定。
4. **结果。** Story 2.2 与实施规格为 `done`，Epic 2 仍 `in-progress`，Story 2.3 等未开始项仍 `backlog`。本轮不改业务、不执行正式库操作。Git 结果按实际退出码和 SHA 另行报告。
5. **事后验证。** 开发和独立批次各保留 103/103 Django、21/21 真实探针和各 11 阶段退出 0，复用历史 NFR-001 20×10。不重跑，不将原 403 写成未发生或虚构恢复动作。 [最终验收](_bmad-output/implementation-artifacts/story-2-2-final-acceptance.md)


## D-046 2026-11-27 Checkpoint 1 批准 Story 2.3 实施

1. **触发**。BMAD 6.12.4 Build Step 2 提出 Story 2.3 的正式八条 AC、实施规格和隔离验收设计。团队先明确允许在不接触历史日志和锁的前提下基于当前 main 进入 Step 2。 [Checkpoint 1](_bmad-output/implementation-artifacts/story-2-3-checkpoint-1.md)
2. **AI 建议**。仅变更本人查询、导航和最小历史原因投影，复用已批准的设备锁、固定候选、锁后取时与事务机制。隔离自测可先做，正式库所需四列 SELECT 留待只读核对及另行批准。
3. **人类决定**。用户在本会话明确回复「批准并继续」。这是规格与开发批准，不是正式授权、测试通过或最终验收。三人共同操作及审阅安排、Sprint 8／5 和实验 A 不变，本条不代签成员意见。
4. **结果**。规格由 draft 经 ready-for-dev 转到 in-progress，Sprint 仅同步 2.3。保留旧结果地址和 201 路径，补本人列表／详情、授权原因和隔离验证入口。不改正式库、历史日志或锁。不 commit 或 push。 [实施规格](_bmad-output/implementation-artifacts/spec-2-3-query-own-reservations.md)
5. **事后验证**。已静态核对本轮差异及验证入口。沙箱原 Python 退出 103，未取得真实自测回执，保留 in-progress。待普通 PowerShell 核验 103 项原回归、10 项新增测试及 15 个独立探针，再据实推进 review。 [验证交接](_bmad-output/implementation-artifacts/story-2-3-verification-handoff.md)

   **2026-11-27 事后实证。** 用户报告已在普通 Windows PowerShell 执行 `verify-story-2-3.ps1`。本会话读取并复算批次 `story-2-3-run-20261127-111101-492-41d9eb74`，113/113 Django（原 103 项全部同名、零跳过）、15/15 隔离探针、10 阶段退出 0、83 个输入一致、三份可比基线与夹具清理通过。八条 AC 实证后，按本次明确授权推进至 review 并准备新会话独立评审。沿用经独立验证的 NFR-001 标准组，不重跑；未操作正式库、未授权、未标 done、未 commit/push。 [开发证据](_bmad-output/implementation-artifacts/story-2-3-dev-evidence.md) · [原始回执](_bmad-output/implementation-artifacts/story-2-3-run-20261127-111101-492-41d9eb74/README.md)

## D-047 2026-11-27 负责人处置 Story 2.3 独立评审

1. **触发。** 安装版 BMAD 6.12.4 `bmad-code-review` full Step 4。基线 `c4912cb911ffeccbd4a8cfefa0b7eaaf26dab64d`，四视角实际返回 23 条原始发现，逐项裁决并归并为 0 Decision、8 Patch、2 Defer、9 Rejected。 [四视角独立评审](_bmad-output/implementation-artifacts/story-2-3-independent-review.md)
2. **AI 建议与依据。** 建议选择 2 保留非阻塞行动项，用现有独立入口跑一次，不为旧 I7 硬编码或缺少迟发原因 SELECT 注入多开整改轮次。FR-002/009/015/018、ADR-002～008、PC 和正式 AC-1～8 的当前代码及原始回执支持隔离复验。现行已证权限仅 SELECT(id)，正式发布需要独立的 W1 门槛。
3. **人类决定及理由。** 项目负责人在本轮明确「选择2：保留为行动项」，接受四视角和逐项裁决，批准 P01～P08 在不影响正式 AC、安全性和数据一致性的前提下合理延期，并保留编号、理由、风险及处理节点。保留 W1/W2 和九项驳回依据，W1 仍是 High 正式发布门槛而非可豁免延期。负责人仅承诺独立复验通过后再批准必要的四列最小 SELECT，本条不是授权。旧 I7 和迟发原因 SELECT 证据限制按实保留，在后续相关验证前处理。Sprint 8／5 和实验 A 不变，团队三位成员共同操作和审阅，不代录个人表决。
4. **结果。** 0 项修复、8 项行动项在规格中未勾选。规格从 `in-review`、Sprint 从 `review` 同步回 `in-progress`，待一次独立隔离复验，不要求先补丁。2.5 保持 `backlog`。中央延期台账写入预检被拒，待合并版保留八项行动、W2 及单列 W1，不将副本实测当作中央合并。 [人工处置](_bmad-output/implementation-artifacts/story-2-3-review-disposition.md) · [待合并记录](_bmad-output/implementation-artifacts/story-2-3-review-deferred-pending.md)
5. **事后验证。** 本会话实际核对复验入口散列未变，语法、开发原始归档 113/113、15/15、10 个退出 0、83 项输入及夹具清理通过离线核验，新增运行前的源码检查通过。这不是新独立实测，正式运行和权限复核也未执行。台账合并脚本在临时副本验证前缀逐字节保留、首次只追加一次、重跑不写、冲突或未知底稿变化不写。D-040 的历史 NFR-001 继续复用，不重复 20×10 或等待整点。后续独立结果以新目录和唯一 `STORY23_INDEPENDENT_REVIEW_RUN_OK` 为准。 [独立复验脚本](_bmad-output/implementation-artifacts/review-story-2-3-isolated.ps1)

   **2026-11-27 事后实证。** 项目负责人报告已在普通 Windows PowerShell 完成一次独立隔离复验及中央台账合并。新批次 `story-2-3-run-20261127-114813-950-de7b7f2c` 原始记录经独立只读核对，113/113 Django（原 103 项同名、零跳过）、15/15 PostgreSQL 探针、10 个退出 0、83 项输入、三份基线及夹具清理一致。正式 AC-1～AC-8 的隔离证据通过，无新增阻塞。中央台账已真实合并，逐字节核对原记录不变、P01～P08/W2 与单列 W1 各一次；未发现独立保存的终端合并 stdout，不补造。按当次条件推进规格/Sprint 到 `in-review`/`review` 待正式运行，保留 D-047 处置、Story 2.5 backlog、Sprint 8／5 和实验 A。W1 仍未关闭，只准备最小四列授权及真实 Chrome 方案，未访问正式库或执行 GRANT，没有启动正式服务、追加测试、标 done、commit 或 push。沿用已核验 D-040 历史 NFR-001；不将独立核对写为 AI 再跑。 [原始证据与逐 AC](_bmad-output/implementation-artifacts/story-2-3-independent-recheck.md) · [正式运行交接](_bmad-output/implementation-artifacts/story-2-3-formal-runtime-handoff.md)

   **2026-11-27 正式窗口批准，尚未实跑。** 负责人接受 Story 2.3 独立复验结论，保留 D-047 原非阻塞待办及延期；批准仅在 `127.0.0.1:5433/lab_booking` 确认无权限漂移后条件性补历史表四列 SELECT，并做 8003 三角色预约业务只读 Chrome 烟测。未批准新演示预约或 FR-018 业务写入。沙箱凭据访问拒绝，原 .venv 探针退出 103，仅完成只读本机状态及执行工具静态复核，未连正式库、未授权、未启动服务，W1 未关闭。中央台账及 `review` 不变。 [普通 PowerShell 执行单](_bmad-output/implementation-artifacts/story-2-3-formal-execution.md)

   **2026-11-27 正式授权异常与恢复。** 负责人在普通 PowerShell 的批次 `story-2-3-formal-20261127-120858-648-0dcaa5b4` 已实际提交四列 GRANT，退出 0。实际授权前后矩阵只增加批准四列，无转授或额外权限。后置 catalog 退出 1 并误报「Migration records changed」；原迁移、对象和所有者值未变，实时 tuple 与 JSON list 的比较触发误报。仅修复只读工具的表示归一，真实差异仍被拒，已用原回执离线验证并归档 17 份原始文件。不重复授权。沙箱只读 Recover 未能加载脚本，待普通 PowerShell 补齐读回及 Chrome 现场证据，保留 review，未关闭 W1 或标 done。 [故障取证与恢复](_bmad-output/implementation-artifacts/story-2-3-formal-recovery.md)

   **2026-11-27 正式 Serve 工具续跑。** 原正式批次两次实际 Recover 均证明四列权限精确。首次 Serve 的候选检查因所填学生账号未满足存在、启用及角色条件退出 1，留 stdout/stderr 而无前置快照；随后同目录重试触发防覆盖。只改正式验证入口，独立分配 smoke／Chrome／Finish 证据目录，以散列绑定有效 ACL 和同一前置快照，以尝试标识绑定 8003 PID。离线模拟验证通过，32 份原始回执归档。未再连接正式库、授权或启动真实应用／Chrome；待普通 PowerShell 实跑，Story 保持 review，不动中央延期台账。 [Serve 恢复交接](_bmad-output/implementation-artifacts/story-2-3-serve-recovery.md)

   **2026-11-27 正式样本就绪受阻。** 新 smoke 实际通过三类预置账号及精确 ACL 核对，随后 `sample-before-catalog` 退出 1。原记录的安全窗口为 20 分钟，学生 #1 已结束仍待审核，访问列表将触发 FR-018；教师无既有详情。本轮未启动 8003，只修正式核验工具，复用受保护预置清单、把只读 Inspect 与 Serve 分开，并保留所有写入防线。用原样本离线比对并归档 12 份原始回执；无新正式浏览器结果，不重跑授权或测试，保持 review。 [正式样本阻塞与执行命令](_bmad-output/implementation-artifacts/story-2-3-formal-sample-hold.md)

   **2026-11-27 负责人批准有限正式业务变化。** 接受只读前置结论，批准学生 #1 仅从本人列表进行一次正常失效、系统历史及重复读取核对；批准教师由已验收 2.1 正常入口最多提交一条合法无冲突演示预约，已有合格记录时复用。任何其他正式业务变化、迁移和授权未获准。本轮记录范围，调整专用验证工具，使用数据库只读前后逐行比对及 8003 本次进程的写入门禁。离线验证通过，本轮尚无正式运行回执，保持 `review`。 [有限写入执行单](_bmad-output/implementation-artifacts/story-2-3-authorized-demo.md)

## D-048 2026-11-27 负责人最终验收 Story 2.3

1. **触发。** BMAD 6.12.4 对 Story 2.3 的四视角独立评审、正式运行及只读恢复已留存。最终 Finish 五项机器断言通过，但正式教师库没有可复用本人预约。 [独立复验](_bmad-output/implementation-artifacts/story-2-3-independent-recheck.md) · [原始证据索引](_bmad-output/implementation-artifacts/story-2-3-formal-runtime-evidence/README.md)
2. **AI 建议。** 分开功能 AC 和正式 Chrome 覆盖。FR-002／009／015／018、ADR-002～008 和 AC-1～8 可由现有独立实测及正式权限、失效、角色对照证据支持。保留教师本人详情缺口，不再以写正式数据补证，不用隔离证据冒充现场。
3. **人类判断及依据。** 负责人明确批准最终验收。依据为独立 113/113 Django、15/15 PostgreSQL 探针、四视角评审及八条 AC、五项 Finish 断言、正式四列精确 SELECT 和学生按需失效及幂等原证。负责人实际确认教师异主及不存在详情均为 404，管理员身份页无「我的预约」且直访列表 403。明确接受教师本人详情未在正式 Chrome 执行，由独立隔离实测支持该功能。不代签三位成员、不推断其他体验。
4. **结果。** 按 Step 5 关闭 W1，将实施规格与 Sprint Story 2.3 更新为 `done`。Epic 2 保持 `in-progress`，Story 2.5 `backlog`。保留 P01～P08、W2、原九项驳回、Sprint 8／5 和实验 A。负责人授权以指定消息提交和推送，不改业务源码。 [最终验收](_bmad-output/implementation-artifacts/story-2-3-final-acceptance.md) · [中央延期台账](_bmad-output/implementation-artifacts/deferred-work.md)
5. **后验依据。** 16 条补证请求与 Django 日志一致，两个 404 响应体同散列，正式前后业务行散列相等，学生 #1 仅有原系统历史，独立运行角色前后都只有原 `id` 及获批四列 SELECT，无表级 SELECT 或转授。早先 Finish 失败、教师 POST 403 和恢复如实归档，均不重放。不把本次核对记为新测试，不宣称正式教师本人详情或 201 通过。 [机器回执](_bmad-output/implementation-artifacts/story-2-3-formal-runtime-evidence/teacher-readonly/post-8a49872cb2be/result.json)

## D-049 2026-11-27 Checkpoint 1 批准 Story 2.5 实施

1. **触发。** BMAD 6.12.4 Build Step 2 的单 Story 实施规格及 AC-1～8 验收设计已提交人工确认。 [Checkpoint 1](_bmad-output/implementation-artifacts/story-2-5-checkpoint-1.md)
2. **AI 建议。** 仅开发管理员详情／历史、全量及筛选，复用先授权、固定候选、设备升序锁、锁后复核及 FR-018 原子提交。在正式库按缺口另批历史五列 SELECT，不扩大服务角色。
3. **人工决定及边界。** 用户在本会话明确回复「批准并继续」，适用已确认的正式 AC 和本次规格。未批准正式授权或发布，本条不代签其他成员，不作最终验收。Sprint 8／5 和实验 A 不变。
4. **结果。** 实施规格经 ready-for-dev 进入 in-progress，仅同步 Sprint 2.5，代码与隔离验证入口已准备，其中设备原谓词共享策略因沙箱拒写交付单文件增量补丁。 [规格](_bmad-output/implementation-artifacts/spec-2-5-admin-reservation-query.md)
5. **后验依据。** 补丁静态应用检查、脚本语法及测试清单核对已完成。原 Python 在沙箱不可启动，实际预检未通过，没有运行 Django／PostgreSQL 验证。待团队在普通 PowerShell 一次实跑，再依据原始结果决定是否进入 review。 [验证交接](_bmad-output/implementation-artifacts/story-2-5-verification-handoff.md)

   **2026-11-27 Story 2.5 真实回归首批。** 团队在普通 PowerShell 应用了共享权限补丁并运行隔离回归。125 项中 124 项通过（12 项 2.5、40 项设备用例全过），Story 2.3 本人导航断言把管理路由公共前缀误认作本人链接，回归真实退出 1，未启动探针。按用户本次要求修正精确链接与双角色对照，保留同名用例和实际失败日志；业务及权限代码不再变更。整改复验仍待普通 PowerShell 实跑，状态保持 in-progress。 [故障证据及命令](_bmad-output/implementation-artifacts/story-2-5-regression-remediation.md)

   **2026-11-27 Story 2.5 整改复测通过。** 团队报告已在普通 PowerShell 执行整改版。只读核对实际原始结果为 5/5 针对性、125/125 Django、17/17 PostgreSQL 探针、12 个阶段退出 0、87 项输入、四份隔离基线及清理一致。首批单项失败原证保留，原权限验证未放宽。按本次用户有条件授权，规格与 Sprint 仅推进 2.5 至评审，下一会话独立 Code Review。本轮不代填最终验收或正式运行，不改原 8／5 与实验 A。 [开发证据](_bmad-output/implementation-artifacts/story-2-5-dev-evidence.md) · [评审交接](_bmad-output/implementation-artifacts/story-2-5-code-review-handoff.md)

## D-050 2026-11-27 负责人批准 Story 2.5 独立评审处置

1. **触发。** BMAD 6.12.4 full 独立 Code Review 完成四视角及 23 条逐项裁决，实施规格列出 13 个 Patch 候选、5 个 Defer 和 3 条驳回，另有 W01 正式发布门槛。 [评审](_bmad-output/implementation-artifacts/story-2-5-independent-review.md) · [裁决](_bmad-output/implementation-artifacts/story-2-5-review-triage.md)
2. **AI 建议。** 选 2 保留行动项。只修 M01：管理员详情遇无效设备参数仍可进入 FR-018 失效事务，违反 AC-8 无效输入无业务变化。其他 Patch 是非阻塞的可读性、集成或取证事项。W01 与代码整改分开，必须在独立复验后按 AC-6 实际 ACL 缺量最小处理。
3. **人类判断及依据。** 负责人在本会话明确回复「选择2：保留为行动项。」批准 M01 交回原 Build，P01～P12 以不影响正式 AC、安全性、数据一致性为条件延期，保留五项 Defer 和三项驳回原裁决。W01 为 High 正式发布门槛，不批准延期；仅在整改后的独立复验通过后另行批准实际缺少的五列 SELECT。保留原 Sprint 8／5、实验 A 及已独立核验的 NFR-001 标准组，三人共同操作、共同审阅，不代签其他成员。本轮不改业务代码、不访问正式库、不开迁移或授权窗口、不标 done、不自动提交推送。
4. **结果。** 实施规格和看板仅将 Story 2.5 退回 in-progress；0 修复，M01 仍开放，原 5 项与批准 12 项延期进入中央台账，三条驳回不变。W01 不纳入延期。 [人工处置](_bmad-output/implementation-artifacts/story-2-5-review-disposition.md) · [整改交接](_bmad-output/implementation-artifacts/story-2-5-remediation-handoff.md) · [中央台账](_bmad-output/implementation-artifacts/deferred-work.md)
5. **后验依据。** 台账回执验证原字节前缀、17 个唯一条目和幂等读回，前后散列已归档。原 5/5 专项、125/125 Django、17/17 PostgreSQL 探针及首次 124/125 导航失败、整改仍为开发执行证据，评审曾离线复算，不代替整改后的独立运行。新回执待 M01 完成后取得，当前未执行。 [合并回执](_bmad-output/implementation-artifacts/story-2-5-review-support/deferred-merge-receipt.txt) · [开发证据](_bmad-output/implementation-artifacts/story-2-5-dev-evidence.md) · [首次失败与整改](_bmad-output/implementation-artifacts/story-2-5-regression-remediation.md)

   **2026-11-27 Story 2.5 M01 真实开发专项通过。** 团队已在普通 PowerShell 执行，原证为 3/3 Django、1/1 真实 HTTP/PostgreSQL、10 阶段零退出、87 项散列与三份隔离基线及夹具清理一致。实际五个 400 无业务读取、锁、取时或写入，同一预约随后合法查询只写一条系统历史，重复不写。依本次有条件授权，规格／Sprint 仅推进 2.5 回评审，就 M01 交回原 Code Review 会话。其余裁决、W01、Sprint 8／5 及实验 A 不变，不计作独立复验或正式验收。 [M01 开发原证](_bmad-output/implementation-artifacts/story-2-5-m01-dev-evidence.md)

## D-051 2026-11-27 负责人关闭 Story 2.5 M01 并有条件批准 W01

1. **触发。** BMAD 6.12.4 原独立复验保留 5/5 专项、125/125 Django、17/17 PostgreSQL 探针及 M01 的真实可复算原证。团队普通 PowerShell 的正式只读预检显示历史五列全缺、已有安全样本。 [独立复验](_bmad-output/implementation-artifacts/story-2-5-m01-independent-run-result.md)
2. **AI 建议。** 分开关闭 AC-8 的代码问题和 W01 正式权限门槛。只以刷新后实际差集授权，查看现有预约且阻断业务写。缺少现场状态时沿用独立隔离原证，不为取证新增数据。
3. **负责人决定。** 本会话接受独立复验并正式批准关闭 M01。有条件批准仅为 lab_booking_app 增加 public.audit_operationhistory 实缺的 actor_id、before_status、after_status、decision_at、recorded_at 列 SELECT 及安全正式运行。不批准其他授权、迁移或业务变化。不代签成员个人意见。
4. **结果。** 规格勾选 M01。W01 有条件批准但不关闭，规格／Sprint 仍为 in-review／review。准备一次自动化权限与浏览器取证入口，只使用现有预置账户及预约。 [执行单](_bmad-output/implementation-artifacts/story-2-5-w01-authorized-run.md)
5. **后验依据。** 已复算 21:19 原只读 ACL、样本、来源散列及退出 0；原独立批的外层控制台标记与进程退出未单独留档，不补造、不重跑。沙箱受保护 passfile 拒绝访问，未执行正式权限和浏览器步骤，不声称正式通过。不改业务源码、Sprint 8／5 或实验 A，不标 done、不提交或推送。

## D-052 2026-11-27 负责人最终验收 Story 2.5

1. **触发。** 负责人报告执行 W01 正式恢复，要求核对实际回执、标记、权限、四角色 Chrome、后置快照及 AC-1～AC-8。
2. **AI 建议。** 按正式回执关闭发布门槛，保留早期失败、实际一次授权、工具专项、隔离与正式证据边界；准备 Sprint 1 整体验收和回顾，不提前填写团队意见。
3. **人工决定。** 负责人在本会话明确以证据完整及各项实测通过为条件批准 Story 2.5 最终验收，并授权提交和推送；条件由本次原始回执核对满足。未代表其他组员、未另作 Sprint 整体验收或实际回顾决定。
4. **结果。** 按 BMAD 6.12.4 收尾关闭 W01；M01 保持关闭；Story 2.5 规格／看板为 `done`。原 17 个非阻塞延期事项、Sprint 8／5、实验 A 及 Sprint 2 待办保持原状。 [最终验收](_bmad-output/implementation-artifacts/story-2-5-final-acceptance.md)
5. **后验依据。** 22:31 五列精确授权一次提交，22:40 恢复批读回跳过授权。正式 37 条 Chrome／服务端文档匹配，四组业务摘要和 ACL 不变，17 个阶段退出 0，末行 `complete exit=0`，唯一 `STORY25_W01_FORMAL_OK`。外层控制台退出码没有单独入档，不补造。 [正式回执](_bmad-output/implementation-artifacts/story-2-5-w01-final-evidence/verified-receipt.json) · [Sprint 1 汇总](_bmad-output/implementation-artifacts/sprint-1-acceptance-and-retro-prep-2026-11-27.md)

## D-053 2026-11-27 负责人确认 Sprint 1 逐项验收并要求准备 Sprint 2

1. **触发。** Sprint 1 最后一条 2.5 已受 D-052 验收，用户要求汇总八条正式 AC、NFR 实证、开放事项和回顾，准备原定 Sprint 2。
2. **AI 建议。** 以验收及原始证据结清已交付范围，按实记延迟一天。复用成熟预检、隔离实测、独立读回、定向恢复和自动归档。实验 A 用同一可审定基线并只在确认后冻结。
3. **负责人实际确认。** “作为项目负责人，我确认Sprint 1原定八条Story均已完成逐项验收。” 指定保留 8／5、五条顺序，实验前冻结，不提前开发 2.4，并授权本轮提交和推送。没有代为确认另外两名成员意见、实验正式分组或实际启动日。
4. **结果。** Sprint 1 已交付范围证据验收通过，归档回顾与下一 Sprint 准备。86/86 仅适用当前入口，NFR-001 沿用逐轮原证。延期不批量关闭，第二台 Windows 待复现。Sprint 2 五条 backlog，实际启动未登记，实验 A 未执行和未填数值。 [验收](_bmad-output/implementation-artifacts/sprint-1-final-acceptance-2026-11-27.md) · [回顾](retrospective.md) · [预登记和一次确认](_bmad-output/planning-artifacts/sprint-2-startup-and-experiment-a.md)
5. **后验依据。** 原 JSONL 复算 10 个 201、190 个 409、每轮有效待审恰一；八条状态和 81 个实验候选源文件由原提交核对，不运行新业务测试、不重授。实际团队决定、第二台复现和实验证据随真实事件追加。
