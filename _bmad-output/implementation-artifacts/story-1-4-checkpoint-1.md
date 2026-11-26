# Story 1.4 Checkpoint 1

2026-11-25，BMAD 6.12.4 Build Step 2。 [实施规格](spec-1-4-edit-equipment-basics.md)

## 已核对

- 本地 `main` 与本地 `origin/main` 引用均为 `e200fee335536941e0705c112aefbf6751b244c3`，开始时工作树干净。Sprint 中 1.1～1.3 全为 `done`，1.4 为 `backlog`，Epic 1 为 `in-progress`。2.1 与其余后续 Story 未启动。 [Sprint 跟踪](sprint-status.yaml) · [Git 基线](https://github.com/yatongwu578-hub/bmad-lab-booking-system/commit/e200fee335536941e0705c112aefbf6751b244c3)
- 依据仓库工作约定、课程要求、正式 PRD、Architecture、项目约束、Epics、Sprint 计划、根目录决策日志与延期台账。承接已完成的账号、设备、查询与隔离设施，不改需求、架构、冲刺或原延期裁决。正式 AC 只采用 Epics 中 1.4 的八条。 [工作约定](../../AGENTS.md) · [课程要求](../../docs/course-requirements.md) · [PRD](../planning-artifacts/PRD.md) · [Architecture](../planning-artifacts/architecture.md) · [项目约束](../planning-artifacts/project-context.md) · [Epics](../planning-artifacts/epics.md#story-14-管理员维护设备基础信息并保护设备身份) · [Sprint 计划](../planning-artifacts/sprint-plan.md) · [决策日志](../../decision-log.md) · [延期台账](deferred-work.md)
- 官方渲染使用既有 `D:/ttAPP/python.exe`（仅 BMAD）、独立临时目录供 uv 使用，退出 0，指向受原渲染器校验的 `13340bf8aef33bedeff3/workflow.md` 快照。未改渲染源或旧缓存。
- 原 `.venv` 存在，`pyvenv.cfg` 指向 Python 3.13.17。受限执行版本命令退出 103，密码文件路径探测报拒绝访问；只申请了原 `.venv\Scripts\python.exe --version` 的具体执行授权，`sandbox_approval: false` 自动拒绝，没有弹窗。历史证据已证明原解释器可用，不能把本次受限失败判为未安装。未重装、未重建、未连接数据库、实际执行测试 0 项。历史隔离回归 55/55 无跳过不代表本轮结果。 [1.3 独立复审](story-1-3-independent-recheck.md)

## 验证设计

- **AC-6／T-01**。初态为可用，管理员取得旧表单。A 使用隔离夹具与独立事务锁定同一行、改为维修或停用。B 从旧表单只提交四个合法字段。分别验证 A 已提交再发 B，以及 B 在 A 提交前发出且由观察连接证实阻塞于 A。A 提交放行后，B 必须锁后重读并成功更新四列。观察连接读取完整末态，主键、编号、总数及无关设备不变，状态保持 A 的提交。检查 SQL 顺序及 UPDATE 列。没有预约／历史模型，以无相关路由、调用或 SQL 取证，不伪造表或计数。
- **AC-4／T-03**。对编辑路由冻结六类未授权请求（匿名、学生、教师各 GET/POST），给 POST 配上有效 CSRF，分离角色与中间件拒绝原因。逐次断言拒绝、无编辑模板内容或设备数据泄露、设备全字段与总数不变。另测管理员缺失、错配 CSRF，各自不写；管理员合法 GET 与有效令牌 POST 单列。计划分母不是实测结果。
- **AC-8**。沿用 Story 1.2 最外层提交及回滚检查。通过真实编辑入口与服务验证写入后回滚、明确 COMMIT 拒绝、COMMIT 前断连及真实提交后丢确认，记录阶段、写入/COMMIT 尝试和独立回读。两种断连都提示待核查，数据库末态可以不同。回滚式 TestCase 不作为实际提交证据。各独立连接先核实库、角色、地址、版本及 Read Committed，再操作当次专属夹具；使用有限等待，在 `finally` 清理当次夹具并核对前后状态。不放开既有 flush 守卫。 [Story 1.2 独立复审](story-1-2-independent-recheck.md)

## 正式库最小授权候选

D-026 与 D-030 的实际核验记录表明，`lab_booking_app` 对设备表有七列 SELECT 和原六列 INSERT，在已核验基线没有 UPDATE。行锁也需要至少一列 UPDATE 权限，拟写入的四列 UPDATE 已满足这个前提，不需为锁另扩权限。现况结论来自留档，不是在本轮重查业务库。 [业务库授权留档](story-1-3-runtime-evidence.md#授权边界与结果) · [PostgreSQL 17 SELECT 权限](https://www.postgresql.org/docs/17/sql-select.html)

```sql
GRANT UPDATE (name, category, location, description)
ON TABLE public.equipment_equipment TO lab_booking_app;
```

仅供另批后执行。届时由原表所有者以单事务核对目标、角色、版本、对象归属及有效权限，若漂移即停止。前后校验四列 UPDATE、既有读写权限不变，及编号、状态、主键不可由该角色 UPDATE。不得授予表级 UPDATE、DELETE、TRUNCATE、DDL 或转授权，不改测试角色。此次没有连接正式库或执行 GRANT。

## 课程与人工检查点

第 26 页按 FR→ADR／PC→正式 AC→计划证据复核一致性。第 27 页保留真实 Story 状态，开发自测后停在 review 交独立会话。第 33 页保留规格、测试、状态及对应 Git 基线证据。第 34 页实验 A 条件不变，1.4 不记入对照。第 36 页等实际人工决定再登记，不预写审批。PPT 原件未在本次仓库核验中找到，页码按课程基线及已归档团队记录执行。三位组员共同操作与审阅，不另派个人任务。

规格无未决需求，建议批准并继续。当前环境访问缺口阻止测试验证，不阻止批准规格。要继续到 review，需先让具体安全命令可在原解释器和隔离测试库执行，或由团队在本机按同样边界运行并提供原始输出。正式库授权与最终验收不是本检查点的批准对象。目前只新增规格和本记录，未改业务代码、Sprint 状态或决策日志，未提交或推送。
