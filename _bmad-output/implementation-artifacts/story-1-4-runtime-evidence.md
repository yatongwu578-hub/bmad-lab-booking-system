# Story 1.4 正式库运行证据与验收核对

2026-11-26 11:46，D-035 的正式库授权及本机运行门槛 W1 已取得证据，当时仍等待负责人最终验收。负责人随后按 D-036 正式批准，规格和 Sprint 中的 Story 1.4 现为 `done`。这没有改变以下真实运行时间、输出和结论。 [最终验收](story-1-4-final-acceptance.md) · [Sprint 状态](sprint-status.yaml) · [收尾清单](story-1-4-closeout-checklist.md)

## 真实运行及证据来源

团队在普通 PowerShell 执行，原汇总自报操作者为 `w`。只读 ACL 批次为 11:46:02.049～11:46:02.219，运行恢复为 11:46:02.262～11:46:13.297，均为 +08:00。核验本轮只读解析日志并重算散列，未连接数据库、打开浏览器、重跑测试或重新授权。不推断其他成员的个人参与，也不把团队运行说成 Codex 执行。

| 历史步骤 | 已核对的原始输出 |
| --- | --- |
| 10:56 首次调用 | `django_migrations.app` 歧义，psql 退出 3。单事务在 GRANT 前中止，运行未启动。 [原始错误](story-1-4-runtime-run-20261126-105606-102/acl-raw.txt) · [原始汇总](story-1-4-runtime-run-20261126-105606-102/run-summary.txt) |
| 11:20 授权及中止 | [授权前只读](story-1-4-runtime-acl-check-20261126-112028-049/acl-raw.txt) 为 `NOT_GRANTED`。[授权](story-1-4-runtime-run-20261126-112028-249/acl-raw.txt) 有阶段矩阵、`D035_ACL_ASSERTIONS_PASSED` 及退出 0，随后 [业务角色新连接只读回读](story-1-4-runtime-run-20261126-112028-249/runtime-acl-readback.txt) 退出 0，证明提交。8001 服务启动保留。原 Chrome 工具因类别拟改值等于原值退出 1，在启动浏览器和发出任何编辑请求之前停止。 [Chrome 中止](story-1-4-runtime-run-20261126-112028-249/chrome-db-raw.txt) · [原始汇总](story-1-4-runtime-run-20261126-112028-249/run-summary.txt) |
| 11:46 恢复时只读 ACL | `lab_booking_migrator` 在 PostgreSQL 17.12、`127.0.0.1:5433/lab_booking` 核对对象所有者、入口和权限，`D035_ACL_STATE=GRANTED`、只读 `COMMIT`、退出 0。有效继承角色为空，矩阵等同 11:20 的授权后阶段。 [原始 ACL](story-1-4-runtime-acl-check-20261126-114602-047/acl-raw.txt) · [汇总](story-1-4-runtime-acl-check-20261126-114602-047/run-summary.txt) |
| 11:46 运行恢复 | 汇总确认 `-RuntimeOnly` 跳过 GRANT，应用角色只读快照退出 0，Chrome 批次退出 0，唯一最终标记为 `result=passed`。复用原虚拟环境 Python 3.13.17 的项目服务，根进程 39000，监听 5364，未新启服务。 [汇总](story-1-4-runtime-run-20261126-114602-260/run-summary.txt) · [服务身份](story-1-4-runtime-run-20261126-114602-260/service-identity.txt) · [独立 ACL 读回](story-1-4-runtime-run-20261126-114602-260/runtime-acl-readback.txt) · [Chrome 原始日志](story-1-4-runtime-run-20261126-114602-260/chrome-db-raw.txt) |

角色 `lab_booking_app` 仅 `name / category / location / description` 的 UPDATE 有效。主键、设备编号、状态的 UPDATE 均无，原七列 SELECT 和不含主键的六列 INSERT 不变。原权限断言同时拒绝表级权限（含 UPDATE、DELETE）、列级再授权、额外序列权限，以及角色和 public schema／数据库 CREATE 等扩张。恢复没有重复授权、迁移或触碰 5432。

只读批次的 2 项工具散列和运行批次的 9 项输入散列已对应当前文件及历史证据逐条重算，运行前后清单字节一致。11:46 业务角色启动回读与 11:20 快照的散列亦相同。隔离复验前后 53 项清单一致并逐项匹配当前文件。 [ACL 输入清单](story-1-4-runtime-acl-check-20261126-114602-047/inputs.sha256) · [运行前清单](story-1-4-runtime-run-20261126-114602-260/inputs.sha256) · [运行后清单](story-1-4-runtime-run-20261126-114602-260/inputs.after.sha256) · [隔离复验汇总](story-1-4-independent-remediation-20261126-103026-904-00f7bfce/independent-summary.txt)

## Chrome 与独立数据库回读

真实 Chrome 159.0.8154.34 在 8001 上操作。失败用例逐例由新的业务角色只读连接回读。管理员按页面实际表单提交了恰好一次正常编辑，详情渲染和回读一致。12 个 Chrome 分阶段数据库快照均核对了目标身份、版本及 Read Committed。

| 用例 | 真实结果 |
| --- | --- |
| 匿名 GET／POST | 302／302，正确引导登录，未见受限内容，设备整行不变 |
| 学生 GET／POST | 403／403，未见受限内容，设备整行不变 |
| 教师 GET／POST | 403／403，未见受限内容，设备整行不变 |
| 管理员伪造编号、伪造状态 | 各 400，有相应字段保护提示，设备整行不变，无部分保存 |
| 管理员合法对照 | 表单 200，POST 302 回原详情，详情 200，四字段与独立回读一致 |

| 设备基础字段 | 编辑前 | 编辑后 |
| --- | --- | --- |
| 名称 | 课程演示设备 | 课程演示设备 · Story 1.4 |
| 类别 | 课程演示 | 课程设备 · Story 1.4 |
| 位置 | 课程演示区 | 实验室演示区 |
| 说明 | 软件工程管理课程 Story 1.2 演示档案，可保留。 | Story 1.4 基础资料编辑验证，仅用于课程演示 |

主键 `1`、唯一编号 `EQ-DEMO-S12-20261125`、状态 `available` 不变。设备总数 1、迁移记录 17、其它设备摘要不变，退出后会话数回到初始 1。登录入口为 `http://127.0.0.1:8001/login/`，验证过的详情和管理编辑路径分别为 `/equipment/1/` 和 `/equipment/1/edit/`。不要为截图或补证重复提交。

## 正式 AC-1～AC-8

[正式 AC](../planning-artifacts/epics.md#story-14-管理员维护设备基础信息并保护设备身份)对应 FR-016／FR-002、ADR-002／003／006／008 和 D-024 的 Read Committed 协议。隔离复验在批准的 `test_lab_booking` 留证 **68/68 Django、10/10 真实 PostgreSQL 探针、1/1 Q-3（两种传输）**，无跳过。团队按独立评审委托实跑，独立评审核验。同一套件的开发自测、正式库 Chrome 与此处隔离复验不相加。 [隔离原始输出](story-1-4-remediation-run-20261126-103027-319/raw.txt) · [专项原始输出](story-1-4-independent-remediation-20261126-103026-904-00f7bfce/q3-raw.txt) · [四视角独立复审](story-1-4-targeted-independent-recheck.md#2026-11-26-独立复验结果)

| AC | 验收证据核对 |
| --- | --- |
| AC-1 | 正式 Chrome 四字段实际更新，原设备身份、状态、数量不变，详情与读库一致。隔离 R2 新说明空白和换行保真、自动转义及 Q-3 已有 CRLF 字节不变。 |
| AC-2 | 编号只读，正式伪造返回 400 且整行不变。隔离 PostgreSQL 唯一约束真实拒绝重复编号。 |
| AC-3 | 正式伪造状态返回 400、整行不变。隔离三种原状态间六种伪造均被整笔拒绝，无状态、预约或历史处理。 |
| AC-4 | 正式 Chrome 六例角色拒绝，无泄露、无业务变化，合法管理员单列。隔离 T-03 也为 6/6，缺失／错配 CSRF 各 403 并单列。R1 两个等锁撤权／停用探针均锁后复核并返回 403、未写入。 |
| AC-5 | 隔离管理员 GET、合法 POST 及含非法字段的 POST 对不存在设备均为 404，无新增、无替换、无其它设备变动。未在正式库重复。 |
| AC-6 | 隔离实际 SQL 证实短事务锁后重读、仅更新四列。T-01 4/4，维修、停用各有一次真实等待，旧表单不覆盖最新状态。正式库只验证普通更新及 Read Committed。 |
| AC-7 | 隔离拒绝删除方法、无物理删除路由与表单动作。正式浏览器原位更新，主键、编号、设备数量不变，ACL 无 DELETE。 |
| AC-8 | 隔离异常探针 4/4。确认回滚或明确拒绝返回失败且不部分保存。提交前断连、提交后丢确认均为待核查、不自动重试，独立回读分别为原值、新值。正式库未做故障注入。 |

W1 发布验证证据已满足，并由负责人作为 D-036 最终验收依据接受。R1／R2／R7／Q-3 已由 D-035 关闭，Q-1／Q-2、R3～R6、W2 和项目级延期不重新裁决。只覆盖 Story 1.4 编辑入口的 NFR-002 部分，不能据此宣称全项目 NFR-002 或 NFR-001 已完成。正式库运行证据不计入实验 A。
