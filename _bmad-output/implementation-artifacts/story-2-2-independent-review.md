# Story 2.2 · BMAD full 独立代码评审

## 结论与范围

本轮未发现违反正式 AC 的阻塞性产品缺陷，无 High。存在一项 Medium 取证准确性问题及若干 Low 回归覆盖或工具问题。开发原批次的结果可核实，但不是本轮新独立运行。本轮新跑 Django 0 项、PostgreSQL 探针 0 项，不能据此最终验收。Story 保持 `review`，规格保持 `in-review`，等待正式处置及一次隔离独立复验。

以上状态是初评检查点。负责人随后选择 2，批准六项待办非阻塞延期，Step 4 同步转入 `in-progress` 交独立隔离复验，不要求先补丁。 [负责人处置及最新状态](story-2-2-review-disposition.md)

安装版 BMAD 6.12.4 `bmad-code-review` full。解析用 `uv run --no-cache --python D:/ttAPP/python.exe` 及独立临时目录。该安装的 Code Review 直接使用 SKILL 和 steps，无 `workflow.md` 渲染入口。激活无 prepend、append 或完成钩子。用户明确确认了范围检查点。四视角全部实际返回，受会话并发上限限制三路先启动，空位后启动第四路。没有调整模型或代填任何组员意见。

基线与 HEAD 均为 `930d3cb1c6ce02a934a93295b850c9109165dcf1`。冻结时 16 文件、+1437/−9、1616 行、108577 字节，SHA-256 `1C1FBE19A64987D687119B7957C99BB866C90DEC037016A4A8844B1D9BA20553`。含未跟踪的占用模板、Django 测试、PostgreSQL 探针、验证包装、规格和管理文档。四个既有日志及锁文件不纳入，已应用的入口补丁只做反向预检，退出 0，不重放。新原始运行目录单独审计。没有更改模型、迁移、权限策略、2.1 核心事务或后续 Story 路由。

独立读取并交叉核对 [AGENTS](../../AGENTS.md)、[课程基线](../../docs/course-requirements.md)、[正式 PRD](../planning-artifacts/PRD.md)、[Architecture](../planning-artifacts/architecture.md)、[project-context](../planning-artifacts/project-context.md)、[Epics](../planning-artifacts/epics.md)、[Sprint 计划](../planning-artifacts/sprint-plan.md)、[决策日志](../../decision-log.md)、[Sprint 状态](sprint-status.yaml)、[延期台账](deferred-work.md)、[实施规格](spec-2-2-query-equipment-occupancy.md)、[实施检查点](story-2-2-checkpoint-1.md)、[开发证据](story-2-2-dev-evidence.md)及原始运行目录。

## 正式 AC 独立核对

以下是独立源码和归档复核，不是独立实跑通过。

| AC | 裁决及依据 |
| --- | --- |
| 1 | 一致。北京时间半开自然日、目标设备、有效待审和进行中／未来已批准。10:30 保留 10:00–11:00 已批准占用，11:00 起仍显示原历史区间而非当前或未来占用。不计拒绝／取消／失效，不改历史口径。空闲补集按冻结规格扣除有效占用以及已列出的历史。新增 Django AC-1 用例复核了可控边界、分组和区间。 |
| 2 | 一致。到开始仍待审核的目标记录，包括已结束记录，先原子写失效和系统历史，再生成结果。已批准不变，重复不重写，设备和日期外无变化。查看真实 `frozen-due`、双向交错和 AC-2 测试。 |
| 3 | 一致。设备及日期稳定谓词固定 ID，不预排过期或未到点待审。必要时仅锁目标行，复查有效账号、设备、固定 ID，再采样一次 `clock_timestamp() AS decision_at`。比较实际 SQL 列引用、别名及绑定，不把字段别名当字段本体。无待审／无候选路径在另一连接持锁时照常返回，无额外设备写锁。 |
| 4 | 一致。合法新增 307 的实际阻塞 PID 为 3176，锁后首次绑定仅 306，第二次包含 306、307。到期旁路夹具 309 首次未处理，308 独立失效并留历史，次查只新增 309 的历史。提交先和查询先均有真实阻塞、独立读回及其他设备 201 对照。 |
| 5 | 一致。三角色详情有同一日期入口并保留各自原导航，真实 HTTP 查询均 200，不向任何角色投影他人身份、预约 ID、详情链接或原因。匿名、停用会话、等锁撤权为 302／302／403，均不取时、不写业务数据、不泄露占用。开发批次不是在 Chrome 中实际点击该控制，正式运行需区别取证。 |
| 6 | 一致。合法空日和收尾后空日 200，缺值、非法格式或日历日期 400，不存在设备 404，相关拒绝路径没有预约扫描、写锁和业务 DML。正常输入格式严格，重复日期参数的框架取末值行为不是已定义的正式 AC。 |
| 7 | 一致。设备可用／维修／停用、所选占用和最终可否提交分别展示，空日或过去日期不承诺可预约。真实响应 200 → 他人 201 → 原用户 409，持久化只留胜者。 |
| 8 | 一致。第二次历史 INSERT 23514、COMMIT 23505 均 503 明确失败并整体回滚；提交前断连和真实提交后模拟丢确认均 503 待核查，不渲染正常查询、不自动重试。真实独立读回分别证明未持久化与已持久化。第二历史 INSERT 日志绑定采样缺陷见 P1，不影响 SQLSTATE 和读回。 |

## 原始证据复算

- 开发归档中逐名复算 103 个唯一发现／执行测试，103 个通过、零跳过，一行 `OK`，耗时 21.853 秒。旧 D-040 91 个完全同名，新增 12 个。11 个阶段退出 0，system check 无问题，迁移漂移 dry-run 无 changes，探针 stderr 为 0 字节且唯一标记 `STORY22_PROBE_OK cases=21`。 [Django 原始回归](story-2-2-run-20261126-224427-552-98c04aee/regression.stderr.txt) · [阶段](story-2-2-run-20261126-224427-552-98c04aee/stages.txt)
- 原始 JSONL 23 行，21 个唯一案例加身份及清理。实际目标为 `lab_booking_test@127.0.0.1:5433/test_lab_booking`，PostgreSQL 17.12、Read Committed，角色无超额权限和正式库 CONNECT。三份基线字节相同，SHA-256 `5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272`。前后实际持久读回为 12 张表、19 条迁移、五受控表零行且读回摘要一致。不是全 schema、ACL 或序列指纹。JSONL SHA-256 为 `3DEB399ED4B3F49E6E82E1416F86817BFC0256D0A0B3ABFB8AB48D0205C0A9C8`。 [原始 JSONL](story-2-2-run-20261126-224427-552-98c04aee/independent.jsonl) · [基线](story-2-2-run-20261126-224427-552-98c04aee/baseline-before.json)
- 开发前后 79 份输入清单字节一致，清单 SHA-256 为 `14DA756307D52A468C90105406BABB9603B70D119A5AAAA5A499EFD149DA6D26`。本轮落评审记录前工作树重算匹配 78/79，唯一不同是自测后追加说明及更新状态的管理规格。规格的归档 hash 为 `9A36B00D5CE55254F1CCB95151B6192208127893B1F4408444EBC9CB3944228F`，落本轮记录前为 `6BF048CEC1FFF3392E5A1692D6E24566D042139442E4D6FFB03D17F19FA2DEBB`，全部业务、测试、脚本及正式 AC 文件匹配。未修改、回填或替换原清单。 [输入清单](story-2-2-run-20261126-224427-552-98c04aee/before.sha256)
- CRLF 单独核对。默认 Git 对跟踪文件报告 154 个行尾问题；只有单次调用设置 `cr-at-eol`，同时保留 `blank-at-eol,blank-at-eof,space-before-tab`，跟踪范围检查退出 0，新源码和测试无报告。新 Markdown 检查点第 38 行有真实空白缩进，不当成 CRLF 假阳性，不影响代码。没有改 Git 配置。
- 2.1 提交、本人结果及时间／锁／审计／数据库守卫核心未变。复算历史标准组 SHA-256 `3364EDF809D5F11C2E865C6608636C6A80FA16736D16C74CA4E1C759D9A7AEC1`，10 轮、每轮 20 个不同数据库 PID、真实并发重叠、1 个 201、19 个 409、1 条持久有效待审。复用 D-040 历史 NFR-001 标准证据，不重新等待整点，不计为新验证，不据此宣称全项目 NFR-002 完成。 [D-040 独立验收](story-2-1-targeted-independent-recheck/d040-independent-final-review.md)

## 运行交接

本项目原 .venv 的沙箱探测已有退出 103 记录，本轮不重试。新增 [独立隔离 PowerShell 入口](review-story-2-2-isolated.ps1) 仅委托原受保护运行器一次，明确不执行入口补丁、正式库、迁移、GRANT、NFR-001 或 Git 操作。文件已通过 PowerShell 语法解析，归档审计分支以内联 PowerShell 运行通过，未执行脚本的数据库分支。普通 PowerShell 新批次同时保存原退出码、原成功标记、独立目录及独立审计标记。

```powershell
& '.\_bmad-output\implementation-artifacts\review-story-2-2-isolated.ps1'
```

已有绝对路径不同才传 `-Passfile`、`-Chrome`、`-Psql`，不提交凭据。三位组员共同操作，先确认同一隔离库无其他验证入口运行。只运行一次，回传新目录和唯一 `STORY22_INDEPENDENT_REVIEW_RUN_OK`，失败保存实际错误不自动重跑。旧开发目录只可用 `-EvidenceDirectory` 做离线归档审计，标记为 `STORY22_ARCHIVE_AUDIT_OK`。

正式运行另行确认后才执行，不能复跑 Story 2.1 的迁移、授权或演示写入入口。先以既有 `lab_booking_app` 在允许的环境独立只读核对身份、版本、隔离级别、D-042 迁移和有效 ACL。检查别名及空 ACL 用经审核的 `CASE WHEN cardinality(...) > 0 THEN ... END`，不要向 `aclexplode` 传零维空数组。若与已验模型一致，无需新增迁移或 GRANT。旧权限覆盖账号启用／角色读、所需设备读列及设备行锁、预约 SELECT／状态 UPDATE、审计列 INSERT 与返回 ID。不要求表级扩权、DELETE、DDL 或新序列权限。 [正式 ACL 原始读回](story-2-1-targeted-independent-recheck/runtime-run-20261126-214810-493-1c23760f9bbc/acl.jsonl) · [D-042](story-2-1-final-acceptance.md)

以批准的已知设备和不会触发到期待审写入的日期，三业务角色从目录进详情、实际在 Chrome 选日提交、核对 URL 与日期，验证占用、空日、三层说明、如有历史则保留实际时段、返回详情及目录。合法对照和匿名分开，匿名跳转、无正文与无业务变化分别检查。选择测试日期前读回受控记录并留安全窗口。没有适当的正式数据就不造夹具，历史／混合场景以隔离库补证。记录启动源码散列、真实身份、请求状态、正文及前后业务读回。未知 503 或实际数据／ACL 漂移则停止并只读查证。正式库不做故障注入、竞争压测、补 GRANT 或迁移，本轮没有连接正式库或重启服务。

课程第 25、26、27、33、34、36 页按仓库课程要求和既有记录核对，原 PPT 未在工作区找到。保留可测试故事、FR／ADR／PC 到 AC 及证据追踪、独立会话和真实状态、原 8／5 及实验 A 条件、D-043 和实际检查点意见，不代写人工决定，不标 `done`，不提前开始 2.3、管理员管理、审批或取消，也未 commit/push。

[逐条裁决](story-2-2-review-triage.md) · [实施规格中的待办](spec-2-2-query-equipment-occupancy.md#review-findings)
