# Story 2.2 · 独立复验收尾

**结论。** Story 2.2 在隔离环境的独立复验通过，正式 AC-1～AC-8 无新增阻塞。依据四视角裁决及负责人 D-044 处置，P1～P6 保持开放延期，D1 和 13 项不采纳原裁决不变。规格已回 `in-review`、Sprint 已回 `review`，未标记 `done`。正式系统烟测仍待执行，不等同最终验收或发布。 [D-044 处置](story-2-2-review-disposition.md) · [四视角裁决](story-2-2-review-triage.md) · [正式验证命令](story-2-2-runtime-handoff.md)

## 证据来源、范围与完整性

- **团队实际执行。** 项目负责人在本会话报告已在普通 PowerShell 执行 `review-story-2-2-isolated.ps1`。本次实际目录为 `story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2`，北京时间 2026-11-26 23:27:00.823～23:28:13.603。独立评审会话只读审计这个新目录，不启动新的 Python、Django、Chrome 或数据库操作。不将 22:44 开发自测冒充独立批次。
- **原始结果。** 原 Python 3.13.17、Django 5.2.19、PostgreSQL 17.12、Read Committed，唯一目标 `lab_booking_test@127.0.0.1:5433/test_lab_booking`。原始 Django 日志列出 103 个唯一同名用例（旧 91＋新增 12），103/103、零跳过、24.359 秒，唯一 `OK`。系统检查无问题，迁移漂移检查无变化。新探针有 21 个唯一实际案例，加身份／清理共 23 行，唯一 `STORY22_PROBE_OK cases=21`，stderr 为空。11 个原始阶段顺序正确、退出码均为 0，含 `complete exit=0`。独立审计重算为 `STORY22_ARCHIVE_AUDIT_OK`，不代填未归档的外层控制台原行。 [阶段](story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/stages.txt) · [Django 原始日志](story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/regression.stderr.txt) · [探针 JSONL](story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/independent.jsonl)
- **散列与清理。** 运行前后 79 项 SHA-256 清单字节相同，评审落盘前当前 79/79 均匹配。清单 SHA-256 为 `22C7B1C42B26794245AB2C43CCBFE7DB6D5DDFD92BC82B8E175B12244EF3B07A`，探针 JSONL 为 `DF364D912567C2A866A57AFD51ECD7B1D0F3CA42BAD8B09CEFBC777B1EA3D0FA`。三份数据库基线字节均相同，SHA-256 为 `5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272`。12 张表、19 条迁移登记，五张受控业务／认证表均回到 0，JSONL 开场和清理快照的行散列也逐项相同。不把这些摘要当作全库模式或 ACL 指纹。复审只更新管理规格，既有证据清单原样保留。 [输入清单](story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/before.sha256) · [基线](story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/baseline-before.json) · [探针后基线](story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/baseline-after-independent.json)
- **历史复用。** 2.1 的提交、设备锁、时钟、失效和提交异常核心路径无变化。继续引用 D-040 已独立核验的标准 20 请求 × 10 轮、200 个响应，每轮 1 个 201、19 个 409、1 条持久有效待审。没有重新压测或等待整点，不把旧数据计入 2.2 新结果。 [D-040](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

## 正式 AC 逐项确认

| AC | 独立结果与本批可复查证据 |
| --- | --- |
| AC-1 | **通过。** 新 Django AC-1 两项实跑通过。只纳设备及北京时间日期的半开区间。10:30 的 10:00–11:00 已批准仍占用，到 11:00 转为历史展示，不再计有效占用；尚未开始的待审有效，终态不计入。历史和未占用口径不变。 |
| AC-2 | **通过。** Django 覆盖恰到开始、已结束待审、重复查询及范围外不写。真实 `frozen-due`、`submit-first`、`query-first` 证明到期释放、系统历史原子新增且重复不再写。 `real-start-boundary` 的真实 UTC 证据为等锁 15:27:47.962305 < 开始 15:27:53.876394 ≤ 判定 15:27:53.902610。 |
| AC-3 | **通过。** 真实 SQL 先按设备／日期绑定冻结，再锁设备行、复核账号、重读设备与固定 ID、取一次 `clock_timestamp() AS decision_at`。身份与锁返回的单调时点及语句次序一致。空候选和无待审在另一连接 PID 18508 持设备锁时正常返回，不额外取写锁，也不写历史。判定后跨开始才提交仍以原判定处理。 |
| AC-4 | **通过。** `frozen-legal` 真实写方及阻塞 PID 43328，首次重读只绑定 397，次查 397、398。 `frozen-due` 首次只处理 399，400 仍待审且无历史，次查才给 400 写失效历史。提交先与查询先真实阻塞分别为 24688、27280，各自先行者只写一条历史，其他设备合法提交 201。 |
| AC-5 | **通过。** 三角色在设备 608 的详情返回 200，实际表单 action 指向同设备占用路由，后续真实 HTTP 查询均 200，身份不同于夹具申请人且不投影受限信息。匿名／停用会话 302，等锁撤权 403，均无取时、业务 DML 或受限内容。此为服务端及 HTTP 验证，不冒称该新控件已由真实 Chrome 手动提交。 |
| AC-6 | **通过。** 真实空日 200、非法日 400、不存在设备 404，复核无预约扫描、取时或 DML 的拒绝路径；Django 还覆盖缺日期、边界日期和非 GET 限制。 |
| AC-7 | **通过。** AC-7 用例通过可用／维修／停用、空日和过去日期三层语义。 `stale-result-conflict` 为查空 200、另一申请 201、原用户重叠 409，独立观测只持久化胜者。 |
| AC-8 | **通过。** `history-second` 两次写入尝试、真实 23514、零 COMMIT、503、无持久部分写入。 `commit-rejected` 实际 23505、503、前后不变。提交前断连和真实提交成功后模拟丢确认均 503「待核查」且不重试，前者 414／415 未变，后者 416／417 同时失效并各有历史。日志注入前采样值仍非实际执行值，AC-8 依赖真实错误及独立读回。 |

课程第 25／26／27／33／34／36 页依据仓库课程基线核对。可测试验收及 FR→ADR→AC→证据链、真实 Sprint 状态、课程产物、实验 A 方案和 D-044 人工判断保持可追溯。三位组员共同操作，不分派个人任务。D-044 中央台账没有新合并回执，沿用安全交接，不把待合并记成已合并。未访问正式库、未修改业务代码、未启动 Story 2.3、未提交或推送。
