# Story 2.2 开发验证与独立评审交接

**2026-11-26（北京时间）｜通过开发自测，进入 review。** 团队在普通 PowerShell 应用设备详情补丁并实际运行。当前 Build 会话只读核验原始证据，不冒称由会话亲自运行、独立代码评审通过或人工最终验收。正式 Story 2.2 AC-1～AC-8、需求与 Sprint 范围未改。 [正式 AC](../planning-artifacts/epics.md#story-22-查询具体设备在指定日期的占用时段) · [实施规格](spec-2-2-query-equipment-occupancy.md) · [Sprint 状态](sprint-status.yaml) · [D-043](../../decision-log.md#d-043-2026-11-26-负责人批准-story-22-checkpoint-1)

## 补丁与实际运行

- 基线 `930d3cb1c6ce02a934a93295b850c9109165dcf1`。设备视图和模板差异各为补丁预期的 1、5 行新增，`git apply --reverse --check` 退出 0，只检查，不反向应用、不重放。详情表单以实际设备主键反向生成查询地址，保留申请、编辑和返回目录导航。
- 真实批次 `story-2-2-run-20261126-224427-552-98c04aee`，22:44:27～22:45:34。11 个阶段均为 `exit=0`，无 `failure.txt`；独立探针原始 stdout 恰有 `STORY22_PROBE_OK cases=21`，stderr 为空。原 .venv Python 3.13.17、Django 5.2.19，真实数据库身份为 `127.0.0.1:5433/test_lab_booking`、`lab_booking_test`、PostgreSQL 17.12、Read Committed；角色没有超额属性及正式库 CONNECT。未接触业务库。 [阶段退出码](story-2-2-run-20261126-224427-552-98c04aee/stages.txt) · [环境预检](story-2-2-run-20261126-224427-552-98c04aee/preflight.txt) · [探针标准输出](story-2-2-run-20261126-224427-552-98c04aee/independent.stdout.txt)
- Django 103 项发现／执行／通过一致，零跳过，耗时 21.853 秒。逐名比对 D-040 归档，旧 91 项集合完全一致，新增 12 项全部实际执行。Django system check 无问题，迁移漂移检查为 `No changes detected`。 [Django 标准输出](story-2-2-run-20261126-224427-552-98c04aee/regression.stdout.txt) · [逐测试结果](story-2-2-run-20261126-224427-552-98c04aee/regression.stderr.txt) · [计数](story-2-2-run-20261126-224427-552-98c04aee/regression-counts.txt)
- 真实 HTTP／PostgreSQL 探针为 21 个唯一场景，另有开头环境和末尾清理记录。三份隔离数据库基线字节一致，SHA-256 `5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272`。独立探针清理前后 schema 与原始数据指纹一致，12 张表、19 条迁移不变。账号、会话、设备、预约、历史五表均回到 0，未把序列消耗等同于夹具残留。 [全量 JSONL](story-2-2-run-20261126-224427-552-98c04aee/independent.jsonl) · [初始基线](story-2-2-run-20261126-224427-552-98c04aee/baseline-before.json) · [回归后基线](story-2-2-run-20261126-224427-552-98c04aee/baseline-after-regression.json) · [探针后基线](story-2-2-run-20261126-224427-552-98c04aee/baseline-after-independent.json)
- 核验时逐项复算 79 份输入文件，均匹配前后清单。清单字节一致，SHA-256 `14DA756307D52A468C90105406BABB9603B70D119A5AAAA5A499EFD149DA6D26`。原始 JSONL SHA-256 `3DEB399ED4B3F49E6E82E1416F86817BFC0256D0A0B3ABFB8AB48D0205C0A9C8`。核验完成后仅更新管理文档与状态，不改本批受测源码或测试，不覆盖原清单。 [输入前清单](story-2-2-run-20261126-224427-552-98c04aee/before.sha256) · [输入后清单](story-2-2-run-20261126-224427-552-98c04aee/after.sha256)

## 正式 AC 与测试证据

| 正式 AC | 本批核验结论与定位 |
| --- | --- |
| AC-1 日期与占用 | **通过。** `test_ac1_*` 以独立夹具验证北京时间半开日边界、设备隔离、不同状态和未占用补集。可控时刻 10:30 保留 10:00～11:00 已批准为进行中；11:00 恰到结束及之后只作历史，记录不变、无历史增量。另在 `test_ac2_*` 用同区间待审、10:30 刷新后查库验证失效。 |
| AC-2 先失效后出结果 | **通过。** `test_ac2_*` 覆盖恰到开始、已结束、重复查询不追加、设备／日期外不变；真实 `frozen-due` 及两种查询／提交顺序独立读回过期待审、释放占用和系统历史，已批准对照不变。 |
| AC-3 固定候选、锁与唯一时刻 | **通过。** `test_ac3_*` 与 JSONL 证明顺序为设备／日期候选 → 单目标设备 FOR UPDATE → 账号复核 → 独立设备与固定 ID 重读 → 一次数据库时钟 → 固定 ID 的 FR-018 判断及写入。真实 `no-pending`／`empty` 在另一个连接持设备锁时不额外加锁，另设备预约仍可 201。 |
| AC-4 并发新增只在下次见 | **通过。** `frozen-legal` 的首次查询实际被合法提交 PID 3176 阻塞，锁后绑定仍仅有原 ID 306；新增 307 首次不显示、下一次纳入。 `frozen-due` 旁路夹具 309 首次仍待审，第二次才失效；旧 308 的系统历史未重复。 `test_ac4_*` 另有确定性覆盖。 |
| AC-5 权限和投影 | **通过。** `role-student/teacher/admin` 三组独立合法对照。真实详情 HTTP 200 的日期控件和 action 与真实查询路径一致，调用均 200，主体绑定且不同于申请人，不泄露身份、预约详情链接或处理原因。匿名／停用会话 302，等锁撤权 403，三项都没有取时、失效、历史或受限正文，前后业务数据相同。项目级 NFR-002 仍不作完结声明。 |
| AC-6 空结果与无效输入 | **通过。** 空日、收尾后空日 200；缺日期、无效格式／日历日期 400；不存在设备 404；拒绝路径无预约扫描、写锁或 DML。见 `test_ac6_*`、`empty`、`invalid-date`、`missing-equipment`、`real-start-boundary`。 |
| AC-7 三层语义与实时重检 | **通过。** `test_ac7_*` 逐个验证设备可用／维修／停用与过去日期、不承诺可预约；真实 `stale-result-conflict` 先查空 200，再由教师 201 获得占用，随后学生重叠提交 409，只留下胜者有效记录。 |
| AC-8 原子与异常 | **通过。** `history-second` 实际第二条历史插入触发 PostgreSQL 23514，未 COMMIT，前后均无变更；`commit-rejected` 实际 COMMIT 被 23505 拒绝，同样整体回滚。提前断开连接和真实提交后模拟丢确认均返回 503「待核查」，不保证已提交或回滚、不渲染正常占用、不重试。独立观察前者未持久化，后者两条状态与两条历史同时持久化。见 `test_ac8_*` 和四项 JSONL 原文。 |

T-01 的 `submit-first`／`query-first` 由真实 `pg_blocking_pids` 证明同设备串行，前者提交、后者查询各自先收尾时均只有先行者写历史。T-02 精确 10:00/10:30/11:00 使用测试专用时钟；真实等锁跨开始的 UTC 时刻依次是 `14:45:09.989114 < 14:45:15.924528 <= 14:45:15.949235`；另一场景 `14:45:16.861910` 判定早于开始 `14:45:22.682868`，放行 COMMIT 时已跨开始 `14:45:22.692784`，本次仍按唯一早期判定不写，下一次才失效。T-03 按三项未授权与三项合法对照分开，不将无效输入误计为权限拒绝。详情入口证据是实际样式未改的服务端页面、表单 action 和同路径请求，不声称另做了新的独立浏览器点击测试。 [逐项 Django 原始结果](story-2-2-run-20261126-224427-552-98c04aee/regression.stderr.txt) · [逐请求原始 JSONL](story-2-2-run-20261126-224427-552-98c04aee/independent.jsonl)

## 不回归、历史排除与评审范围

- 源码对比基线确认 2.1 相关 12 个函数（提交、本人结果、权限、窗口、时钟、失效与事务辅助）的 AST 完全一致。设备锁、历史模型与写入、显式隔离级别、数据库守卫及 2.1 原测试与原独立探针文件无差异。B1/B2、原提交及本人结果测试随老 91 项实际通过。本批双向交错与旧占用冲突为新增证据。
- D-040 已独立核验的 NFR-001 原档 SHA-256 `3364EDF809D5F11C2E865C6608636C6A80FA16736D16C74CA4E1C759D9A7AEC1` 复算一致。按原始记录复算 10 轮共 200 个响应，每轮 20 个不同 PostgreSQL 后端且有实际重叠，1 个 201、19 个 409、1 条持久有效待审。原有标准组与本批交错分列，未重跑、不计作本轮结果。 [D-040 独立核验](story-2-1-targeted-independent-recheck/d040-independent-final-review.md) · [NFR-001 原始日志](story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15/nfr001-standard.jsonl)
- 四个历史文件的 SHA-256 与 Checkpoint 1／实施前相同。Story 1.4 旧 stderr 为 `CE07BF985B1264FE225F0B6AC552CAA4404DACA8BD3388747F39F9FD3B56EE55`，Story 2.1 旧 stderr 为 `6819D65A1107661571978FA253D2318EFDD2AEE8FBBF39E196A26F5BF0058755`，两个原锁均为 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`。不纳入 Story 2.2 评审变更范围和未来暂存清单，不删除或覆盖。未暂存或提交。
- **新会话入口。** 以安装版 BMAD 6.12.4 `bmad-code-review`（CR，full）打开本 Story 实施规格并提供本证据文件。差异从上述基线取已修改的 `reservations/{forms,services,urls,views}.py`、`equipment/views.py`、`equipment/templates/equipment/detail.html`；补纳未跟踪的占用模板、`reservations/test_occupancy.py`、`reservations/management/commands/verify_equipment_occupancy.py`、`verify-story-2-2.ps1` 和 2.2 管理文档。补丁作为应用证据，不重复计算两处源码。新运行目录供按需核验，不作为产品源代码差异。重点独立复核固定 ID 的 SQL 和权限、历史分类、GET 的受限写入、已确认失败与提交未知、取证边界。不要将历史缓存、旧日志或旧锁混入 diff。
- 课程按第 25 页 Story 字段与可测标准、第 26 页 FR-004/002/018/015 → ADR-002～008／PC → 正式 AC → 原始证据链、第 27/33 页真实状态及产物、第 34 页不纳入实验 A、第 36 页 D-043 真实人工决定与事后验证处理。依据仓库课程基线及已有团队记录，不宣称直接逐页核验 PPT 原件。三人共同操作及审阅，Sprint 8／5 不变。未改后续 Story、未迁移、未授权、未操作正式库、未标 done、未 commit/push。 [课程基线](../../docs/course-requirements.md) · [原 Sprint 计划](../planning-artifacts/sprint-plan.md)
