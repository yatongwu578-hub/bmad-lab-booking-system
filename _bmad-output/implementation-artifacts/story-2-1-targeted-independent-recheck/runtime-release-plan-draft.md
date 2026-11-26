# Story 2.1 · 正式库迁移、最小权限与浏览器验证提案

**静态核对稿，不是发布批准，也不是正式库实测。** 本轮不连接正式库，不执行迁移、GRANT、账号或预约写入，不启动或停止正式服务。待独立复验、负责人明确审批后，三人共同操作并留原始证据。未实测的项目不得预填通过。

## 发布前检查与迁移顺序

1. 固定获批版本和窗口，备份并核对恢复方案。分别核对迁移与运行的本机连接目标，均为 `127.0.0.1:5433/lab_booking`、PostgreSQL 17.12。迁移会话的 `session_user` 与 `current_user` 均为 `lab_booking_migrator`，运行会话均为 `lab_booking_app`。数据库名、`pg_catalog.host(pg_catalog.inet_server_addr())`、端口、`server_version_num`、明确的 `public` 首要搜索模式、Read Committed、对象所有者及两角色权限都须实际核对。保持受保护的独立 passfile，不输出其内容。禁止沿用测试账号、从环境覆盖 host/port、或依赖未确认的 search_path。
2. 从原项目 .venv 的 migration 模式运行只读计划并检查应用顺序。预期仅 `reservations.0001_initial` 和 `audit.0001_initial`。如果计划已空，先核对登记、DDL 和 R-04 约束，不把 no-op 充当初迁，不重复运行。任意额外/逆向迁移、对象与登记不一致、中断后部分完成或权限/对象所有者异常，都停止并记录。正式执行另批后由 Django 迁移入口按依赖应用，不直接粘贴历史 `sqlmigrate` 输出。历史 SQL 用于静态审查，不代替目标库核对。 [Django 5.2 管理命令](https://docs.djangoproject.com/en/5.2/ref/django-admin/#sqlmigrate)
3. 对照最初的 [预约生成 SQL](../story-2-1-run-20261126-171347-146-27af94f2/reservation-sql.stdout.txt) 和 [审计生成 SQL](../story-2-1-run-20261126-171347-146-27af94f2/audit-sql.stdout.txt)，两表含主键 identity，预约 begin/end 为带时区，审计有真正的预约／设备外键和匹配对象 CHECK。目录验证至少含实际列、类型、可空性、identity、全部主键／外键／检查约束、引用目标、索引及所有者，不能用表清单或迁移登记代替。核对旧表及行摘要符合备份。发现提交结果未知时先只读回查，不自动重放。
4. 按获批策略处理部分发布：迁移失败检查退出码并停。恢复旧应用时不要随手逆向删除预约或历史；若表已承载业务数据，按另外批准的备份与恢复方案执行。

## 最小权限与双向比对

下列语句只是**待审候选的新增列 ACL**。每条为白名单，不给 `GRANT OPTION`，不加表级权限、角色成员关系或序列权限。现有账号和设备权限只核对，不重授或扩大。预约设备读取、账号重读及设备锁沿用既有权限。锁至少需要一列可 UPDATE，现有设备四列基础更新可满足，不需要新增设备状态更新。审计只能写实际 INSERT 投影，并允许 `SELECT (id)` 支持 `RETURNING id`。identity 不是本方案批准序列额外权限的依据，若实际运行提示不符先查生成 SQL 和数据库对象。 [SELECT 行锁](https://www.postgresql.org/docs/17/sql-select.html) · [INSERT / RETURNING](https://www.postgresql.org/docs/17/sql-insert.html) · [Identity](https://www.postgresql.org/docs/17/ddl-identity-columns.html)

```sql
GRANT SELECT (id, applicant_id, equipment_id, start_at, end_at, status, applied_at)
ON TABLE public.reservations_reservation TO lab_booking_app;

GRANT INSERT (applicant_id, equipment_id, start_at, end_at, status, applied_at),
      UPDATE (status)
ON TABLE public.reservations_reservation TO lab_booking_app;

GRANT INSERT (object_type, reservation_id, equipment_id, action, before_status, after_status,
              actor_type, actor_id, reason, decision_at, recorded_at),
      SELECT (id)
ON TABLE public.audit_operationhistory TO lab_booking_app;
```

前后执行**同样的双向比较**。授权前先读原始 ACL（包括 PUBLIC、列 ACL、继承关系和表所有者），并比较实际有效权限。若正好已是目标模型，跳过授权。若为预期的全空新增 ACL 且有效权限不存在额外授权，再进入只执行一次的获批授权批次。若只具备部分或检测到额外有效权限，停止并单独确认缺口和修订方案，不成批重复授予，不临时把权限放大。后置断言不通过则不提交。授权前后检查放在同一事务中，使用 `psql -X -w`、`ON_ERROR_STOP=1` 和 `--single-transaction`；不要在其输入里再嵌套 BEGIN/COMMIT，不要假设普通 SELECT 的 `false` 会停止事务。执行稿须在异常分支明确以事务错误失败，从而回滚，不能只打印一个不匹配结果然后继续。 [PostgreSQL GRANT](https://www.postgresql.org/docs/17/sql-grant.html) · [psql 单事务与退出码](https://www.postgresql.org/docs/17/app-psql.html)

以下为两张新表存在后、经授权的**只读比对查询**。查询不含 PL/pgSQL，没有变量／列名解析歧义，表别名和列均限定。目标仅按下面精确列集合取值。须先确认本次查询列集合与预期对象一致，而非将零结果当成功。前后预期差由 `expected_after` 与 `effective` 逐行比较。

```sql
WITH wanted(table_name, operation, col_names) AS (
  VALUES
    ('reservations_reservation', 'SELECT',
      ARRAY['id','applicant_id','equipment_id','start_at','end_at','status','applied_at']),
    ('reservations_reservation', 'INSERT',
      ARRAY['applicant_id','equipment_id','start_at','end_at','status','applied_at']),
    ('reservations_reservation', 'UPDATE', ARRAY['status']),
    ('audit_operationhistory', 'SELECT', ARRAY['id']),
    ('audit_operationhistory', 'INSERT',
      ARRAY['object_type','reservation_id','equipment_id','action','before_status','after_status',
            'actor_type','actor_id','reason','decision_at','recorded_at'])
), objects AS (
  SELECT c.oid, c.relname::text AS relation_name, c.relowner
  FROM pg_catalog.pg_class AS c
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relkind = 'r'
    AND c.relname IN ('reservations_reservation','audit_operationhistory')
), operations(operation) AS (
  VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')
)
SELECT o.relation_name, pg_catalog.pg_get_userbyid(o.relowner) AS object_owner,
       a.attname AS column_name, q.operation,
       COALESCE(a.attname::text = ANY(w.col_names), false) AS expected_after,
       pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, o.oid, a.attnum, q.operation) AS effective,
       pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, o.oid, a.attnum,
                                       q.operation || ' WITH GRANT OPTION') AS can_delegate
FROM objects AS o
JOIN pg_catalog.pg_attribute AS a ON a.attrelid = o.oid AND a.attnum > 0 AND NOT a.attisdropped
CROSS JOIN operations AS q
LEFT JOIN wanted AS w ON w.table_name = o.relation_name AND w.operation = q.operation
ORDER BY o.relation_name, a.attnum, q.operation;
```

另外逐表检查 `has_table_privilege` 的 SELECT、INSERT、UPDATE、DELETE、TRUNCATE、REFERENCES、TRIGGER、MAINTAIN 及转授权全部为假，避免表级宽权限伪装成有效列权限。检查应用角色不拥有对象、无超额角色属性，不是迁移角色成员；现有 `public` USAGE 和四个设备基础列更新按已批准历史范围，不修改。另开实际运行角色的只读连接复核提交后 ACL，并保留执行前后实际计数与有效权限。提交不明先只读复核。 [PostgreSQL 权限查询函数](https://www.postgresql.org/docs/17/functions-info.html)

## 获批后的真实 Chrome 运行验证

- 先核对已批准的端口及正在监听的进程。若 8001 被占用，只有在确认确切解释器、工作目录、监听进程父子关系、运行模式及已加载版本后，才复用正确版本或获批滚动替换。已有服务是否读取当前源码不能只靠文件散列或 PID 推断。不认识的监听不终止、不关闭其它端口、不覆盖旧日志。新的备用端口须先确定未占用并获批，且只绑定 `127.0.0.1`，不盲目换端口。
- 由授权的只读操作先核对批准的既有演示设备、轮次和账号，取数据库当前北京时间。为师生选择将来同日、整点、至少一小时且不晚于 23:00 的不相交时段，用半开区间及有效状态规则预查无冲突。记录所批准的测试数据保留方式。若设备不可用、演示流水已存在或期间有并发占用，停下核对，不能清库、删生产数据、重放预置或用正式 SQL 直接创建测试夹具。正式 POST 仍受事务内实际冲突检查约束。
- 用独立 Chrome 会话由登录、身份、设备目录、详情、表单和本人结果顺序进入。验证师生的 400→同页改正→201 和本人 200 确认。做一次预先批准的同设备重叠请求并验证明确 409 无新记录、另一账号的同角色异主直接访问得 404 无泄露、管理员无提交入口并在直达时被拒。成功在只读观察侧核对记录号、账号归属、设备和时段。若已有获准且自然到期的本人待审，按同一路径验证一次合法失效及历史；若缺少合规对象，不在正式库造已到期夹具，不等待或标已验证，该项隔离库证据单列。
- 保存版本、实际连接身份、ACL 对照、批准的脱敏示例标识、真实 HTTP 原始记录、运行退出码以及独立前后快照。不得输出登录密码、连接密码、CSRF 或会话 cookie。不在正式库运行故障注入或 20×10 压测；本轮例行独立复验也不等待新整点。
